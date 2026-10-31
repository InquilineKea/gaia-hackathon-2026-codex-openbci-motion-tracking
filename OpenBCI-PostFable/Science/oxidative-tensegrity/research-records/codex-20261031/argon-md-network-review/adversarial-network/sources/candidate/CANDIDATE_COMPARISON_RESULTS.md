# Glucosepane and dityrosine: paired collagen-context MD pilot

**Twelve accepted trajectories completed: three 50-ps runs for each of four linked/control models, 600 ps in aggregate.** Every accepted run includes 30 ps after releasing solute restraints, giving 360 ps of unrestrained tail data in aggregate. These are twelve short trajectories, not one continuous 600-ps trajectory.

All four dry model-validation gates and all twelve wet CPU/CUDA comparisons passed. Every saved frame passed the predefined finite-value, temperature, density, constraint and tracked stereochemistry checks. The final states were independently read back locally. This establishes usable, numerically checked molecular setups for the specified pilot. It does not establish physical parameter accuracy, equilibrium, a mechanical ranking, a binding free energy or a reaction rate.

## What was actually compared

The comparison is paired within each chemistry. Glucosepane uses two capped 15-residue collagen fragments extracted from the primary authors' equilibrated AGE-only fibril. Its unlinked control restores the modified Arg/Lys residues while retaining the same initial backbone context. Dityrosine uses the accepted human collagen source N-telopeptide, residues 2–22, with a hypothesized intramolecular Tyr4–Tyr6 link and its unlinked peptide control. These are local peptide contexts, not complete triple helices or full tendon/fibril models.

Glucosepane uses the published Amber99-compatible set. Dityrosine uses the locked OpenMM CHARMM36 implementation with the published CHARMM/CGenFF DITY patch. Water follows the respective force-field family. The peptide contexts, force fields, water models and source-model protonation choices differ. Cross-chemistry numerical differences cannot be interpreted as a controlled glucosepane-versus-dityrosine stiffness ranking.

| Model | Solute atoms | Total atoms | Na / Cl | Added salt pairs over initial box volume | Accepted trajectories |
|---|---:|---:|---:|---:|---:|
| GLU_CONTROL | 471 | 12,431 | 11 / 12 | 0.136014 M | 3 × 50 ps |
| GLU_LINKED | 481 | 12,702 | 12 / 11 | 0.134286 M | 3 × 50 ps |
| DITY_CONTROL | 298 | 11,596 | 11 / 10 | 0.137917 M | 3 × 50 ps |
| DITY_LINKED | 296 | 11,384 | 11 / 10 | 0.140929 M | 3 × 50 ps |

Solvent placement requested 0.15 M; the actual whole-box pair concentrations are reported above, with the additional neutralizing counterion separate. The glucosepane control has solute charge +1 e and the linked model approximately −1 e; the source neutral glucosepane representation changes the Arg/Lys charge contribution by approximately two units. Both dityrosine models have solute charge −1 e. Charge differences and their solvent/ion response are part of this model change, not a separately isolated effect of covalent connectivity.

## Chemistry and parameter checks

For glucosepane, the source splits the complete modification between AGS and LGX residue definitions. The connection is AGS:NZ–LGX:CE, with a 1.470 Å source equilibrium distance. The linked starting pair in the authors' equilibrated coordinates is 1.457875 Å. All 80 atoms in the authors' capped reference motif were mapped to the residue graph using elements, degrees, charges, edges and nonedges. Both full collagen-fragment models had zero unresolved parameter terms. The source backbone/ring coordinates were preserved before bounded local preparation; the native control's new hydrogens and restored side chains were minimized.

For dityrosine, the published DITY patch adds CE2–CE2 and removes one HE2 hydrogen from each Tyr. Its paired side-chain charge is zero. The local graph audit covered 41 bonds, 66 angles, 98 proper torsions and 40 nonbonded atom entries with no missing local term. The full peptide Systems also include native backbone impropers and 22 CMAP terms per model. The source's two elevated DITY torsion penalty annotations, 30 and 41.1, remain uncertainty flags; this pilot did not independently fit or benchmark their quantum torsion surfaces.

The dry Reference/CUDA-double comparisons passed for all four models. For the Amber models, a separate OpenMM GROMACS topology reader resolving the published force-field files agreed with the explicit adapter to approximately 10^-14 kJ/mol/atom in energy and 10^-13 kJ/mol/nm RMS in forces. Those comparisons concern two implementations/parsers in OpenMM, not a native GROMACS run or experimental validation. Dityrosine's full-context force-field construction and Reference/CUDA check passed; an independent-engine dityrosine benchmark was not performed.

## Dynamics and measured structural readback

Each model used one solvent build and three recorded velocity/thermostat seeds. Each accepted trajectory used 1-fs integration: 2 ps heating, 8 ps NVT, 10 ps NPT, then 30 ps NPT with the solute restraint set to zero. The target bath was 310 K and NPT pressure 1 bar. The initial heavy-solute restraint strengths were 1,000, 500 and 100 kJ/mol/nm². One starting conformation per model and three velocity seeds do not provide a conformational ensemble or independent solvent-start ensemble.

The marker below is the distance between the two modified-site Cα atoms, evaluated over each run's last 30 ps with periodic minimum-image handling. Numbers are the mean and sample SD across the three replica means, not confidence intervals or an equilibrium PMF. The marker definitions and peptide contexts differ between chemistries. Bond-length values check the formed-link geometry; they are not stiffness estimates.

| Model | Cα marker: mean ± SD of replica means | Formed-link bond: mean of replica means |
|---|---:|---:|
| GLU_CONTROL | 11.5518 ± 1.2000 Å | No inter-residue link |
| GLU_LINKED | 11.1344 ± 0.5357 Å | 1.4931 Å |
| DITY_CONTROL | 7.1590 ± 0.0616 Å | No inter-residue link |
| DITY_LINKED | 7.0470 ± 0.0733 Å | 1.5090 Å |

