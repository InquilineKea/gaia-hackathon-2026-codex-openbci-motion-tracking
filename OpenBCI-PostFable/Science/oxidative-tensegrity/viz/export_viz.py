#!/usr/bin/env python3
"""Export real model output for the explainer page: network frames under shear, tensegrity shapes vs matrix
stiffness, and summary series from results/cpu32 and results/alchemi_*. Writes viz/data.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from oxt.cell import TensegrityCell  # noqa: E402
from oxt.materials import COLLAGENS, Damage, build_spec  # noqa: E402
from oxt.network import Batch, Lattice  # noqa: E402

torch.set_num_threads(4)
R = lambda a, n=4: np.round(np.asarray(a, float), n).tolist()
out = {}

# --- network frames: Col I, z = 3.4, healthy vs isotropic vs anisotropic dose-1 crosslinks, simple shear
lat = Lattice(12)
gammas = [0.0, 0.08, 0.16, 0.24, 0.32, 0.4]
specs = [build_spec(lat, COLLAGENS["I"], Damage(m, d), np.random.default_rng(1234), z=3.4, k_gag=1e-6)
         for m, d in [("none", 0.0), ("iso", 1.0), ("aniso", 1.0)]]
b = Batch(lat, specs)
frames = []
Fp = b.F0.clone()
for g in gammas:
    F = b.F_shear(g)
    b.move_affine(Fp, F)
    b.relax(F)
    strain = b.bond_strain(F).numpy()
    frames.append(dict(gamma=g, x=[R(b.x[i].numpy().reshape(-1), 3) for i in range(3)],
                       strain=[R(strain[i], 4) for i in range(3)],
                       stress=R(b.stress(F)[:, 0, 1].numpy(), 6)))
    Fp = F
out["network"] = dict(W=12, L=R(lat.L), bi=lat.bi.tolist(), bj=lat.bj.tolist(), shift=R(lat.shift, 3),
                      alive=[s.alive.astype(int).tolist() for s in specs],
                      rigid=[(s.rigid_node > 0).astype(int).tolist() for s in specs],
                      stiffened=[(s.mu > COLLAGENS["I"].mu * 1.01).astype(int).tolist() for s in specs],
                      labels=["healthy (enzymatic crosslinks only)", "oxidative, isotropic", "oxidative, anisotropic"],
                      frames=frames)

# --- tensegrity shapes vs anchor stiffness (cable units), contractility 0.06
cell = TensegrityCell()
tens = []
for ka in [0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]:
    r = cell.solve(0.06, ka)
    P = cell.P0.copy()
    free = np.ones_like(P, bool)
    free[cell.basal, 2] = False
    P[free] = r["x"]
    tens.append(dict(k=ka, P=R(P.reshape(-1), 3), prestress=round(r["prestress"], 4), height=round(r["height"], 4),
                     footprint=round(r["footprint"], 4)))
out["tensegrity"] = dict(struts=cell.S.tolist(), cables=cell.Cb.tolist(), basal=cell.basal.tolist(),
                         rigid_prestress=round(cell.solve(0.06, 1e3)["prestress"], 4), frames=tens)

# --- summary series (GCP cpu32 unless noted)
res = ROOT / "results" / "cpu32"
net = pd.read_csv(res / "network.csv")
br = {}
for col in ["I", "VII", "IV"]:
    d = net[net.collagen == col]
    for mode, dose in [("none", 0.0), ("iso", 1.0), ("aniso", 1.0)]:
        g = d[(d["mode"] == mode) & (d.dose == dose)].groupby("z_target").agg(z=("z", "mean"), G=("G", "mean"),
                                                                             s=("sig_g0.4", "mean")).reset_index()
        br[f"{col}|{mode}"] = dict(z=R(g.z, 3), G=R(g.G, 6), KG=R((g.s / 0.4) / g.G, 3))
out["branching"] = br

fail = pd.read_csv(res / "failure.csv")
cs = [c for c in fail.columns if c.startswith("fail_e")]
eps = [float(c[6:]) for c in cs]
fc = {}
for col in ["I", "VII"]:
    for mode, dose in [("none", 0.0), ("iso", 1.0), ("aniso", 1.0)]:
        s = fail[(fail.collagen == col) & (fail["mode"] == mode) & (fail.dose == dose)]
        fc[f"{col}|{mode}"] = dict(e=eps, s=R(s[cs].mean(), 5), strength=round(s.strength.mean(), 5),
                                   peak=round(s.strain_at_peak.mean(), 3), tough=round(s.toughness.mean(), 5))
out["failure"] = fc

cellc = pd.read_csv(res / "cell.csv")
cc = {}
for col in ["I", "VII", "IV"]:
    d = cellc[(cellc.source == "collagen") & (cellc.collagen == col)]
    for mode in ["iso", "aniso"]:
        s = pd.concat([d[d["mode"] == "none"], d[d["mode"] == mode]]).sort_values("dose")
        cc[f"{col}|{mode}"] = dict(dose=R(s.dose, 2), yap=R(s.YAP_NC, 3), ps=R(s.prestress_ratio, 3),
                                   rec=R(s.recovery_rate_per_h, 4), self=s.self_supporting.astype(int).tolist(),
                                   E=R(s.E_lin_Pa, 1))
out["cell"] = cc

org = pd.read_csv(res / "organ.csv")
out["tissues"] = {t: dict(age=R(g.age, 0), E=R(g.E_ratio, 3), tough=R(g.toughness / g.toughness.iloc[0], 3),
                          repair=R(g.matrix_recovery_per_yr, 5), aniso=R(g.anisotropy, 3), dose=R(g.dose, 3))
                  for t, g in org.sort_values("age").groupby("tissue")}
out["heart"] = pd.read_csv(res / "heart.csv").round(4).to_dict(orient="list")
tr = pd.read_csv(res / "transport.csv")
p = tr.pivot_table(index="molecule", columns=["tissue", "age"], values="D_eff")
amin, amax = tr.age.min(), tr.age.max()
out["transport"] = {t: {m: round(float(p.loc[m, (t, amax)] / p.loc[m, (t, amin)]), 3) for m in p.index}
                    for t in tr.tissue.unique()}
gag = pd.read_csv(res / "gag_summary.csv")
out["gag"] = gag.round(5).to_dict(orient="records")

for name, path in [("collagen_gag_cpu", ROOT / "results/alchemi_gag/collagen_gag_pilot.json"),
                   ("collagen_gag_l4", ROOT / "results/alchemi_gag/collagen_gag_brev_L4.json"),
                   ("crosslink_pilot", ROOT / "results/alchemi_pilot/crosslink_params_pilot.json"),
                   ("crosslink_converged", ROOT / "results/crosslink_params.json")]:
    if path.exists():
        d = json.loads(path.read_text())
        if "pairs" in d:
            out[name] = {k: round(v["min_total_eV"], 3) for k, v in d["pairs"].items()} | \
                        {"_dist": {k: v["d_at_min"] for k, v in d["pairs"].items()}}
        else:
            out[name] = {k: dict(k_rel=round(v["k_rel"], 2), Fpk=round(v["peak_force_eV_A"], 3))
                         for k, v in d["crosslinks"].items()} | {"_source": d["source"], "_fmax": d.get("final_fmax")}

(ROOT / "viz").mkdir(exist_ok=True)
(ROOT / "viz" / "data.json").write_text(json.dumps(out, separators=(",", ":")))
print("wrote viz/data.json", round((ROOT / "viz" / "data.json").stat().st_size / 1024), "KB", list(out))
