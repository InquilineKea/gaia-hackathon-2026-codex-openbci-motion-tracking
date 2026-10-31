# Oxidative tensegrity — how oxidative crosslinks break tissue mechanotransduction, from bonds to organs

A runnable multiscale model for the MIT ScienceClaw hackathon (2026-10-30 → 11-01). One question at every scale:
**what happens when oxidative crosslinks (AGEs such as glucosepane/pentosidine, dityrosine, disulfide
scrambling, peroxidasin sulfilimine) accumulate on top of a healthy, enzymatically (LOX) crosslinked matrix?**

```
 atomistic        crosslink chemistry stiffness            alchemi_crosslinks.py   (ALCHEMI/MACE)        CPU pilot; GPU pending
 fibre network    branching z, iso vs aniso crosslinks,    oxt/network.py          (PyTorch, CPU/GPU)    RUN
                  collagen I / IV / VII, rupture
 viscoelastic     G', G'' under oscillatory shear          remote/lammps/*.in      (LAMMPS)              prepared
 cell             motor-clutch adhesions + 6-strut         oxt/cell.py             (NumPy/SciPy)         RUN
                  tensegrity + YAP + myosin feedback,
                  recovery rate, entropy
 tissue / organ   7 tissues x age, molecule transport,     oxt/physio.py                                 RUN
                  heart ejection fraction, artery PWV
 critique         independent LLM critics                  agents/critic_swarm.py  (Token Factory)       prepared
```

## Quick start

```bash
python3 -m pytest -q tests                      # 10 hardware-free checks, ~3 s
python3 run_sweep.py --profile smoke            # whole pipeline on tiny networks, ~4 min
python3 run_sweep.py --profile local            # 12x12 networks, 2 seeds, ~1 h on a laptop
python3 make_figures.py --results results/local # figures + SUMMARY.md
```

GPU (Nebius H100 job or Brev instance), after the security review is approved:

```bash
bash remote/nebius_job.sh                       # serverless job on Nebius-Academy-8dj, 1 x H100
bash remote/gpu_run.sh                          # on a Brev/Nebius box: 48x48 networks, 8 seeds, finer grids
ALCHEMI_COMMIT=<reviewed sha> RUN_ALCHEMI=1 bash remote/gpu_run.sh   # + atomistic crosslink rigidities
```

## Model

**Fibre network (micro, ECM).** Periodic 2D triangular lattice, bonds diluted to a target mean connectivity z
(the *branching factor*), one bond cut per fibre line so fibres are finite (Broedersz & MacKintosh, Nat Phys 2011).
Energy = fibre stretching + fibre bending + angular springs at locked junctions + an elastin network (never
ruptures) + a GAG embedding. Equilibrium by L-BFGS under a prescribed deformation gradient with Lees–Edwards
images; stress is the first Piola stress dE/dF. Checked against the analytic triangular-lattice moduli
(G = √3/4 μ, C₁₁ = 3√3/4 μ) to 1e-5. Rupture removes bonds above their failure strain and re-equilibrates.

Oxidative crosslinks enter three ways, at matched dose for isotropic and anisotropic modes:
1. *bridging* links between neighbouring fibres (raise z; anisotropic = only along the tension axis),
2. *intrafibrillar* AGEs (stiffer, more brittle fibre segments; anisotropic = preferentially on-axis),
3. *locked junctions* that resist rotation at fibre crossings.
Each chemistry has a relative rigidity `k_rel` (placeholder now; written by the ALCHEMI stage when it runs).

Collagen types: **I** (thick, stiff fibrils, z≈3.4), **VII** (anchoring fibrils, long and flexible, z≈3.0,
disulfide/TG2 crosslinks), **IV** (basement-membrane chicken-wire network, z≈3.8, sulfilimine crosslinks). Tissues
(skin dermis, dermal–epidermal junction, tendon, cartilage, artery media, myocardium, basement membrane) set z,
elastin, GAG, osmotic prestrain (tissue-level tensegrity), alignment, collagen half-life and crosslink accrual;
dose(age) = r·τ·(1 − e^(−age/τ)).