The glucosepane controls vary substantially between seeds. The dityrosine marker changes are small in this short window. Neither observation is a mechanical test or an established biological difference. The glucosepane control starts from an excerpt of a crosslinked reference pose; its unlinked native ensemble has not been equilibrated independently.

The largest final chemical-bond deviation was 0.128437 Å. The largest saved constraint error was 7.8754047e-07 nm, below the 10^-4 nm limit. No tracked tetrahedral-center sign inversion was found in runtime records or the independent final-coordinate check. The monitored counts are 28 and 31 for the glucosepane control/linked models and 20 for each dityrosine model. All final serialized states record step 50000, time approximately 50 ps and solute restraint parameter k = 0.

## Preserved performance interruption

The first accepted glucosepane-control run used double-precision integration and took about seven minutes. Its projected throughput would not complete the planned set inside the one-hour window. That completed run was retained. A second, incomplete double-precision diagnostic was intentionally stopped for performance; its progress and logs are preserved in `retrieved/attempt-001/` and it is excluded from the twelve accepted trajectories.

The remaining eleven runs used mixed-precision integration, the setting used in the earlier native-link pilot. Energy/force comparisons remained in double precision. Validated dry/wet Systems and physical model inputs were reused with verified identical parameter/input data; no chemical parameter changed. The preserved complete double-precision run and eleven mixed-precision runs have explicit precision/origin labels. Their differing numerical precision is another reason to avoid a quantitative inference from this small pilot. The original shared deadline was retained across both attempts.

At least 21 ps was recorded in the interrupted diagnostic, in addition to the 600 accepted ps. It is not counted as a completed replica. The shared execution window ran from 2026-10-31T13:37:43.137294+00:00 to 2026-10-31T14:00:48.803629+00:00, 23.094 minutes elapsed, within the 60-minute cap. This includes preparation and the performance adjustment, and is not an exact cloud billing total.

## Provenance, retrieval and shutdown

The authors' AGE repository is pinned at `4e51b2bb6ab747ba4c8743b3f676a448f8b26d43`. Git blob identities and SHA-256 values were verified. The 84-MB reference archive's CRC also passed. The exact extracted residues, coordinates and source indices are preserved. A species label was not inferred from the GRO title. The dityrosine parameter archive is the paper-linked Zenodo record 16865891, with its recorded checksum verified. The paper's second Zenodo link resolves to an unrelated taxonomic record; that record was excluded and no unrelated PDF or software executed.

The transport archive SHA-256 is `9e7082d24f7f1dbc95f676c8cfe33f56f0ad32c94be745299e5eb9689c0776b8`. All 199 remotely recorded file hashes match. Both attempts, source versions, interruption notes and resume manifest are preserved. Local independent analyses are additional files. The task VM was stopped after verified retrieval; its disk and raw results were retained.

Only the same nine previously reviewed/approved wheels and pinned Python image ran in the offline, non-root container, with read-only root/inputs, no credentials/home/SSH-agent/Docker-socket mounts, all capabilities dropped and resource limits retained. No new molecular package, native GROMACS, AmberTools, ColBuilder executable, LAMMPS or quantum package was installed or executed. The custom force-field XML retains only the unchanged 301-character native CHARMM version guard, read in full; no author-supplied program ran. Only original standard-library preparation and analysis code ran on the Mac; the simulation libraries ran inside the isolated container.

## Limits and the next useful improvements

These results improve on gas-phase fragment scans by using complete residue connectivity, explicit charge models, stereochemically defined starting structures, compatible force-field-specific solvent and paired unlinked controls. Numerical checks passed, but physical parameter accuracy is not thereby established. The Tyr4–Tyr6 link is a local model hypothesis, the peptide excerpts omit the rest of the fibril, the source contexts differ, and the starting-pose/solvent ensembles are narrow. The high-penalty dityrosine torsions need independent benchmarking before a quantitative mechanical interpretation.

A defensible mechanical ranking next needs a common or explicitly cross-benchmarked parameterization strategy, comparable collagen contexts and attachment sites where chemically possible, controlled protonation/ionic conditions, independent conformer/solvent replicas, and a converged force-extension or PMF protocol. Retain every geometry/convergence flag and reject boundary-minimum fits. The present Cα markers must not be substituted for network stiffness or failure parameters. These models also contain no GAG or decorin, so they do not test H8 binding directly.

The covalent links were present in the topology. No bond-formation/cleavage pathway, redox chemistry, reaction barrier or reaction rate was simulated. The source mfp paper's bond/react/IFF-R procedures were not used here.

## Primary data sources

- [Giannetti et al., introducing AGE crosslinks into atomistic collagen fibrils](https://pmc.ncbi.nlm.nih.gov/articles/PMC13348703/), with the [pinned authors' data repository](https://github.com/gggguido/AGEs-ColBuilder/tree/4e51b2bb6ab747ba4c8743b3f676a448f8b26d43).
- [Graham et al., molecular dynamics of reversible iron–catechol complexes](https://doi.org/10.1016/j.xcrp.2026.103319), used here only as the source of the DITY parameter patch, with the [verified parameter/code archive](https://doi.org/10.5281/zenodo.16865891).

Full details are in `PARAMETER_AUDIT.json`, `RESULT_SUMMARY.json`, `replica_summary.csv`, `prepared/`, `parameters/`, `provenance/` and `retrieved/`. This candidate comparison follows the earlier PYD/DPD pilot. The public snapshot preserves the scientific inputs, exact executed driver versions, both attempts and independent local analysis; account notes and human approval records are excluded.
