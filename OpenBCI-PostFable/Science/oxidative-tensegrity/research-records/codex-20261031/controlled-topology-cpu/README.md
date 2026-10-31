# Controlled topology CPU campaign, 31 October 2026

Read [SWARM_FINDINGS.md](SWARM_FINDINGS.md) for the reviewed results and ranked next simulations. [ACTUAL_DESIGN.md](ACTUAL_DESIGN.md) specifies the executed model. [SOURCE_CHECK_NOTES.md](SOURCE_CHECK_NOTES.md) adjudicates fallible specialist and adversarial assertions. [PROVENANCE_NOTES.md](PROVENANCE_NOTES.md) qualifies retained source and diagnostics.

This is a distinct dimensionless small-strain periodic-network study. It is not collagen molecular dynamics, a replication of the earlier nonlinear H100 model, a calibrated aging result or a phase-transition measurement. No new VM was created. The shared GCP host remains running.

## Contents

`raw/` holds 1,344 production cases, 336 elastic central-force controls, 16 time-step refinements, 48 targeted rate controls, and eight preliminary benchmark cases. `analysis/` holds derived tables and audit summaries. `source/` contains analysis/simulation sources and prior CUDA reference code (not executed in this campaign). `executed-source/` contains exact retrieved production/control source and original remote result hashes. The preliminary benchmark source version was not separately retained. The `gemini-*` folders preserve frozen inputs, manifests, role prompts, original stdlib API runner, final responses, usage and output hashes for six specialists and two adversarial reviewers. Raw model claims are not endorsed wholesale.

`PUBLIC_MANIFEST.json` maps every other file to SHA-256. The original remote result manifests use remote paths: `out/NAME` maps to `raw/NAME`; the targeted batch's shared self-test/isolation records map to `raw/rate-cpu-selftest.json` and `raw/rate-isolation.json`. Other original log/source paths map to their corresponding raw or executed-source files. Review manifests hash each packet's frozen `sources/` files. Final source-check notes can be newer than their frozen review copies.

## Reproduction

Use a disposable credential-free remote Linux environment and independently review dependencies. Recorded numerical versions are Python 3.11.2, NumPy 1.26.4 and SciPy 1.14.1. Use one BLAS thread per worker and preserve the declared seeds, integer edge counts, affinity and model assumptions. The namespace wrappers document the executed isolation layout; their local dependency-copy paths must be adapted to a clean environment. Do not mount credentials or run the simulation inside an API worker with credentials.

Read `executed-source/sweep.py`, `central.py`, `refinement.py` and `rate_controls.py` for exact case loops. Production writes the JSON cases in `raw/`; the other sources import the production module and use the same model. `source/analyze.py` produces the primary aggregate tables. The targeted controls were added after specialist critique, at one high-density slice, within the bounded numerical run. All times and mechanical quantities are dimensionless except wall-clock timings.

A public snapshot excludes credentials, cloud account/preflight information, private approval records, dependency copies, software wheels and unrelated workspace files. It retains software isolation evidence and failed-launch provenance needed to assess this study. Installed RECORD integrity checks do not authenticate vendor provenance. Four seeds per setting and finite rewiring chains limit inference. Bootstrap columns are exploratory, not confirmatory confidence claims. See the report for conditioning, metric and constitutive-model qualifications.
