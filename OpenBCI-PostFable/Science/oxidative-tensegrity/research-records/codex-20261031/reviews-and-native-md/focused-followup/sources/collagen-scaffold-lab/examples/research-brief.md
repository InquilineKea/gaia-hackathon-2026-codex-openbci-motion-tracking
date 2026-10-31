# Collagen matrix architecture investigation

Question: At matched nominal solid fraction and hydrated strut modulus, how does lattice topology change constrained axial stiffness, and which differences survive non-affine relaxation, bending and buckling?

This bundle contains synthetic model outputs, not experimental evidence. Start by reproducing the affine formula and identifying confounds. Current lattice: octet; strut modulus: 100 kPa.

## Workflow
1. Specify collagen source/type, crosslink chemistry, hydration, temperature, specimen geometry and loading rate. Obtain independent hydrated-strut calibration.
2. Reproduce the 44-row topology/strain sweep. Compare both matched solid fraction and fixed radius; do not call this an optimized scaffold.
3. Use GraphReasoning/SciAgents for literature-backed hypotheses. Concept edges are unverified hypotheses, not causal evidence. Spatial strut GraphML is a separate geometric object.
4. ScienceClaw: consume the bundle as local input in a reviewed workflow; create native artifacts using that installation's current API. Do not publish to Infinite automatically.
5. OpenScientist: manually upload sweep.csv (or this JSON bundle) and paste this research question. OpenScientist is a separate project from Buehler's lab.
6. Optional CollagenTransformer: use its reviewed notebook to estimate sequence thermal stability with domain checks. Never convert that output directly to scaffold stiffness.
7. Validate selected architectures with a relaxed beam/continuum model and hydrated compression experiments. Add bending, buckling and fluid effects before interpreting beyond the baseline.

## Assumptions
- Educational linear axial-strut model; unvalidated for collagen scaffolds.
- Affine displacement imposed at every node; zero transverse strain; no equilibrium relaxation.
- Reported stiffness is constrained C_iiii, not free-lateral Young modulus.
- Full edge cylinders; junction overlaps and boundary clipping ignored.
- No bending, buckling, fluid transport, swelling, degradation, thermal stability or biological outcomes modeled.
- Default strut modulus is illustrative; molecular models do not automatically calibrate mesoscale mechanics.

## Decision criteria
Report numerical convergence, parameter provenance, sensitivity and independent validation error. A biologically useful scaffold cannot be selected on stiffness alone.

## Tool status
External packages have not been installed or executed. File-level interchange only; this is not a native API schema.

## Sources
- OpenScientist: https://github.com/openscientist-io/openscientist
- ScienceClaw: https://github.com/lamm-mit/scienceclaw
- GraphReasoning: https://github.com/lamm-mit/GraphReasoning
- SciAgents: https://github.com/lamm-mit/SciAgentsDiscovery
- CollagenTransformer: https://github.com/lamm-mit/CollagenTransformer
