#!/usr/bin/env python3
"""Multiscale sweep: fibre network -> tissue -> cell tensegrity/YAP -> organ read-outs.

  python3 run_sweep.py --profile local            # laptop CPU, ~20 min
  python3 run_sweep.py --profile gpu --device cuda  # Nebius / Brev H100 job

Outputs land in results/<profile>/: network.csv, failure.csv, tissues.csv, cell.csv, organ.csv,
transport.csv, summary.json.  make_figures.py turns them into figures.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent

PROFILES = {
    "smoke": dict(W=8, seeds=1, batch=16, workers=4, threads=1, z=[3.4, 4.6], doses=[1.0],
                  gammas=[0.01, 0.1, 0.3], fail=[0.05, 0.2, 0.4], ages=[20, 80], clutch_T=8.0),
    "local": dict(W=12, seeds=2, batch=6, workers=6, threads=2,
                  z=[3.0, 3.6, 4.4], doses=[0.5, 1.0],
                  gammas=[0.005, 0.03, 0.1, 0.2, 0.35],
                  fail=list(np.round(np.linspace(0.04, 0.6, 9), 3)),
                  ages=[20, 50, 80], clutch_T=40.0),
    "cpu32": dict(W=16, seeds=4, batch=4, workers=30, threads=1,
                  z=[2.8, 3.0, 3.2, 3.4, 3.6, 4.0, 4.4, 5.0], doses=[0.25, 0.5, 0.75, 1.0],
                  gammas=[0.005, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4],
                  fail=list(np.round(np.linspace(0.03, 0.6, 16), 3)),
                  ages=[20, 35, 50, 65, 80], clutch_T=80.0),
    "gpu": dict(W=48, seeds=8, batch=64, workers=1, threads=8,
                z=list(np.round(np.linspace(2.6, 5.4, 15), 2)), doses=[0.1, 0.2, 0.35, 0.5, 0.75, 1.0],
                gammas=[0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5],
                fail=list(np.round(np.linspace(0.02, 0.8, 40), 3)),
                ages=[10, 20, 30, 40, 50, 60, 70, 80, 90], clutch_T=120.0),
}


# ---------------------------------------------------------------------------------------------------
# worker
# ---------------------------------------------------------------------------------------------------
def _worker(task):
    import torch

    torch.set_num_threads(task["threads"])
    from oxt.materials import COLLAGENS, TISSUES, Damage, build_spec, load_crosslink_overrides, tissue_spec
    from oxt.network import Batch, Lattice, coordination, mesh_size

    load_crosslink_overrides()
    lat = Lattice(task["W"])
    specs = []
    for it in task["items"]:
        rng = np.random.default_rng(it["seed"])
        if it.get("tissue"):
            s = tissue_spec(lat, TISSUES[it["tissue"]], it["age"], rng)
        else:
            s = build_spec(lat, COLLAGENS[it["collagen"]], Damage(it["mode"], it["dose"]), rng,
                           z=it["z"], mu_el=it.get("mu_el", 0.0), k_gag=it.get("k_gag", 1e-6))
        s.meta.update(seed=it["seed"])
        specs.append(s)
    b = Batch(lat, specs, device=task["device"])
    rows = [dict(**s.meta, z=coordination(s, lat), mesh=mesh_size(s, lat), bonds=int(s.alive.sum()))
            for s in specs]
    t0 = time.time()
    if "moduli" in task["protocols"]:
        m = b.small_strain_moduli()
        for i, r in enumerate(rows):
            r.update(G=m["G"][i], Cx=m["Cx"][i], Cy=m["Cy"][i])
    if "shear" in task["protocols"]:
        b2 = Batch(lat, specs, device=task["device"])
        sc = b2.shear_curve(task["gammas"])
        for i, r in enumerate(rows):
            r.update({f"sig_g{g}": sc[i, k] for k, g in enumerate(task["gammas"])})
    if "failure" in task["protocols"]:
        b3 = Batch(lat, specs, device=task["device"])
        sig, brk = b3.failure_curve(task["fail"], axis=0)
        for i, r in enumerate(rows):
            r.update({f"fail_e{e}": sig[i, k] for k, e in enumerate(task["fail"])})
            r.update({f"brk_e{e}": int(brk[i, k]) for k, e in enumerate(task["fail"])})
            k = int(np.argmax(sig[i]))
            r.update(strength=float(sig[i, k]), strain_at_peak=float(task["fail"][k]),
                     toughness=float(np.trapz(np.clip(sig[i], 0, None), task["fail"])))
    for r in rows:
        r["seconds"] = time.time() - t0
    return rows


def run_tasks(items, protocols, P, device, label):
    tasks = []
    for k in range(0, len(items), P["batch"]):
        tasks.append(dict(items=items[k:k + P["batch"]], protocols=protocols, W=P["W"], device=device,
                          threads=P["threads"], gammas=P["gammas"], fail=P["fail"]))
    print(f"[{label}] {len(items)} systems in {len(tasks)} batches", flush=True)
    rows = []
    if P["workers"] > 1 and device == "cpu":
        with ProcessPoolExecutor(P["workers"]) as ex:
            for n, out in enumerate(ex.map(_worker, tasks)):
                rows += out
                print(f"[{label}] batch {n + 1}/{len(tasks)} done ({out[0]['seconds']:.0f}s)", flush=True)
    else:
        for n, t in enumerate(tasks):
            out = _worker(t)
            rows += out
            print(f"[{label}] batch {n + 1}/{len(tasks)} done ({out[0]['seconds']:.0f}s)", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------------------------------
def configs(P):
    out = [("none", 0.0)]
    for mode in ("iso", "aniso"):
        out += [(mode, d) for d in P["doses"]]
    return out


def stage_network(P, device):
    from oxt.materials import COLLAGENS

    items, fail_items = [], []
    for col in COLLAGENS:
        for z in P["z"]:
            for mode, d in configs(P):
                for s in range(P["seeds"]):
                    items.append(dict(collagen=col, z=z, mode=mode, dose=d, seed=1000 + s))
        for mode, d in configs(P):
            for s in range(P["seeds"]):
                fail_items.append(dict(collagen=col, z=COLLAGENS[col].z, mode=mode, dose=d, seed=2000 + s))
    net = run_tasks(items, ["moduli", "shear"], P, device, "network")
    fail = run_tasks(fail_items, ["moduli", "shear", "failure"], P, device, "failure")
    return net, fail


def stage_tissues(P, device):
    from oxt.materials import TISSUES

    items = [dict(tissue=t, age=a, seed=3000 + s) for t in TISSUES for a in P["ages"] for s in range(P["seeds"])]
    return run_tasks(items, ["moduli", "shear", "failure"], P, device, "tissues")


def secant_curves(df, gammas, S_pa):
    """E_sec(gamma) = 3 * sigma(gamma)/gamma (incompressible), with E(0) = 3G."""
    strain = np.array([0.0] + list(gammas))
    E = np.stack([3 * df["G"].to_numpy()] + [3 * df[f"sig_g{g}"].to_numpy() / g for g in gammas], 1)
    return strain, np.clip(E, 1e-9, None) * S_pa


def stage_cell(fail, tissues, P, S_pa, seed=0):
    from oxt.cell import CellModel, ClutchParams, MatrixCurve, nuc_cyto_ratio

    groups = []
    g1 = fail.groupby(["collagen", "mode", "dose"], as_index=False).mean(numeric_only=True)
    g1["source"] = "collagen"
    g2 = tissues.groupby(["tissue", "age"], as_index=False).mean(numeric_only=True)
    g2["source"] = "tissue"
    df = pd.concat([g1, g2], ignore_index=True)
    strain, E = secant_curves(df, P["gammas"], S_pa)
    curve = MatrixCurve(strain, E, df["strain_at_peak"].to_numpy())
    cm = CellModel(curve, ClutchParams(T=P["clutch_T"]), seed=seed)
    lo = cm.steady_state(np.ones(len(df)))
    hi = cm.steady_state(np.full(len(df), 2.5))
    rate, slope = cm.recovery_rate(lo["M"], lo["Y"])
    out = df[["source", "collagen", "mode", "dose", "tissue", "age", "G", "strain_at_peak"]].copy()
    out["E_lin_Pa"] = E[:, 0]
    for k in ("Y", "M", "prestress_ratio", "k_anchor", "E_loc", "height", "strut_load", "mc_F", "mc_rho",
              "mc_v", "mc_strain", "mc_torn", "mc_traction_entropy_bits", "mc_entropy_prod_kB_per_s"):
        out[k] = lo[k]
    out["Y_from_high"] = hi["Y"]
    out["bistable"] = np.abs(hi["Y"] - lo["Y"]) > 0.15
    out["YAP_NC"] = nuc_cyto_ratio(lo["Y"])
    out["recovery_rate_per_h"] = rate
    out["dY_dM"] = slope
    # self-support: the cell holds >= half its rigid-anchor prestress and does not tear its matrix
    out["self_supporting"] = (lo["prestress_ratio"] >= 0.5) & ~lo["mc_torn"].astype(bool)
    return out


def stage_organ(tissues, P, S_pa):
    from oxt.materials import TISSUES, tissue_dose
    from oxt.physio import MOLECULES, heart, matrix_recovery_rate, phi_collagen, pwv, transport

    g = tissues.groupby(["tissue", "age"], as_index=False).mean(numeric_only=True)
    g["E_lin_Pa"] = 3 * g["G"] * S_pa
    rows, trows = [], []
    young = {t: g[(g.tissue == t)].sort_values("age").iloc[0] for t in TISSUES}
    for _, r in g.iterrows():
        t = TISSUES[r.tissue]
        y = young[r.tissue]
        Er = r.E_lin_Pa / y.E_lin_Pa
        row = dict(tissue=r.tissue, age=r.age, dose=tissue_dose(t, r.age), E_lin_Pa=r.E_lin_Pa, E_ratio=Er,
                   strength=r.strength, toughness=r.toughness, strain_at_peak=r.strain_at_peak,
                   anisotropy=r.Cx / max(r.Cy, 1e-12),
                   matrix_recovery_per_yr=matrix_recovery_rate(t.half_life_yr, tissue_dose(t, r.age)))
        rows.append(row)
        dens = r.bonds / y.bonds
        for mol in MOLECULES:
            tr = transport(mol, phi_collagen(dens, 0.15), 0.02 if t.k_gag < 1e-3 else 0.06,
                           tissue_dose(t, r.age), t.thickness_um)
            trows.append(dict(tissue=r.tissue, age=r.age, molecule=mol, **tr))
    organ = pd.DataFrame(rows)
    # heart: myocardial matrix + arterial stiffening at the same age
    hrows = []
    for a in sorted(organ.age.unique()):
        myo = organ[(organ.tissue == "myocardium") & (organ.age == a)].iloc[0]
        art = organ[(organ.tissue == "artery_media") & (organ.age == a)].iloc[0]
        myo_y = organ[(organ.tissue == "myocardium")].sort_values("age").iloc[0]
        h = heart(myo.E_ratio, myo.E_lin_Pa / 1e3 * 10, myo_y.E_lin_Pa / 1e3 * 10, pwv(art.E_ratio) / pwv(1.0))
        hrows.append(dict(age=a, PWV_m_s=pwv(art.E_ratio), **h))
    return organ, pd.DataFrame(trows), pd.DataFrame(hrows)


# ---------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="local", choices=PROFILES)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--stages", default="network,tissues,cell,organ")
    ap.add_argument("--out", default=None)
    ap.add_argument("--E-dermis-young-pa", type=float, default=2000.0,
                    help="calibration: Young's modulus assigned to young dermis matrix")
    args = ap.parse_args()
    P = PROFILES[args.profile]
    out = Path(args.out or ROOT / "results" / args.profile)
    out.mkdir(parents=True, exist_ok=True)
    stages = args.stages.split(",")
    t0 = time.time()

    if "network" in stages:
        net, fail = stage_network(P, args.device)
        net.to_csv(out / "network.csv", index=False)
        fail.to_csv(out / "failure.csv", index=False)
    else:
        net, fail = pd.read_csv(out / "network.csv"), pd.read_csv(out / "failure.csv")
    if "tissues" in stages:
        tis = stage_tissues(P, args.device)
        tis.to_csv(out / "tissues.csv", index=False)
    else:
        tis = pd.read_csv(out / "tissues.csv")

    young = tis[(tis.tissue == "skin_dermis") & (tis.age == min(P["ages"]))]
    S_pa = args.E_dermis_young_pa / (3 * young["G"].mean())

    if "cell" in stages:
        cell = stage_cell(fail, tis, P, S_pa)
        cell.to_csv(out / "cell.csv", index=False)
    if "organ" in stages:
        organ, trans, hrt = stage_organ(tis, P, S_pa)
        organ.to_csv(out / "organ.csv", index=False)
        trans.to_csv(out / "transport.csv", index=False)
        hrt.to_csv(out / "heart.csv", index=False)

    from oxt.materials import CROSSLINKS

    summary = dict(profile=args.profile, params=P, device=args.device, S_pa_per_unit=S_pa,
                   crosslinks=CROSSLINKS, seconds=time.time() - t0)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
