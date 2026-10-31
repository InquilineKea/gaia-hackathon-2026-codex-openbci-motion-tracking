#!/usr/bin/env python3
"""ALCHEMI + AIMNet2: does glycation of collagen's GAG-binding residues weaken the collagen-GAG interface?

Collagen side: capped Lys and Arg (the residues dermatan/chondroitin sulfate bind) and their glycated forms,
CML-Lys (Nε-carboxymethyl-lysine) and MG-H1-Arg (methylglyoxal hydroimidazolone), which remove the positive charge.
GAG side: a dermatan-sulfate-like disaccharide (IdoA-GalNAc, methyl glycoside) with 0, 1 (4S) or 2 (2S,4S) sulfates.

For each pair: rigid scans along the cation-anion axis at several orientations, energies from ALCHEMI's AIMNet2
wrapper, all complexes and monomers in one batch.  Reported:
  E_sr   short-range interaction from AIMNet2 (E_complex - E_A - E_B; the wrapper has no long-range Coulomb)
  E_es   screened electrostatics from AIMNet2 partial charges in water (eps 78.5, Debye length 0.8 nm, 0.15 M)
Caveats: rigid fragments (no relaxation), no explicit water or counterions, no conformational entropy, so these
are contact energies to rank chemistries, not binding free energies. Follow-up: OpenMM/GROMACS with a validated
protein-glycan force field.

  python3 alchemi_collagen_gag.py --device cpu --out results/alchemi_gag/collagen_gag_pilot.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

# charged atoms marked with map number 1 (cation side) / 2 (anion side) define the scan axis
COLLAGEN_SIDE = {
    "Lys":       ("CC(=O)NC(CCCC[NH3+:1])C(=O)NC", +1),
    "Arg":       ("CC(=O)NC(CCCNC(=[NH2+])[NH2:1])C(=O)NC", +1),
    "CML-Lys":   ("CC(=O)NC(CCCC[NH2+:1]CC(=O)[O-])C(=O)NC", 0),
    "MG-H1-Arg": ("CC(=O)NC(CCCNC1=NC(=O)C(C)[NH:1]1)C(=O)NC", 0),
}
GAG_SIDE = {
    "DS-0S":   ("COC1OC(CO)C(O)C(OC2OC(C(=O)[O-:2])C(O)C(O)C2O)C1NC(C)=O", -1),
    "DS-4S":   ("COC1OC(CO)C(OS(=O)(=O)[O-:2])C(OC2OC(C([O-])=O)C(O)C(O)C2O)C1NC(C)=O", -2),
    "DS-2S4S": ("COC1OC(CO)C(OS(=O)(=O)[O-:2])C(OC2OC(C([O-])=O)C(O)C(O)C2OS(=O)(=O)[O-])C1NC(C)=O", -3),
}
DISTANCES = [2.8, 3.2, 3.6, 4.0, 4.5, 5.0, 6.0, 8.0]
EPS_W, DEBYE_A, KE = 78.5, 8.0, 14.3996  # eV*A/e^2


def embed(smiles, seed=11):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    key = None
    for a in mol.GetAtoms():
        if a.GetAtomMapNum():
            key = a.GetIdx()
            a.SetAtomMapNum(0)
    p = AllChem.ETKDGv3()
    p.randomSeed = seed
    if AllChem.EmbedMolecule(mol, p) != 0:
        raise RuntimeError(f"embedding failed: {smiles}")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
    X = mol.GetConformer().GetPositions()
    Z = np.array([a.GetAtomicNum() for a in mol.GetAtoms()])
    return Z, X, key


def orient(X, key, direction):
    """Translate so the key atom is at the origin and the centroid lies opposite to `direction`."""
    X = X - X[key]
    c = -X.mean(0)
    c /= np.linalg.norm(c) + 1e-12
    v = np.cross(c, direction)
    s, co = np.linalg.norm(v), float(np.dot(c, direction))
    if s < 1e-9:
        R = np.eye(3) if co > 0 else -np.eye(3)
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - co) / s ** 2)
    return X @ R.T


def spin(X, axis, ang):
    axis = axis / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K
    return X @ R.T


def build_systems(n_orient):
    systems, monomers = [], {}
    for cn, (csmi, cq) in COLLAGEN_SIDE.items():
        Zc, Xc, kc = embed(csmi)
        Xc = orient(Xc, kc, np.array([1.0, 0, 0]))           # key atom at origin, pointing +x: body on -x
        monomers[cn] = (Zc, Xc, cq)
        for gn, (gsmi, gq) in GAG_SIDE.items():
            Zg, Xg, kg = embed(gsmi)
            Xg = orient(Xg, kg, np.array([-1.0, 0, 0]))      # key atom at origin, pointing -x: body on +x
            monomers[gn] = (Zg, Xg, gq)
            for o in range(n_orient):
                Xgo = spin(Xg, np.array([1.0, 0, 0]), 2 * np.pi * o / n_orient)
                for d in DISTANCES:
                    Xd = Xgo + np.array([d, 0, 0])
                    dmin = np.min(np.linalg.norm(Xc[:, None] - Xd[None], axis=-1))
                    if dmin < 1.6:
                        continue
                    systems.append(dict(pair=(cn, gn), orient=o, d=d, Z=np.concatenate([Zc, Zg]),
                                        X=np.vstack([Xc, Xd]), q=cq + gq, n_c=len(Zc)))
    return systems, monomers


def run(systems, monomers, device, chunk=16):
    import torch
    from nvalchemi.data import AtomicData, Batch
    from nvalchemi.hooks import NeighborListHook
    from nvalchemi.models.aimnet2 import AIMNet2Wrapper

    dev = torch.device(device if (device != "cuda" or torch.cuda.is_available()) else "cpu")
    model = AIMNet2Wrapper.from_checkpoint("aimnet2_wb97m_d3_3", device=dev)
    model.eval()
    try:
        model.set_config("active_outputs", {"energy", "charges"})
    except Exception:
        pass

    # single-point evaluations outside a dynamics loop: build the external MATRIX neighbour list ourselves
    # (NeighborListHook normally does this at BEFORE_COMPUTE inside FIRE2/MD)
    nl = NeighborListHook(model.model_config.neighbor_config)

    def evaluate(items):
        E, Q = [], []
        for k in range(0, len(items), chunk):
            data = []
            for Z, X, q in items[k:k + chunk]:
                data.append(AtomicData(positions=torch.tensor(X, dtype=torch.float32),
                                       atomic_numbers=torch.tensor(Z, dtype=torch.long),
                                       energy=torch.zeros(1, 1), forces=torch.zeros(len(Z), 3),
                                       charge=torch.full((1, 1), float(q))))
            b = Batch.from_data_list(data, device=dev)
            nl._rebuild(b)
            with torch.enable_grad():
                out = model(b)
            E += out["energy"].detach().reshape(-1).cpu().tolist()
            ch = out.get("charges")
            ptr = np.cumsum([0] + [len(Z) for Z, _, _ in items[k:k + chunk]])
            chv = ch.detach().reshape(-1).cpu().numpy() if ch is not None else None
            Q += [None if chv is None else chv[ptr[i]:ptr[i + 1]] for i in range(len(ptr) - 1)]
        return E, Q

    mono_names = list(monomers)
    Em, _ = evaluate([monomers[n] for n in mono_names])
    Em = dict(zip(mono_names, Em))
    Ec, Qc = evaluate([(s["Z"], s["X"], s["q"]) for s in systems])
    for s, e, q in zip(systems, Ec, Qc):
        a, g = s["pair"]
        s["E_sr"] = e - Em[a] - Em[g]
        if q is not None:
            Xa, Xg = s["X"][:s["n_c"]], s["X"][s["n_c"]:]
            r = np.linalg.norm(Xa[:, None] - Xg[None], axis=-1)
            s["E_es"] = float(KE / EPS_W * np.sum(np.outer(q[:s["n_c"]], q[s["n_c"]:]) * np.exp(-r / DEBYE_A) / r))
        else:
            s["E_es"] = float("nan")
    return Em


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--orient", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "results" / "alchemi_gag" / "collagen_gag.json"))
    a = ap.parse_args()
    t0 = time.time()
    systems, monomers = build_systems(a.orient)
    print(f"{len(systems)} complexes + {len(monomers)} monomers")
    run(systems, monomers, a.device)
    table = {}
    for (cn, gn) in {s["pair"] for s in systems}:
        rows = [s for s in systems if s["pair"] == (cn, gn)]
        best = min(rows, key=lambda s: s["E_sr"] + s["E_es"])
        by_d = {}
        for d in DISTANCES:
            v = [s["E_sr"] + s["E_es"] for s in rows if s["d"] == d]
            if v:
                by_d[str(d)] = float(np.min(v))
        table[f"{cn}|{gn}"] = dict(min_total_eV=best["E_sr"] + best["E_es"], E_sr_at_min=best["E_sr"],
                                   E_es_at_min=best["E_es"], d_at_min=best["d"], orient_at_min=best["orient"],
                                   min_over_orient_by_distance=by_d)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(source="alchemi:aimnet2_wb97m_d3_3", seconds=time.time() - t0,
                                   caveats=["rigid fragments", "no explicit solvent/counterions",
                                            "screened Coulomb uses AIMNet2 charges, eps 78.5, Debye 8 A",
                                            "contact energies, not binding free energies"],
                                   pairs=table), indent=2))
    for k in sorted(table):
        r = table[k]
        print(f"{k:22s} min E = {r['min_total_eV']:+.3f} eV  (short-range {r['E_sr_at_min']:+.3f}, "
              f"screened es {r['E_es_at_min']:+.3f}) at {r['d_at_min']} A")
    print("wrote", out)


if __name__ == "__main__":
    main()
