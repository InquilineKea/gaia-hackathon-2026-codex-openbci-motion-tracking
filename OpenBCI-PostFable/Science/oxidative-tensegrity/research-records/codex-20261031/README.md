# Collagen critiques and molecular pilot records — 2026-10-31

This publication contains the following bounded scientific records:

- [Reviewed Gemini critiques and native PYD/DPD MD](reviews-and-native-md/README.md): the eight-reviewer critique, six-reviewer H5/H8/Brev follow-up, and six 20-ps explicit-solvent native-crosslink stability runs (120 ps total).
- [Glucosepane/dityrosine linked-control MD](glucosepane-dityrosine/README.md): twelve accepted 50-ps local collagen-context trajectories (600 ps total), including 30 ps without solute restraints per trajectory. The interrupted diagnostic is retained separately.

- [Gemini 4 Argon MD critique and network-regime design](argon-md-network-review/README.md): eight specialist reviews, two adversarial reviews, checked findings and next-simulation recommendations. No new molecular or network sweep was run in that review.

The original review reports are also published on the [Human–Avian–AI Symbiosis blog](https://humanavianaisymbiosis.wordpress.com/). Each snapshot has its own SHA-256 manifest. The first snapshot's README records its pre-upload staging state; this index records its subsequent inclusion in the Git publication. Snapshot files were preserved exactly.

The MD work establishes bounded numerical setup/integration checks. It does not establish equilibrium, physical force-field accuracy, a cross-chemistry stiffness ranking, a chemical reaction rate, a GAG/decorin binding result or a tissue-mechanics parameter. The native pilot retained restraints throughout. Glucosepane/dityrosine use distinct peptide contexts, force-field families and source-model charge choices. The candidate report discloses the precision adjustment and DITY torsion-parameter uncertainties.

Original runtime data, paired restart records, inputs, driver versions, source attribution and numerical summaries are included. Credentials, software wheels, private account notes and human approval records are excluded. Inclusion of code is not authorization to execute it. Upstream source licenses and notices remain applicable.

- [Controlled topology CPU sweeps and Gemini 4 Argon review](controlled-topology-cpu/README.md): 1,344 production cases, 400 control/refinement cases, eight CPU benchmark cases, six specialist and two adversarial reviews, targeted rate controls and source-checked limitations.

- [Graph audit and largest-size time-step/rate controls](graph-audit-largest-size-controls/README.md): exact reconstruction of336 prior graphs,384 largest-size controls, Gemini4Argon specialist/adversarial review and source-checked numerical limits.
