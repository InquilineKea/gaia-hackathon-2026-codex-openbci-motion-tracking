# Graph audit and largest-size controls, 31 October 2026

This follow-up reconstructs the336 graph treatment variants in the previous controlled CPU campaign and adds384 unique mechanical controls at width24. It uses the same finite graph specimens and dimensionless small-strain model. It adds structural measurements and numerical/rate controls, not independent replication, molecular dynamics or calibrated collagen evidence.

Read SWARM_FINDINGS.md for reviewed results; PROTOCOL.md specifies the matrix, bounds and predeclared numerical tolerance. SOURCE_CHECK_NOTES.md adjudicates model critiques; PROVENANCE_NOTES.md explains source and interpretation limits. Final conclusions must distinguish converged but G0-ineligible cases, integration error, correlated seed blocks and co-changing topology variables.

## Data and source layout

`inputs/expected_graphs.json` contains the336 old graph hashes/aggregates. `inputs/prior_mechanical_references.json` contains compact old-case values for unchanged-baseline checks. `raw/audit.json` contains reconstructed active edge indices, exact degrees, node component labels, component edge/bending counts and primitive winding vectors/ranks. Primitive normalization preserves real-span rank but not the full integer subgroup index. `raw/controls.json` contains384 mechanical case records including stress traces and uncapped-rate diagnostics. `analysis/` contains graph summaries, time-step pairs, paired treatment differences, rate comparisons, baseline reproduction and numerical acceptance summaries.

`source/` contains reviewed original sources and analysis. `executed-source/` contains retrieved execution sources and input hashes. Worker logs and completion, gradient and isolation diagnostics are retained separately in `raw/`. The remote source paths in REMOTE_HASHES.json map into these folders; retrieval verification confirms their hashes. Dependency-copy hashes detect content changes but are not independent package vendor authentication. No copied dependencies, credentials, account configuration or private approval notes are included in the public snapshot.

`gemini-review/` and `gemini-adversarial/` contain frozen scientific inputs, role prompts, source manifests, original stdlib API driver, final model responses and usage metadata. Model outputs are not executed or accepted wholesale. Thinking text and signatures are excluded. Same-model consensus is internal review, not independent validation.

## Reproduction

Use a disposable credential-free remote Linux environment after reviewing source and dependencies. Recorded versions: Python3.11.2, NumPy1.26.4, SciPy1.14.1; one BLAS thread per numerical worker. Adapt the namespace wrapper's task/dependency paths to a clean environment, preserving hidden home directories and read-only dependency mounts. Numerical workers must have no network or secret mounts. The API worker has separate access to the Gemini key and scientific packet only; never place that key in a numerical namespace.

Run audit.py and controls.py with model.py available from the designated /mnt/work directory. Save each worker's out directory separately. The generator's graph function is AST-identical to the prior executed rate-control source. audit.py requires every prior mask hash to match; controls.py stops on an incomplete/failed numerical solve. analyze.py runs from the task workspace using the retained folder layout and derives the aggregate files. It uses only the Python standard library locally. All mechanical times, energies and stresses are dimensionless; elapsed_seconds fields are wall-clock measurements.

PUBLIC_MANIFEST.json in the publication snapshot maps every other published file to SHA-256. No new VM or numerical package was needed; the shared GCP host remains running. No additional experiments beyond the declared384 cases are part of this follow-up.

Frozen review packets can precede final source-check notes and analysis-helper revisions. Each role file lists exactly the transmitted sources; packet hashes include numbered text. Claim-audit files distinguish accepted observations from qualified or rejected reviewer assertions.
