# PYD/DPD collagen MD pilot: completed result

All six approved trajectories completed on the separate Brev L4: three PYD and three DPD runs, each 20 ps, for **120 ps and 120,000 integration steps in total**. All predefined runtime checks and all six wet CPU/CUDA comparisons passed. Local post-run geometry checks also passed.

This is a short, restrained numerical stability pilot of already formed native collagen crosslinks. It does not establish equilibrium, compare mechanical stiffness, validate AGE chemistry, or simulate a chemical reaction.

## Systems and protocol

The matched inputs contain six capped human collagen peptide segments with one complete PYD or DPD link, using the existing explicit ColBuilder Amber99SB-star-ILDNP protein/HYP/native-crosslink terms. The paired physical System XML, coordinates and atom map were preserved; no generic force field was substituted for the crosslink. PYD has 1,793 solute atoms and DPD has 1,792. Their paired source hashes and prior dry numerical checks are retained under `inputs/`.

Both systems were solvated with TIP3P water and Joung–Cheatham Na/Cl parameters, neutralized and given a requested 0.15 M added salt. Each chemistry used one solvent build and three different initial-velocity/thermostat seeds. Thus the replicas do not sample independent initial conformer or solvent ensembles.

Each run used 1-fs Langevin-middle integration: 2 ps heating, 8 ps NVT at 310 K, and 10 ps NPT at 310 K/1 bar. Heavy-solute positional restraints tapered from 1,000 to 500 to 100 kJ/mol/nm². PME, a 1.0-nm cutoff, explicit original solute exclusions/1–4 exceptions, and constraints on source hydrogen-bond lengths were retained. The last 10 ps therefore still have restraints; temperature/density near target values do not demonstrate equilibration.

| System | Solute atoms | Total atoms | Waters | Na / Cl | Added salt pairs over initial volume |
|---|---:|---:|---:|---:|---:|
| PYD | 1,793 | 30,238 | 9,464 | 27 / 26 | 0.132510 M |
| DPD | 1,792 | 29,872 | 9,343 | 26 / 25 | 0.128370 M |

Each system has one additional neutralizing sodium ion, separate from the added NaCl pairs. Residual net charge is at the approximately one-to-two microelectron rounding level of the source parameters. The actual salt-pair concentration follows the water-placement convention and whole-box volume; it is reported rather than relabeled as exactly 0.15 M.

## Per-replica measured results

| Chemistry / replica | Seed | Time | Final temperature | Final density | Final heavy-solute displacement | Largest final bond deviation |
|---|---:|---:|---:|---:|---:|---:|
| PYD / 1 | 20261031 | 20 ps | 308.437 K | 1.002454 g/mL | 0.9070 Å | 0.10274 Å |
| PYD / 2 | 20261032 | 20 ps | 311.272 K | 0.997080 g/mL | 0.9640 Å | 0.10326 Å |
| PYD / 3 | 20261033 | 20 ps | 309.141 K | 1.006086 g/mL | 0.9142 Å | 0.09683 Å |
| DPD / 1 | 20261131 | 20 ps | 311.983 K | 0.998110 g/mL | 0.8563 Å | 0.10795 Å |
| DPD / 2 | 20261132 | 20 ps | 311.338 K | 0.999322 g/mL | 0.8843 Å | 0.10888 Å |
| DPD / 3 | 20261133 | 20 ps | 307.311 K | 1.001267 g/mL | 0.8453 Å | 0.09239 Å |

Displacement is the direct heavy-solute coordinate displacement from that replica’s minimized frame, without structural alignment. It is not an equilibrium fluctuation, an aligned RMSD or a stiffness measurement. The atom counts and independent seeds differ between chemistries; small differences between these short trajectories cannot rank PYD against DPD.

## Acceptance and independent readback

All 120 saved frames had finite coordinates, forces and energies, temperatures within the declared 20–650 K envelope and densities within 0.5–1.5 g/mL. The largest saved constraint-length error was 7.7613658e-07 nm, below the 10^-4 nm limit. No tracked tetrahedral-center sign inversion was reported; the checks tracked 109 centers in PYD and 108 in DPD. A separate local implementation rechecked the final signs, source bond lengths and nonlocal heavy-atom contacts. It found no final nonlocal heavy-atom contact below 1.6 Å outside graph-distance-three neighborhoods.

For the six minimized solvated systems, the largest CPU/CUDA-double energy difference was 8.3715094e-06 kJ/mol/atom and the largest force-component RMS difference was 0.0040477091 kJ/mol/nm. Their respective acceptance limits were 0.01 and 1. These compare platforms within OpenMM; they do not establish independent-engine or physical force-field accuracy.

Each final serialized state independently records stepCount 20000 and time 20.00000000000146 ps. Restart with each matching final System XML and State XML together; a System alone does not restore positions, velocities, box, time and context parameters. Binary checkpoints are retained but may require the same compatible software/hardware environment.

## Execution, integrity and scope

The eight construction/trajectory phases took 204.233 seconds in total, including per-phase process overhead, well below the approved one-hour computation cap. Container start: 2026-10-31T12:38:58.786145+00:00. Host completion: 2026-10-31T12:42:35.956019+00:00. Timing is a pilot observation, not a production-throughput guarantee or a cloud billing total.

Only the nine reviewed, hash-locked OpenMM/NumPy/CUDA wheels ran inside a non-root, offline container with a read-only root and input mounts, all capabilities dropped, no-new-privileges, default seccomp, a three-CPU quota, 10 GiB RAM and a 256-process limit. Isolation checks all passed. No home, cloud credential, SSH agent or Docker socket was mounted into the workload. Installed packages lived on disposable runtime storage; the container was removed after completion. No molecular package was installed or executed on the Mac.

The retrieved 52,617,502-byte transport archive matches SHA-256 `157b87b5a592cab8d3e2b4e3d31aaaaf23bfbd0ce8677536fea166cebbdb8064`. All 90 remotely recorded file hashes match. The executed source manifest matched the local execution packet. Original remote records remain intact; local geometry analyses are additional files identified as such.

The prior source/parameter checks support numerical consistency but do not certify the force field. The task VM was stopped after verified retrieval; its disk and raw results were retained.

## What this improves and what comes next

This run demonstrates that complete collagen-linked native-crosslink models can be assembled in water, checked across CPU/CUDA, integrated under the bounded protocol, and retrieved with reproducible source/result records. It improves the workflow beyond isolated gas-phase fragment curves. It does not yet repair those curves or convert their curvatures into tissue parameters.

A glucosepane/dityrosine comparison next requires complete site-specific residue definitions, charge/protonation/stereochemistry, compatible parameters and chemically appropriate collagen sequences. PYD/DPD are native controls and cannot stand in for those AGE/oxidative chemistries. Match environments where chemically meaningful and report valence/attachment differences explicitly. After parameter and geometry validation, test restraint release and longer conformer/solvent replicas before a separately converged force-extension or PMF protocol. H8 binding would additionally require the actual modified residues and the intended GAG/proteoglycan interface.

Fixed-topology classical MD studies already formed covalent links. Formation or cleavage requires specified reactants/products, proton transfers and catalyst/oxidant conditions, then a validated quantum/QM-MM or reactive-potential pathway and barrier assessment. No reaction trajectory or reaction-rate prediction was produced here.

Full numerical details: `RESULT_SUMMARY.json`, `replica_summary.csv`, `RETRIEVAL_VERIFICATION.json`, and `raw/`. The earlier six-reviewer H5/H8/completed-Brev critique remains the separately published WordPress report; this new MD result is a local follow-up and was not part of that Gemini source packet.
