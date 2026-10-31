# Execution and interpretation record

Study date: 2026-10-31. User authorization: US$25 total. Study window began 15:36:23 UTC; all study-related instances were verified STOPPED at 16:34:44 UTC. Pricing the full 0.97257-hour window at $5.40/hour gives $5.2519. This is a conservative elapsed-window compute estimate, not a billed usage statement, and excludes small prorated storage charges. Instances were operated sequentially. Two new 50 GB disks remain after shutdown, pending explicit deletion authorization; together their listed storage rate is $12.264/month. The older stopped calibration instance is not part of that newly created storage.

## Infrastructure and deviations

An earlier stopped H100 failed to resume. A new replacement completed commissioning but later lost its SSH gateway. The recovery API returned an internal-server error. Those instances were stopped before a second replacement was used. Direct provider SSH with agent forwarding disabled restored access to the second replacement after its gateway also failed. No private account details, addresses, keys or connection files are included in this public package.

The initial FIRE optimizer was inadequate for many low-force residual targets. A main hold batch is retained even though only 126/256 trajectories passed. The original fracture expansion and a first long optimizer check were interrupted before complete trajectory files were emitted; their partial diagnostics are retained. Two 16-case one-step hold batches are optimizer diagnostics only, not scientific relaxation protocols. An original five-pair limited-memory BFGS optimizer with energy-decreasing line search then replaced FIRE; the physical energy and internal-variable law were unchanged. Failed equilibrium terminates a revised case, rather than accumulating an apparently complete curve from unresolved states.

## Completed revised production

| Batch | Cases | Full-path converged | Seeds | L | Strain step | Time step | Force tolerance | Iteration cap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lbfgs-hold | 256 | 254 | 16 | 24 | 0.005 | 0.05 | 1e-8 | 20000 |
| lbfgs-fracture | 256 | 246 | 8 | 24 | 0.005 | 0.05 | 1e-8 | 20000 |
| lbfgs-large | 128 | 120 | 8 | 48 | 0.005 | 0.05 | 1e-8 | 30000 |
| lbfgs-refined-hold | 64 | 64 | 4 | 24 | 0.005 | 0.025 | 3e-9 | 50000 |
| lbfgs-refined-fracture | 128 | 101 | 4 | 24 | 0.0025 | 0.025 | 3e-9 | 50000 |
| fracture-half-fixedtol | 128 | 126 | 4 | 24 | 0.0025 | 0.025 | 1e-8 | 50000 |
| fracture-quarter | 128 | 126 | 4 | 24 | 0.00125 | 0.0125 | 1e-8 | 50000 |
| fracture-eighth | 128 | 127 | 4 | 24 | 0.000625 | 0.00625 | 1e-8 | 50000 |

The hold ramp is hard-coded to 20 mechanical increments of 0.005; its passed CLI strain-step argument is unused. Hold refinement therefore checks time integration and force tolerance, not ramp strain-step convergence. Internal memory updates freeze geometry and the strain-dependent rate for each exponential update; this is a split, approximate integration of the stated continuous law. The first fracture refinement changed both time/strain resolution and tolerance. Three extra batches at fixed 1e-8 tolerance were added to isolate step effects; the paired comparison uses the same four seeds. No additional physical parameter was tuned to improve architecture contrasts. Row capacity increased from 1000 to 4000 for the finest traces; the earlier successful kernel is retained as network-lbfgs-primary.cu. Source/network.cu is the final kernel, executed-source/ is the exact remotely returned source snapshot, and source/ additionally contains updated local analysis. Source/network-fire.cu preserves the earlier optimizer.

Total saved case trajectories: 1600, of which 32 are optimizer diagnostics. Full-path convergence: 1394. These counts include repeated seeds, resolutions and solvers; there are only 50 distinct graph realizations. Three sizes: 144, 576 and 2304 nodes. A graph is identified by L, seed and architecture, not by the constitutive law or rupture threshold. The 1215 paired contrasts include exploratory outputs and are not multiplicity-adjusted tests.

## Interpretation rules

The raw stage labels are 0 for the small-strain stiffness probes, 1 for hold, 2 for post-damage loading, and 3 for pre-damage loading. A failed solve is cumulative within a trajectory. Full-path convergence and finite outputs are necessary for full curve comparisons. First-damage onset uses a converged pre-damage prefix, even if a later part of that specimen fails. Work to 0.8 is supplied only for complete converged damage curves; partial observed work and peaks are explicitly different fields. Absence of first damage before the end is not a measured damage threshold.

Primary hold step/tolerance comparisons use 62 complete common cases. All accepted primary hold paths remained below 0.10 maximum segment extension. Displacement nonaffinity is sensitive to solver choice and is not used as a reliable headline result. For fracture refinement, initial-state strain/nonaffinity comparisons are omitted because the first saved strain changes with the loading increment. The final two fracture resolutions share 126 complete curves; all 128 first-damage prefixes are accepted. Relative outliers are retained even when the median is small.

## Software and integrity

NVIDIA H100 80 GB HBM3, driver 580.173.02, CUDA compiler package 13.0.88-1, CUDA runtime 13.0.96-1, GCC/G++ 13.3.0. No new packages, repositories, containers or model downloads were used. CUDA compilation and simulation occurred in a bounded remote service as an unprivileged user with network disabled, home hidden and a dedicated writable directory. Package verification reported no mismatches. Vendor image/toolchain provenance was not independently attested; this remains a disclosed supply-chain limitation.

The final returned archive's 92 checksum entries were verified against the extracted files before shutdown. The raw remote checksum file refers to paths relative to the remote study root. For its source/* entries, use executed-source/* in this distribution; current source/ includes later local analysis edits. A final local manifest covers the distributed package separately. Code correctness tests are not physical validation.

Reported revised execution times (seconds): hold 7.522; fracture 23.726; large 45.458; refined hold 15.787; refined fracture 57.954; fixed-tolerance half step 39.157; quarter step 66.807; eighth step 109.275. These are workload timings from the program and are not a controlled GPU-versus-CPU speedup benchmark. Provisioning, recovery, compilation and inspection dominate the elapsed billable window.
