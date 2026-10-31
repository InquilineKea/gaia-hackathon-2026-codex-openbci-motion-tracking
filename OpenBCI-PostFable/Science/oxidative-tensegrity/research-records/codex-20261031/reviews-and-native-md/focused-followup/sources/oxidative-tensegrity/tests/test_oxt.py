"""Hardware-free checks: python3 -m pytest -q tests"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oxt.cell import TensegrityCell, expanded_octahedron, k_adhesion  # noqa: E402
from oxt.lammps_export import export  # noqa: E402
from oxt.materials import COLLAGENS, TISSUES, Damage, build_spec, tissue_dose  # noqa: E402
from oxt.network import Batch, Lattice, SystemSpec, coordination  # noqa: E402
from oxt.physio import heart, transport  # noqa: E402


def full_spec(lat, **kw):
    Nb = lat.Nb
    d = dict(alive=np.ones(Nb, bool), mu=np.ones(Nb), kappa_b=np.ones(Nb), eps_r=np.full(Nb, 9.0),
             rigid_node=np.zeros(lat.N), kappa=0.0, mu_el=0.0, k_gag=0.0)
    d.update(kw)
    return SystemSpec(**d)


def test_lattice_bonds_are_unit_length():
    lat = Lattice(8)
    d = lat.X[lat.bj] - lat.X[lat.bi] + lat.shift
    assert np.allclose(np.linalg.norm(d, axis=1), 1.0)


def test_full_triangular_lattice_moduli_match_analytic():
    lat = Lattice(8)
    m = Batch(lat, [full_spec(lat)]).small_strain_moduli()
    assert m["G"][0] == pytest.approx(math.sqrt(3) / 4, rel=1e-3)
    assert m["Cx"][0] == pytest.approx(3 * math.sqrt(3) / 4, rel=1e-3)
    assert m["Cy"][0] == pytest.approx(3 * math.sqrt(3) / 4, rel=1e-3)


def test_rigid_rotation_costs_no_energy():
    import torch

    lat = Lattice(8)
    spec = build_spec(lat, COLLAGENS["I"], Damage("iso", 1.0), np.random.default_rng(0), k_gag=0.0)
    b = Batch(lat, [spec])
    th = 0.3
    R = torch.tensor([[[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]], dtype=torch.float64)
    x = b.X[None] @ R.transpose(1, 2)
    assert float(b.energy(x, R)) < 1e-20


def test_target_connectivity_and_crosslink_bridging():
    lat = Lattice(16)
    rng = np.random.default_rng(1)
    s0 = build_spec(lat, COLLAGENS["I"], Damage(), rng, z=3.4)
    assert coordination(s0, lat) == pytest.approx(3.4, abs=0.25)
    s1 = build_spec(lat, COLLAGENS["I"], Damage("aniso", 1.0), np.random.default_rng(1), z=3.4)
    added = s1.alive & ~s0.alive
    assert added.sum() > 0 and np.all(lat.bdir[added] == 0)  # anisotropic bridges only along the axis


def test_tissue_dose_saturates_with_turnover():
    t = TISSUES["myocardium"]  # fast turnover: plateaus early
    assert tissue_dose(t, 80) - tissue_dose(t, 50) < 0.01
    assert tissue_dose(TISSUES["tendon"], 80) > tissue_dose(TISSUES["skin_dermis"], 80)
    assert tissue_dose(TISSUES["skin_dermis"], 80) > tissue_dose(TISSUES["skin_dermis"], 20)


def test_tensegrity_geometry_and_tension_only_cables():
    P, S, Cb = expanded_octahedron()
    assert len(S) == 6 and len(Cb) == 24
    cell = TensegrityCell()
    stiff = cell.solve(0.06, 100.0)
    soft = cell.solve(0.06, 0.003)
    assert stiff["prestress"] > 5 * soft["prestress"]   # a soft matrix cannot hold the cell's tension
    assert soft["height"] < stiff["height"]


def test_adhesion_stiffness_units():
    assert k_adhesion(1000.0, 1e-6) == pytest.approx(4 * math.pi / 9, rel=1e-9)  # pN/nm


def test_transport_limits():
    free = transport("TGF-beta1", 0.0, 0.0, 0.0, 10.0)
    dense = transport("TGF-beta1", 0.3, 0.06, 1.0, 10.0)
    assert dense["D_eff"] < free["D_eff"]
    assert 0 < dense["delivered_frac"] <= 1


def test_heart_stiffer_matrix_lowers_filling():
    young = heart(1.0, 10.0, 10.0, 1.0)
    old = heart(3.0, 30.0, 10.0, 1.3)
    assert old["EDV"] < young["EDV"] and old["SV"] < young["SV"]


def test_lammps_export(tmp_path):
    lat = Lattice(8)
    spec = build_spec(lat, COLLAGENS["VII"], Damage("iso", 1.0), np.random.default_rng(2), mu_el=0.01)
    inp = export(spec, lat, tmp_path, name="t")
    data = (tmp_path / "t.data").read_text()
    assert f"{lat.N} atoms" in data and "Angles" in data
    assert "fix             shear all deform" in inp.read_text()
