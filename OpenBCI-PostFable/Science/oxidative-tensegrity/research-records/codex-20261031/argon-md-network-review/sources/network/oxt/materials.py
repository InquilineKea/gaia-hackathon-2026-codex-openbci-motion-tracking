"""Collagen types, crosslink chemistries, tissues, and the builder that turns them into networks.

Every number here is a *dimensionless model parameter* chosen to be qualitatively consistent with the
literature cited in README.md, not a measurement.  Crosslink rigidities (`k_rel`) are placeholders
that `alchemi_crosslinks.py` overwrites via `results/crosslink_params.json` when it is run on a GPU.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from .network import Lattice, SystemSpec

ROOT = Path(__file__).resolve().parents[1]

# --- crosslink chemistries ---------------------------------------------------------------------
# k_rel: relative junction rigidity (dimensionless, pyridinoline = 1). oxidative: formed by ROS / glycoxidation.
CROSSLINKS = {
    "HLNL":          dict(k_rel=0.6, oxidative=False, note="LOX-derived divalent, immature; healthy"),
    "pyridinoline":  dict(k_rel=1.0, oxidative=False, note="LOX-derived trivalent, mature; healthy"),
    "pentosidine":   dict(k_rel=1.6, oxidative=True,  note="AGE, glycoxidation Lys-Arg"),
    "glucosepane":   dict(k_rel=1.8, oxidative=True,  note="AGE, most abundant Lys-Arg crosslink in aged ECM"),
    "dityrosine":    dict(k_rel=2.2, oxidative=True,  note="radical Tyr-Tyr biphenyl, short and stiff"),
    "disulfide":     dict(k_rel=1.2, oxidative=True,  note="Cys-Cys; physiologic in Col VII NC2, scrambled under oxidation"),
    "isopeptide_TG2": dict(k_rel=1.1, oxidative=False, note="transglutaminase-2 Gln-Lys; Col VII anchoring"),
    "sulfilimine":   dict(k_rel=1.4, oxidative=True,  note="peroxidasin/HOBr Met-S=N-Hyl; physiologic in Col IV NC1"),
}


def load_crosslink_overrides(path: Path | None = None) -> dict:
    path = path or ROOT / "results" / "crosslink_params.json"
    if path.exists():
        data = json.loads(path.read_text())
        for name, v in data.get("crosslinks", {}).items():
            if name in CROSSLINKS and "k_rel" in v:
                CROSSLINKS[name]["k_rel"] = float(v["k_rel"])
                CROSSLINKS[name]["source"] = data.get("source", str(path))
        return data
    return {}


# --- collagen types ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Collagen:
    name: str
    mu: float          # fibre stretch stiffness (Col I = 1)
    kappa: float       # fibre bending stiffness
    eps_r: float       # fibre-segment rupture strain
    z: float           # native mean connectivity ("branching factor")
    oxidative_xl: tuple  # dominant oxidative chemistries for this collagen
    note: str


COLLAGENS = {
    "I":  Collagen("I", 1.00, 3e-3, 0.10, 3.4, ("glucosepane", "pentosidine", "dityrosine"),
                   "fibril-forming, thick banded fibrils; dermis, tendon, myocardium, bone"),
    "VII": Collagen("VII", 0.25, 3e-4, 0.25, 3.0, ("disulfide", "dityrosine"),
                    "anchoring fibrils at dermal-epidermal junction; long, flexible, loop-forming"),
    "IV": Collagen("IV", 0.10, 1e-4, 0.30, 3.8, ("sulfilimine", "dityrosine"),
                   "basement-membrane chicken-wire network (7S tetramers, NC1 hexamers)"),
}


# --- oxidative damage ------------------------------------------------------------------------------
@dataclass(frozen=True)
class Damage:
    mode: str = "none"        # none | iso | aniso
    dose: float = 0.0         # 0..1, oxidative crosslinks relative to a heavily aged tissue
    axis: int = 0             # anisotropic crosslinks form along this lattice direction (tension axis)
    bridge_frac: float = 0.06  # new inter-fibre links per bond at dose 1
    stiff_frac: float = 0.5   # fraction of fibre segments with intrafibrillar AGEs at dose 1
    stiff_gain: float = 1.0   # intrafibrillar stretch-stiffness gain per unit k_rel
    rigid_frac: float = 0.5   # fraction of junctions locked (angle-constraining) at dose 1
    kx0: float = 2e-3         # locked-junction angular stiffness per unit k_rel
    brittle: float = 0.45     # rupture strain multiplier for damaged segments
    chem: str | None = None   # override chemistry (default: collagen's dominant)


def build_spec(lat: Lattice, col: Collagen, dmg: Damage, rng: np.random.Generator, *,
               z: float | None = None, mu_el: float = 0.0, k_gag: float = 1e-6,
               prestrain: float = 0.0) -> SystemSpec:
    Nb = lat.Nb
    z = col.z if z is None else z
    # dilution probability p chosen so that, after cutting one bond per fibre line, z = 6 p (1 - 1/W)
    p = min(1.0, z / 6.0 / (1 - 1.0 / lat.W))
    alive = rng.random(Nb) < p
    for line in range(lat.n_lines):
        members = np.flatnonzero(lat.line == line)
        alive[rng.choice(members)] = False

    mu = np.full(Nb, col.mu)
    kb = np.ones(Nb)
    eps_r = np.full(Nb, col.eps_r)
    rigid = np.zeros(lat.N)
    meta = dict(collagen=col.name, mode=dmg.mode, dose=dmg.dose, z_target=z)

    if dmg.mode != "none" and dmg.dose > 0:
        chems = (dmg.chem,) if dmg.chem else col.oxidative_xl
        k_rel = float(np.mean([CROSSLINKS[c]["k_rel"] for c in chems]))
        meta["chem"] = "+".join(chems)
        meta["k_rel"] = k_rel
        on_axis = lat.bdir == dmg.axis

        def pick(pool, n):
            n = min(n, pool.size)
            return rng.choice(pool, n, replace=False) if n > 0 else np.array([], dtype=int)

        # 1. bridging crosslinks: new links between neighbouring fibres (raise connectivity)
        n_bridge = int(round(dmg.dose * dmg.bridge_frac * Nb))
        missing = np.flatnonzero(~alive)
        pool = missing[on_axis[missing]] if dmg.mode == "aniso" else missing
        new = pick(pool, n_bridge)
        alive[new] = True
        mu[new] = col.mu * k_rel
        eps_r[new] = col.eps_r * dmg.brittle

        # 2. intrafibrillar crosslinks: stiffer, more brittle segments (equal count in iso and aniso)
        present = np.flatnonzero(alive)
        n_st = int(round(dmg.dose * dmg.stiff_frac * present.size))
        if dmg.mode == "aniso":
            first = present[on_axis[present]]
            rest = present[~on_axis[present]]
            chosen = pick(first, n_st)
            if chosen.size < n_st:
                chosen = np.concatenate([chosen, pick(rest, n_st - chosen.size)])
        else:
            chosen = pick(present, n_st)
        mu[chosen] *= 1 + dmg.stiff_gain * k_rel * dmg.dose
        kb[chosen] *= 1 + 2 * k_rel * dmg.dose
        eps_r[chosen] *= dmg.brittle

        # 3. locked junctions: angle-constraining crosslinks at fibre crossings (isotropic by nature)
        n_lock = int(round(dmg.dose * dmg.rigid_frac * lat.N))
        rigid[rng.choice(lat.N, n_lock, replace=False)] = dmg.kx0 * k_rel

    return SystemSpec(alive=alive, mu=mu, kappa_b=kb, eps_r=eps_r, rigid_node=rigid,
                      kappa=col.kappa, mu_el=mu_el, k_gag=k_gag, prestrain=prestrain, meta=meta)


# --- tissues (macro scale) -------------------------------------------------------------------------
@dataclass(frozen=True)
class Tissue:
    name: str
    collagen: str
    z: float
    mu_el: float          # elastin network
    k_gag: float          # proteoglycan / GAG embedding
    prestrain: float      # osmotic swelling prestrain (tissue tensegrity)
    aligned: bool         # fibres aligned -> oxidative crosslinks form anisotropically
    half_life_yr: float   # collagen turnover half-life
    xl_rate: float        # oxidative crosslink dose accrued per year with no turnover
    thickness_um: float   # diffusion path from nearest capillary for signalling molecules
    readout: str
    note: str


# half_life_yr: turnover of the *mature, crosslinked* collagen pool (assumption).  Verzijl 2000: cartilage ~117 y,
# skin ~15 y; tendon core essentially not renewed; myocardial bulk collagen turns over in months but its mature
# crosslinked perimysial pool far more slowly (5 y assumed); basement membrane 3 y assumed.
# xl_rate: dose per year with no turnover, set so skin dermis reaches ~0.5 at age 80 (glucosepane trend).
# diffusion_um: path from the nearest capillary (avascular tissues: the full depth).
TISSUES = {
    "skin_dermis":   Tissue("skin_dermis", "I", 3.4, 0.010, 1e-4, 0.00, False, 15, 0.012, 80, "fibroblast YAP",
                            "Col I/III + elastin; Col VII anchors epidermis"),
    "skin_DEJ":      Tissue("skin_DEJ", "VII", 3.0, 0.002, 1e-4, 0.00, False, 15, 0.012, 100, "anchoring strength",
                            "dermal-epidermal junction anchoring fibrils"),
    "tendon":        Tissue("tendon", "I", 4.6, 0.001, 1e-5, 0.00, True, 200, 0.010, 300, "tensile strength",
                            "aligned Col I; core collagen essentially not renewed"),
    "cartilage":     Tissue("cartilage", "I", 3.6, 0.000, 2e-3, 0.03, False, 117, 0.010, 1500, "chondrocyte YAP",
                            "Col II network pre-tensioned by aggrecan swelling (Col I parameters used as proxy)"),
    "artery_media":  Tissue("artery_media", "I", 3.4, 0.050, 1e-4, 0.02, True, 40, 0.010, 300, "pulse-wave velocity",
                            "elastin lamellae + circumferential Col I/III"),
    "myocardium":    Tissue("myocardium", "I", 3.2, 0.005, 1e-4, 0.00, False, 5, 0.012, 10, "ejection fraction",
                            "perimysial/endomysial Col I/III around cardiomyocytes"),
    "basement_membrane": Tissue("basement_membrane", "IV", 3.8, 0.000, 1e-4, 0.00, False, 3, 0.012, 0.1, "filtration / diffusion",
                                "Col IV + laminin sheet"),
}


def tissue_dose(t: Tissue, age_yr: float, alpha: float = 2.5) -> float:
    """Crosslink accrual with turnover that crosslinks themselves slow down (crosslinked collagen resists
    MMP cleavage, same alpha as physio.matrix_recovery_rate):  dd/dt = r - d / (tau * exp(alpha d))."""
    tau = t.half_life_yr / np.log(2)
    d, dt = 0.0, 0.05
    for _ in range(int(age_yr / dt)):
        d += dt * (t.xl_rate - d / (tau * np.exp(alpha * d)))
    return float(min(1.0, d))


def tissue_spec(lat: Lattice, t: Tissue, age_yr: float, rng, mode: str | None = None) -> SystemSpec:
    col = COLLAGENS[t.collagen]
    d = tissue_dose(t, age_yr)
    mode = mode or ("aniso" if t.aligned else "iso")
    dmg = Damage(mode=mode if d > 0 else "none", dose=d)
    spec = build_spec(lat, col, dmg, rng, z=t.z, mu_el=t.mu_el, k_gag=t.k_gag, prestrain=t.prestrain)
    spec.meta.update(tissue=t.name, age=age_yr, dose=d)
    return spec
