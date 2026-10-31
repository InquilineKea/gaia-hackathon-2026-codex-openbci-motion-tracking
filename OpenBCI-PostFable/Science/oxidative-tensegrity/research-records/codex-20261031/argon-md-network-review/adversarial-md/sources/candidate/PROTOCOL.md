# Paired glucosepane and dityrosine collagen-context pilot

This is the follow-on requested after the PYD/DPD test. Use the same reviewed nine-wheel runtime and retained L4 only, at the quoted $0.845421/hour plus storage. The full preparation/dynamics phase has a one-hour wall-time cap; retain failures and stop the VM after verified retrieval.

The scientific question is whether each published crosslink representation can be placed in its specified collagen context and pass numerical/structural checks against its corresponding unlinked control. The two contexts and force fields differ. This design does not yield a controlled head-to-head mechanical ranking or a reaction rate.

## Models

- `GLU_LINKED`: two 15-residue collagen fragments extracted from the authors' equilibrated AGE-only fibril, plus ACE/NME caps. The source AGS101–LGX1046 pair has a 1.457875 Å C–N bond. All source crosslink heavy atoms and their stereochemistry are retained. The excerpt is not a full fibril or a complete triple helix. Its taxonomy is not inferred from the GRO title.
- `GLU_CONTROL`: the same fragment backbones with AGS restored to Arg and LGX restored to Lys. The Lys terminal nitrogen uses the former linked nitrogen position; new hydrogens are built and minimized. Net solute charges are approximately −1 and +1 e, respectively, following the published neutral glucosepane representation. Ion counts are adjusted separately. These are source-model protonation choices, not a pKa validation.
- `DITY_LINKED`: the existing human collagen N-telopeptide source TER120/A residues 2–22 (chain J in the accepted native coupon), with Tyr4–Tyr6 linked at CE2–CE2 and the two HE2 hydrogens removed. CHARMM ACE/CT3 caps preserve the paired terminal treatment. This is a local intramolecular crosslink hypothesis, not a measured site assignment.
- `DITY_CONTROL`: the same capped peptide and source coordinates with the two native Tyr residues unlinked.

Glucosepane uses the authors' Amber99-compatible residue/parameter set. Dityrosine uses the locked OpenMM CHARMM36 data plus the published CHARMM/CGenFF DITY charges and 19 relevant bonded parameter types. The derived XML retains only the original wheel's 301-character CHARMM-version initializer, read in full; no author-supplied program or XML script is executed. Higher CGenFF torsion penalty annotations (30 and 41.1 for DITY terms) remain an accuracy concern and require independent benchmarking before quantitative interpretation.

## Gates before dynamics

Static checks already verify source hashes, the glucosepane residue graph/charge/attachment, the mapping of all 80 published capped-motif atoms, complete Amber graph parameter coverage for both collagen excerpts, and local DITY bond/angle/proper/nonbonded coverage. Full-context impropers and CMAP are resolved by the native CHARMM force-field implementation, not invented in the adapter.

All four models must construct a complete physical System and pass bounded dry Reference-platform minimization with backbone restraints. Reject missing terms/templates, nonfinite values, tracked stereochemical inversions, or a chemical bond deviation above 0.4 Å. Compare Reference and CUDA-double energy/forces with limits 10^-4 kJ/mol/atom and 0.01 kJ/mol/nm RMS. For the Amber models, additionally compare against OpenMM's separate GROMACS source-topology reader with limits 10^-5 kJ/mol/atom and 0.01 kJ/mol/nm RMS. This is a parser/platform check within OpenMM, not execution of native GROMACS or proof of physical accuracy.

## Solvent and bounded dynamics

Use a proper principal-axis rotation and 1.2-nm padding. Amber models use TIP3P/Joung–Cheatham Na/Cl; CHARMM models use the native CHARMM modified TIP3P and ion parameters. Request 0.15 M salt, neutralize, report actual counts/net charge and preserve the force-field-specific water model. Reject over 100,000 atoms. Use PME, a 1.0-nm cutoff, 10^-5 electrostatic tolerance and 1-fs Langevin-middle dynamics at 310 K. Keep each force field's native exclusions/1–4 rules and dispersion treatment.

Three recorded velocity/thermostat seeds per model; one solvent build per model. Each trajectory has 2 ps heating, 8 ps NVT, 10 ps NPT at 1 bar, then 30 ps NPT with solute restraints released: 50 ps each, at most 12 runs and 600 ps total. This is a short stability/structural pilot; the free tail does not establish equilibrium or adequate conformational sampling. Initial heavy-solute restraints are 1,000, then 500, then 100 kJ/mol/nm², then zero.

Before each trajectory, require wet CPU/CUDA energy/force differences below 0.01 kJ/mol/atom and 1 kJ/mol/nm RMS. At every saved ps require finite quantities, no tracked stereocenter sign inversion, constraint error below 10^-4 nm, temperature 20–650 K and density 0.5–1.5 g/mL. Save final paired System/State XML, coordinates and solute frames. Report the actual completed time and failures. No reaction formation/cleavage, tensile loading, binding PMF or tissue calibration is included.
