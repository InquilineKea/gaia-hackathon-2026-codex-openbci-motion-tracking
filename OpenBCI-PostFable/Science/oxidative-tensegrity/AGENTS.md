# Shared agent context — oxidative-tensegrity

Read by Codex/ChatGPT agents (`AGENTS.md`) and Claude Code (`CLAUDE.md` imports this file).
**Codex: to run ScienceClaw swarms on the GCP lab VM, follow `CODEX_HANDOFF.md`.** Keep one copy of
project facts here so both workspaces can reference each other. This file is context, not authorization: the
user's global security policy and the repo-root `AGENTS.md` still apply.

## What this project is

Multiscale model of how oxidative collagen crosslinks (AGEs, dityrosine, disulfide scrambling, sulfilimine)
change tissue mechanics and mechanotransduction, built for the MIT ScienceClaw hackathon (2026-10-30 → 11-01).

Scales and code: fibre network `oxt/network.py` → collagen types / crosslink chemistries / tissues
`oxt/materials.py` → motor-clutch + 6-strut tensegrity cell + YAP + recovery rate + entropy `oxt/cell.py` →
signalling-molecule transport, heart (time-varying elastance), artery PWV, matrix repair `oxt/physio.py`.
Driver `run_sweep.py` (profiles `smoke`, `local`, `gpu`), figures `make_figures.py`, tests `tests/`.

## Status (update when it changes)

