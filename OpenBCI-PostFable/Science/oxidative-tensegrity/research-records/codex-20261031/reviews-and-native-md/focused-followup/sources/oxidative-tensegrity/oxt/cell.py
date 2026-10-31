"""Cell scale: motor-clutch adhesions on a nonlinear fibrous matrix, a 6-strut tensegrity cell,
YAP with YAP->myosin feedback, recovery rate (resilience) and entropy proxies.

Matrix input for every condition is a secant Young's modulus curve E_sec(strain) in Pa, taken from the
network simulation (strain-stiffening and rupture included).  Nothing here is fitted to data.

References for model structure (parameters are textbook defaults from these papers):
  motor-clutch: Chan & Odde, Science 2008; talin reinforcement: Elosegui-Artola et al., NCB 2016;
  nuclear flattening -> YAP: Elosegui-Artola et al., Cell 2017; cell tensegrity: Ingber, J Cell Sci 2003;
  expanded-octahedron tensegrity: Coughlin & Stamenovic, J Appl Mech 1997;
  recovery-rate / resilience: Pyrkov, ..., Fedichev, Nat Commun 2021.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

KBT = 4.11  # pN nm at 298 K


# --------------------------------------------------------------------------------------------------
# matrix stiffness seen by an adhesion
# --------------------------------------------------------------------------------------------------
@dataclass
class MatrixCurve:
    strain: np.ndarray        # (G,) increasing
    E_sec: np.ndarray         # (M, G) Pa
    fail_strain: np.ndarray   # (M,) local strain at which the matrix tears

    def E_at(self, s):
        """Row-wise linear interpolation of E_sec at strains s (M,)."""
        s = np.clip(s, self.strain[0], self.strain[-1])
        j = np.clip(np.searchsorted(self.strain, s) - 1, 0, len(self.strain) - 2)
        s0, s1 = self.strain[j], self.strain[j + 1]
        w = (s - s0) / (s1 - s0)
        r = np.arange(self.E_sec.shape[0])
        return self.E_sec[r, j] * (1 - w) + self.E_sec[r, j + 1] * w


def k_adhesion(E_pa, a_m):
    """Substrate spring constant of a circular adhesion of radius a on an incompressible half-space,
    k = 4 pi E a / 9 (as used by Elosegui-Artola 2016), in pN/nm."""
    return 4 * math.pi * E_pa * a_m / 9 * 1e3


# --------------------------------------------------------------------------------------------------
# motor-clutch with talin reinforcement, vectorised over conditions
# --------------------------------------------------------------------------------------------------
@dataclass
class ClutchParams:
    n_m: float = 400       # myosin motors
    F_m: float = 2.0       # pN stall force per motor
    v_u: float = 120.0     # nm/s unloaded retrograde flow
    n_c: int = 75          # baseline available clutches
    n_c_max: int = 225
    k_on: float = 1.0      # 1/s
    k_off0: float = 0.1    # 1/s
    F_b: float = 2.0       # pN slip-bond force scale
    kappa_c: float = 5.0   # pN/nm clutch stiffness
    F_talin: float = 5.0   # pN talin unfolding -> reinforcement
    d_rho: float = 0.005   # integrin recruitment per unfolding event (fraction of n_c)
    tau_rho: float = 20.0  # s, adhesion turnover
    koff_reinf: float = 0.1  # off-rate factor for talin-unfolded (vinculin-reinforced) clutches
    a_m: float = 0.5e-6    # adhesion radius (m)
    L_field_m: float = 5e-6  # distance over which adhesion displacement strains the matrix (m)
    T: float = 40.0        # s simulated
    dt: float = 2e-3


def motor_clutch(curve: MatrixCurve, n_motor: np.ndarray, p: ClutchParams = ClutchParams(), seed=0,
                 traction_bins=None):
    rng = np.random.default_rng(seed)
    M, C = curve.E_sec.shape[0], p.n_c_max
    bound = np.zeros((M, C), bool)
    xc = np.zeros((M, C))
    unfolded = np.zeros((M, C), bool)
    rho = np.ones(M)
    x_sub = np.zeros(M)
    steps = int(p.T / p.dt)
    rec0 = steps // 2
    acc = dict(F=np.zeros(M), v=np.zeros(M), nb=np.zeros(M), rho=np.zeros(M), strain_max=np.zeros(M),
               P=np.zeros(M), strain=np.zeros(M))
    F_hist = np.zeros((M, steps - rec0), dtype=np.float32)
    idx = np.arange(C)[None, :]
    for t in range(steps):
        strain = x_sub / (p.a_m * 1e9)
        k = k_adhesion(curve.E_at(strain), p.a_m)
        F_sub = k * x_sub
        v = np.clip(p.v_u * (1 - F_sub / (n_motor * p.F_m)), 0, None)
        xc = np.where(bound, xc + v[:, None] * p.dt, xc)
        nb = bound.sum(1)
        x_sub = p.kappa_c * (xc * bound).sum(1) / (k + nb * p.kappa_c)
        Fi = np.where(bound, p.kappa_c * (xc - x_sub[:, None]), 0.0)
        # talin unfolding before integrin unbinding triggers reinforcement
        newly = bound & ~unfolded & (Fi > p.F_talin)
        unfolded |= newly
        rho += p.d_rho * newly.sum(1) - (rho - 1) / p.tau_rho * p.dt
        rho = np.clip(rho, 1, p.n_c_max / p.n_c)
        koff = p.k_off0 * np.exp(np.clip(Fi, 0, 60) / p.F_b) * np.where(unfolded, p.koff_reinf, 1.0)
        unbind = bound & (rng.random((M, C)) < 1 - np.exp(-koff * p.dt))
        avail = idx < (p.n_c * rho)[:, None]
        bind = ~bound & avail & (rng.random((M, C)) < 1 - math.exp(-p.k_on * p.dt))
        bound = (bound & ~unbind) | bind
        unfolded &= bound
        xc = np.where(bind, x_sub[:, None], xc)
        if t >= rec0:
            acc["F"] += F_sub
            acc["v"] += v
            acc["nb"] += nb
            acc["rho"] += rho
            acc["P"] += F_sub * v  # power against the matrix, pN nm/s
            acc["strain"] += strain
            acc["strain_max"] = np.maximum(acc["strain_max"], strain)
            F_hist[:, t - rec0] = F_sub
    n = steps - rec0
    out = {k: (v / n if k != "strain_max" else v) for k, v in acc.items()}
    # Shannon entropy of the traction distribution on fixed bins (bits)
    bins = traction_bins if traction_bins is not None else np.linspace(0, 400, 41)
    H = np.zeros(M)
    for m in range(M):
        h, _ = np.histogram(F_hist[m], bins=bins)
        q = h[h > 0] / h.sum()
        H[m] = -(q * np.log2(q)).sum()
    out["traction_entropy_bits"] = H
    # entropy production: motor work dissipated (traction * flow) + motor slip power, in kB/s
    out["entropy_prod_kB_per_s"] = (out["P"] + n_motor * p.F_m * out["v"]) / KBT
    # matrix strain decays away from an adhesion (~a/r); average it over the inter-adhesion field
    out["torn"] = out["strain"] * p.a_m / p.L_field_m > curve.fail_strain
    return out


# --------------------------------------------------------------------------------------------------
# 6-strut tensegrity cell anchored to the matrix
# --------------------------------------------------------------------------------------------------
def expanded_octahedron(L=1.0):
    """Coughlin-Stamenovic 6-strut tensegrity: 12 nodes at (0, +-L/4, +-L/2) and cyclic permutations,
    struts of length L, 24 cables of length sqrt(6)/4 L joining nearest non-strut nodes."""
    a, b = L / 2, L / 4
    P = []
    for s1 in (1, -1):
        for s2 in (1, -1):
            P += [(0, s1 * b, s2 * a), (s2 * a, 0, s1 * b), (s1 * b, s2 * a, 0)]
    P = np.array(P, float)
    n = len(P)
    D = np.linalg.norm(P[:, None] - P[None], axis=-1)
    struts = [(i, j) for i in range(n) for j in range(i + 1, n) if abs(D[i, j] - L) < 1e-9]
    lc = math.sqrt(6) / 4 * L
    cables = [(i, j) for i in range(n) for j in range(i + 1, n) if abs(D[i, j] - lc) < 1e-9]
    assert len(struts) == 6 and len(cables) == 24, (len(struts), len(cables))
    return P, np.array(struts), np.array(cables)


class TensegrityCell:
    """Cables = actomyosin (tension only, contractile), struts = microtubules (compression),
    basal face nodes adhere to the matrix through springs whose stiffness comes from the network.

    Contractility c shortens cable rest lengths: L0 = (1 - c) L_geom.  At equilibrium we report the
    basal footprint, cell height, strut compression, anchor traction and a nuclear-flattening proxy.
    """

    def __init__(self, k_cable=1.0, k_strut=200.0, size_um=10.0):
        self.P0, self.S, self.Cb = expanded_octahedron(1.0)
        z = self.P0[:, 2]
        self.P0 = self.P0 - [0, 0, z.min()]
        self.basal = np.flatnonzero(np.isclose(self.P0[:, 2], 0.0))  # 2 nodes; add next layer below
        # rotate so that a triangular face is basal: use the three lowest nodes of a face
        self.P0, self.basal = self._face_down()
        # the basal face has no actin cables of its own: the matrix, through adhesions, is the tension
        # member that closes the basal triangle (Ingber: ECM as part of the cell's tensegrity)
        bset = set(self.basal.tolist())
        self.Cb = np.array([c for c in self.Cb if not (c[0] in bset and c[1] in bset)])
        self.k_cable, self.k_strut, self.size_um = k_cable, k_strut, size_um
        self.Lc0 = np.linalg.norm(self.P0[self.Cb[:, 0]] - self.P0[self.Cb[:, 1]], axis=1)
        self.Ls0 = np.linalg.norm(self.P0[self.S[:, 0]] - self.P0[self.S[:, 1]], axis=1)

    def _face_down(self):
        P = self.P0
        # find a cable triangle
        adj = {}
        for i, j in self.Cb:
            adj.setdefault(i, set()).add(j)
            adj.setdefault(j, set()).add(i)
        tri = None
        for i in adj:
            for j in adj[i]:
                for k in adj[j]:
                    if k in adj[i] and k != i:
                        tri = (i, j, k)
                        break
                if tri:
                    break
            if tri:
                break
        A, B, C = P[list(tri)]
        n = np.cross(B - A, C - A)
        n /= np.linalg.norm(n)
        if np.dot(n, P.mean(0) - A) < 0:
            n = -n
        # rotation taking n to +z
        zax = np.array([0, 0, 1.0])
        v = np.cross(n, zax)
        s, c = np.linalg.norm(v), np.dot(n, zax)
        if s < 1e-12:
            R = np.eye(3)
        else:
            vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
        Q = (P - A) @ R.T
        Q[:, 2] -= Q[:, 2].min()
        return Q, np.array(tri)

    def solve(self, contractility, k_anchor, x0=None):
        """k_anchor: in-plane anchor stiffness (units of k_cable). Basal nodes are held at z=0."""
        n = len(self.P0)
        Lc = (1 - contractility) * self.Lc0
        anchor = self.P0[self.basal, :2].copy()
        free = np.ones((n, 3), bool)
        free[self.basal, 2] = False

        def unpack(q):
            P = self.P0.copy()
            P[free] = q
            return P

        def energy(q):
            P = unpack(q)
            dc = P[self.Cb[:, 0]] - P[self.Cb[:, 1]]
            lc = np.linalg.norm(dc, axis=1)
            ext = np.clip(lc - Lc, 0, None)               # cables are tension-only
            ds = P[self.S[:, 0]] - P[self.S[:, 1]]
            ls = np.linalg.norm(ds, axis=1)
            ua = P[self.basal, :2] - anchor
            E = 0.5 * self.k_cable * (ext ** 2).sum() + 0.5 * self.k_strut * ((ls - self.Ls0) ** 2).sum() \
                + 0.5 * k_anchor * (ua ** 2).sum() + 1e-6 * (P[:, :2].mean(0) ** 2).sum()
            g = np.zeros_like(P)
            fc = (self.k_cable * ext / np.maximum(lc, 1e-12))[:, None] * dc
            np.add.at(g, self.Cb[:, 0], fc)
            np.add.at(g, self.Cb[:, 1], -fc)
            fs = (self.k_strut * (ls - self.Ls0) / ls)[:, None] * ds
            np.add.at(g, self.S[:, 0], fs)
            np.add.at(g, self.S[:, 1], -fs)
            g[self.basal, :2] += k_anchor * ua
            g[:, :2] += 2e-6 * P[:, :2].mean(0) / n
            return E, g[free]

        q0 = self.P0[free] if x0 is None else x0
        r = minimize(energy, q0, jac=True, method="L-BFGS-B", options=dict(maxiter=5000, gtol=1e-10))
        P = unpack(r.x)
        base = P[self.basal]
        area = 0.5 * abs(np.cross(base[1, :2] - base[0, :2], base[2, :2] - base[0, :2]))
        b0 = self.P0[self.basal]
        area0 = 0.5 * abs(np.cross(b0[1, :2] - b0[0, :2], b0[2, :2] - b0[0, :2]))
        lc = np.linalg.norm(P[self.Cb[:, 0]] - P[self.Cb[:, 1]], axis=1)
        ls = np.linalg.norm(P[self.S[:, 0]] - P[self.S[:, 1]], axis=1)
        tension = self.k_cable * np.clip(lc - Lc, 0, None)
        compression = self.k_strut * np.clip(self.Ls0 - ls, 0, None)
        ua = np.linalg.norm(P[self.basal, :2] - anchor, axis=1)
        height = P[:, 2].max()
        return dict(
            footprint=area / area0,
            height=height / self.P0[:, 2].max(),
            prestress=tension.mean(),
            strut_load=compression.mean(),
            anchor_traction=(k_anchor * ua).mean(),
            anchor_disp_um=ua.mean() * self.size_um,
            slack_cables=int((lc < Lc).sum()),
            # nuclear flattening proxy: spread footprint and low height (Elosegui-Artola 2017)
            flattening=(area / area0) / (height / self.P0[:, 2].max()),
            x=r.x,
        )


# --------------------------------------------------------------------------------------------------
# coupled cell state: adhesion + tensegrity + YAP + myosin feedback
# --------------------------------------------------------------------------------------------------
def hill(x, k, n=2.0):
    x = np.maximum(x, 0)
    return x ** n / (x ** n + k ** n)


@dataclass
class CellParams:
    beta: float = 1.5        # YAP -> myosin gain (YAP/TAZ drive actomyosin genes)
    c0: float = 0.04         # baseline cable contractility per unit myosin
    F50: float = 60.0        # pN per adhesion for half-maximal adhesion signalling
    ps50: float = 0.5        # transmitted prestress (fraction of rigid-anchor value) for half-max import
    k_cable_pN_nm: float = 5.0
    tau_Y: float = 0.5       # h, YAP shuttling
    tau_M: float = 6.0       # h, myosin transcription/turnover


def yap_from(F_adh, prestress_ratio, p: CellParams):
    """Nuclear YAP needs both adhesion signalling and cytoskeletal prestress reaching the nucleus."""
    return hill(F_adh, p.F50) * hill(prestress_ratio, p.ps50, 3.0)


def nuc_cyto_ratio(Y):
    return 0.7 + 2.8 * Y


class CellModel:
    """Evaluates steady YAP for a matrix condition at a given myosin level M (1 = basal)."""

    def __init__(self, curve: MatrixCurve, clutch=ClutchParams(), cp=CellParams(), seed=0):
        self.curve, self.clutch, self.cp, self.seed = curve, clutch, cp, seed
        self.cell = TensegrityCell(k_cable=1.0)
        self._ps_cache = {}

    def _rigid_prestress(self, c):
        key = round(float(c), 4)
        if key not in self._ps_cache:
            self._ps_cache[key] = self.cell.solve(key, 1e3)["prestress"]
        return self._ps_cache[key]

    def mechanics(self, M):
        """M: (Mcond,) myosin level. Returns dict of arrays."""
        M = np.asarray(M, float)
        mc = motor_clutch(self.curve, self.clutch.n_m * M, self.clutch, seed=self.seed)
        # anchor stiffness in cable units, using the matrix secant modulus at the adhesion strain
        E_loc = self.curve.E_at(mc["strain"])
        k_anchor = k_adhesion(E_loc, 2e-6) * mc["rho"] / self.cp.k_cable_pN_nm
        con = np.minimum(0.5, self.cp.c0 * M)
        tens = [self.cell.solve(c, ka) for c, ka in zip(con, k_anchor)]
        ps_rigid = np.array([self._rigid_prestress(c) for c in con])
        ps_ratio = np.array([t["prestress"] for t in tens]) / ps_rigid
        Y = yap_from(mc["F"], ps_ratio, self.cp)
        out = dict(Y=Y, k_anchor=k_anchor, E_loc=E_loc, prestress_ratio=ps_ratio,
                   flattening=np.array([t["flattening"] for t in tens]),
                   footprint=np.array([t["footprint"] for t in tens]),
                   height=np.array([t["height"] for t in tens]),
                   strut_load=np.array([t["strut_load"] for t in tens]),
                   prestress=np.array([t["prestress"] for t in tens]))
        out.update({f"mc_{k}": v for k, v in mc.items()})
        return out

    def steady_state(self, M_init, iters=6, damp=0.6):
        """Fixed point of M -> Y(M) -> M_target = 1 + beta Y."""
        M = np.asarray(M_init, float).copy()
        for _ in range(iters):
            mech = self.mechanics(M)
            M = damp * (1 + self.cp.beta * mech["Y"]) + (1 - damp) * M
        mech = self.mechanics(M)
        mech["M"] = M
        return mech

    def recovery_rate(self, M_star, Y_star, dM=0.15):
        """Linearise dY/dt = (Y(M) - Y)/tau_Y, dM/dt = (1 + beta Y - M)/tau_M around the fixed point.
        dY_ss/dM is estimated by finite difference of the mechanics.  Returns slowest decay rate (1/h).
        A rate near zero is critical slowing down: loss of resilience in the Fedichev sense."""
        lo = self.mechanics(M_star - dM)["Y"]
        hi = self.mechanics(M_star + dM)["Y"]
        s = (hi - lo) / (2 * dM)
        rates = []
        for si in s:
            J = np.array([[-1 / self.cp.tau_Y, si / self.cp.tau_Y],
                          [self.cp.beta / self.cp.tau_M, -1 / self.cp.tau_M]])
            rates.append(-np.max(np.linalg.eigvals(J).real))
        return np.array(rates), s