**Cell (micro).** Motor-clutch adhesions (Chan & Odde 2008) with talin-unfolding reinforcement
(Elosegui-Artola 2016) pull on the matrix through its *nonlinear* secant modulus, so strain stiffening is felt.
The cell body is a 6-strut expanded-octahedron tensegrity (actin cables in tension, microtubule struts in
compression); its basal face has no cables, so **the matrix is the tension member that closes it**. A soft or
torn matrix therefore cannot hold the cell's prestress. YAP needs both adhesion signalling and prestress reaching
the nucleus; YAP raises myosin (feedback). Read-outs: YAP N/C, prestress held, traction, *self-support* (holds
≥ half its rigid-anchor prestress without tearing the matrix), bistability.

**Resilience and entropy.** Recovery rate = slowest eigenvalue of the YAP–myosin loop linearised at its fixed
point; it approaches zero near a tipping point (critical slowing down, the quantity Pyrkov/Fedichev track as
"resilience"). Matrix repair rate = turnover × MMP accessibility (crosslinks block collagenase). Entropy proxies:
Shannon entropy of the traction-state distribution (bits) and entropy production of the actomyosin–matrix motor
(k_B/s). These are proxies, labelled as such.

**Macro.** Signalling-molecule delivery (O₂, glucose, IGF-1, TGF-β1, VEGF165, albumin, IgG, exosomes) via
two-population Ogston hindrance through collagen fibres and GAG plus AGE-enhanced matrix binding; LV as a
time-varying elastance with EDPVR stiffness tied to myocardial matrix modulus and contractility tuned to matrix
stiffness (Engler et al. 2008); arterial PWV by Moens–Korteweg.

## Using every ScienceClaw resource

| Resource | Role here | Status |
|---|---|---|
| Python + SciPy/PyTorch | equilibrium, rupture, cell mechanics | **run locally** |
| Nebius Cloud H100 (serverless jobs) | 48×48 networks, 8 seeds, 15 z values, 9 ages | `remote/nebius_job.sh` ready |
| NVIDIA Brev ($150) | same GPU script on an L40S/H100 instance; ALCHEMI tutorials | `remote/gpu_run.sh` ready |
| NVIDIA ALCHEMI Toolkit | batched stretch scans of 8 crosslink chemistries → `k_rel` feeds the network | 101 example run (Docker, CPU); scan piloted on CPU; full run on Brev GPU |
| MACE / MACE-OFF | MLIP inside ALCHEMI; ASE cross-check backend | same |
| LAMMPS | viscoelastic G′, G″ by oscillatory shear | decks in `remote/lammps/` |
| Nebius Token Factory | four independent critics (mechanobiologist, network-mechanics skeptic, geroscientist, statistician) | `agents/critic_swarm.py` ready |
| Nebius Scientific AI platform (MCP) | optional: OpenMM/AMBER steered MD of crosslinked collagen peptides as a second atomistic check | needs team API key |
| Claude / OpenAI / Gemini credits | agents that drive the above | — |

## Results — local run, 2026-10-30 (`results/local/`, 12×12 lattices, 2 seeds: trends only)

Figures in `results/local/figures/`, every number in `results/local/SUMMARY.md`.

1. **Branching factor dominates stiffness, and oxidative crosslinks matter most below the rigidity threshold.**
   Healthy Col I: G rises ~50× from z≈3.2 to 4.6. Dose-1 oxidative crosslinks raise G ~9× at low z but
   only ~1.6–2.3× above the isostatic point. The flexible collagens gain most: Col VII at z≈3.2 goes from
   G≈3.4e-4 to 7e-3 (~21×), Col IV ~30×.
2. **Crosslinks erase strain stiffening** (the stiffness range cells feel by pulling): K(γ=0.35)/G₀ falls from
   6–11 in healthy sub-isostatic networks to ~2.5 at dose 1, and to ~1.1 above isostatic.
3. **Isotropic vs anisotropic.** Matched doses of anisotropic crosslinks give Cx/Cy = 1.8–3.8; isotropic
   ones leave it at the finite-size baseline (0.65–1.0). Tissues: tendon anisotropy 0.94 → 2.5 and artery
   1.17 → 1.84 between ages 20 and 80.
