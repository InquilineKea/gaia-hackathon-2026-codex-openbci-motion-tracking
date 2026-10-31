#!/usr/bin/env python3
"""Three-way comparison of the crosslink stretch scans: MACE-OFF, MACE-MP (ALCHEMI, Brev L4) and PM7 (MOPAC).

Two observables from the same E(L) curves:
  k_rel       curvature at the energy minimum, relative to pyridinoline (what the scans were designed around)
  peak force  max dE/dL over -6% .. +25% end-to-end extension
For each, pairwise Spearman between methods and PM7's spread over RDKit conformer seeds, so model disagreement
can be compared with conformer noise.  Writes results/alchemi_brev/crosslink_model_comparison.{json,md}.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent
D = ROOT / "results" / "alchemi_brev"
SRC = {"MACE-OFF": "crosslink_mace_off.json", "MACE-MP": "crosslink_mace_mp.json", "PM7": "crosslink_pm7.json"}
PAIRS = [("MACE-OFF", "MACE-MP"), ("PM7", "MACE-OFF"), ("PM7", "MACE-MP")]


def main():
    runs = {m: json.loads((D / f).read_text())["crosslinks"] for m, f in SRC.items()}
    names = list(runs["PM7"])
    pm7 = runs["PM7"]
    obs = {"k_rel": "k_rel", "peak_force": "peak_force_eV_A"}
    val = {o: {m: np.array([runs[m][n][key] for n in names]) for m in runs} for o, key in obs.items()}
    rho = {o: {f"{a} vs {b}": float(spearmanr(val[o][a], val[o][b])[0]) for a, b in PAIRS} for o in obs}

    # conformer robustness: does each PM7 seed reproduce the seed-7 ranking?
    seeds = list(pm7[names[0]].get("peak_force_by_seed", {}))
    seed_rho = {}
    for o, by in [("k_rel", "k_rel_by_seed"), ("peak_force", "peak_force_by_seed")]:
        if seeds and by in pm7[names[0]]:
            ref = [pm7[n][by][seeds[0]] for n in names]
            seed_rho[o] = {s: float(spearmanr(ref, [pm7[n][by][s] for n in names])[0]) for s in seeds[1:]}
    # where the energy minimum sits on the 21-point strain grid (index 4 = unstrained)
    argmin = {m: {n: int(np.argmin(runs[m][n]["E_eV"])) for n in names} for m in runs}

    rows = []
    for i, n in enumerate(names):
        r = dict(chemistry=n)
        for o in obs:
            r |= {f"{o}_{m}": float(val[o][m][i]) for m in runs}
        r |= {k: pm7[n][k] for k in ("k_rel_seed_mean", "k_rel_seed_sd", "peak_force_seed_mean", "peak_force_seed_sd")
              if k in pm7[n]}
        r["E_min_index"] = {m: argmin[m][n] for m in runs}
        rows.append(r)
    out = dict(spearman=rho, pm7_seed_vs_seed7_spearman=seed_rho, chemistries=rows,
               note="k_rel relative to pyridinoline in every method; seed spread is PM7 over RDKit conformer seeds")
    (D / "crosslink_model_comparison.json").write_text(json.dumps(out, indent=2))

    def pm(n, o):
        k = f"{o}_seed_mean" if o == "k_rel" else "peak_force_seed_mean"
        return f" ({pm7[n][k]:.2f} ± {pm7[n][k.replace('mean', 'sd')]:.2f})" if k in pm7[n] else ""

    order = sorted(range(len(names)), key=lambda i: -val["peak_force"]["PM7"][i])
    md = ["Peak force, eV/Å (PM7: seed 7, then mean ± sd over seeds)", "",
          "| Chemistry | MACE-OFF | MACE-MP | PM7 |", "|---|---|---|---|"]
    md += [f"| {names[i]} | {val['peak_force']['MACE-OFF'][i]:.2f} | {val['peak_force']['MACE-MP'][i]:.2f} | "
           f"{val['peak_force']['PM7'][i]:.2f}{pm(names[i], 'peak_force')} |" for i in order]
    md += ["", "Curvature at the energy minimum, k_rel (pyridinoline = 1); E-min index of 21 (4 = unstrained)", "",
           "| Chemistry | MACE-OFF | MACE-MP | PM7 | E-min index OFF / MP / PM7 |", "|---|---|---|---|---|"]
    md += [f"| {names[i]} | {val['k_rel']['MACE-OFF'][i]:.2f} | {val['k_rel']['MACE-MP'][i]:.2f} | "
           f"{val['k_rel']['PM7'][i]:.2f}{pm(names[i], 'k_rel')} | "
           f"{argmin['MACE-OFF'][names[i]]} / {argmin['MACE-MP'][names[i]]} / {argmin['PM7'][names[i]]} |" for i in order]
    md += ["", "| Pair | Spearman k_rel | Spearman peak force |", "|---|---|---|"]
    md += [f"| {p} | {rho['k_rel'][p]:.2f} | {rho['peak_force'][p]:.2f} |" for p in rho["k_rel"]]
    if seed_rho:
        md += ["", "| PM7 seed vs seed 7 | Spearman k_rel | Spearman peak force |", "|---|---|---|"]
        md += [f"| {s} | {seed_rho['k_rel'][s]:.2f} | {seed_rho['peak_force'][s]:.2f} |" for s in seed_rho["k_rel"]]
    (D / "crosslink_model_comparison.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
