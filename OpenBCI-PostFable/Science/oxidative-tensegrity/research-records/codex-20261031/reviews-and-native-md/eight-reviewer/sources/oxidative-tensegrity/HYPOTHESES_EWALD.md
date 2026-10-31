# Collagen-crosslinking hypotheses in the spirit of the Ewald lab

Labels follow the shared convention from the ScienceClaw lab pipeline posts on humanavianaisymbiosis.wordpress.com:
**SIMULATED** (this repo's model), **CITED** (verified on PubMed 2026-10-31), **PROPOSED** (untested).
Swarm round 1 (ScienceClaw, Gemini) output is treated as leads only; several of its specifics were not verifiable.

Anchors (CITED):
- Ewald et al., *Nature* 2015 (PMID 25517099): longevity via reduced insulin/IGF-1 signalling requires and prolongs
  collagen expression ("collagen remodelling in longevity").
- Teuscher et al., *Nat Commun* 2024 (PMID 38177158): longevity interventions (daf-2 RNAi, glp-1) slow age-related
  collagen stiffening; a hemidesmosome-linked loop (cuticle → hypodermis → basement membrane → muscle) couples force to
  ECM gene expression through YAP-1; yap-1 loss blunts daf-2 lifespan extension; EMB-9/collagen IV adds new layers on
  old, un-turned-over matrix.
- Ewald, *Antioxidants* 2018 (PMID 30274229): NADPH-oxidase (BLI-3/DUOX) redox signalling in stress, immunity and
  aging; in *C. elegans* BLI-3 supplies H₂O₂ for cuticle tyrosine crosslinking.
- Statzer et al., *Aging Cell* 2021 (PMID 34346557): youthful vs aged matreotypes predict longevity drugs.
- Dakhovnik et al., *npj Aging* 2025 (PMID 41266379): Gly:Pro:Hyp 3:1:1 supplementation extends worm lifespan and
  prolongs collagen expression (human arm observational, industry-funded).

---

## H1. Crosslinked collagen is "immortal" collagen: turnover escape drives the aging matreotype

**Claim.** Oxidative crosslinks make collagen resistant to proteolysis, so each crosslink removes that molecule from the
turnover pool. Crosslink load therefore rises super-linearly with age wherever turnover is slow, and longevity
interventions work partly by keeping the matrix in the renewable pool.
**SIMULATED.** With turnover slowed as exp(2.5·dose), age-80 dose reaches 0.77 in tendon but plateaus at 0.11 in
myocardium; matrix repair rate falls 2–4× by age 80 in slow-turnover tissues.
**PROPOSED test (worm).** Photoconvertible EMB-9::Dendra2 pulse-chase: the fraction of "old" basement-membrane collagen
that persists should rise with age in wild type, rise less in daf-2, and fall when crosslink formation is reduced in
adults (adult-only *bli-3* or *pxn-2* RNAi). Measure dityrosine autofluorescence (ex 320 / em 410 nm) in the old layer.
**Falsifier.** Old-collagen persistence is unchanged by adult-only crosslink reduction.

## H2. Longevity reads the matrix's *nonlinearity*, not its stiffness

**Claim.** YAP-1 mechanosensing at hemidesmosomes responds to how much the matrix stiffens under strain. Oxidative
crosslinks flatten that response long before they raise baseline stiffness much, so aging is first a loss of
mechanical dynamic range.
**SIMULATED.** Dose-1 crosslinks cut K(γ=0.35)/G₀ from 6–11 to ~2.5 in sub-isostatic networks; YAP saturates
above ~1 kPa, so absolute stiffness carries little signal on stiff matrices.
**PROPOSED test.** Worm: dose–response slope of a *yap-1* or collagen reporter to graded external pressure (the
Teuscher pressure assay) at days 1, 5, 10; predict the slope falls with age, is preserved in daf-2, and is flattened
by adult cuticle crosslinking (BLI-3 overexpression). Mammalian: fibroblasts on strain-stiffening (fibrin or PIC)
vs linear (PA) gels at matched G₀, ± glycation; predict YAP and COL1A1 track K(γ), not G₀.
**Falsifier.** Reporter slope is age-independent, or YAP tracks G₀ and not K(γ).

## H3. Oxidative crosslinking is a developmental program that becomes harmful only when it outlasts matrix renewal

**Claim.** Dityrosine (BLI-3/DUOX + peroxidase) and sulfilimine (peroxidasin) crosslinks are required to build
cuticle and basement membrane. Harm comes from the same chemistry continuing on adult matrix that is no longer
replaced. The time window, not the chemistry, decides.
**SIMULATED (pilot, not converged).** ALCHEMI/MACE-OFF stretch scans rank dityrosine (3.2×) and sulfilimine (2.9×)
the stiffest linkages relative to pyridinoline; glucosepane ≈ pyridinoline.
**PROPOSED test.** Auxin-inducible degradation of BLI-3 or PXN-2 started after the L4 molt vs from hatching: predict
developmental loss blisters and shortens life, while adult-onset partial loss slows cuticle stiffening (AFM) and
extends lifespan in a *yap-1*-dependent way.
**Falsifier.** Adult-onset degradation leaves stiffening and lifespan unchanged.

## H4. Crosslinks accumulate along the load axis, making tissues brittle exactly where they are used

**Claim.** Tensioned fibrils are shielded from proteases and reorganise reactive sites, so oxidative crosslinks build
up anisotropically along load lines. Tissues become stiffer and brittle along the direction they bear load.
**SIMULATED.** Matched-dose anisotropic crosslinks give Cx/Cy 1.8–3.8 (isotropic stays ~0.7–1.0); tendon anisotropy
rises 0.94 → 2.5 by age 80; Col I strain-at-peak falls 0.36 → 0.04–0.08 with strength roughly unchanged.
**PROPOSED test.** Worm: dityrosine fluorescence and AFM stiffness mapped relative to furrows and muscle-attachment
(hemidesmosome) lines across age. Mouse tail-tendon fascicles glycated ex vivo under static load vs slack: predict
higher SHG/birefringence anisotropy and lower failure strain only in loaded fascicles.
**Falsifier.** Crosslink markers and failure-strain loss are isotropic regardless of load history.

## H5. Recovery rate of the matrix–YAP loop is an individual-level aging clock (Fedichev-style resilience)

**Claim.** The YAP–myosin–matrix feedback loop slows its recovery as the matrix approaches the mechanosensing
threshold, the critical slowing down that precedes loss of resilience. Its recovery time should predict remaining
lifespan in individual animals.
**SIMULATED.** Recovery rate drops to 0.12–0.14 /h (vs 0.166 elsewhere) where YAP is most sensitive to myosin.
**PROPOSED test.** Individually tracked worms (microfluidics/WorMotel): pulse pressure, time the return of a *yap-1* or
collagen reporter to baseline; predict recovery time lengthens with age, is delayed by daf-2, and predicts each worm's
remaining lifespan better than chronological age.
**Falsifier.** Recovery time adds no predictive power beyond age.

## H6. Feed-forward lock-in: YAP→LOX makes anti-crosslink therapy work only together with collagen renewal

**Claim.** Nuclear YAP raises LOX/LOXL2 (a round-1 swarm lead, to be verified), so stiff matrix makes itself stiffer.
Breaking crosslinks alone is undone by the loop; boosting renewal alone just feeds fresh collagen into a crosslinking
environment. Together they should be synergistic.
**SIMULATED.** Not yet in the model: needs a YAP→crosslink-rate term (next model change).
**PROPOSED test.** 2×2 factorial in worms: Gly:Pro:Hyp 3:1:1 (or *col-120* activation) × adult-onset crosslink
reduction (bli-3 degradation or aminoguanidine). Readouts: lifespan, cuticle AFM stiffness, pressure-reporter slope.
Predict a positive interaction term.
**Falsifier.** Additive or antagonistic effects.

## H7. Long-lived species avoid crosslink load by renewal, not by low glycation

**Claim.** Seabirds, parrots and tortoises tolerate high blood glucose; what keeps their matrices young is collagen
residence time.
**CITED context.** Seabird foot-web pentosidine shows weak or no age correlation (kittiwake, puffin, murre).
**PROPOSED test.** Across archived species samples, collagen residence-time proxies (D-Asp racemization or bomb-pulse
¹⁴C) should explain crosslink load better than plasma glucose or HbA1c.
**Falsifier.** Glycemia explains more variance than residence time.

---

**Known model gaps these hypotheses expose.** No YAP→LOX feedback (H6). Passive myocardial stiffness lumps titin into
the non-collagen fraction; the swarm correctly notes alagebrium also acts on titin glycation. 2D networks; atomistic
crosslink rigidities are an unconverged pilot.

---

## ScienceClaw swarm round 2 (2026-10-31, Gemini 3.6 Flash, dry-run, 6 collectives × 3 agents)

Logs: `swarm/work/round2_H*.log`. Swarm syntheses are LLM output with literature tools; specific residue numbers,
cysteine positions and effect sizes below were **not** independently verified.

| H | Swarm verdict (summarised) | My read |
|---|---|---|
| H1 turnover escape | Supports: AGE crosslinks sterically block MMP-1/-13 unwinding at the Gly775-Leu776 site; AGE-RAGE signalling also suppresses turnover in chondrocytes | Consistent with established work that glycated collagen resists MMP cleavage. Adds a second, cell-signalling route to escape. |
| H2 nonlinearity | Supports via strain-stiffening PIC hydrogels: talin unfolding and vinculin reinforcement on stiffening networks, nuclear deformation and YAP entry | Plausible; matched-G₀ PIC vs PA is the right experiment. No direct evidence yet that glycation flattens collagen nonlinearity. |
| H3 developmental program | **Raises an alternative**: BLI-3 H₂O₂ also activates SKN-1/Nrf2 (via WDR-23 oxidation), so adult *bli-3* loss could *shorten* life through lost stress signalling, not lengthen it through less crosslinking | Important competing prediction. The AID experiment discriminates: measure SKN-1 targets (*gst-4*) alongside cuticle stiffness. Cysteine positions unverified. |
| H4 load-axis | Supports: tensile strain protects collagen from collagenase by blocking local unwinding; proposes SMD + stretch-proteolysis to find the critical strain | Strain-protection of collagen is established. Load-dependent *glycation* itself was not found. |
| H5 recovery clock | Mechanisms only (YAP-1 export kinetics, AMPK/AAK-2 gating, cofilin): **no evidence** found linking mechanotransduction recovery time to individual lifespan | Genuine gap: H5 is novel, not refuted. Worth running as stated. |
| H6 YAP→LOX lock-in | Claims YAP/TEAD binds MCAT motifs in *LOX*/*LOXL2* promoters and suggests TEAD-palmitoylation inhibitors as a lever | Needs verification against primary ChIP data before the model gets a YAP→crosslink term. |

## H8. Arginine glycation, not lysine glycation, decouples GAGs from collagen

**Claim.** Dermatan/chondroitin sulfate binds collagen mainly through arginine. Methylglyoxal converts arginine to
MG-H1 (the most abundant protein AGE) and removes that contact, so the proteoglycan interface that lets fibrils
slide is lost. CML on lysine leaves the interface largely intact.
**SIMULATED (ALCHEMI + AIMNet2, rigid gas-phase fragments, 6 orientations; `results/alchemi_gag/`).**
Arg–DS contact −2.3 to −3.1 eV vs MG-H1-Arg −1.1 to −1.6 eV, with the minimum pushed from 2.8 Å to 4–4.5 Å
(contact lost). CML-Lys stays as bound as Lys (−1.9 to −2.4 vs −1.6 to −1.9 eV). Contact energies, not free
energies: explicit-solvent OpenMM/GROMACS free energies are needed before trusting magnitudes.
**PROPOSED test.** Decorin/DS binding to collagen I films pre-treated with methylglyoxal (MG-H1) vs glyoxylate
(CML) at matched AGE load, by SPR or pull-down; in worms, cuticle collagen arginine glycation (MG) vs lifespan
with *glod-4* (glyoxalase) mutants, which accumulate methylglyoxal.
**Falsifier.** MG-treated and CML-treated collagen lose GAG binding equally.

---

**Net.** H1, H2, H4 have supporting literature; H3 gained a competing hypothesis that sharpens the experiment;
H5 is an open gap; H6 hinges on an unverified regulatory claim.
