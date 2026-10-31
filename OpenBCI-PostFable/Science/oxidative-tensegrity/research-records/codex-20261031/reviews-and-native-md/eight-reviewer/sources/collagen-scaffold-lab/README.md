# Fibril — collagen scaffold laboratory

A dependency-free, local browser application for exploring collagen-inspired strut lattices and preparing research inputs for OpenScientist and the LAMM/Buehler ecosystem. Open `index.html` directly, or serve this directory on loopback:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open http://127.0.0.1:8765. No build, npm installation, credentials or external service is required. Source is original JavaScript, HTML and CSS. A server started in a terminal lasts only while that process runs.

## What works

- Orbitable canvas 3D view, true-scale compression, keyboard rotation/zoom and animated loading.
- Simple cubic, body-centered cubic, octet/FCC and reinforced BCC finite strut networks.
- Cell count, cell pitch, strut radius, hydrated strut modulus, loading axis and compression controls.
- Affine stiffness, stress, nominal void fraction and geometric surface/volume estimates.
- Matched-solid-fraction or fixed-radius topology comparisons.
- 44-row topology/strain CSV sweep; research JSON containing geometry, metrics, provenance, a research brief and embedded GraphML files.
- Separate spatial geometry and conceptual hypothesis graph exports.
- Validated local material calibration import. Example: `examples/calibration-format.json`. This file is explicitly synthetic; replace its source and hydration with actual measurement provenance before scientific use.

## Mechanics and boundaries

Length is mm, modulus/stress kPa, strain dimensionless. For circular struts, A = πr². Each strut has direction n and reference length L. Every node follows the same prescribed affine strain with zero transverse strain:

    C_iiii = E_s / V * sum(A L n_i^4)
    sigma_ii = C_iiii * compression_magnitude
    energy_density = 0.5 * C_iiii * compression_magnitude^2
    nominal_solid_fraction = sum(A L) / V

Positive stress denotes compressive magnitude. This C_iiii is a constrained-strain stiffness, **not** a relaxed Young's modulus. The ideal axial-strut energy is evaluated without solving nodal equilibrium. It cannot capture internal relaxation, bending, buckling, shear stability, damage, viscoelasticity, hydration kinetics, crosslink chemistry, permeability, cell response or clinical performance. All four geometries have cubic symmetry, so the reported X/Y/Z stiffnesses agree. Axis controls change the loading visualization, not this symmetry.

The material modulus is an illustrative user input, not a literature-derived universal collagen modulus. Geometry volume counts full cylinders, ignores junction overlap, and does not clip cylinders at the sample box. Reported porosity is nominal. The same approximation is used when matching material fraction across geometries. Very thick struts require a volumetric calculation. Finite boundaries affect material fraction when cell count changes. The render shows strut centerlines with approximate screen widths, not a watertight manufacturing mesh.

At the default octet setting (3 cells, 0.6 mm pitch, 0.025 mm radius, 100 kPa illustrative material modulus, 3% compression), the affine stiffness is about 1.80 kPa, nominal void fraction 89.2%, and compressive stress 0.054 kPa. These numbers are model outputs, not collagen validation results.

## Sample research workflow and interfaces

1. **Formulation record:** collagen type/source, concentration, crosslinking, hydration, temperature, loading rate and sample preparation. Obtain an independent hydrated strut modulus; do not infer it from a molecular model without a documented scale bridge.
2. **Geometry screen:** compare all four networks at matched nominal solid fraction. Repeat at fixed radius to expose the material-amount confound. Download the CSV and bundle.
3. **OpenScientist:** manually upload `examples/sweep.csv` or a downloaded bundle, and paste the question from `examples/research-brief.md`. Its documented UI accepts CSV/JSON. This is a data-file interface, not an implemented REST client.
4. **ScienceClaw:** provide the same files as local investigation inputs in a separately reviewed installation. Map outputs to native artifacts through that version's supported interface. This app neither writes to ScienceClaw's store nor launches/publishes investigations.
5. **GraphReasoning/SciAgents:** use `concepts.graphml` as a small hypothesis graph for literature curation. Its relations have no asserted empirical evidence. `geometry.graphml` is a different graph: nodes are physical points and edges are struts. The documented GraphReasoning workflow reads GraphML with NetworkX; these files require workflow-specific mapping before embedding/reasoning.
6. **CollagenTransformer:** optional sequence thermal-stability branch, using the lab's inference notebooks after review. Thermal stability is a distinct outcome; it does not calibrate stiffness. No arbitrary FASTA-to-notebook API is invented here.
7. **Validation loop:** rerun chosen architectures with a relaxed beam/continuum model, examine mesh convergence and boundary conditions, then compare with independent hydrated compression measurements. Import only a measured **strut** modulus into this app; fitting it to scaffold stiffness and then claiming independent validation would be circular.

Useful investigation prompt:

> At matched nominal solid fraction and measured hydrated strut modulus, how does topology change constrained axial stiffness? Which trends survive non-affine relaxation, bending and buckling? Reproduce the supplied synthetic baseline, identify confounds, separate simulation outputs from experimental evidence, and propose discriminating measurements. Do not infer cell compatibility from mechanics alone.

## Sources checked 2026-10-24

- [OpenScientist](https://github.com/openscientist-io/openscientist) — separate project, repository author Justin Reese; not attributed here to Buehler.
- [ScienceClaw](https://github.com/lamm-mit/scienceclaw) — Buehler/LAMM scientific tool and artifact orchestration.
- [GraphReasoning](https://github.com/lamm-mit/GraphReasoning) — graph extraction, representation and scientific reasoning; GraphML-based example workflow.
- [SciAgentsDiscovery](https://github.com/lamm-mit/SciAgentsDiscovery) — materials hypothesis generation/refinement.
- [CollagenTransformer](https://github.com/lamm-mit/CollagenTransformer) — collagen triple-helix thermal stability models and inference notebooks.
- [HierarchicalDesign](https://github.com/lamm-mit/HierarchicalDesign) — related multiscale architected-material learning work, demonstrated on metal metamaterials; its learned parameters are not transferred to collagen here.

The Collagen-Structure-Modeler and colbuilder candidate URLs could not be retrieved in this session. No API or functioning integration is claimed for them. These source checks are not immutable revision pins or a full supply-chain audit.

## Checks

```sh
node test-model.js
```

Original test code checks graph connectivity, unique edges, closed-form cubic stiffness, one-cell octet topology, cubic symmetry, modulus/radius scaling, geometric scale invariance, zero strain, matched solid fraction, and independently calculated spring-energy curvature. Browser checks confirmed rendered results and that doubling the material modulus doubles both stiffness and stress.

## Files and execution status

`model.js` contains the standalone numerical model; `app.js` the UI and exports. `examples/` includes a ready-to-upload sample CSV, graphs, inputs and research brief. `SECURITY-REVIEW.md` records the limited source reconnaissance and the separate gate for external execution. No external package has been installed or executed, and no live OpenScientist/ScienceClaw job has been submitted.
