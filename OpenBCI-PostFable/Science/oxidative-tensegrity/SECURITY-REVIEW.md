# Pre-execution security review — 2026-10-30 (Claude Code)

Scope: every third-party component this project would *execute*. Static review only (repository pages,
`pyproject.toml`, documentation); nothing third-party was installed or run. Local runs used only packages already
present on this Mac (numpy 1.26.4, scipy 1.17.0, torch 2.9.1, pandas, matplotlib) and original code.

## Findings

| Severity | Component | Finding | Mitigation in this repo |
|---|---|---|---|
| **High** | NVIDIA ALCHEMI Toolkit `0.3.0-rc` | Branch head `84fe8e8f` was committed **2026-10-29** (1 day old) — fails the 7-day package-age rule in the repo `AGENTS.md`. Branch is a moving release candidate. | `remote/gpu_run.sh` refuses to install unless `ALCHEMI_COMMIT=<sha>` is set explicitly. Pick a sha ≥ 7 days old if the needed features exist there, or grant an explicit exception (as was done for certifi). |
| **High** | ALCHEMI `pyproject.toml` | `[tool.uv] index-strategy = "unsafe-best-match"` with PyPI + `pypi.nvidia.com` + `download.pytorch.org`: a package name present on several indexes resolves to the best version across all of them — the classic dependency-confusion pattern. The deck's install line repeats it. | Our install uses `--index-strategy first-index`. Still review the resolved lock (`uv pip compile`) before installing. |
| Medium | ALCHEMI dependencies | Lower-bound-only pins: `torch>=2.8`, `nvalchemi-toolkit-ops>=0.5.0`, `nvidia-physicsnemo>=2.2.0`, `cuequivariance-ops-torch-cu13>=0.8.0`; `aimnet` fully unpinned. Large transitive tree (physicsnemo, warp-lang, zarr 3). | Compile a lockfile on the GPU box, check publish dates of each resolved version, then install with `--require-hashes`. |
| Medium | ALCHEMI repo ships `AGENTS.md`, `CLAUDE.md`, `.claude/skills/*` | Agent-instruction files are a prompt-injection surface: an agent opened inside that clone will treat them as instructions. | Treat as reference documentation only; do not run an agent with that clone as its working directory without reviewing those files. Our script was written from the skill *text*, not executed. |
| Low | ALCHEMI build | Hatchling backend, no custom build hooks; Apache-2.0; two console scripts (`nvalchemi-io-test`, `nvalchemi-training`). | — |
| Medium | MACE model weights (`medium-0b2`, MACE-OFF) | Downloaded at runtime from upstream URLs; PyTorch checkpoints can contain pickled code. | Load only on the disposable GPU box; verify checksum against the MACE release notes. |
| Low | `remote/gpu_run.sh` mesoscale deps | numpy 1.26.4, scipy 1.14.1, pandas 2.2.3, matplotlib 3.9.2, torch 2.5.1 (cu124), pip 24.3.1, uv 0.5.11, rdkit 2024.9.6, ase 3.24.0 — exact pins, all > 7 days old. | Pinned; no hashes yet. |
| Medium | Nebius CLI, Brev CLI, LAMMPS | Not installed or inspected. Install only from the vendors' official channels (Nebius docs, `brevdev` Homebrew tap, conda-forge `lammps` pinned version). | You install these; they need your account credentials, which agents must not handle. |
| Low | `agents/critic_swarm.py` | Sends a results digest (CSV numbers + README excerpt) to `api.tokenfactory.nebius.com`. No personal data, paths or keys in the payload; key read from `NEBIUS_API_KEY` env only. stdlib `urllib`, no new packages. | Review `digest()` output before first run if you want to see exactly what leaves the machine. |
| Low | Nebius job image `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime` | Official Docker Hub image, tag > 1 year old; digest not pinned. | Pin `@sha256:` once you pull it. |

## Execution environment

GPU work must run on a disposable Brev instance or Nebius VM/job with no personal credentials, SSH keys or
browser data copied onto it. Nothing from the personal machine's credential stores
should be placed on those machines.

## Not verified

Commit signatures, the full transitive dependency tree, CI workflows, `.pre-commit-config.yaml` and `Makefile`
contents of ALCHEMI, MACE checkpoint hashes, LAMMPS binaries. A clean static read does not establish safety.

**Approval needed before any of the above is executed.**

## Executed 2026-10-30 (user: "Just run ALCHEMI 101")

- Where: Docker container `alchemi101` (python:3.12.7-bookworm, digest sha256:78c6833c…), 6 CPUs / 6 GB, all
  capabilities dropped except file ownership/setuid needed by pip, `no-new-privileges`, only a scratch folder
  mounted. No home directory, keys, keychain or browser data visible to it. Network on (needed for installs and the
  MACE-OFF checkpoint download from GitHub).
- Installed: `nvalchemi-toolkit[mace] @ 84fe8e8f` from PyPI only (no extra indexes, `first-index`), rdkit 2024.9.6,
  ase 3.24.0. Other dependencies resolved to their latest releases (torch 2.15.0, warp-lang 1.18.0, …); some are
  likely < 7 days old — full list in the scratch `alchemi-freeze.txt`. Not hash-verified.
