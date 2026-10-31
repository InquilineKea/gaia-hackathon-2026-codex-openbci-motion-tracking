# ScienceClaw swarm runs (summary; raw logs stay local in swarm/work/)

Setup: ScienceClaw `894598c` in a throwaway Docker container, Gemini 3.6 Flash backend, `--dry-run`, Infinite
pointed at a dead port (each agent's start-up call to Infinite was blocked there; nothing was posted). Skills
installed five extra packages at runtime inside the container (e.g. `chembl-webresource-client`).

## Round 1 — checking the model's predictions (5 collectives, 3–4 agents each, all exit 0)

| Topic | Takeaway |
|---|---|
| Crosslinks vs brittleness (Col I) | Supports the mechanism: crosslinks shift load from inter-molecular sliding to triple-helix backbone tension, consistent with the model's falling failure strain. |
| Collagen VII anchoring fibrils | Pentosidine raises fibril stiffness and lowers strain-to-failure; Col VII NC1/NC2 domains are Lys/Arg rich (susceptible). |
| AGE stiffening and YAP/TAZ | Proposes a YAP→LOX/LOXL2 feed-forward loop (not in the model; see H6). YAP saturation on stiff matrix attributed to motor-clutch limits, as in the model. |
| Growth-factor transport | Matrix-bound VEGF/HSPG binding and RAGE signalling matter more than steric hindrance; flags Ogston as too simple. |
| Heart / alagebrium | Alagebrium also acts on titin glycation, so the model's collagen share of passive myocardial stiffness is oversimplified. |

Unreliable specifics (fabricated-looking residue numbers, an off-topic semiconductor analogy) were discarded.

## Round 2 — Ewald-style hypotheses

See the table at the end of `../HYPOTHESES_EWALD.md`.
