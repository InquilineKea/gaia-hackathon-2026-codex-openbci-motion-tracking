"""Glycosaminoglycan (GAG) / proteoglycan links between collagen fibres, three competing models, plus cyclic loading.

Motivated by the question of whether added collagen crosslinking stiffens a network yet costs it resilience by
blocking GAG-mediated fibril sliding (tendon data: GAG removal changes stress relaxation more than modulus).

GAG modes (all at matched collagen network, crosslinks and GAG count):
  bridge          permanent elastic springs between neighbouring fibres (GAG as a load-bearing crosslink)
  sliding         springs that slip once their strain exceeds eps_slip: the rest length moves with the fibres,
                  a Coulomb-friction element that dissipates energy without permanent damage. Slip is blocked at
                  fibre junctions locked by oxidative crosslinks (assumption: crosslinks pin fibrils so the
                  proteoglycan interface can no longer shear).
  polyelectrolyte no bridges; hydrated GAG swells the matrix (isotropic osmotic prestrain) and embeds it
GAG links occupy lattice slots not used by collagen and carry no bending/angle terms.
"""
from __future__ import annotations

import numpy as np
import torch

from .network import Batch, Lattice, SystemSpec

GAG_MODES = ("none", "bridge", "sliding", "polyelectrolyte")


def attach_gag(spec: SystemSpec, lat: Lattice, mode: str, density: float, rng: np.random.Generator,
               k_g: float = 0.05, eps_slip: float = 0.01, swell: float = 0.03, k_embed: float = 2e-3):
    """Returns per-slot arrays (gag mask, stiffness, slip strain) and mutates spec for the polyelectrolyte mode."""
    Nb = lat.Nb
    gag = np.zeros(Nb, bool)
    slip = np.full(Nb, np.inf)
    if mode in ("bridge", "sliding"):
        free = np.flatnonzero(~spec.alive)
        n = min(free.size, int(round(density * Nb)))
        gag[rng.choice(free, n, replace=False)] = True
        if mode == "sliding":
            locked = spec.rigid_node > 0
            pinned = locked[lat.bi] | locked[lat.bj]
            slip = np.where(pinned, np.inf, eps_slip)
    elif mode == "polyelectrolyte":
        spec.prestrain = max(spec.prestrain, swell)
        spec.k_gag = max(spec.k_gag, k_embed)
    spec.meta.update(gag_mode=mode, gag_density=density if mode in ("bridge", "sliding") else 0.0,
                     gag_links=int(gag.sum()))
    return dict(gag=gag, k_g=np.where(gag, k_g, 0.0), slip=slip)


class GAGBatch(Batch):
    def __init__(self, lat, specs, gags, device="cpu", dtype=torch.float64):
        super().__init__(lat, specs, device=device, dtype=dtype)
        t = lambda a: torch.as_tensor(np.stack(a), device=device, dtype=dtype)
        self.gag = torch.as_tensor(np.stack([g["gag"] for g in gags]), device=device)
        self.kg = t([g["k_g"] for g in gags])
        self.slip_eps = t([g["slip"] for g in gags])
        self.L0g = torch.ones_like(self.kg)

    def energy(self, x, F, per_system=False):
        e = super().energy(x, F, per_system=True)
        ln = torch.linalg.norm(self.bond_vectors(x, F), dim=-1)
        e = e + 0.5 * (self.kg * (ln - self.L0g) ** 2).sum(1)
        return e if per_system else e.sum()

    def slip(self, F):
        """Move rest lengths of over-strained sliding links so they sit at +-eps_slip. Returns # slipped."""
        ln = torch.linalg.norm(self.bond_vectors(self.x, F), dim=-1)
        s = (ln - self.L0g) / self.L0g
        # 5% band above the threshold so re-equilibration does not re-trigger the same link forever
        over = self.gag & (s.abs() > self.slip_eps * 1.05)
        target = ln / (1 + torch.sign(s) * torch.where(torch.isfinite(self.slip_eps), self.slip_eps, 0.0))
        self.L0g = torch.where(over, target, self.L0g)
        return over.sum(1)

    def F_path(self, kind, amp):
        return self.F_shear(amp) if kind == "shear" else self.F_stretch(amp, 0)

    def cyclic(self, kind="tension", amp=0.15, n_half=8, n_cycles=3, max_cascade=4):
        """Load 0 -> amp -> 0 n_cycles times with slip and collagen rupture after every step.
        Returns strains (n,), stress (B, n), and per-system slipped/broken counts."""
        ax = (0, 1) if kind == "shear" else (0, 0)
        up = np.linspace(0, amp, n_half + 1)[1:]
        down = np.linspace(amp, 0, n_half + 1)[1:]
        path = np.concatenate([np.concatenate([up, down]) for _ in range(n_cycles)])
        Fp = self.F0.clone()
        self.relax(Fp)
        sig, slipped, broken = [], torch.zeros(self.B, dtype=torch.long), torch.zeros(self.B, dtype=torch.long)
        for g in path:
            F = self.F_path(kind, g)
            self.move_affine(Fp, F)
            self.relax(F)
            for _ in range(max_cascade):
                ns = self.slip(F).cpu()
                nb = self.rupture(F).cpu()
                slipped += ns
                broken += nb
                if int(ns.sum() + nb.sum()) == 0:
                    break
                self.relax(F)
            sig.append(self.stress(F)[:, ax[0], ax[1]].cpu().numpy())
            Fp = F
        return path, np.stack(sig, 1), slipped.numpy(), broken.numpy()


def loop_metrics(path, sig, n_half, n_cycles):
    """Per system: dissipated energy per cycle (loop area), first/last-cycle secant stiffness at peak,
    residual stress after the last unload, stiffness retained (fatigue)."""
    per = 2 * n_half
    eps = np.concatenate([[0.0], path])
    out = []
    for s in sig:
        s0 = np.concatenate([[0.0], s])
        diss = []
        for c in range(n_cycles):
            seg = slice(c * per, (c + 1) * per + 1)
            diss.append(float(np.trapz(s0[seg], eps[seg])))  # loading work minus unloading work
        peak1 = s[n_half - 1]
        peakN = s[(n_cycles - 1) * per + n_half - 1]
        amp = path[n_half - 1]
        out.append(dict(diss_c1=diss[0], diss_last=diss[-1], peak_c1=peak1, peak_last=peakN,
                        secant_c1=peak1 / amp, secant_last=peakN / amp,
                        stiffness_retained=peakN / peak1 if peak1 else np.nan,
                        residual_stress=s[-1], loss_ratio=diss[0] / max(0.5 * peak1 * amp, 1e-12)))
    return out
