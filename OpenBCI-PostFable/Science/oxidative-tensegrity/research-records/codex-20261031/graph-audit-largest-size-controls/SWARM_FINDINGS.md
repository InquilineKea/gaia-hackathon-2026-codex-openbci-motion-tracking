# Graph audit and largest-size time-step/rate controls: reviewed collagen-network follow-up

Completed 31 October 2026. This is a dimensionless, small-strain network study motivated by collagen mechanics. It is not molecular dynamics, a chemical crosslink comparison, calibrated tissue mechanics or a physical phase-transition measurement.

## What this follow-up resolves

The [previous controlled CPU study](https://humanavianaisymbiosis.wordpress.com/2026/10/31/controlled-collagen-connectivity-clustering-hub-bias-cpu-sweeps/) found lower retained stress after a hub-biased topology intervention, while warning that clustering, fragmentation and bending structure changed together. Its time-step refinement covered only a smaller lattice. This follow-up reconstructs every prior graph exactly, measures the missing component structure, and tests the largest lattice with finer time steps and broader rate controls.

All 336 prior graph treatment variants reconstructed with identical edge-mask hashes. All 384 new mechanical cases converged. The 96 eligible fine-step comparisons passed the predeclared per-case tolerance of 0.01 percentage points in retention. Hub-minus-uniform retention remains negative in every tested paired seed for both bending coefficients and all three coordination settings. These are descriptive results from the same four seed blocks, not additional independent replication or an isolated causal effect of hubs.

The audit ran in 503.57 seconds and the controls in 857.44 seconds, concurrently on two single-thread CPU workers of the existing GCP machine. No new VM, GPU or numerical package was needed. The shared machine remains running.

## Scope and reproducibility

The audit covers widths 12, 18 and 24, seven coordination targets, four original seeds per size/setting and four treatment arms. The 336 variants contain 311 distinct edge masks. Reconstructing them adds observables, not specimens. The generator's graph function is identical to the previously executed source at the syntax-tree level, and every reconstructed mask matches its saved SHA-256. Full degree sequences remain identical between each triangle intervention and its uniform reference. Total and directional edge counts remain matched across treatments.

The controls use width 24, or 576 nodes, at target coordination 3.2, 4.0 and 4.8. All four arms, two bending coefficients and time steps 0.1, 0.05 and 0.025 give 288 strain-dependent-rate cases. Uniform/hub rate controls at three bending coefficients, two rate choices and time step 0.1 give 144 cases, with 48 overlaps counted once: 384 unique new mechanical cases.

The axial/collinear-bending quadratic energy and quasistatic strain-memory model are unchanged. Equilibrium fraction is 0.5, hold strain 0.1 and duration five internal units. Beta=10 uses the assumed strain-dependent rate; beta=0 uses unit rate. Times and material parameters lack biological calibration. Stiffness matching divides stress by initial shear modulus G0, equivalent here to rescaling the entire energy. This changes microscopic stiffness as well as architecture. Final matched stress is 0.1 times retention and is not independent corroboration.

Nineteen remotely hashed files were retrieved and verified, including exact executed sources, inputs and worker diagnostics. Comparison with 144 prior reference rows, representing 128 unique case keys, gives exactly zero difference in both G0 and retention. Separate output directories preserve each worker's diagnostics. The numerical runs had no network access or home-directory access and used read-only copies of existing NumPy 1.26.4 and SciPy 1.14.1. File hashes and prior installed RECORD checks do not independently authenticate vendor provenance.

## The graph audit changes the connectivity interpretation

Nine of 336 treatment variants, representing seven distinct masks, have both old directional winding flags true but no component with rank-two cycle winding. For example, the width-24 hub graph at coordination 3.2 and seed 74000 has a giant component of 378 nodes and 921 edges, with primitive winding vector (1,−1) and rank one.

A diagonal cycle can have nonzero winding in both basis directions while spanning only one independent direction. The old flags correctly implemented their stated definition; reading them as two independent winding directions would be wrong. The new rank is computed separately for each component. Primitive vector normalization preserves span rank, not the full integer homology subgroup index. Neither winding rank nor the old flags establish graph biconnectivity or complete mechanical rigidity.

Exact component counts also replace the earlier heuristic that giant-component mean degree might equal whole-network degree divided by giant fraction. That identity requires all edges to lie in the giant component. In 200 of the 336 variants, some edges lie elsewhere. The packet now records giant edges and nodes directly, so its reported mean degree is the per-graph quantity 2E_giant/N_giant, averaged over seeds.

| Width-24 target coordination | Arm | Mean isolated-node fraction | Mean exact giant degree | Rank-two giant components, out of four |
| --- | --- | ---: | ---: | ---: |
| 2.4 | Uniform | 4.5573% | 2.5564 | 4 |
| 2.4 | Hub-biased | 47.5260% | 4.6982 | 0 |
| 3.2 | Uniform | 0.9983% | 3.2379 | 4 |
| 3.2 | Hub-biased | 35.4167% | 4.9968 | 2 |
| 4.8 | Uniform | 0.0000% | 4.8021 | 4 |
| 4.8 | Hub-biased | 13.4115% | 5.5463 | 4 |

At coordination 4.8, mean hub degree counts for degrees zero through six are 77.25, 11.75, 15.5, 13.5, 16, 33.25 and 408.75 nodes out of 576. The finite graphs concentrate strongly at degrees zero and six, while retaining intermediate degrees. An exact zero/six-only distribution is false. This finite histogram does not establish thermodynamic condensation, sampler equilibrium or a growing preferential-attachment process.

At the same setting, giant-component bending-motif counts average 1310.75 for hub-biased graphs versus 1108.75 for uniform graphs. Whole-network mean degree is matched, but giant density, isolated-node fraction, degree distribution, clustering and bending structure remain coupled. The audit makes that coupling measurable; it does not remove it.

## Largest-size time-step checks pass the declared observable tolerance

All 384 solves completed the full internal duration, with maximum force residual 3.72e-10. Of these, 376 pass the matched-stiffness eligibility criteria. The eight exclusions are uniform, zero-bending cases at coordination 3.2 under the two rate choices. They converged but fail the positive-initial-shear-stiffness gate; the hub counterparts are eligible. Thus there is no eligible uniform/hub zero-bending pair at that coordination.

All 96 fine-step comparisons in the finite-bending, strain-dependent-rate matrix are eligible. The largest retention difference between time steps 0.05 and 0.025 is 0.0000960511 as a fraction, or 0.00960511 percentage points. It is below the predeclared 0.01-point per-case limit, with little margin at the worst case. The largest difference between the original 0.1 step and 0.025 is 0.0293849 percentage points.

Passing this check supports numerical adequacy for the tested retained-stress observable at these settings. It does not prove the zero-step limit, trajectory accuracy, uniqueness of displacement in floppy modes or physical correctness. The largest within-seed change in a treatment contrast between the two finer steps is 0.0106946 percentage points. That is a different quantity from the predeclared individual-case gate; no claim is made that every contrast change is below 0.01 points.

The largest uncapped rate argument sampled before an update is 1.04602, compared with the implemented cap at 30. No cap activations occurred at the sampled update states in these runs. This closes the previous logging gap without establishing behavior between update states or outside the tested matrix.

## Retained-stress differences survive finer steps

The following contrasts use beta=10 and compare hub-biased minus uniform retention within the same seed. Differences and ranges are percentage points. Each row has four paired seeds; these are descriptive values without a significance or population-confidence claim.

| Target coordination | Bending coefficient | Mean contrast at step 0.1 | Mean contrast at step 0.025 | Range of four contrasts at step 0.025 |
| --- | ---: | ---: | ---: | --- |
| 3.2 | 0.003 | −42.6397 | −42.6170 | −44.5314 to −40.1476 |
| 3.2 | 0.03 | −25.5536 | −25.5233 | −29.5885 to −21.6908 |
| 4.0 | 0.003 | −15.3752 | −15.3588 | −19.7277 to −12.9267 |
| 4.0 | 0.03 | −10.5376 | −10.5243 | −11.3632 to −8.9993 |
| 4.8 | 0.003 | −1.9391 | −1.9374 | −2.7356 to −1.5629 |
| 4.8 | 0.03 | −3.9155 | −3.9103 | −4.9215 to −3.0903 |

For the last row, the four fine-step differences are −3.5044, −4.9215, −4.1249 and −3.0903 points. The direction survives refinement in every observed paired hub contrast. The especially large lower-coordination differences remain results of the declared topology/material normalization and assumed model; they are not predictions of a corresponding biological effect.

Triangle-high minus triangle-low differences remain heterogeneous across seeds. At coordination 4.8 and bending coefficient 0.03, the fine-step mean is +0.1664 points, with four values +0.1961, +0.4843, −0.0847 and +0.0699. At other settings, means and seed signs vary. Refinement does not convert the weak achieved clustering intervention into an isolated causal test: triangle arms preserve degrees but also change bending motifs, and their finite chains do not demonstrate mixing. These results support neither a universal clustering ranking nor a claim that clustering has no mechanical effect.

## Broader rate controls preserve the composite hub contrast

The new constant-rate comparison extends the previous coordination-4.8 control to 3.2 and 4.0. Both columns below use time step 0.1, the same four paired seeds and finite bending. Beta=0 controls were not refined to the smaller steps in this campaign, so the fine-step tolerance above does not apply to them.

| Target coordination | Bending coefficient | Hub minus uniform, constant rate | Hub minus uniform, strain-dependent rate |
| --- | ---: | ---: | ---: |
| 3.2 | 0.003 | −42.5477 points | −42.6397 points |
| 3.2 | 0.03 | −25.5244 points | −25.5536 points |
| 4.0 | 0.003 | −15.3519 points | −15.3752 points |
| 4.0 | 0.03 | −10.5459 points | −10.5376 points |
| 4.8 | 0.003 | −1.9277 points | −1.9391 points |
| 4.8 | 0.03 | −3.9175 points | −3.9155 points |

The contrast persists under unit rate in all six tested finite-bending slices at this time step. Strain-rate acceleration alone therefore cannot explain its appearance within these comparisons. This does not isolate a bending, degree or fragmentation mechanism, or establish equivalence between rate laws.

For eligible zero-bending pairs at coordination 4.0 and 4.8, constant-rate arm means agree with the equal-fraction homogeneous reference 0.5+0.5 exp(−5), with essentially zero paired contrast. Accelerated zero-bending contrasts are small but nonzero, approximately −0.0647 and −0.0088 points respectively. At coordination 3.2 there is no eligible zero-bending matched pair; an absence-of-effect claim cannot be extended there.

## Final-time agreement does not imply transient rate agreement

A numerical reviewer suggested examining earlier times in the existing saved traces. This required no additional simulation. At coordination 4.8, bending coefficient 0.003 and time 0.5, switching from unit to strain-dependent rate changes mean normalized stress by −4.7309 percentage points in uniform graphs and −5.5429 points in hub-biased graphs. The hub-minus-uniform gap at that time changes from −0.8331 to −1.6452 points. All values use the original 0.1 step and the same four seeds.

Thus substantial intermediate-time rate sensitivity coexists with similar final-time topology contrasts. The simple homogeneous exp(−5) reference is not a universal bound on stress tails in the coupled bending/axial-memory network. A unique energy-partition mechanism has not been measured here; resolving it requires explicit stress/energy decomposition and appropriately refined transient controls. The packet includes derived comparisons at times 0.2, 0.5, 1, 2 and 5, with paired values preserved.

## Review and next decisions

Three Gemini 4 Argon specialists reviewed graph reconstruction, numerical controls and inference, followed by an adversarial Argon critique of their findings. Frozen inputs, final responses, usage and hash records accompany this report. All four calls completed, using 275,922 input tokens, 13,583 visible output tokens and 30,861 reported thinking tokens. Model thinking text is excluded. SOURCE_CHECK_NOTES.md and the individual claim-audit files record the final adjudications. This is internal review using one model family, not independent experimental or literature validation.

The next useful simulations should separate mechanisms rather than add more versions of the same composite perturbation. First refine the beta=0 comparisons where a rate-law equivalence claim matters: covering both finer steps for two arms, three coordination values, four seeds and two bending coefficients would require 96 additional cases. Then add a diagnostic replay to measure axial and bending energies and consistently defined stress contributions without changing the constitutive law. The saved stress/RMS traces do not retain displacement or memory fields needed for an exact retrospective decomposition. Then define a constrained topology study that separates giant-component membership, component density and bending motifs from triangle closure or degree heterogeneity. Constraints change the ensemble and must be stated. An active-hexagon sampler requires the correct forward/reverse proposal adjustment if its proposal neighborhood is state dependent.

Increase independent seed blocks only after selecting the primary contrasts and a meaningful effect size; the same four old seeds do not provide a powered confirmatory study. A dense coordination grid and larger sizes would be needed for finite-size boundary analysis, with connectivity, winding rank and independent mechanical response modes measured separately. Selected contrasts should then be checked in the nonlinear model before discussing finite-strain behavior. Collagen-specific conclusions still require defensible chemistry, material calibration and experimental comparison. This campaign resolves graph interpretation and a bounded numerical uncertainty; it establishes no physical phase-transition location.
