# Glucosepane and dityrosine collagen-context MD pilot — 2026-10-31

Twelve accepted 50-ps trajectories compare linked and unlinked local collagen models within each chemistry. The accepted total is 600 ps, including 360 ps after solute restraints were released. The preserved interrupted diagnostic is additional and is excluded from those totals.

Read `CANDIDATE_COMPARISON_RESULTS.md` for the measured results and their limitations. These are short numerical stability/structural pilots. The two chemistries use different peptide contexts, force-field families and source-model charge choices; their values do not establish an across-chemistry mechanical ranking, physical force-field accuracy, equilibrium or a reaction rate.

## Contents

- `prepared/` and `parameters/`: model coordinates, atom mappings, residue graphs, topology inputs and parameter coverage.
- `provenance/` and `licenses/`: pinned source identities, retrieval hashes and upstream attribution.
- `retrieved/attempt-001/` and `retrieved/attempt-002/`: original saved frames, restart records, numerical checks and runtime logs. Attempt 1 retains the completed double-precision run and interrupted diagnostic. The remaining eleven accepted integrations used mixed precision.
- `retrieved/project/` and `retrieved/project_attempt002/`: exact driver/entry versions and source manifests for both attempts, with cloud launcher, private software-review and human approval records excluded.
- `RESULT_SUMMARY.json` and `replica_summary.csv`: additional local structural analyses and per-replica data.
- `PUBLIC_MANIFEST.json`: SHA-256 values for every public file except the manifest itself.

No software wheels, container image, credentials, private account notes or human approval records are distributed. Original source/result hashes remain unchanged; the report has publication wording and private-record references adapted. `PUBLIC_SNAPSHOT.json` identifies coverage and omissions. Original private records remain intact. Publication is not an authorization to execute the included code; reproduction requires a separately reviewed environment.

Retain source attribution and license notices in `licenses/ATTRIBUTION.md`. The derived DITY XML is not an official OpenMM/CHARMM release. The saved paired System/State XML records are more portable than binary checkpoints, which can require compatible software/hardware.
