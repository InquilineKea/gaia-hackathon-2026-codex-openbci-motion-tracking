# Argon collagen MD critique and phase-regime design — 2026-10-31

Read `SWARM_FINDINGS.md` for the source-checked synthesis and `NEXT_SIMULATIONS.md` for the proposed follow-up campaign. Eight Gemini 4 Argon specialists and two adversarial reviewers completed ten API requests. No additional MD/QM/network sweep was run.

Raw reviewers are fallible, same-model AI outputs, not independent scientific validation. Their unsupported statements and corrections remain visible in `CLAIM_AUDIT.json`, `ADVERSARIAL_CLAIM_AUDIT.json` and `SOURCE_CHECK_NOTES.md`. Do not use raw reviewer recommendations to alter a Hamiltonian, reseed a trajectory, or infer a physical phase without the source checks.

The root `sources/`, `manifest.json`, `roles.json`, `review_swarm.py` and `reviews/` record the first round. `adversarial-md/` and `adversarial-network/` each preserve their exact additional source packet, hashes, roles, runner and output. Only the selected adversarial role ran in each packet; unused role definitions are retained to reproduce the runner's eight-role schema.

`RUN_SUMMARY.json` records model settings, token counts and the token-cost estimate. `REVIEW_HASHES.json` in each round verifies the remote results. The local source/CSV, saved-coordinate and independent graph audits are identified as additional analyses. Their original standard-library scripts are included; no imported repository or model-generated program was executed. Model thought parts/signatures, credentials, private account notes and execution-approval records are excluded.

The molecular data and complete runtime records were published in the earlier research packet at Git commit 81e160606351a48557e4a2b91bc9296115a0d9aa. This packet contains selected frozen scientific sources for review, with original attribution retained. Inclusion of code does not authorize its execution. Public snapshot hashes are in `PUBLIC_MANIFEST.json`; publication verification is recorded separately.
