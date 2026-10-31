#!/usr/bin/env python3
"""Does crosslinking stiffen collagen yet cost it resilience by blocking GAG-mediated sliding?

Grid: oxidative crosslink dose x GAG mode (none/bridge/sliding/polyelectrolyte) x loading (tension/shear),
collagen I at native branching, matched GAG count. Cyclic loading 0 -> amp -> 0, three cycles.

  python3 run_gag.py --profile local             # laptop, ~30-40 min
  python3 run_gag.py --profile gpu --device cuda  # Brev / Nebius
"""
from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PROFILES = {
    "smoke": dict(W=8, seeds=1, doses=[0.0, 1.0], densities=[0.12], n_half=3, n_cycles=2, workers=4, batch=8),
    "local": dict(W=12, seeds=2, doses=[0.0, 0.5, 1.0], densities=[0.12], n_half=6, n_cycles=3, workers=6, batch=4),
    "cpu32": dict(W=12, seeds=4, doses=[0.0, 0.5, 1.0], densities=[0.12], n_half=6, n_cycles=3, workers=30,
                  batch=1),
    "gpu": dict(W=40, seeds=8, doses=[0.0, 0.25, 0.5, 0.75, 1.0], densities=[0.06, 0.12, 0.2], n_half=12,
                n_cycles=5, workers=1, batch=64),
}
AMP = {"tension": 0.06, "shear": 0.12}  # below collagen I fibre rupture, so loops measure sliding, not fracture


def _worker(task):
    import torch

    torch.set_num_threads(task["threads"])
    from oxt.gag import GAGBatch, attach_gag, loop_metrics
    from oxt.materials import COLLAGENS, Damage, build_spec
    from oxt.network import Lattice

    lat = Lattice(task["W"])
    specs, gags = [], []
    for it in task["items"]:
        rng = np.random.default_rng(it["seed"])
        mode = "iso" if it["dose"] > 0 else "none"
        s = build_spec(lat, COLLAGENS["I"], Damage(mode, it["dose"]), rng, mu_el=0.0, k_gag=1e-6)
        g = attach_gag(s, lat, it["gag"], it["density"], np.random.default_rng(it["seed"] + 7))
        s.meta.update(seed=it["seed"], loading=it["loading"])
        specs.append(s)
        gags.append(g)
    b = GAGBatch(lat, specs, gags, device=task["device"])
    t0 = time.time()
    path, sig, slipped, broken = b.cyclic(task["loading"], AMP[task["loading"]], task["n_half"], task["n_cycles"])
    met = loop_metrics(path, sig, task["n_half"], task["n_cycles"])
    rows = []
    for i, s in enumerate(specs):
        rows.append(dict(**s.meta, **met[i], slipped=int(slipped[i]), broken=int(broken[i]),
                         seconds=time.time() - t0, **{f"s{k}": float(v) for k, v in enumerate(sig[i])}))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="local", choices=PROFILES)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    P = PROFILES[a.profile]
    out = Path(a.out or ROOT / "results" / a.profile)
    out.mkdir(parents=True, exist_ok=True)
    tasks = []
    for loading in ("tension", "shear"):
        items = [dict(dose=d, gag=g, density=rho, seed=5000 + s, loading=loading)
                 for d in P["doses"] for g in ("none", "bridge", "sliding", "polyelectrolyte")
                 for rho in P["densities"] for s in range(P["seeds"])]
        for k in range(0, len(items), P["batch"]):
            tasks.append(dict(items=items[k:k + P["batch"]], loading=loading, W=P["W"], n_half=P["n_half"],
                              n_cycles=P["n_cycles"], device=a.device,
                              threads=1 if P["workers"] > 1 else 8))
    print(f"[gag] {sum(len(t['items']) for t in tasks)} systems in {len(tasks)} batches", flush=True)
    rows, t0 = [], time.time()
    if P["workers"] > 1 and a.device == "cpu":
        with ProcessPoolExecutor(P["workers"]) as ex:
            for n, r in enumerate(ex.map(_worker, tasks)):
                rows += r
                print(f"[gag] batch {n + 1}/{len(tasks)} ({r[0]['seconds']:.0f}s)", flush=True)
    else:
        for n, t in enumerate(tasks):
            rows += _worker(t)
            print(f"[gag] batch {n + 1}/{len(tasks)}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "gag.csv", index=False)
    summ = df.groupby(["loading", "dose", "gag_mode"]).agg(
        secant=("secant_c1", "mean"), diss=("diss_c1", "mean"), loss_ratio=("loss_ratio", "mean"),
        retained=("stiffness_retained", "mean"), residual=("residual_stress", "mean"),
        slipped=("slipped", "mean"), broken=("broken", "mean")).reset_index()
    summ.to_csv(out / "gag_summary.csv", index=False)
    print(summ.round(5).to_string())
    print(f"done in {time.time() - t0:.0f}s -> {out}")


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
