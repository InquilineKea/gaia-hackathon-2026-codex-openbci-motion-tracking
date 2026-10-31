# Collagen follow-up: H5, H8 and the completed Brev crosslink calculations

Six focused Gemini reviewers returned 23 observations on H5 recovery dynamics, H8 collagen–GAG interactions and the completed MACE-OFF/MACE-MP Brev crosslink calculations. Codex checked the numerical claims against the frozen source and output tables, checked the cited primary evidence, and corrected the reviewer overclaims below. This is an AI-assisted research critique, not independent experimental validation.

The main result is a change in priorities: test H5's numerical recovery mechanism, make H8 adduct- and interface-specific, and benchmark the crosslink calculations before using their stiffness estimates in a tissue model. The completed calculations support model comparison; they do not yet establish a physiological crosslink ranking.

## Reviewed findings

1. **H5 needs a measured fixed-point residual before its recovery rate can be interpreted.** `CellModel.steady_state()` defaults to six damped iterations without a convergence tolerance. Its output may be close to a fixed point, but the current routine does not establish that. Record the residual of M = 1 + beta Y(M), repeat from low and high starting states, and reject unconverged states before computing the Jacobian. Source: `oxidative-tensegrity/oxt/cell.py`, lines 340–349.

2. **H5 shows recovery-rate modulation, but the current table does not establish critical slowing down or a lifespan clock.** The 62-row table has dY/dM from −0.004605 to 0.155807, recovery rates from 0.125116 to 0.167924 per hour, and no flagged bistable rows. With beta = 1.5, the largest observed loop gain beta·dY/dM is 0.233710; the local two-variable model loses stability at gain 1. Its assumed six-hour myosin timescale sets a baseline near 0.1667 per hour. The variation is real within this calculation; proximity to a bifurcation is not demonstrated. Sweep both timescales and feedback gain, verify finite-difference convergence, and compare the Jacobian prediction with direct small-perturbation recovery. Source: `oxt/cell.py`, lines 351–367, and `results/cpu32/cell.csv`.

3. **The biological motivation for H5 survives; individual lifespan prediction remains a separate hypothesis.** Teuscher and colleagues provide ECM/YAP mechanotransduction context in C. elegans. Pyrkov and colleagues study organism-level recovery properties in longitudinal blood and activity records. Neither establishes this model's six-hour local loop or remaining-lifespan prediction from YAP recovery. A useful experimental test would follow the same organisms through repeated mechanical perturbations and survival, with prespecified age adjustment, held-out prediction, censoring and repeated-measurement controls. [Teuscher et al., 2024](https://pubmed.ncbi.nlm.nih.gov/38177158/), [Pyrkov et al., 2021](https://pubmed.ncbi.nlm.nih.gov/34035236/).

4. **H8 should distinguish free GAG contacts, decorin core binding and intact proteoglycan binding.** Reigle and colleagues found that glucose-glycated type I collagen bound heparin and keratan-sulfate proteoglycan more weakly, while decorin and biglycan binding remained similar. That challenges universal detachment language. Their glucose treatment does not isolate MG-H1 versus CML, so it does not directly falsify the proposed adduct-specific mechanism. Compare free DS/CS chains, decorin core and intact decorin separately, and quantify the actual adduct mixture rather than treating a glycating reagent as a pure modification. [Primary article and methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC2746388/).

5. **H8's fragment scans describe selected gas-phase contacts, not aqueous binding free energies.** The current scans use small rigid fragments without explicit water, counterions or an ensemble of collagen/GAG conformations. Sugar stereochemistry, protonation, anchor distances, closest heavy-atom contacts and orientation coverage need explicit checks. Differences between the CPU and GPU outputs cannot be attributed uniquely to rotation count because the compared setups also differ in other respects. The next numerical improvement is a controlled convergence matrix with fixed molecular inputs and seeds, followed by explicit-solvent sampling. A binding PMF needs a defined separation/orientation coordinate, overlapping windows, independent convergence checks and appropriate restraint/standard-state treatment; an ordinary MD trajectory alone does not supply it. Source: `alchemi_collagen_gag.py` and `results/alchemi_gag/`.

6. **The completed Brev results have substantial disagreement between models.** All seven non-reference chemistries differ by more than 30% under the explicitly defined larger/smaller normalized-stiffness ratio. HLNL differs 5.60-fold and sulfilimine 5.77-fold. Dityrosine is above the pyridinoline proxy in both models, but it is not the highest entry in MACE-OFF: HLNL is 16.29 versus dityrosine's 4.31. These are discrepancies between model outputs, not confidence intervals or measured biological effects. Preserve both models and their absolute curvatures; do not hide the disagreement by averaging them into a single network parameter. Source: the completed `results/alchemi_brev/crosslink_mace_off.json` and `crosslink_mace_mp.json`.

7. **Some stiffness fits need a new scan before interpretation.** `analyse()` fits a quadratic to the five points nearest the global energy minimum. The minimum is at the −6% grid boundary for MACE-OFF sulfilimine and for the MACE-MP pyridinoline reference. The reference problem affects every normalized MACE-MP value. HLNL's minimum occurs at +18.8% strain in MACE-OFF versus +0.2% in MACE-MP. Save the relaxed coordinates, forces and convergence flags at every point; extend and recenter boundary scans; compare forward/reverse paths and several starting conformers; fit a verified local basin and report fit-window sensitivity. A changed minimum can reflect different conformational basins, but the saved energy table alone cannot establish that cause. Source: `alchemi_crosslinks.py`, especially `analyse()`, and the completed Brev energy grids.

