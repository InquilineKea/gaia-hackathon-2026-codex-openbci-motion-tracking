# Collagen critiques and molecular pilot records — 2026-10-31

This publication contains two bounded scientific snapshots:

- [Reviewed Gemini critiques and native PYD/DPD MD](reviews-and-native-md/README.md): the eight-reviewer critique, six-reviewer H5/H8/Brev follow-up, and six 20-ps explicit-solvent native-crosslink stability runs (120 ps total).
- [Glucosepane/dityrosine linked-control MD](glucosepane-dityrosine/README.md): twelve accepted 50-ps local collagen-context trajectories (600 ps total), including 30 ps without solute restraints per trajectory. The interrupted diagnostic is retained separately.

The original review reports are also published on the [Human–Avian–AI Symbiosis blog](https://humanavianaisymbiosis.wordpress.com/). Each snapshot has its own SHA-256 manifest. The first snapshot's README records its pre-upload staging state; this index records its subsequent inclusion in the Git publication. Snapshot files were preserved exactly.

The MD work establishes bounded numerical setup/integration checks. It does not establish equilibrium, physical force-field accuracy, a cross-chemistry stiffness ranking, a chemical reaction rate, a GAG/decorin binding result or a tissue-mechanics parameter. The native pilot retained restraints throughout. Glucosepane/dityrosine use distinct peptide contexts, force-field families and source-model charge choices. The candidate report discloses the precision adjustment and DITY torsion-parameter uncertainties.

Original runtime data, paired restart records, inputs, driver versions, source attribution and numerical summaries are included. Credentials, software wheels, private account notes and human approval records are excluded. Inclusion of code is not authorization to execute it. Upstream source licenses and notices remain applicable.
