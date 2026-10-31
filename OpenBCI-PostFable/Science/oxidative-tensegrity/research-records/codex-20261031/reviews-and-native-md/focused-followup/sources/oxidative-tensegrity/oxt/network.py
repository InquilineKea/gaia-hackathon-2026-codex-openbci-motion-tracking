"""Discrete fibre-network mechanics: diluted triangular lattice (Broedersz-MacKintosh type).

Fibres are straight lines of bonds through a periodic 2D triangular lattice.  Energy terms:
  stretching   0.5 * mu_b * (|d_b| - 1)^2              per bond (fibre segment)
  bending      0.5 * kappa_p * theta_p^2               per pair of collinear bonds on one fibre
  rigid xlink  0.5 * kx_q * (phi_q - pi/3)^2           per adjacent spoke pair at a locked junction
  elastin      0.5 * mu_el * (|d_b| - 1)^2             on every lattice bond, never ruptures
  GAG tether   0.5 * k_gag * |x_i - F X_i|^2           embedding / osmotic background
Units: lattice spacing = 1 (one fibre segment between junctions), stress in units of mu_colI / spacing.

Mechanical equilibrium is found by L-BFGS on the summed energy of a batch of independent systems,
under a prescribed deformation gradient F with Lees-Edwards periodic images.  Stress is the first
Piola stress P = (1/A) dE/dF, which equals the total derivative at equilibrium.  Rupture removes
collagen bonds whose strain exceeds their rupture strain and re-equilibrates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import torch

SQ3 = math.sqrt(3.0)
DIRS = np.array([[1.0, 0.0], [0.5, SQ3 / 2], [-0.5, SQ3 / 2]])


class Lattice:
    """Periodic W x W triangular lattice. Bond id = 3 * node + direction (outgoing)."""

    def __init__(self, W: int):
        if W % 2:
            raise ValueError("W must be even for a periodic triangular lattice")
        self.W, self.N = W, W * W
        self.L = np.array([W, W * SQ3 / 2])
        self.area = float(self.L[0] * self.L[1])

        def idx(i, j):
            return (j % W) * W + (i % W)

        X = np.zeros((self.N, 2))
        nxt = np.zeros((self.N, 3), dtype=np.int64)
        shift = np.zeros((3 * self.N, 2))
        for j in range(W):
            for i in range(W):
                X[idx(i, j)] = (i + 0.5 * (j % 2), j * SQ3 / 2)
        for j in range(W):
            for i in range(W):
                a = idx(i, j)
                even = j % 2 == 0
                nbrs = [(i + 1, j), (i if even else i + 1, j + 1), (i - 1 if even else i, j + 1)]
                for k, (ni, nj) in enumerate(nbrs):
                    b = idx(ni, nj)
                    nxt[a, k] = b
                    d = X[b] - X[a]
                    shift[3 * a + k] = np.round((DIRS[k] - d) / self.L)
        prv = np.zeros_like(nxt)
        for a in range(self.N):
            for k in range(3):
                prv[nxt[a, k], k] = a
        self.X, self.nxt, self.prv = X, nxt, prv
        self.bi = np.repeat(np.arange(self.N), 3)
        self.bj = nxt.reshape(-1)
        self.bdir = np.tile(np.arange(3), self.N)
        self.shift = shift * self.L  # image offset in reference coordinates
        self.Nb = 3 * self.N

        # bending pairs: incoming bond along k into node a, outgoing bond along k out of a
        a = np.repeat(np.arange(self.N), 3)
        k = np.tile(np.arange(3), self.N)
        self.bend_in = 3 * prv[a, k] + k
        self.bend_out = 3 * a + k
        self.bend_node = a

        # spokes around each node in ccw order: out0, out1, out2, in0(rev), in1(rev), in2(rev)
        spokes, signs = [], []
        for n in range(self.N):
            s = [3 * n + 0, 3 * n + 1, 3 * n + 2, 3 * prv[n, 0] + 0, 3 * prv[n, 1] + 1, 3 * prv[n, 2] + 2]
            spokes.append(s)
            signs.append([1, 1, 1, -1, -1, -1])
        spokes, signs = np.array(spokes), np.array(signs, dtype=float)
        self.ang_u = spokes.reshape(-1)
        self.ang_v = np.roll(spokes, -1, axis=1).reshape(-1)
        self.ang_su = signs.reshape(-1)
        self.ang_sv = np.roll(signs, -1, axis=1).reshape(-1)
        self.ang_node = np.repeat(np.arange(self.N), 6)

        # fibre lines (for cutting one bond per line so fibres are finite)
        self.line = -np.ones(self.Nb, dtype=np.int64)
        lid = 0
        for kk in range(3):
            for start in range(self.N):
                if self.line[3 * start + kk] >= 0:
                    continue
                n = start
                while self.line[3 * n + kk] < 0:
                    self.line[3 * n + kk] = lid
                    n = nxt[n, kk]
                lid += 1
        self.n_lines = lid


@dataclass
class SystemSpec:
    """Per-system bond-level parameters (numpy, length Nb unless noted)."""
    alive: np.ndarray
    mu: np.ndarray
    kappa_b: np.ndarray        # per-bond bending factor; pair kappa = kappa * sqrt(f_in f_out)
    eps_r: np.ndarray
    rigid_node: np.ndarray     # length N, angular stiffness at locked junctions
    kappa: float
    mu_el: float
    k_gag: float
    prestrain: float = 0.0     # isotropic osmotic (GAG swelling) prestrain: tissue-scale tensegrity
    meta: dict = field(default_factory=dict)


class Batch:
    """Stack of systems on one lattice, evaluated together on one device."""

    def __init__(self, lat: Lattice, specs: list[SystemSpec], device="cpu", dtype=torch.float64):
        self.lat, self.specs, self.B = lat, specs, len(specs)
        t = lambda a: torch.as_tensor(np.asarray(a), device=device, dtype=dtype)
        ti = lambda a: torch.as_tensor(np.asarray(a), device=device, dtype=torch.long)
        self.device, self.dtype = device, dtype
        self.X = t(lat.X)
        self.shift = t(lat.shift)
        self.bi, self.bj = ti(lat.bi), ti(lat.bj)
        self.bend_in, self.bend_out = ti(lat.bend_in), ti(lat.bend_out)
        self.ang_u, self.ang_v = ti(lat.ang_u), ti(lat.ang_v)
        self.ang_su, self.ang_sv = t(lat.ang_su), t(lat.ang_sv)
        self.ang_node = ti(lat.ang_node)
        self.alive = torch.as_tensor(np.stack([s.alive for s in specs]), device=device)
        self.mu = t(np.stack([s.mu for s in specs]))
        self.kb = t(np.stack([s.kappa_b for s in specs]))
        self.eps_r = t(np.stack([s.eps_r for s in specs]))
        self.kappa = t([s.kappa for s in specs])[:, None]
        self.kx = t(np.stack([s.rigid_node for s in specs]))
        self.mu_el = t([s.mu_el for s in specs])[:, None]
        self.k_gag = t([s.k_gag for s in specs])[:, None, None]
        self.pre = t([s.prestrain for s in specs])
        eye = torch.eye(2, device=device, dtype=dtype)
        self.F0 = eye.expand(self.B, 2, 2) * (1 + self.pre)[:, None, None]
        self.x = (self.X[None] @ self.F0.transpose(1, 2)).clone()

    # ---- energy -------------------------------------------------------------------------
    def bond_vectors(self, x, F):
        img = torch.einsum("bij,nj->bni", F, self.shift)
        return x[:, self.bj] - x[:, self.bi] + img

    def energy(self, x, F, per_system=False):
        d = self.bond_vectors(x, F)
        ln = torch.linalg.norm(d, dim=-1)
        a = self.alive.to(self.dtype)
        mu_eff = self.mu * a + self.mu_el
        e = 0.5 * (mu_eff * (ln - 1.0) ** 2).sum(1)

        din, dout = d[:, self.bend_in], d[:, self.bend_out]
        cr = din[..., 0] * dout[..., 1] - din[..., 1] * dout[..., 0]
        dt = (din * dout).sum(-1)
        th = torch.atan2(cr, dt)
        kp = self.kappa * torch.sqrt(self.kb[:, self.bend_in] * self.kb[:, self.bend_out]) \
            * a[:, self.bend_in] * a[:, self.bend_out]
        e = e + 0.5 * (kp * th ** 2).sum(1)

        u = d[:, self.ang_u] * self.ang_su[None, :, None]
        v = d[:, self.ang_v] * self.ang_sv[None, :, None]
        phi = torch.atan2(u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0], (u * v).sum(-1))
        kq = self.kx[:, self.ang_node] * a[:, self.ang_u] * a[:, self.ang_v]
        e = e + 0.5 * (kq * (phi - math.pi / 3) ** 2).sum(1)

        xa = self.X[None] @ F.transpose(1, 2)
        e = e + 0.5 * (self.k_gag * (x - xa) ** 2).sum((1, 2))
        return e if per_system else e.sum()

    # ---- equilibrium ----------------------------------------------------------------------
    def relax(self, F, ftol=1e-7, max_rounds=40, iters=300):
        # ftol 1e-8 stalls at float64 round-off for these sizes; 1e-7 reproduces stress to ~1e-4 relative
        x = self.x.detach().clone().requires_grad_(True)
        opt = torch.optim.LBFGS([x], lr=1.0, max_iter=iters, history_size=50,
                                tolerance_grad=ftol, tolerance_change=1e-16,
                                line_search_fn="strong_wolfe")

        def closure():
            opt.zero_grad()
            en = self.energy(x, F)
            en.backward()
            return en

        # Floppy (sub-isostatic) networks have tiny forces long before they are relaxed, so a force
        # criterion alone stops early and overestimates stiffness: also require the energy to settle.
        fmax = float("inf")
        e_prev = float(self.energy(x.detach(), F))
        for _ in range(max_rounds):
            opt.step(closure)
            with torch.no_grad():
                e_now = float(self.energy(x, F))
            fmax = float(x.grad.abs().max())
            if fmax < ftol * 10 and abs(e_prev - e_now) <= 1e-10 * abs(e_now) + 1e-18:
                break
            e_prev = e_now
        self.x = x.detach()
        return fmax

    def stress(self, F):
        Fv = F.detach().clone().requires_grad_(True)
        e = self.energy(self.x, Fv)
        (g,) = torch.autograd.grad(e, Fv)
        return g / self.lat.area  # (B, 2, 2) first Piola stress

    def move_affine(self, F_old, F_new):
        M = F_new @ torch.linalg.inv(F_old)
        self.x = self.x @ M.transpose(1, 2)

    def bond_strain(self, F):
        d = self.bond_vectors(self.x, F)
        return torch.linalg.norm(d, dim=-1) - 1.0

    def rupture(self, F):
        """Break every alive collagen bond above its rupture strain. Returns # broken per system."""
        s = self.bond_strain(F)
        brk = self.alive & (s > self.eps_r)
        self.alive = self.alive & ~brk
        return brk.sum(1)

    # ---- protocols ------------------------------------------------------------------------
    def F_shear(self, g):
        F = self.F0.clone()
        F[:, 0, 1] += g * (1 + self.pre)
        return F

    def F_stretch(self, e, axis):
        F = self.F0.clone()
        F[:, axis, axis] *= (1 + e)
        return F

    def shear_curve(self, gammas):
        Fp = self.F0.clone()
        out = []
        self.relax(Fp)
        for g in gammas:
            F = self.F_shear(g)
            self.move_affine(Fp, F)
            self.relax(F)
            out.append(self.stress(F)[:, 0, 1].cpu().numpy())
            Fp = F
        return np.stack(out, 1)  # (B, n_gamma)

    def small_strain_moduli(self, eps=2e-3):
        """Linear shear modulus and constrained uniaxial moduli C_xx, C_yy (prestressed state)."""
        x0 = self.x.clone()
        self.relax(self.F0)
        xr = self.x.clone()
        base = self.stress(self.F0)
        res = {}
        for name, F in [("G", self.F_shear(eps)), ("Cx", self.F_stretch(eps, 0)), ("Cy", self.F_stretch(eps, 1))]:
            self.x = xr.clone()
            self.move_affine(self.F0, F)
            self.relax(F)
            P = self.stress(F)
            if name == "G":
                res[name] = ((P[:, 0, 1] - base[:, 0, 1]) / eps).cpu().numpy()
            else:
                ax = 0 if name == "Cx" else 1
                res[name] = ((P[:, ax, ax] - base[:, ax, ax]) / (eps * (1 + self.pre))).cpu().numpy()
        self.x = x0
        return res

    def failure_curve(self, strains, axis=0, max_cascade=8):
        """Quasi-static uniaxial (laterally constrained) stretch with bond rupture."""
        Fp = self.F0.clone()
        self.relax(Fp)
        sig, broken = [], []
        for e in strains:
            F = self.F_stretch(e, axis)
            self.move_affine(Fp, F)
            self.relax(F)
            nb = torch.zeros(self.B, dtype=torch.long, device=self.device)
            for _ in range(max_cascade):
                k = self.rupture(F)
                nb += k
                if int(k.sum()) == 0:
                    break
                self.relax(F)
            sig.append(self.stress(F)[:, axis, axis].cpu().numpy())
            broken.append(nb.cpu().numpy())
            Fp = F
        return np.stack(sig, 1), np.stack(broken, 1)


def coordination(spec: SystemSpec, lat: Lattice) -> float:
    return 2.0 * spec.alive.sum() / lat.N


def mesh_size(spec: SystemSpec, lat: Lattice) -> float:
    """Mean pore size (lattice units): sqrt(area / number of fibre-bounded faces), estimated
    from the alive bond density via Euler: faces ~ E - V for a connected planar graph."""
    E = spec.alive.sum()
    deg = np.bincount(lat.bi[spec.alive], minlength=lat.N) + np.bincount(lat.bj[spec.alive], minlength=lat.N)
    V = (deg > 0).sum()
    faces = max(E - V, 1)
    return math.sqrt(lat.area / faces)
