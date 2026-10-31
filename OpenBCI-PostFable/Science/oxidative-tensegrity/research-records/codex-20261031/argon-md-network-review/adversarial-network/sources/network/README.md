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

## Results — GCP 32-vCPU run, 2026-10-31 (`results/cpu32/`, 16×16 lattices, 4 seeds, 8 branching values)

Confirms the local trends with tighter error bars; one local number was a small-lattice artefact.

- **Branching:** healthy Col I G rises ~260× from z = 2.8 to 5.0. Dose-1 oxidative crosslinks multiply G ~14×
  at z = 2.8 but only 1.4–2.2× above z = 4.
- **Strain stiffening erased:** K(γ=0.4)/G₀ in healthy sub-isostatic networks is 8.8 (Col I), 14.7 (Col VII),
  12.8 (Col IV) at z = 2.8. It falls to 3–4.6 with dose-1 crosslinks and to ~1.1 for every network at z = 5.
- **Anisotropy:** anisotropic crosslinks give Cx/Cy = 1.2–3.6, rising with branching; isotropic stay 0.68–0.94.
- **Brittleness, corrected:** Col I strain-at-peak falls 0.20 → 0.08 (aniso) / 0.11 (iso). The local run's
  0.36 baseline was a 12×12 artefact. Strength rises slightly (0.0167 → 0.018–0.021); toughness is unchanged.
  Col VII: +25% strength, +23% toughness, strain-at-peak halves (0.51 → 0.26–0.28). Col IV: 0.31 → 0.14–0.17.
- **Cells:** healthy Col VII holds 14% prestress, YAP N/C 0.75, not self-supporting; isotropic dose-1
  crosslinks make it self-supporting. Recovery is slowest (0.125–0.14 /h) in the soft transition zone.
- **Heart:** EF 51.7% → 49.3% from age 20 to 80, mostly from arterial elastance.

## GAG sliding vs crosslinks (`run_gag.py`, GCP, 12×12, 4 seeds; `results/cpu32/gag*.csv`, fig6)

Question (from a ChatGPT design session): can crosslinking stiffen collagen yet cost it resilience by blocking
GAG-mediated fibril sliding? Three GAG models at matched collagen and GAG count, three load cycles below fibre
rupture (6% tension, 12% shear).

- **Sliding GAGs + crosslinks:** stiffness rises ~6× from dose 0 to 1, while the dissipated fraction per cycle
  falls from 0.54–0.56 to 0.09–0.10 (dose 0.5) and 0.02–0.08 (dose 1); slip events fall ~3×.
- **Partly by construction, partly emergent.** Slip is assumed blocked at crosslink-locked junctions. At dose 0.5
  only ~44% of links are pinned, which alone predicts a loss ratio near 0.31; the observed 0.09 means the stiffer
  network also starves free links of strain.
- **Which GAG model fits tendon data.** Removing sliding GAGs barely changes stiffness (0.053 → 0.042 in
  tension) but abolishes dissipation, as tendon GAG-removal experiments report. Bridge GAGs instead predict a 2.8×
  modulus drop on removal, contradicting that data.
- **Polyelectrolyte GAGs** dissipate only by fibre rupture at dose 1 (damage, not resilience).

## Collagen–GAG interface vs glycation (ALCHEMI + AIMNet2; `results/alchemi_gag/`)

Rigid gas-phase contact energies of capped Lys/Arg and their glycated forms with dermatan-sulfate disaccharides
(0/1/2 sulfates), on CPU (6 orientations) and the Brev L4 (24 orientations). Robust across both: **MG-H1-Arg is the
weakest binder and the only one pushed out of contact (4.0–4.5 Å)**; Arg binds more strongly than Lys; CML-Lys stays
bound. Magnitudes moved by up to ~0.5 eV between machines (RDKit conformers differ across CPU architectures;
batch effects were ruled out), so averaging over conformers is the next step. See H8 in `HYPOTHESES_EWALD.md`.

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
placeholder: glucosepane comes out no stiffer than pyridinoline, not 1.8× (later shown to depend on the starting
conformer; see the PM7 section).

## Converged crosslink scan on Brev (`results/alchemi_brev/`)

Both machine-learned potentials converged on the NVIDIA L4 (final force 0.020 and 0.019 eV/Å; ~45 min each, 168
systems in two-chemistry GPU batches). Stretch stiffness relative to pyridinoline, MACE-OFF / MACE-MP: dityrosine
4.3 / 6.8, glucosepane 1.0 / 1.55, TG2 isopeptide 0.6 / 0.8, disulfide 2.2 / 1.05, pentosidine 0.5 / 1.4,
sulfilimine 0.6 / 3.5, HLNL 16.3 / 2.9. Rank correlation between the models is only 0.48. These values are **not**
fed into the network model. *Superseded by the PM7 check below: the disagreement comes from the measure and the
starting conformer, not from the potentials.*

## PM7 tie-breaker and conformer check (`pm7_crosslinks.py`, `compare_crosslink_models.py`)

Same fragments, anchors and 21 strains, relaxed with semi-empirical PM7 (MOPAC 23.2.5, reviewed in
`SECURITY-REVIEW.md`) on the Brev box in a no-network container: 504 optimisations (3 RDKit conformer seeds),
none failed, ~15 min on 4 CPUs. Full tables: `results/alchemi_brev/crosslink_model_comparison.md`.

- **Curvature at the energy minimum (`k_rel`) is not a usable measure.** All three methods disagree on it
  (Spearman 0.40–0.48), and the energy minimum often sits far from the unstrained length (HLNL: step 16 of 21 in
  MACE-OFF, 14 in PM7), so the quadratic fit tracks conformational rearrangements, not bond stiffness.
- **Peak force agrees across methods from a shared start** (Spearman 0.95–0.98 between MACE-OFF, MACE-MP and PM7,
  all from seed 7), **but not across conformers**: PM7 from two other conformers ranks it with Spearman 0.48
  against seed 7. Pyridinoline's anchor distance ranges 6.8–10.3 Å by conformer and its peak force 0.15–4.15
  eV/Å. The scan mostly measures how much slack the fragment's starting conformer has.
- **Robust across methods and conformers:** dityrosine is stiff (1.81–1.88 eV/Å, rigid biaryl, same length in
  every conformer); disulfide (0.06–0.08) and TG2 isopeptide (0.06–0.16) are soft. **Not determined:**
  glucosepane vs pyridinoline, HLNL, pentosidine, sulfilimine. The earlier claims "dityrosine is the stiffest" and
  "glucosepane is no stiffer than pyridinoline" are withdrawn.
- Next: conformer ensembles (≥20 seeds) or pre-extended fragments, so the covalent regime is measured
  separately from unfolding; ultimately crosslinks inside a triple helix (Brev job B6).

## Caveats

2D networks (isostatic point z = 4, not 6 as in 3D); small local lattices (finite size); all parameters are
literature-informed assumptions, not fits; pyridinium/charged crosslinks neutralised in the atomistic fragments;
non-reactive MLIPs give stiffness, not bond rupture; the cell is one tensegrity unit, not a cytoskeleton; organ
models are lumped. Treat trends, not absolute numbers.

See `SECURITY-REVIEW.md` before running anything third-party, and `AGENTS.md` for the shared cross-agent status.
