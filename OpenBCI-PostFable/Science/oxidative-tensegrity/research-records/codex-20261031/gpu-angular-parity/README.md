# Collagen CUDA angular parity passed; normalization and 3D atlas review

31 October 2026. The bounded Nebius CPU/GPU parity test completed successfully on an existing idle H100. All 20 check groups passed, including the 24 saved established-CPU-callback states comprising 23,330 angular evaluations. No new instance or volume was provisioned; the worker was left running and its GPU returned to idle. No production 3D architecture-atlas simulations ran in this test.

## Numerical results

The original module represents four distinct laws: signed 2D harmonic hinges, wrapped 2D hinges, unsigned 3D bending and 3D cosine locks. Six device kernels build periodic arms, evaluate angular terms, gather node forces, reduce energy/virial and differentiate with respect to deformation. Frozen activity masks represent broken fibres/locks; damage timing remains the network solver's responsibility.

Across 818 angular cases, largest scaled per-term CPU/GPU error was 4.35e-15. Force finite-difference error was 4.15e-11 and affine-virial finite-difference error was 2.40e-10. The 24 established CPU callback snapshots passed at both mild and severe prescribed deformation: CPU/reference force error <=7.21e-16; GPU/CPU assembled-force error <=5.21e-18; GPU/global energy-virial reduction error <=5.75e-16. Scaled error is abs(a-b)/(1+abs(a)+abs(b)); thresholds were unchanged. All active valid fixtures remained finite. Dead-term zeros, invalid-state counts, same-device deterministic repeats, empty topology and fixed-coordinate deformation derivatives passed.

These are numerical component and frozen-state validations. They do not commission an entire FCC3D equilibrium/fracture trajectory, establish collagen accuracy under extreme stress, or validate molecular chemistry/contact/sliding. Device memory/race-sanitizer and full-trajectory/damage-onset comparisons remain follow-up gates. The optional LAMMPS callback is still transfer-based; the default production backend was not automatically switched.

## Timing and resource bounds

| Angular terms | GPU resident kernel chain | GPU host adapter | CPU term adapter |
|---|---:|---:|---:|
| 1,024 | 0.118 ms | 7.42 ms | 2.60 ms |
| 16,384 | 0.365 ms | 73.45 ms | 39.72 ms |
| 65,536 | 0.895 ms | 301.14 ms | 191.19 ms |
| 262,144 | 4.627 ms | 1,571.61 ms | 880.09 ms |

Ten resident repeats per size. GPU host adapter includes allocations, transfers, force gathering, reduction and downloads; CPU term adapter includes input/output marshalling and term evaluation but not the same gather/reduction work. Resident kernel timings exclude transfers and allocations. These are deliberately separate measurement scopes, not a fair full-integrator speedup comparison. The current host adapter gives no demonstrated production speedup; production should retain data on device and benchmark the whole solver.

The process ran offline as UID 65534 in private namespaces under a 4 GiB host-memory cgroup, two CPU cores and a 600-second timeout plus ten-second kill grace. The observed interval was approximately eight seconds from host file timestamps (one-second resolution). No capacity was added. At the observed official public H100 rate of $4.50/hour, a conservative ten-second attribution is $0.0125; the full 610-second bound would be $0.7625 of existing capacity. Account-specific settled billing was not checked. The authorized incremental-spend ceiling was $2. Source: [Nebius pricing](https://nebius.com/prices).

All eight retrieved remote file hashes matched. Raw reports, completion marker, logs, PTX, executed numerical source and frozen CPU fixtures accompany this packet. The original compiled CPU shared library is retained locally and its hash is in the remote manifest; the public packet omits that platform-specific binary. No credentials, account identifiers, host IPs, software wheels or private account responses are included.

## Does renormalization work?

For the current zero-elastin model, multiplying all elastic stiffnesses by s multiplies energy, force, stress and moduli by s while preserving displacement-controlled equilibrium geometry and strain-based damage thresholds. Matching s=G_target/G_initial is therefore a valid scalar initial-stiffness control under those assumptions. It changes microscopic stiffness parameters, so fixed-material E1 and matched-G E2 answer different questions.

The current helper omits mu_el. Its exact-scaling claim fails at nonzero elastin/background: mu=1, mu_el=0.1 and s=2.3 give stiffness ratio 2.181818 rather than 2.3, a 5.14% shortfall. This analytic counterexample and static source audit are saved; active/historical runs were not rewritten. Correct and independently test that path before collagen–elastin work. Reject unresolved/negative initial G rather than relying on a denominator floor, and independently verify the achieved matched modulus.

Matching G_xy does not match a 3D anisotropic stiffness tensor, relaxation time, fracture mechanism or physical chemistry. It is also distinct from real-space renormalization. [Shivers et al.](https://arxiv.org/abs/1807.01205) develop a renormalization/scaling theory for specified idealized fibre-network classes. Testing it here requires reversible strain/size/bending sweeps, independent realizations, declared scaling fits and held-out prediction; current parity does not establish universal critical behaviour. Read RENORMALIZATION_AUDIT.md for the equations and limits.

## The 3D architecture-atlas proposal

The proposal is a useful next study after full-solver and generator validation. A concrete screening design is 3 generators × 15 settings × 8 paired realization blocks = 360 records, with 720 E1/E2 mechanical evaluations before additional loading protocols, sizes or convergence checks. The accompanying randomized CSV is proposed, not executed. It uses controlled orientation/loading/connectivity/curvature/link-placement contrasts plus four selected interactions, with explicit matching failures and graph-level replication.

Three issues must be resolved before execution: phantomization changes junction topology and usually imposes binary junctions with z<=4; stochastic 3D fibres require a defined finite capture/connection rule; curved geometry needs correct stress-free rest angles and segment resolution. Matching node count alone does not match collagen volume fraction or material law. The proposed common z targets are 2.8, 3.2 and 3.6; achieved geometry/degree/volume distributions and failures must be retained.

Separate E1/E2, loading directions and repeated measures; add finite-size checks beyond 360. Fracture energy needs an appropriate complete crack/interface observable; pure elasticity does not provide hysteresis or time-dependent recovery, and threshold damage is not a calibrated fatigue law. Pareto strength/fracture/recoil rankings need uncertainty and held-out confirmation. Compare compatible experimental collagen conditions before molecular aging or elastin coupling. Full design and primary references are in ATLAS_DESIGN_REVIEW.md.
