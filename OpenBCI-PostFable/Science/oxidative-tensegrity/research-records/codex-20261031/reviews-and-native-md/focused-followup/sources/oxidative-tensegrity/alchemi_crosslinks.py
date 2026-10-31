#!/usr/bin/env python3
"""Atomistic stage (GPU): batched stretch scans of crosslink model compounds with NVIDIA ALCHEMI.

STATUS: written against the ALCHEMI Toolkit 0.3.0-rc API as documented in its own agent skills
(nvalchemi-data-structures, nvalchemi-model-wrapping) and the ALCHEMI 101 deck.  NOT executed yet:
it needs a CUDA GPU (Brev / Nebius) and the third-party install must pass the review in
SECURITY-REVIEW.md and get the user's explicit approval first.

What it computes, for every crosslink chemistry in oxt/materials.py:
  - build a capped model fragment from SMILES (RDKit ETKDG), anchors = the two atom-mapped methyls
  - stretch the anchor-anchor distance in n_steps increments; at each length relax all other atoms
    with the anchors frozen (simple FIRE on model forces) -- every image of every chemistry sits in
    ONE GPU batch, so one model forward pass per step serves the whole scan
  - fit E(L) near the minimum -> axial stiffness k (eV/A^2), and max dE/dL -> peak force (eV/A)
  - write results/crosslink_params.json with k_rel = k / k(pyridinoline); the network model picks
    this up automatically (oxt.materials.load_crosslink_overrides)

Caveats printed into the JSON: foundation MLIPs are not reactive, so the peak force is a stiffness
proxy, not a bond-rupture force; fragments are minimal models, not the full crosslinked helices;
charges of pyridinium-type crosslinks are neutralised.

  python3 alchemi_crosslinks.py --model mace-off:medium --device cuda
  python3 alchemi_crosslinks.py --model mace-mp:medium-0b2 --out results/crosslink_params_mp.json  # 2nd model
  python3 alchemi_crosslinks.py --backend ase-mace-off   # cross-check with a second model family
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

# [CH3:1] and [CH3:2] mark the anchor atoms pulled apart.  Simplified neutral model fragments.
FRAGMENTS = {
    "HLNL":           "[CH3:1]CCCC(O)CNCCCC[CH3:2]",
    "pyridinoline":   "[CH3:1]CCn1cc(O)c(CC[CH3:2])cc1=O",         # neutral pyridinone proxy for 3-OH-pyridinium
    "pentosidine":    "[CH3:1]CCCn1c(NCCC[CH3:2])nc2ncccc12",       # imidazo[4,5-b]pyridine core
    "glucosepane":    "[CH3:1]CCCN1CC(O)C(O)C2N=C(NCCC[CH3:2])N=C12",  # approximate bicyclic core
    "dityrosine":     "[CH3:1]c1ccc(O)c(-c2cc([CH3:2])ccc2O)c1",
    "disulfide":      "[CH3:1]CSSC[CH3:2]",
    "isopeptide_TG2": "[CH3:1]CCC(=O)NCCCC[CH3:2]",
    "sulfilimine":    "[CH3:1]CCS(C)=NCCC[CH3:2]",
}


def build_atoms(smiles, seed=7):
    from ase import Atoms
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    anchors = [None, None]
    for a in mol.GetAtoms():
        if a.GetAtomMapNum() in (1, 2):
            anchors[a.GetAtomMapNum() - 1] = a.GetIdx()
            a.SetAtomMapNum(0)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise RuntimeError(f"embedding failed for {smiles}")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=2000)
    pos = mol.GetConformer().GetPositions()
    Z = [a.GetAtomicNum() for a in mol.GetAtoms()]
    atoms = Atoms(numbers=Z, positions=pos, pbc=False)
    atoms.center(vacuum=12.0)  # box large enough that stretched images never see their neighbours
    return atoms, anchors


def stretched_images(atoms, anchors, strains):
    """Affinely stretch along the anchor axis so each image starts near its constrained minimum."""
    i, j = anchors
    p = atoms.get_positions()
    axis = p[j] - p[i]
    L0 = np.linalg.norm(axis)
    u = axis / L0
    s = (p - p[i]) @ u
    imgs = []
    for e in strains:
        q = p + np.outer(s * e, u)
        a = atoms.copy()
        a.set_positions(q)
        imgs.append(a)
    return imgs, L0


# ------------------------------------------------------------------------------------------------
# ALCHEMI backend: one Batch holding every image of every chemistry
# ------------------------------------------------------------------------------------------------
def resolve_checkpoint(model_spec):
    """'mace-off:medium' (organic MLIP, ASL licence) or 'mace-mp:medium-0b2' (materials MLIP) -> local file."""
    from mace.calculators import foundations_models as fm

    family, _, name = model_spec.partition(":")
    if family == "mace-off":
        fm.mace_off(model=name or "medium", device="cpu", return_raw_model=True)  # downloads into the cache
        cache = Path(fm.get_cache_dir())
        hits = sorted(cache.glob(f"*OFF*{name or 'medium'}*.model"))
        if not hits:
            raise SystemExit(f"MACE-OFF checkpoint not found in {cache}")
        return str(hits[0])
    if family == "mace-mp":
        return fm.download_mace_mp_checkpoint(name or "medium-0b2")
    if Path(model_spec).exists():
        return model_spec
    raise SystemExit(f"unknown model spec {model_spec!r}")


def run_alchemi(jobs, model_spec, device, n_steps, fmax_tol):
    """Every image of every chemistry in ONE ALCHEMI Batch; anchors frozen with FreezeAtomsHook;
    ALCHEMI's batched FIRE2 relaxes all of them with one model forward pass per step."""
    import torch
    from nvalchemi._typing import AtomCategory
    from nvalchemi.data import AtomicData, Batch
    from nvalchemi.dynamics import FIRE2
    from nvalchemi.dynamics.base import ConvergenceHook, DynamicsStage
    from nvalchemi.dynamics.hooks import FreezeAtomsHook
    from nvalchemi.hooks import NeighborListHook
    from nvalchemi.models.mace import MACEWrapper

    dev = torch.device(device if (device != "cuda" or torch.cuda.is_available()) else "cpu")
    ckpt = resolve_checkpoint(model_spec)
    # ALCHEMI 0.3.0-rc (84fe8e8f) bug: MACEWrapper.from_checkpoint always routes its argument through
    # mace's download_mace_mp_checkpoint, which rejects local files (examples/advanced/04 hits the same
    # path).  Pass existing files straight through.
    import mace.calculators.foundations_models as fm

    _download = fm.download_mace_mp_checkpoint
    fm.download_mace_mp_checkpoint = lambda p=None: p if p and Path(str(p)).exists() else _download(p)
    try:
        # float64: energies are ~-1e4 eV per fragment, float32 rounding (~4 meV) would swamp the stiffness fit
        model = MACEWrapper.from_checkpoint(checkpoint_path=ckpt, device=dev, dtype=torch.float64)
    finally:
        fm.download_mace_mp_checkpoint = _download
    model.eval()

    data = []
    for jb in jobs:
        for a in jb["images"]:
            d = AtomicData.from_atoms(a)
            n = d.num_nodes
            d.positions = d.positions.to(torch.float64)  # FIRE2 kernels take their dtype from positions
            d.forces = torch.zeros(n, 3, dtype=torch.float64)
            d.energy = torch.zeros(1, 1, dtype=torch.float64)
            d.add_node_property("velocities", torch.zeros(n, 3, dtype=torch.float64))
            cat = torch.full((n,), AtomCategory.GAS.value, dtype=torch.long)
            cat[jb["anchors"]] = AtomCategory.SPECIAL.value  # FreezeAtomsHook's default target
            d.atom_categories = cat
            data.append(d)
    batch = Batch.from_data_list(data, device=dev)
    opt = FIRE2(
        model=model, dt=0.05, n_steps=n_steps,
        convergence_hook=ConvergenceHook(criteria=[
            {"key": "forces", "threshold": fmax_tol, "reduce_op": "norm", "reduce_dims": -1}]),
        hooks=[NeighborListHook(model.model_config.neighbor_config, stage=DynamicsStage.BEFORE_COMPUTE),
               FreezeAtomsHook()],
    )
    batch = opt.run(batch)
    # energies/forces of the last evaluated step (written into the batch by the dynamics engine)
    e = batch["energy"].detach().reshape(-1).cpu().numpy()
    f = batch["forces"].detach().clone()
    cats = batch.atom_categories.reshape(-1)
    f[cats == AtomCategory.SPECIAL.value] = 0.0
    fmax = float(f.norm(dim=1).max())
    if len(e) != sum(len(j["images"]) for j in jobs):
        raise RuntimeError(f"batch returned {len(e)} systems; expected all images (ordering check)")
    return e, opt.step_count, fmax