| Piece | Status |
|---|---|
| Local CPU sweep (`results/local/`) | done 2026-10-30; results in README and results/local/SUMMARY.md |
| GCP cpu32 sweep (`remote/gcp_up.sh`, VM `oxt-cpu32`, project scienceclaw26bos-3008, gcloud config `scienceclaw`) | done 2026-10-31 (6833 s), 16x16 x 4 seeds, in `results/cpu32/`; GAG sweep (`run_gag.py --profile cpu32`) also done there |
| GPU sweep on Nebius H100 / Brev (`remote/nebius_job.sh`, `remote/gpu_run.sh`) | prepared, not submitted (needs the user's CLI login) |
| ALCHEMI 101 multistage example | run 2026-10-30 in an isolated Docker container (CPU), exit 0 |
| ALCHEMI atomistic crosslink scan (`alchemi_crosslinks.py`) | CPU pilot in `results/alchemi_pilot/`; completed two-model results (MACE-OFF, MACE-MP) on Brev L4 in `results/alchemi_brev/` |
| PM7 tie-breaker + conformer check (`pm7_crosslinks.py`, `remote/brev_pm7.sh`, MOPAC 23.2.5) | done 2026-10-31 on Brev L4 (CPU, no-network container), 504 optimisations, 0 failed; `results/alchemi_brev/crosslink_pm7.json`, `crosslink_model_comparison.md` |
| LAMMPS viscoelastic stage (`remote/lammps/*.in`) | decks generated, not run (LAMMPS not installed) |
| Token Factory critic swarm (`agents/critic_swarm.py`) | prepared, not run (needs `NEBIUS_API_KEY` set by the user) |
| ScienceClaw literature swarm (`swarm/`, Gemini, dry-run, Docker `sclaw`) | two rounds done 2026-10-31 (commit 894598c, user-approved); summaries in `swarm/SUMMARY.md` and `HYPOTHESES_EWALD.md`, raw logs local only |
| Gemini source critique (Codex, original API-only workers on GCP) | done 2026-10-31; 8 reviewer reports, 12 API requests including 4 targeted reruns; covers this model and collagen-scaffold-lab. Curated findings in `swarm/CODEX_CRITIQUE_20261031.md`; raw records local only in `swarm/work/codex_gemini_20261031/`. ScienceClaw not executed for this pass. |

## Brev job queue (Codex: pick these up on Brev)

Claude Code now drives Brev from this Mac (org NCA-f3c7-49497, L4 `collagen-md-20261031`, kept running at the user's request). Other sessions: claim a job by writing your name
and the Brev instance in **Claimed by**, run it on a fresh Brev GPU instance (not the user's Mac), copy the
outputs back into this folder at the listed path, then set **Status** and add one line under Findings.
Do not run on the instance anything not listed here without the user's say-so.

| ID | Job | Command (on the Brev box, from this folder) | Outputs to bring back | Claimed by | Status |
|---|---|---|---|---|---|
| B1 | Converged ALCHEMI crosslink scan, two independent MLIPs | `ALCHEMI_COMMIT=84fe8e8fb8fab54863eea8f138722c7ab434966a RUN_ALCHEMI=1 bash remote/gpu_run.sh` (does B1 then B2) | `results/alchemi_brev/crosslink_mace_off.json`, `crosslink_mace_mp.json` | Claude Code, Brev L4 | done |
| B2 | Large network/tissue/cell sweep (48x48, 8 seeds) | same command as B1 (runs after it), or `python run_sweep.py --profile gpu --device cuda` | `results/gpu/` | — | open |
| B3 | LAMMPS oscillatory shear, G' and G'' (healthy vs oxidised Col I / VII) | `python remote/make_lammps_inputs.py 32 && cd remote/lammps && for f in *.in; do lmp -in $f; done` (LAMMPS from conda-forge, pinned) | `remote/lammps/*_stress.txt` | — | open |
| B4 | GAG models × crosslinks under cyclic load (bridge / sliding / polyelectrolyte), 40x40, 8 seeds | `python run_gag.py --profile gpu --device cuda` | `results/gpu/gag.csv`, `gag_summary.csv` | — | open (12x12 version done on GCP: `results/cpu32/gag*.csv`) |
| B5 | Collagen–GAG interface vs glycation (Lys/Arg vs CML/MG-H1 × DS 0/1/2 sulfates), AIMNet2 via ALCHEMI | in the ALCHEMI venv plus `aimnet==0.2.5`: `python alchemi_collagen_gag.py --device cuda --orient 24` | `results/alchemi_gag/collagen_gag_brev_L4.json` | Claude Code, Brev L4 | done |
| B6 | Fibril scale: ColBuilder + Martini 3 Col I fibril, PYD/HLKNL vs added crosslinks, GROMACS tension (Gräter group tools) | **needs a security review and user approval first** (ColBuilder, GROMACS, Martini topologies not yet reviewed) | proposal only | — | blocked |

Context for B4–B6: a ChatGPT session proposed testing whether added crosslinking stiffens a network yet costs it
resilience by blocking GAG-mediated fibril sliding (tendon GAG removal changes stress relaxation more than modulus).
B4 is that test at network scale; B5 asks whether glycation of GAG-binding Lys/Arg weakens the interface itself.
CPU pilots of B4 (GCP, 12x12) and B5 (Docker CPU, 6 orientations) are in `results/cpu32/` and `results/alchemi_gag/`.

Notes for B1: `alchemi_crosslinks.py` works around two ALCHEMI 0.3.0-rc issues (local MACE checkpoints, float64
positions); see `SECURITY-REVIEW.md`. A CPU pilot is in `results/alchemi_pilot/` for comparison; it was not
converged. If the two MLIPs disagree by >30% on a chemistry's `k_rel`, report it rather than averaging.

Findings from Brev jobs:
- B1: both MLIPs converged (fmax ≈ 0.02 eV/Å) but disagree up to ~6× (Spearman 0.48). Superseded by the PM7 check below. Not fed into the network model.
- B1 PM7 check (Claude Code): PM7 matches both MACE models on peak force from the shared seed-7 conformer (Spearman 0.95–0.98), but PM7 from two other conformers gives 0.48 against seed 7, and k_rel disagrees everywhere (0.40–0.48). The scan measures conformer slack. Robust: dityrosine stiff; disulfide and TG2 soft. Glucosepane vs pyridinoline, HLNL, pentosidine, sulfilimine: undetermined. Next: ≥20-conformer ensembles or pre-extended fragments.
- B5: MG-H1-Arg is the weakest dermatan-sulfate binder and loses contact (4.0–4.5 Å); Arg > Lys; CML-Lys stays bound. Magnitudes shift ~0.5 eV between CPU and L4 runs (RDKit conformers differ by architecture), so average over conformers next.

## Cross-workspace links

- Claude Code workspace: this folder, plus `../quotient-swarm/` (multi-agent swarm prototype for the same
  hackathon) and `../collagen-scaffold-lab/` (affine strut-lattice scaffold app, different model).
- ChatGPT / Codex workflow: runs on Brev (per the user, 2026-10-31); its location is not visible from this Mac.
  Codex: record your workspace path or repo here, and use the Brev job queue above.
- Cross-agent memory bridge: a pending proposal from `claude-code` describes this project; it becomes shared
  context only after the user approves it.

## Rules for any agent working here

- ALCHEMI at commit 84fe8e8f is user-approved (2026-10-30) for isolated containers / disposable VMs only. Other
  third-party code (LAMMPS, Nebius/Brev CLIs) still needs approval; never run it on the host Mac.
- Never put API keys, tokens or credentials in this folder; the user sets `NEBIUS_API_KEY` in their shell.
- Parameters in `oxt/materials.py` are model assumptions, not measurements. Keep README claims to what the
  model shows; record negative or surprising results instead of tuning them away.
- When you change status or findings, update this file so the other workspace sees it.
