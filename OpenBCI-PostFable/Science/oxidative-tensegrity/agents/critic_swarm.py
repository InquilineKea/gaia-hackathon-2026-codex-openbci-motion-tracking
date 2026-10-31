#!/usr/bin/env python3
"""Independent scientific critics on Nebius Token Factory (OpenAI-compatible API, stdlib only).

Each critic gets the same compact results digest and a different role; their objections are stored
side by side so disagreements stay visible instead of being averaged away.  The digest is built from
results CSVs only (numbers + model assumptions) -- no personal data, keys, or file paths.

  export NEBIUS_API_KEY=...            # set it yourself; never commit it
  python3 agents/critic_swarm.py --list-models
  python3 agents/critic_swarm.py --results results/local --models deepseek-ai/DeepSeek-R1-0528,<other>

Base URL from docs.tokenfactory.nebius.com (checked 2026-10-30).
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

BASE = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

ROLES = {
    "mechanobiologist": "You are a mechanobiologist (YAP/TAZ, focal adhesions, ECM). Identify which predicted "
                        "trends contradict published experiments and name the specific experiment that would test each.",
    "biomechanics_skeptic": "You are a fibre-network mechanics expert (rigidity percolation, strain stiffening). "
                            "Find modelling artefacts: finite size, 2D vs 3D, parameter choices that drive the result.",
    "aging_biologist": "You are a geroscientist familiar with AGE crosslinks (glucosepane, pentosidine) and "
                       "Fedichev's resilience / recovery-rate work. Judge whether the recovery-rate and entropy "
                       "proxies are meaningful and how they could be measured in humans or mice.",
    "statistician": "You are a statistician. Point out where seeds, sample size, or uncertainty are insufficient "
                    "for the claims, and what minimum replication would be needed.",
}


def digest(results: Path) -> str:
    parts = []
    for name in ("failure.csv", "cell.csv", "organ.csv", "heart.csv"):
        p = results / name
        if not p.exists():
            continue
        df = pd.read_csv(p)
        keep = [c for c in df.columns if not c.startswith(("sig_g", "fail_e", "brk_e"))]
        num = df[keep]
        if name == "failure.csv":
            num = df.groupby(["collagen", "mode", "dose"])[["G", "Cx", "Cy", "strength", "toughness",
                                                             "strain_at_peak", "z"]].mean().reset_index()
        parts.append(f"## {name}\n{num.round(5).to_csv(index=False)[:6000]}")
    readme = (results.parents[1] / "README.md")
    model = readme.read_text()[:5000] if readme.exists() else ""
    return f"# Model description (excerpt)\n{model}\n\n# Results\n" + "\n".join(parts)


def chat(model, system, user, key, max_tokens=1800):
    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(dict(model=model, max_tokens=max_tokens, temperature=0.3,
                             messages=[{"role": "system", "content": system},
                                       {"role": "user", "content": user}])).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/local")
    ap.add_argument("--models", default="deepseek-ai/DeepSeek-R1-0528")
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise SystemExit("set NEBIUS_API_KEY in your shell first (not in a file in this repo)")
    if args.list_models:
        req = urllib.request.Request(BASE.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for m in json.loads(r.read())["data"]:
                print(m["id"])
        return
    results = Path(args.results)
    text = digest(results)
    models = args.models.split(",")
    out = []
    for i, (role, sys_prompt) in enumerate(ROLES.items()):
        model = models[i % len(models)]
        ask = ("Critique this multiscale model of oxidative collagen crosslinks -> tissue mechanics -> cell "
               "tensegrity/YAP -> organ function. Give (1) the three weakest claims, (2) one alternative "
               "hypothesis the data cannot rule out, (3) one decisive experiment. Be concrete.\n\n" + text)
        reply = chat(model, sys_prompt, ask, key)
        out.append(dict(role=role, model=model, critique=reply))
        print(f"--- {role} ({model})\n{reply[:1500]}\n")
    (results / "critiques.json").write_text(json.dumps(out, indent=2))
    print("wrote", results / "critiques.json")


if __name__ == "__main__":
    main()