def run_ase_mace_off(jobs, device, n_steps, fmax_tol):
    """Cross-check backend using the mace-torch ASE calculator (MACE-OFF organic model)."""
    from ase.constraints import FixAtoms
    from ase.optimize import FIRE
    from mace.calculators import mace_off

    calc = mace_off(model="medium", device=device)
    E = []
    for jb in jobs:
        for a in jb["images"]:
            a = a.copy()
            a.calc = calc
            a.set_constraint(FixAtoms(indices=jb["anchors"]))
            FIRE(a, logfile=None).run(fmax=fmax_tol, steps=n_steps)
            E.append(a.get_potential_energy())
    return np.array(E), n_steps, float("nan")


def analyse(jobs, energies, strains):
    k, Fpk, out = {}, {}, {}
    n = len(strains)
    for c, jb in enumerate(jobs):
        e = energies[c * n:(c + 1) * n]
        L = jb["L0"] * (1 + np.asarray(strains))
        e = e - e.min()
        near = np.argsort(np.abs(L - L[np.argmin(e)]))[:5]
        coef = np.polyfit(L[near], e[near], 2)
        k[jb["name"]] = 2 * coef[0]
        Fpk[jb["name"]] = float(np.max(np.gradient(e, L)))
        out[jb["name"]] = dict(L0_A=jb["L0"], k_eV_A2=2 * coef[0], peak_force_eV_A=Fpk[jb["name"]],
                               E_eV=e.tolist(), L_A=L.tolist(), smiles=FRAGMENTS[jb["name"]])
    ref = k.get("pyridinoline") or np.median(list(k.values()))
    for name in out:
        out[name]["k_rel"] = float(k[name] / ref)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="alchemi", choices=["alchemi", "ase-mace-off"])
    ap.add_argument("--model", default="mace-off:medium")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--fmax", type=float, default=0.02)
    ap.add_argument("--min-strain", type=float, default=-0.06)
    ap.add_argument("--max-strain", type=float, default=0.25)
    ap.add_argument("--n-strain", type=int, default=21)
    ap.add_argument("--out", default=str(ROOT / "results" / "crosslink_params.json"))
    ap.add_argument("--chem-per-batch", type=int, default=0, help="chemistries per batch; 0 = all in one")
    args = ap.parse_args()

    strains = np.linspace(args.min_strain, args.max_strain, args.n_strain)
    jobs = []
    for name, smi in FRAGMENTS.items():
        atoms, anchors = build_atoms(smi)
        imgs, L0 = stretched_images(atoms, anchors, strains)
        jobs.append(dict(name=name, images=imgs, anchors=anchors, L0=L0))
    n_img = sum(len(j["images"]) for j in jobs)
    per = args.chem_per_batch or len(jobs)
    print(f"{len(jobs)} chemistries x {len(strains)} strains = {n_img} systems, {per} chemistries per GPU batch")
    t0 = time.time()
    E, steps, fmax = [], 0, 0.0
    for k in range(0, len(jobs), per):  # chunks bound GPU memory (all 168 systems at float64 overflow a 24 GB L4)
        group = jobs[k:k + per]
        if args.backend == "alchemi":
            e, s, f = run_alchemi(group, args.model, args.device, args.steps, args.fmax)
        else:
            e, s, f = run_ase_mace_off(group, args.device, args.steps, args.fmax)
        E = np.concatenate([E, e])
        steps, fmax = max(steps, s), max(fmax, f)
    res = analyse(jobs, E, strains)
    payload = dict(
        source=f"{args.backend}:{args.model}", seconds=time.time() - t0, steps=steps, final_fmax=fmax,
        caveats=["non-reactive MLIP: peak force is a stiffness proxy, not a rupture force",
                 "minimal neutral fragments, not crosslinked triple helices",
                 "k_rel is relative to the pyridinoline fragment"],
        crosslinks=res)
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    for n, r in res.items():
        print(f"{n:15s} k={r['k_eV_A2']:.3f} eV/A^2  k_rel={r['k_rel']:.2f}  Fpk={r['peak_force_eV_A']:.2f} eV/A")
    print("wrote", out)


if __name__ == "__main__":
    main()
