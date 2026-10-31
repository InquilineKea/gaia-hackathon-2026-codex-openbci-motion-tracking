"""Tissue/organ read-outs driven by the network simulation.

transport   hindered diffusion of signalling molecules through the crosslinked matrix (Ogston
            obstruction for collagen fibres and GAG chains, plus reversible matrix binding).
heart       left ventricle as a time-varying elastance (Suga-Sagawa) with an exponential EDPVR whose
            stiffness tracks the myocardial matrix modulus; contractility follows the Engler et al. 2008
            observation that cardiomyocytes beat best on matrix near native stiffness.
artery      Moens-Korteweg pulse-wave velocity from the medial matrix modulus.
matrix recovery  repair rate of matrix damage: turnover rate x MMP accessibility (crosslinks block
            collagenase cleavage), giving a Fedichev-style tissue recovery rate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# --------------------------------------------------------------------------------------------------
# signalling molecules: Stokes radius (nm), free diffusivity in water at 37 C (um^2/s),
# matrix binding (dimensionless partition to bound state in healthy matrix), uptake (1/s)
# --------------------------------------------------------------------------------------------------
MOLECULES = {
    "O2":          dict(r=0.17, D0=3000.0, bind=0.0,  uptake=1.0,  ages_binding=0.0),
    "glucose":     dict(r=0.36, D0=900.0,  bind=0.0,  uptake=0.05, ages_binding=0.0),
    "IGF-1":       dict(r=1.6,  D0=150.0,  bind=2.0,  uptake=1e-3, ages_binding=0.5),
    "TGF-beta1":   dict(r=2.4,  D0=100.0,  bind=5.0,  uptake=1e-3, ages_binding=1.0),
    "VEGF165":     dict(r=3.0,  D0=80.0,   bind=10.0, uptake=1e-3, ages_binding=1.0),
    "albumin":     dict(r=3.5,  D0=70.0,   bind=0.2,  uptake=1e-5, ages_binding=0.5),
    "IgG":         dict(r=5.3,  D0=45.0,   bind=0.2,  uptake=1e-5, ages_binding=0.3),
    "exosome":     dict(r=50.0, D0=4.0,    bind=0.5,  uptake=1e-4, ages_binding=0.3),
}
R_COLLAGEN_NM = 40.0  # fibril radius
R_GAG_NM = 0.5        # GAG chain radius


def ogston(r_s, phi, r_f):
    return math.exp(-math.sqrt(max(phi, 0.0)) * (1 + r_s / r_f))


def transport(mol: str, phi_col: float, phi_gag: float, dose: float, thickness_um: float):
    """Effective diffusivity, arrival time and steady fraction delivered to the far side."""
    m = MOLECULES[mol]
    hind = ogston(m["r"], phi_col, R_COLLAGEN_NM) * ogston(m["r"], phi_gag, R_GAG_NM)
    # AGE-modified matrix sequesters growth factors (RAGE-like and charge changes); exosomes are sieved
    K = m["bind"] * (1 + 2.0 * m["ages_binding"] * dose)
    D = m["D0"] * hind / (1 + K)
    L = thickness_um
    t_arrive = L ** 2 / (2 * D)                          # s
    lam = math.sqrt(D / m["uptake"]) if m["uptake"] > 0 else float("inf")
    x = L / lam
    frac = 2 * math.exp(-x) / (1 + math.exp(-2 * x)) if np.isfinite(lam) else 1.0  # sech, overflow-safe
    return dict(D_eff=D, hindrance=hind, bound_ratio=K, t_arrive_s=t_arrive, delivered_frac=frac)


def phi_collagen(bond_density_ratio: float, phi0: float) -> float:
    """Fibre volume fraction scales with fibre length density in the simulated network."""
    return phi0 * bond_density_ratio


# --------------------------------------------------------------------------------------------------
# heart
# --------------------------------------------------------------------------------------------------
@dataclass
class LVParams:
    V0: float = 10.0        # mL unstressed volume
    A: float = 0.35         # mmHg, EDPVR scale
    beta0: float = 0.025    # 1/mL, EDPVR stiffness, young myocardium
    w_col: float = 0.5      # fraction of passive stiffness from ECM (rest from titin)
    Ees0: float = 2.5       # mmHg/mL end-systolic elastance
    Ea0: float = 2.0        # mmHg/mL arterial elastance, young
    P_fill: float = 10.0    # mmHg end-diastolic pressure
    E_opt_kpa: float = 10.0  # matrix stiffness at which cardiomyocytes contract best (Engler 2008)
    s_log: float = 1.2


def heart(E_myo_ratio: float, E_myo_kpa: float, E_myo_kpa_young: float, pwv_ratio: float,
          p: LVParams = LVParams()):
    beta = p.beta0 * ((1 - p.w_col) + p.w_col * E_myo_ratio)
    EDV = p.V0 + math.log(p.P_fill / p.A + 1) / beta

    def eff(E):
        return math.exp(-(math.log(E / p.E_opt_kpa)) ** 2 / (2 * p.s_log ** 2))

    Ees = p.Ees0 * eff(E_myo_kpa) / eff(E_myo_kpa_young)
    Ea = p.Ea0 * pwv_ratio ** 2  # arterial elastance ~ characteristic impedance ~ PWV (stiffening proxy)
    ESV = (Ea * EDV + Ees * p.V0) / (Ea + Ees)
    SV = EDV - ESV
    return dict(EDV=EDV, ESV=ESV, SV=SV, EF=SV / EDV, Ees=Ees, Ea=Ea, beta_EDPVR=beta)


def pwv(E_ratio: float, pwv_young=6.0):
    """Moens-Korteweg: PWV ~ sqrt(E h / 2 r rho); geometry held fixed so PWV scales as sqrt(E)."""
    return pwv_young * math.sqrt(max(E_ratio, 1e-9))


# --------------------------------------------------------------------------------------------------
# matrix-level recovery (resilience)
# --------------------------------------------------------------------------------------------------
def matrix_recovery_rate(half_life_yr: float, dose: float, alpha=2.5):
    """Repair of damaged matrix needs MMP cleavage; crosslinked collagen resists collagenase
    (approximately exponential in crosslink density).  Returns 1/yr."""
    return math.log(2) / half_life_yr * math.exp(-alpha * dose)