- MACE checkpoints are loaded with `torch.load(weights_only=False)` (pickle) by ALCHEMI itself; MACE-OFF is under
  the Academic Software License (non-commercial).
- Ran: `examples/intermediate/01_multistage_pipeline.py` (ALCHEMI 101 "get started") — exit 0 on CPU.
- ALCHEMI issues found (report to the NVIDIA team): `MACEWrapper.from_checkpoint` cannot load a local checkpoint
  (always routed through `download_mace_mp_checkpoint`; `examples/advanced/04_mace_nvt.py` with `MACE_MODEL_PATH`
  hits it); FIRE2 kernels take their dtype from positions, which `AtomicData.from_atoms` creates as float32, so a
  float64 model fails unless positions are cast; CPU throughput ~17 s per FIRE2 step for 780 atoms (GPU needed).
- Delete the container when done: `docker rm -f alchemi101`.

## ScienceClaw (lamm-mit/scienceclaw) — static review 2026-10-31 (not executed)

Cloned to a scratch folder and read; nothing installed or run. Apache-2.0 (package.json says MIT).

| Severity | Finding | Mitigation |
|---|---|---|
| **Critical** | `autonomous/deep_investigation.py:349` runs LLM-written shell commands (`run_command` action) with `shell=True` and the **full environment** (`env={**os.environ}`), so every API key in the environment is readable by model-chosen commands. Every investigation goes through `run_deep_investigation`. Text fetched from papers/web can steer those commands (prompt injection). | Run only in a throwaway Docker container that mounts nothing but a work folder; the only secret inside is the Gemini key (lab account, expires Sunday). |
| **High** | Latest commits `894598c`/`778a853` are dated **2026-10-30** (1 day old), failing the 7-day rule. The prior commit `ab9aba1` (2026-08-21) predates the `--dry-run` fix for `investigate`. | Pin `894598c` with explicit user approval, or `ab9aba1` without the dry-run fix (not recommended: posting risk). |
| **High** | Runtime installs: `core/skill_executor.py` calls `deps/installer.ensure_deps`, which runs unpinned `pip install <pkg>` whenever a skill needs one. `requirements.txt` is unpinned (`openai>=1`, `anthropic>=0.20`, `tooluniverse` with no version). | Container only; record `pip freeze` afterwards. |
| **High** | Publishing: `investigate` posts a synthesis to Infinite (`infinite-lamm.vercel.app`) unless `--dry-run`; `setup.py` registers an agent account on Infinite; the heartbeat daemon posts every cycle; `utils/imgur.py` can upload figures to imgur. | Use `--dry-run` only, skip `setup.py` and the daemon, and set `INFINITE_API_BASE=http://127.0.0.1:9` so any missed post fails. Dry-run code path checked: anchor post, agent registration and synthesis post are all gated. |
| Medium | `install.sh` advertises `curl … \| bash`; `install_scienceclaw_command.sh` symlinks into `~/.local/bin` and suggests editing shell rc files. | Not used. |
| Medium | Repo ships `AGENTS.md` and an OpenClaw skill pack: agent-instruction files are a prompt-injection surface. | Never run an agent with that clone as its working directory. |
| Info | Endpoints seen in core code: Infinite, PubMed/NCBI, doi.org, arXiv, generativelanguage.googleapis.com (Gemini), imgur. No reads of `.ssh`, `.aws`, keychain, gcloud or browser stores found by grep. | — |

**Not verified:** the 300+ skills individually, `tooluniverse` and its dependency tree, transitive pins. Grep-level review only.

## MOPAC (openmopac) v23.2.5 — review 2026-10-31, executed on Brev (user: "Yes, review then run")

Used for the PM7 tie-breaker (`pm7_crosslinks.py`, `remote/brev_pm7.sh`). The ScienceClaw `mopac` skill was read
but not used: it is a thin ASE wrapper and passes an `scf=` keyword ASE's MOPAC calculator does not accept.

| Severity | Finding | Mitigation |
|---|---|---|
| Low | Prebuilt binaries (`bin/mopac`, `lib/libmopac.so.2`, Intel `libiomp5.so`, MKL statically linked); source not rebuilt. | Official `openmopac/mopac` release, Apache-2.0, published 2026-05-03 by the MOPAC maintainer (passes the 7-day rule). Tarball sha256 `bc1a814a…9377` matches GitHub's recorded asset digest and is re-checked by `brev_pm7.sh` before every run. |
| Info | Tarball has no install scripts (the `.run` installer was not used). `strings` shows only citation URLs; no socket, curl, `system`/`popen` or shell strings. Dynamic deps: libc, libm, libgcc_s, libiomp5. | — |

Execution: Brev L4 box, `python:3.12.7-bookworm` container with `--network none`, MOPAC tarball mounted read-only,
the existing `oxt-alchemi-venv` (rdkit 2024.9.6, ase 3.24.0, already reviewed) mounted read-only. No new Python
packages. Nothing ran on the Mac.
