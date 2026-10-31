# Controlled collagen-network connectivity, clustering and hub-bias CPU sweeps: Gemini 4 Argon review

Completed 31 October 2026. These are dimensionless network simulations motivated by collagen mechanics. They are not molecular dynamics, measured collagen properties, validated aging mechanisms, or evidence of a biological phase transition.

## What ran and why

The existing GCP CPU machine completed the controlled campaign after an eight-case CPU benchmark passed. No H100 or new VM was required. The shared GCP machine remains running. The production sweep took 859.95 seconds, about 14 minutes 20 seconds. This is an observed runtime for this particular sparse linear model and matrix, not a throughput promise for molecular dynamics or nonlinear mechanics.

The study follows the [prior matched-stiffness network findings](https://humanavianaisymbiosis.wordpress.com/2026/10/31/matched-stiffness-collagen-network-relaxation-h100-results/) and the [Argon critique and phase-regime study plan](https://humanavianaisymbiosis.wordpress.com/2026/10/31/gemini-argon-collagen-md-critique-network-phase-regimes/). It adopts stiffness matching, explicit topology controls and separate connectivity measurements. Its CPU mechanics are a distinct small-strain linearization, so its numbers must not be combined with the earlier nonlinear H100 results as a replication.

| Batch | Completed cases | Numerical outcome |
| --- | ---: | --- |
| Initial CPU benchmark | 8 | All converged; elastic null passed; 1.34 seconds |
| Production | 1,344 | All converged; 859.95 seconds |
| Central-force elastic control | 336 | All converged; 234.05 seconds |
| Half-time-step refinement | 16 | All converged; limited to width 12 and one seed |
| Critique-led rate controls | 48 | All converged; 46.72 seconds |

The main and control batches comprise 1,744 mechanical cases, plus the eight benchmark cases. They represent 336 graph treatment variants, 311 distinct edge masks and 84 base graph settings. Four seeds per size/setting provide the paired comparisons. Repeated material parameters, controls and time steps are not additional independent specimens. Seed streams are shared across coordination levels; there are 12 size-seed blocks and eight distinct seed identifiers.

## Executed model and interventions

Periodic triangular lattices had widths 12, 18 and 24, corresponding to 144, 324 and 576 nodes. Target mean coordination was 1.2, 1.6, 2.0, 2.4, 3.2, 4.0 or 4.8. Integer directional edge counts slightly change the realized coordination. All four treatment arms match total and directional edge counts at a given size and coordination.

Uniform dilution provides the reference. Triangle-biased and triangle-suppressed alternating-hexagon flips preserve each node's degree while attempting to change triangle closure. Fixed-node degree-squared-biased edge replacements favor degree heterogeneity. Each nonbaseline intervention uses 100 times the node count in proposals. These are finite topology interventions, without demonstrated equilibrium sampling or chain mixing. Maximum degree is six; the hub intervention is not a growing preferential-attachment network.

The mechanics combine quadratic axial extension with collinear bending. The axial energy contains an equilibrium fraction r and a relaxing strain-memory fraction 1−r. Production uses r=1 and r=0.5, with bending coefficients 0.003 and 0.03. Quasistatic sparse conjugate-gradient solves alternate with an exponential frozen-step memory update. Production's assumed rate is exp(min(30,10 times the absolute axial memory mismatch)). Rate-cap activation was not logged. Hold strain is 0.1 and duration is five internal units; neither is calibrated to tissue strain or biological time.

Initial stiffness matching uses stress divided by initial shear modulus G0. In this model that is equivalent to uniformly rescaling the whole energy. It compensates microscopic stiffness as well as architecture. A force-activated crosslink law would be a different constitutive hypothesis and could require a different matching analysis. Final matched stress is algebraically 0.1 times retention; it is not a second independent observable.

## Connectivity and positive shear response are different outcomes

At width 24 and target coordination 2.4, realized coordination is approximately 2.3958. Uniform graphs have a mean largest-component fraction of 0.9171 and winding flags in both periodic basis directions for every seed. The hub-biased graphs have a mean largest-component fraction of 0.4462 and neither winding flag in any seed. Their edge counts remain matched. Topology therefore changes connectivity substantially at the same mean coordination.

The matched-stiffness comparisons at this coordination are ineligible because initial shear modulus is near zero. Directional winding flags describe periodic connectivity; a single diagonal cycle can set both flags. They do not establish two independent winding directions within one component, graph biconnectivity, or full mechanical rigidity.

Of 1,344 production cases, 584 pass the declared matching eligibility criteria and 760 are excluded because G0 does not exceed 1e-6. None of those exclusions is a conjugate-gradient failure. Gates of 1e-8, 1e-6 and 1e-4 produce 584, 584 and 582 eligible cases respectively. The high-density four-pair contrasts below are unchanged across these gates. Conditional retention and unconditioned initial stiffness answer different questions; the packet supplies both, including all-pair stiffness differences at coordination 3.2 where conditional pairing loses some cases. This operational gate is not a universal rigidity threshold.

## High-density hub bias lowers retained stress in this model

At width 24, target coordination 4.8 and r=0.5, all four paired seeds pass the matching gate. The following production values use the strain-accelerated rate. Retention is final stress divided by initial stress; differences are percentage points, not percent relative changes.

| Bending coefficient | Uniform mean retention | Hub-biased mean retention | Hub minus uniform | Four paired differences, percentage points |
| --- | ---: | ---: | ---: | --- |
| 0.003 | 52.2879% | 50.3488% | −1.9391 points | −1.7265, −2.7382, −1.7274, −1.5643 |
| 0.03 | 54.9071% | 50.9915% | −3.9155 points | −3.5089, −4.9281, −4.1303, −3.0948 |

This is a descriptive response to a composite intervention. At the same high-density setting, hub bias raises mean degree variance from 0.9765 to 4.7134 and mean local clustering from 0.31743 to 0.35094, while reducing the mean largest-component fraction from 1 to 0.86589. Bending motifs also change. These comparisons cannot isolate a causal effect of clustering, degree variance or fragmentation.

Four paired seeds are too few for strong distributional inference, especially across many inspected settings. Exploratory pointwise bootstrap intervals are preserved in the derived data for transparency; they are not used here as validated 95% coverage, significance tests or evidence of a phase boundary. The raw paired differences show the observed range without that claim.

## A review led to a direct rate control

The mechanics and numerics reviewers identified a missing comparison: production's strain-dependent axial rate differed from the constant-rate homogeneous reference. A bounded 48-case follow-up added constant-rate and relaxing central-force controls at width 24, coordination 4.8, arms uniform/hub, all four seeds, three bending coefficients and both rate choices.

| Bending coefficient | Hub minus uniform, constant rate | Hub minus uniform, strain-dependent rate |
| --- | ---: | ---: |
| 0 | 0.0000 percentage points | −0.0088 percentage points |
| 0.003 | −1.9277 percentage points | −1.9391 percentage points |
| 0.03 | −3.9175 percentage points | −3.9155 percentage points |

With zero bending and constant rate, both arm means equal 0.5033689735, matching the analytic equal-fraction null 0.5+0.5 exp(−5). The finite-bending hub contrast persists under constant rate. Thus a strain-rate-acceleration-only explanation fails in this tested high-density slice. This does not identify a unique mechanism, separate the topology covariates, or establish the same result throughout the grid. The runtime's separate exp(−5) field is a fully relaxing analytic reference; it must not be confused with the equal-fraction reference.

## The clustering intervention needs improvement

At width 24 and coordination 4.8, the high-triangle and low-triangle arms average 593.5 and 589 triangles. Mean local clustering is 0.31923 versus 0.31557. Degree variance is exactly matched, but mean bending-motif counts are 1106.5 versus 1111.25. Each arm accepts only about 112–115 moves out of 57,600 proposals.

The high-minus-low retention difference at bending coefficient 0.03 is about +0.1666 percentage points. This narrow achieved perturbation, low acceptance, co-changing bending structure and four-seed sample do not support saying that clustering is mechanically unimportant. Dividing this response by the small clustering difference would not produce a reliable causal derivative.

## Numerical checks and provenance

The maximum production force residual is 3.31e-10. Elastic retention error is zero in the saved production summary. The 16 half-step checks change retention by at most 0.00018266, or 0.01827 percentage points. Those checks cover width 12 and one seed, so they do not bound every width-24 result. A small force residual also does not bound displacement along floppy modes.

Numerical execution used existing NumPy 1.26.4 and SciPy 1.14.1 copies inside isolated remote workers with no network access, hidden home directories, read-only dependencies and restricted CPU threads. No new simulation package was installed. Installed package RECORD checks are useful integrity checks, not independent vendor authentication. Exact production/control sources and retrieved outputs have hash records. The preliminary benchmark source was revised in place before production; an exact separate preliminary-source version is not retained. A failed initial control launcher executed no numerical workload; its log is retained. Shared diagnostic filenames preserve their last writer. These qualifications are documented with the data.

## What the Gemini swarm changed

Six Gemini 4 Argon specialists reviewed connectivity, clustering, hubs, mechanics, statistics and numerics. Two adversarial Argon reviewers then checked those critiques against frozen sources and audit tables; the mechanics adversary also received the added rate controls. All eight API calls completed with high thinking settings, 493,517 input tokens, 24,671 visible output tokens and 75,021 reported thinking tokens. Thinking text is not published. Sources, final responses, usage and hash manifests are retained. Same-model agreement is internal review, not independent scientific validation.

The reviewed conclusions preserve valid graph conventions and reject overstated repairs. The conditional finite-cluster mean including isolates is a declared statistic, not inherently a bug. Winding rank and biconnectivity are different concepts. Whole-area renormalization cancels in retention and cannot explain its difference. Seed reuse is a valid blocking choice if dependence is respected. Future active-hexagon proposals need the correct asymmetric proposal adjustment; blindly replacing the current proposal rule would change the sampling measure. Assertions of thermodynamic condensation, exact degree distributions, universal thresholds and biological aging remain unsupported. SOURCE_CHECK_NOTES.md records additional corrections to both specialist and adversarial claims.

## Recommended next simulations

First, reconstruct the deterministic graph masks and verify their saved hashes. Add degree histograms, isolated-node fractions, giant-component internal edges and bends, and per-component winding-vector rank. Keep rank separate from graph biconnectivity and mechanical rigidity. This inexpensive audit would show which structural variables actually move together.

Second, refine time steps at width 24 for all paired seeds at coordination 3.2, 4.0 and 4.8, logging the maximum uncapped rate argument. Extend constant-rate and relaxing zero-bending controls across those settings. Predeclare convergence and numerical-error tolerances before interpreting small effects.

Third, improve motif separation while declaring the target graph measure. Test whether a practically useful degree-preserving clustering difference is reachable while controlling bending motifs. If proposing uniformly from an active-hexagon list, include the forward/reverse proposal-count correction. A separate constrained hub study can hold component membership or triangle density approximately fixed, but those constraints define a new ensemble and need explicit accounting.

Fourth, increase to at least 20 paired seed blocks as an initial replication stage, then use a power analysis tied to a meaningful effect size to set the final count. Preselect contrasts, respect seed blocks and adjust any confirmatory multiple comparisons. Larger sizes and denser coordination sampling would be needed for finite-size threshold analysis. Reproduce selected contrasts in the nonlinear network model before discussing finite-strain behavior. Collagen-specific inference would additionally need defensible chemical parameterization and experimental calibration. The present CPU campaign supplies testable leads for those studies; it establishes no physical phase-transition location.