8. **Molecular dynamics is a useful next layer, with chemistry-specific inputs and a separate reaction workflow.** The current fragment script represents pyridinoline with a neutral pyridinone proxy and does not place each crosslink in its full collagen environment. Start from complete, charged, stereochemically defined crosslinked peptides and verified parameters. Existing local PYD and DPD collagen coupons provide a practical preparation/stability pilot; these are native enzymatic crosslinks, not substitutes for glucosepane or dityrosine. The follow-on AGE/oxidative comparison needs complete site-specific residue definitions, matched peptide environments and independent replicas. Fixed-topology classical MD can study already formed links and their solvent response. Reaction formation or cleavage needs a defined reactant/product pathway and a validated QM/QM-MM or reactive-potential treatment, with barriers checked independently. Foundation ML potentials are not inherently fixed-topology, but these fragment scans do not validate their reactive chemistry.

## Completed Brev comparison

Each model normalizes its own curvature to its own pyridinoline-proxy value. The reference is therefore exactly 1 by definition. The ratio column is larger/smaller and is not a statistical uncertainty. Absolute reference curvatures are 0.096846 and 0.050813 eV/Å² for MACE-OFF and MACE-MP respectively.

| Fragment chemistry | MACE-OFF relative k | MACE-MP relative k | Larger/smaller ratio |
|---|---:|---:|---:|
| HLNL | 16.290 | 2.909 | 5.600 |
| Pyridinoline proxy | 1.000 | 1.000 | 1.000 by definition |
| Pentosidine | 0.528 | 1.445 | 2.738 |
| Glucosepane | 1.040 | 1.550 | 1.491 |
| Dityrosine | 4.309 | 6.800 | 1.578 |
| Disulfide | 2.150 | 1.048 | 2.051 |
| TG2 isopeptide | 0.603 | 0.802 | 1.330 |
| Sulfilimine | 0.605 | 3.488 | 5.769 |

The completed initial relaxations report final maximum-force values of 0.019736 and 0.019362 eV/Å. This is an improvement over the earlier unconverged pilot. It does not establish convergence of every strain point, the local curvature fit, the molecular representation or the biological extrapolation.

## Reviewer claims corrected during synthesis

| Raw reviewer claim or suggestion | Reviewed treatment |
|---|---|
| H5 slopes only span about −0.004 to +0.005 and recovery is invariant | Recomputed maximum slope is 0.155807; recovery varies. The assumed timescale remains influential, but complete invariance is false. |
| Dityrosine is the stiffest fragment in both completed models | False for MACE-OFF, where HLNL has the larger reported normalized curvature. |
| A changed minimum proves a conformational jump | Possible explanation; coordinates and path continuity are needed to establish it. |
| Glucose glycation directly refutes MG-H1-specific H8 | It bounds the broad claim; the actual adduct-specific comparison was not performed. |
| Rotation count alone explains CPU/GPU contact differences | The comparison is confounded; repeat with matched inputs and settings. |
| Crosslink a (PPG)10 peptide using lysine/arginine/tyrosine chemistry and call MG-H1 a crosslink | PPG lacks those side chains. The modeled MG-H1 is an arginine monoadduct, not an inter-residue bridge. Use an explicit compatible sequence and connectivity. |
| A separate electrostatic term proves double counting | NVIDIA documents a short-range AIMNet2 plus separate electrostatics workflow. The exact wrapper still needs inspection; the addition alone is not proof of a bug. |

The last distinction is supported by [NVIDIA's AIMNet2/Ewald example](https://nvidia.github.io/nvalchemi-toolkit/examples/advanced/08_aimnet2_ewald_pipeline.html); that example does not validate the project's exact wrapper or solvent correction.

## Improvements to carry forward

Implement residual-based H5 convergence and numerical perturbation tests first. For H8, narrow the claim and match the chemistry across computation and experiment. For the Brev scans, preserve every geometry and convergence flag, reject boundary fits, and benchmark representative strain points against an independently validated method. Then run a short solvent/force-field stability pilot on complete collagen-linked structures before committing to long trajectories or extracting mechanical parameters. A later glucosepane/dityrosine comparison should use matched sequences and sites where chemically meaningful, record differences in valence and attachment topology, and separate model sensitivity from sampling uncertainty.

A published parameterization study supplies a useful precedent for collagen AGE models and explicit-solvent simulations, but a fragment archive or a table of constants is not by itself a complete runnable collagen topology. Complete connectivity, residue templates, charges, stereochemistry and compatible force-field terms must be checked together. [Nash et al., Proteins, 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8048459/).

## Run and review record

The follow-up used Gemini `gemini-3.6-flash`, six roles, three concurrent workers and six API requests with no automatic retries. All responses finished normally. Two required local formatting repairs: escaping invalid JSON backslashes in mathematical text and expanding one unambiguous shortened source filename. No scientific wording was changed in those raw reports. The API reported 199,823 input tokens, 7,307 answer tokens and 6,662 thinking tokens, 213,792 total. The source packet contains 37 files with recorded hashes.

The raw run manifest retains its original partial/error status because two responses failed initial JSON/source-name validation. A separate reviewed summary records all six available reports and their repairs. The archive directory named `validated` indicates format, filename and line-range checks; scientific assertions were evaluated separately in this synthesis. Some review prompts contained the same supplied primary-evidence notes, so reviewer agreement is not independent literature confirmation.

The new Brev follow-up instance has been provisioned for the proposed dynamics work. At publication, no new trajectory or reaction calculation from this follow-up is being reported. Existing dry-preparation and solvent-pilot records from a separate local collagen project remain separate evidence and were not in this Gemini source packet. Full records, raw responses, numerical comparisons and source hashes are retained in the local research archive.