4. **Col I becomes brittle; Col VII becomes stronger but less extensible.** Col I strength is about
   unchanged, but strain at peak stress drops from 0.36 to 0.04–0.08. Col VII gets stronger (0.0095 → 0.016)
   and tougher, while its strain at peak drops from 0.46 to 0.25–0.29. Aged cartilage: modulus ×2.2 and peak
   strain 0.18 → 0.04.
5. **Cells.** YAP saturates (N/C ≈ 3.1) on anything stiffer than ~1 kPa, so oxidative crosslinks change YAP
   mainly on soft, flexible matrices. On healthy Col VII, YAP N/C is 0.70 and the tensegrity holds only 4%
   of its rigid-anchor prestress, so the cell cannot support itself. Crosslinked Col VII pushes YAP to
   2.2–2.7. Recovery rate is lowest (0.12–0.14 /h vs 0.166) exactly where YAP is most sensitive to myosin:
   critical slowing down at the mechanosensing threshold. Traction-state entropy (1.6 → 5.3 bits) and
   entropy production (23k → 48k k_B/s) both rise with matrix stiffness.
6. **Transport.** By age 80, effective diffusivity of matrix-binding growth factors falls to 0.56–0.70×
   (TGF-β1, VEGF165) in tendon, cartilage, artery and skin. Small solutes are unchanged (≥0.99×). Matrix
   repair rate falls 2–4× through crosslink-driven MMP resistance, the tissue-scale loss of resilience.
7. **Heart.** Ejection fraction falls 51.7% → 48.7% and stroke volume 75 → 69 mL from age 20 to 80. PWV
   rises only 6.0 → 6.4 m/s. Real aorta PWV roughly doubles, so the model under-predicts it: elastin
   fragmentation and calcification are not modelled.

Known artefacts: the basement-membrane modulus moves within seed noise; myocardial crosslink dose plateaus at
~0.11 because of the assumed 5-year turnover; the "self-supporting" and "torn" thresholds are judgment calls.
The 48×48, 8-seed GPU profile is what to trust.

## ALCHEMI status

The ALCHEMI 101 multistage pipeline ran in an isolated Docker container (CPU). The crosslink scan runs through
ALCHEMI's FIRE2 + FreezeAtomsHook + NeighborListHook in float64. On CPU a step takes ~17 s per 780 atoms, so
only a partially relaxed pilot (MACE-OFF small) ran locally; the full two-model scan needs the Brev GPU.
ALCHEMI bugs found and worked around are listed in `SECURITY-REVIEW.md`.

Pilot result (`results/alchemi_pilot/`, MACE-OFF23 small via ALCHEMI FIRE2, 56 systems in one batch, 60 steps,
266 s, **not converged**: final fmax 0.30 eV/Å vs 0.05 target). Stretch stiffness relative to pyridinoline:
dityrosine 3.2, sulfilimine 2.9, HLNL 2.5, disulfide 1.3, pentosidine 1.2, glucosepane 1.0, TG2 isopeptide 1.0.
Peak resisting force is lowest for the disulfide (0.18 eV/Å), the weak link. Two cautions: unconverged
relaxation overestimates stiffness (likely why the long HLNL chain ranks high), and fragments differ in length,
so k_rel mixes linker geometry with chemistry. The pilot is therefore **not** fed into the network
(`results/crosslink_params.json` is absent, so placeholders stay in use). It already contradicts one
placeholder: glucosepane comes out no stiffer than pyridinoline, not 1.8×.

## Caveats

2D networks (isostatic point z = 4, not 6 as in 3D); small local lattices (finite size); all parameters are
literature-informed assumptions, not fits; pyridinium/charged crosslinks neutralised in the atomistic fragments;
non-reactive MLIPs give stiffness, not bond rupture; the cell is one tensegrity unit, not a cytoskeleton; organ
models are lumped. Treat trends, not absolute numbers.

See `SECURITY-REVIEW.md` before running anything third-party, and `AGENTS.md` for the shared cross-agent status.
