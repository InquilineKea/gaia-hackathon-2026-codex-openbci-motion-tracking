#!/usr/bin/env python3
"""Semi-empirical tie-breaker for the crosslink stretch scan: the same fragments, anchors and strains as
alchemi_crosslinks.py, relaxed with MOPAC PM7 instead of a machine-learned potential.

Why: MACE-OFF and MACE-MP converged but rank the crosslinks differently (Spearman 0.48).  PM7 is an
independent physics-based method (NDDO quantum chemistry), so where it sides with one MLIP that ranking is
better supported; where it disagrees with both, the chemistry is model-sensitive and should be reported so.

Each image is one MOPAC job: Cartesian optimisation with the two anchor atoms frozen (MOPAC opt flags 0).
Extra RDKit seeds give a conformer spread, so model disagreement can be compared with conformer noise.

  python3 pm7_crosslinks.py --workers 4 --seeds 7,11,23 --out results/alchemi_brev/crosslink_pm7.json
Needs the `mopac` binary on PATH (openmopac v23.2.5, see SECURITY-REVIEW.md), rdkit and ase.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from alchemi_crosslinks import FRAGMENTS, analyse, build_atoms, stretched_images

ROOT = Path(__file__).resolve().parent
KCAL_TO_EV = 0.0433641
KEYWORDS = "PM7 XYZ GNORM=0.1 LET CHARGE=0 THREADS=1 NOINTER GEO-OK"
HOF = re.compile(r"FINAL HEAT OF FORMATION\s*=\s*(-?\d+\.\d+)\s*KCAL/MOL")
GNORM = re.compile(r"GRADIENT NORM\s*=\s*(\d+\.\d+)")


def run_image(task):
    """One constrained PM7 optimisation -> (energy eV, final gradient norm kcal/mol/A, status)."""
    symbols, pos, anchors = task
    lines = [KEYWORDS, "crosslink stretch image", ""]
    for k, (s, p) in enumerate(zip(symbols, pos)):
        f = 0 if k in anchors else 1
        lines.append(f"{s:2s} {p[0]:14.8f} {f} {p[1]:14.8f} {f} {p[2]:14.8f} {f}")
    with tempfile.TemporaryDirectory() as d:
        inp = Path(d) / "job.mop"
        inp.write_text("\n".join(lines) + "\n")
        try:
            subprocess.run(["mopac", str(inp)], cwd=d, capture_output=True, timeout=1800, check=False)
        except subprocess.TimeoutExpired:
            return float("nan"), float("nan"), "timeout"
        out = (Path(d) / "job.out").read_text(errors="replace") if (Path(d) / "job.out").exists() else ""
    h = HOF.findall(out)
    g = GNORM.findall(out)
    if not h:
        err = next((ln.strip() for ln in out.splitlines() if "ERROR" in ln.upper()), "no heat of formation")
        return float("nan"), float("nan"), err[:120]
    return float(h[-1]) * KCAL_TO_EV, float(g[-1]) if g else float("nan"), "ok"


def scan(names, seed, strains, workers):
    jobs, tasks = [], []
    for name in names:
        atoms, anchors = build_atoms(FRAGMENTS[name], seed=seed)
        imgs, L0 = stretched_images(atoms, anchors, strains)
        jobs.append(dict(name=name, anchors=anchors, L0=L0))
        tasks += [(a.get_chemical_symbols(), a.get_positions(), set(anchors)) for a in imgs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(run_image, tasks))
    E = np.array([r[0] for r in res])
    bad = [(jobs[i // len(strains)]["name"], i % len(strains), r[2]) for i, r in enumerate(res) if r[2] != "ok"]
    return jobs, E, np.array([r[1] for r in res]), bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7", help="RDKit embedding seeds; the first matches the MACE scans")
    ap.add_argument("--only", default="", help="comma-separated subset of chemistries (smoke tests)")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--min-strain", type=float, default=-0.06)
    ap.add_argument("--max-strain", type=float, default=0.25)
    ap.add_argument("--n-strain", type=int, default=21)
    ap.add_argument("--out", default=str(ROOT / "results" / "alchemi_brev" / "crosslink_pm7.json"))
    args = ap.parse_args()

    names = [n for n in FRAGMENTS if not args.only or n in args.only.split(",")]
    seeds = [int(s) for s in args.seeds.split(",")]
    strains = np.linspace(args.min_strain, args.max_strain, args.n_strain)
    t0 = time.time()
    per_seed, gmax, failures = {}, 0.0, []
    for seed in seeds:
        jobs, E, G, bad = scan(names, seed, strains, args.workers)
        failures += [dict(seed=seed, chemistry=n, strain_index=i, status=s) for n, i, s in bad]
        if bad:  # interpolate isolated failures rather than dropping a whole chemistry
            for c in range(len(jobs)):
                e = E[c * len(strains):(c + 1) * len(strains)]
                ok = np.isfinite(e)
                if ok.sum() >= 5:
                    e[~ok] = np.interp(strains[~ok], strains[ok], e[ok])
        per_seed[seed] = analyse(jobs, E, strains)
        gmax = max(gmax, float(np.nanmax(G)))
        print(f"seed {seed}: {len(jobs) * len(strains)} images, {len(bad)} failed, {time.time() - t0:.0f} s", flush=True)

    main_seed = seeds[0]
    res = per_seed[main_seed]
    for n in res:
        ks = [per_seed[s][n]["k_rel"] for s in seeds]
        fs = [per_seed[s][n]["peak_force_eV_A"] for s in seeds]
        res[n]["k_rel_by_seed"] = dict(zip(map(str, seeds), ks))
        res[n]["k_rel_seed_mean"], res[n]["k_rel_seed_sd"] = float(np.mean(ks)), float(np.std(ks))
        res[n]["peak_force_by_seed"] = dict(zip(map(str, seeds), fs))
        res[n]["peak_force_seed_mean"], res[n]["peak_force_seed_sd"] = float(np.mean(fs)), float(np.std(fs))
        res[n]["by_seed"] = {str(s): dict(L0_A=per_seed[s][n]["L0_A"], E_eV=per_seed[s][n]["E_eV"]) for s in seeds}
    payload = dict(
        source="mopac-23.2.5:PM7", seconds=time.time() - t0, seeds=seeds, keywords=KEYWORDS,
        final_fmax=gmax * KCAL_TO_EV, final_fmax_note="max final MOPAC gradient norm over images, eV/A",
        failures=failures,
        caveats=["semi-empirical NDDO (PM7), gas phase, closed-shell neutral fragments",
                 "same fragments, anchors and strains as the MACE scans; k_rel relative to pyridinoline",
                 "k_rel_seed_sd is the conformer spread across RDKit seeds, not a model error bar"],
        crosslinks=res)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    for n, r in res.items():
        print(f"{n:15s} k_rel={r['k_rel']:.2f}  seeds {r['k_rel_seed_mean']:.2f}±{r['k_rel_seed_sd']:.2f}  "
              f"Fpk={r['peak_force_eV_A']:.2f}  seeds {r['peak_force_seed_mean']:.2f}±{r['peak_force_seed_sd']:.2f} eV/A")
    print("wrote", out, "failures:", len(failures))


if __name__ == "__main__":
    main()
