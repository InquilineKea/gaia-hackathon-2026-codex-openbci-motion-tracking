# Collagen reviews and native-crosslink MD pilot — 2026-10-31

This bounded research packet contains the eight-reviewer Gemini critique, the six-reviewer H5/H8/completed-Brev follow-up, and six completed explicit-solvent PYD/DPD collagen MD stability tests. It is staged for publication; this directory is not evidence of an upload.

The Gemini reports were published on the Human–Avian–AI Symbiosis WordPress blog. The MD pilot completed three 20-ps replicas per chemistry, 120 ps total. All runtime/platform/final-geometry checks passed; the VM was stopped after result retrieval. Short restrained trajectories do not establish equilibrium, mechanical ranking, AGE chemistry or reaction rates.

## Contents

- `eight-reviewer/REPORT.md`: first reviewed critique; source packets, hashes, reviewer JSON and API-only runner.
- `focused-followup/REPORT.md`: H5/H8/completed-Brev critique; source packets, hashes and reviewer JSON.
- `native-crosslink-md/MD_PILOT_RESULTS.md`: measured pilot results and scientific limitations.
- `native-crosslink-md/raw/`: original trajectory/state/system files, numerical checks, progress and runtime logs.
- `native-crosslink-md/inputs/`: exact paired native-link input models and dry-preparation checks.
- `native-crosslink-md/pilot.py`: the executed bounded molecular driver; package pins/hashes are retained without distributing wheels.

Raw OpenMM checkpoints can require a compatible hardware/software environment. The paired XML System/State records are the more portable restart record. Source parameters derive from ColBuilder at the pinned revision identified in the native input provenance; its license is included. Retain original source attribution and the scope limitations. No authors' new glucosepane/dityrosine data are redistributed in this packet.

The packet excludes credentials, software wheels, account/incident notes and human approval records. Runtime configuration logs describe only the public-data workload and its isolation. Publication does not authorize executing the code; use your own reviewed environment.

## Published reviews

- https://humanavianaisymbiosis.wordpress.com/2026/10/31/gemini-collagen-review-findings-eight-reviewer-report/
- https://humanavianaisymbiosis.wordpress.com/2026/10/31/collagen-followup-h5-h8-completed-brev-crosslinks/
