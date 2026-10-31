#!/usr/bin/env python3
"""Figures + SUMMARY.md from a results directory written by run_sweep.py."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# reference categorical palette, fixed slot order (dataviz skill, validated light-mode instance)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"
MODE_COLOR = {"none": C[0], "iso": C[1], "aniso": C[2]}
MODE_LABEL = {"none": "healthy (enzymatic only)", "iso": "oxidative, isotropic", "aniso": "oxidative, anisotropic"}
plt.rcParams.update({"axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "lines.linewidth": 2})


def cols_with(df, prefix):
    cs = [c for c in df.columns if c.startswith(prefix)]
    return cs, np.array([float(c[len(prefix):]) for c in cs])


def fig_branching(net, out):
    cols = sorted(net.collagen.unique())
    fig, axs = plt.subplots(1, len(cols), figsize=(4 * len(cols), 3.4), sharey=True)
    dmax = net.dose.max()
    for ax, col in zip(np.atleast_1d(axs), cols):
        d = net[net.collagen == col]
        for mode in ("none", "iso", "aniso"):
            s = d[(d["mode"] == mode) & ((d.dose == dmax) | (mode == "none"))]
            g = s.groupby("z_target").agg(G=("G", "mean"), Gs=("G", "std"), z=("z", "mean")).reset_index()
            ax.errorbar(g.z, g.G, yerr=g.Gs, color=MODE_COLOR[mode], marker="o", ms=5, capsize=2,
                        label=MODE_LABEL[mode] + ("" if mode == "none" else f", dose {dmax:g}"))
        ax.axvline(4.0, color=MUTED, ls=":", lw=1)
        ax.text(4.03, 0.03, "isostatic z=4 (2D)", color=MUTED, fontsize=7, transform=ax.get_xaxis_transform())
        ax.set_yscale("log")
        ax.set_title(f"Collagen {col}", color=INK)
        ax.set_xlabel("connectivity z (branching factor)")
    np.atleast_1d(axs)[0].set_ylabel("linear shear modulus G (units of μ_I)")
    np.atleast_1d(axs)[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Rigidity vs branching: oxidative crosslinks rigidify sub-isostatic networks", color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig1_branching_rigidity.png", dpi=160)
    plt.close(fig)


def fig_stiffening(fail, out):
    cs, g = cols_with(fail, "sig_g")
    cols = sorted(fail.collagen.unique())
    dmax = fail.dose.max()
    fig, axs = plt.subplots(1, len(cols), figsize=(4 * len(cols), 3.4))
    for ax, col in zip(np.atleast_1d(axs), cols):
        for mode in ("none", "iso", "aniso"):
            s = fail[(fail.collagen == col) & (fail["mode"] == mode) & ((fail.dose == dmax) | (mode == "none"))]
            sig = s[cs].mean().to_numpy()
            K = np.gradient(sig, g)
            ax.plot(g, K / max(s.G.mean(), 1e-12), color=MODE_COLOR[mode], marker="o", ms=4, label=MODE_LABEL[mode])
        ax.set_yscale("log")
        ax.set_xlabel("shear strain γ")
        ax.set_title(f"Collagen {col}", color=INK)
    np.atleast_1d(axs)[0].set_ylabel("differential stiffness K(γ) / G₀")
    np.atleast_1d(axs)[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Strain stiffening (the range cells sense through) is flattened by oxidative crosslinks", color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig2_strain_stiffening.png", dpi=160)
    plt.close(fig)


def fig_failure(fail, out):
    cs, e = cols_with(fail, "fail_e")
    cols = sorted(fail.collagen.unique())
    dmax = fail.dose.max()
    fig, axs = plt.subplots(2, len(cols), figsize=(4 * len(cols), 6.4))
    for j, col in enumerate(cols):
        ax = axs[0, j]
        for mode in ("none", "iso", "aniso"):
            s = fail[(fail.collagen == col) & (fail["mode"] == mode) & ((fail.dose == dmax) | (mode == "none"))]
            ax.plot(e, s[cs].mean().to_numpy(), color=MODE_COLOR[mode], label=MODE_LABEL[mode])
        ax.set_title(f"Collagen {col}: stretch to failure (x)", color=INK)
        ax.set_xlabel("tensile strain")
        ax.set_ylabel("stress σ_xx")
        ax = axs[1, j]
        d = fail[fail.collagen == col].groupby(["mode", "dose"]).agg(
            cx=("Cx", "mean"), cy=("Cy", "mean"), tough=("toughness", "mean"), strength=("strength", "mean")).reset_index()
        base = d[d["mode"] == "none"].iloc[0]
        for mode in ("iso", "aniso"):
            s = pd.concat([d[d["mode"] == "none"], d[d["mode"] == mode]])
            ax.plot(s.dose, s.strength / base.strength, color=MODE_COLOR[mode], marker="o", label=f"strength, {mode}")
            ax.plot(s.dose, s.tough / base.tough, color=MODE_COLOR[mode], marker="s", ls="--", label=f"toughness, {mode}")
            ax.plot(s.dose, (s.cx / s.cy) / (base.cx / base.cy), color=MODE_COLOR[mode], marker="^", ls=":",
                    label=f"anisotropy Cx/Cy, {mode}")
        ax.axhline(1, color=MUTED, lw=1)
        ax.set_xlabel("oxidative crosslink dose")
        ax.set_ylabel("relative to healthy")
    axs[0, 0].legend(frameon=False, fontsize=7)
    axs[1, 0].legend(frameon=False, fontsize=6)
    fig.suptitle("Strength, toughness and anisotropy: isotropic vs anisotropic oxidative crosslinks", color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig3_failure_anisotropy.png", dpi=160)
    plt.close(fig)


def fig_cell(cell, out):
    c = cell[cell.source == "collagen"]
    metrics = [("YAP_NC", "YAP nuclear/cytoplasmic"), ("prestress_ratio", "tensegrity prestress held\n(fraction of rigid anchor)"),
               ("mc_F", "traction per adhesion (pN)"), ("recovery_rate_per_h", "recovery rate (1/h)"),
               ("mc_traction_entropy_bits", "traction-state entropy (bits)"),
               ("mc_entropy_prod_kB_per_s", "entropy production (k_B/s)")]
    cols = sorted(c.collagen.dropna().unique())
    fig, axs = plt.subplots(len(cols), len(metrics), figsize=(2.9 * len(metrics), 2.6 * len(cols)), squeeze=False)
    for i, col in enumerate(cols):
        d = c[c.collagen == col]
        h = d[d["mode"] == "none"]
        for j, (m, lab) in enumerate(metrics):
            ax = axs[i, j]
            for mode in ("iso", "aniso"):
                s = pd.concat([h, d[d["mode"] == mode]]).sort_values("dose")
                ax.plot(s.dose, s[m], color=MODE_COLOR[mode], marker="o", ms=4, label=MODE_LABEL[mode])
                bad = s[~s.self_supporting.astype(bool)]
                ax.scatter(bad.dose, bad[m], s=60, facecolors="none", edgecolors=INK, lw=1, zorder=3)
            if i == 0:
                ax.set_title(lab, color=INK, fontsize=8)
            if j == 0:
                ax.set_ylabel(f"Collagen {col}")
            if i == len(cols) - 1:
                ax.set_xlabel("oxidative dose")
    axs[0, 0].legend(frameon=False, fontsize=6)
    fig.suptitle("Cell tensegrity + motor-clutch + YAP on each matrix (open ring = cell not self-supporting)", color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig4_cell_mechanotransduction.png", dpi=160)
    plt.close(fig)


def fig_tissues(organ, cell, trans, heart, out):
    fig, axs = plt.subplots(2, 3, figsize=(13, 7))
    tissues = list(organ.tissue.unique())
    color = {t: C[i % len(C)] for i, t in enumerate(tissues)}
    for t in tissues:
        o = organ[organ.tissue == t].sort_values("age")
        axs[0, 0].plot(o.age, o.E_ratio, color=color[t], marker="o", ms=4, label=t)
        axs[0, 1].plot(o.age, o.toughness / o.toughness.iloc[0], color=color[t], marker="o", ms=4)
        axs[0, 2].plot(o.age, o.matrix_recovery_per_yr, color=color[t], marker="o", ms=4)
        ce = cell[(cell.source == "tissue") & (cell.tissue == t)].sort_values("age")
        axs[1, 0].plot(ce.age, ce.YAP_NC, color=color[t], marker="o", ms=4)
    axs[0, 0].set_ylabel("matrix modulus / age-20 value")
    axs[0, 0].legend(frameon=False, fontsize=7)
    axs[0, 1].set_ylabel("toughness / age-20 value")
    axs[0, 2].set_ylabel("matrix repair rate (1/yr)")
    axs[0, 2].set_yscale("log")
    axs[1, 0].set_ylabel("resident-cell YAP N/C")
    ax = axs[1, 1]
    old, young = trans.age.max(), trans.age.min()
    piv = trans.pivot_table(index="molecule", columns=["tissue", "age"], values="D_eff")
    mols = ["O2", "glucose", "IGF-1", "TGF-beta1", "VEGF165", "IgG", "exosome"]
    x = np.arange(len(mols))
    w = 0.8 / len(tissues)
    for k, t in enumerate(tissues):
        r = (piv[(t, old)] / piv[(t, young)]).reindex(mols)
        ax.bar(x + k * w, r, w * 0.9, color=color[t])
    ax.set_xticks(x + 0.4 - w / 2, mols, rotation=35, fontsize=7)
    ax.axhline(1, color=MUTED, lw=1)
    ax.set_ylabel(f"effective diffusivity, age {old:g} / age {young:g}")
    ax = axs[1, 2]
    ax.plot(heart.age, heart.EF * 100, color=C[0], marker="o", label="ejection fraction (%)")
    ax.plot(heart.age, heart.SV, color=C[1], marker="s", label="stroke volume (mL)")
    ax.plot(heart.age, heart.PWV_m_s * 10, color=C[2], marker="^", label="PWV × 10 (m/s)")
    ax.set_xlabel("age (yr)")
    ax.legend(frameon=False, fontsize=7)
    for a in axs[0]:
        a.set_xlabel("age (yr)")
    axs[1, 0].set_xlabel("age (yr)")
    fig.suptitle("Macro scale: age-accrued oxidative crosslinks across tissues", color=INK)
    fig.tight_layout()
    fig.savefig(out / "fig5_tissues_organs.png", dpi=160)
    plt.close(fig)


def md(df):
    """Markdown table without the optional tabulate dependency."""
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def summary(res, fail, cell, organ, heart, trans):
    L = ["# Results summary", "", f"Source: `{res}`. Model outputs, not measurements.", ""]
    g = fail.groupby(["collagen", "mode", "dose"]).agg(G=("G", "mean"), Cx=("Cx", "mean"), Cy=("Cy", "mean"),
                                                      strength=("strength", "mean"), toughness=("toughness", "mean"),
                                                      strain_at_peak=("strain_at_peak", "mean"), z=("z", "mean")).reset_index()
    g["Cx/Cy"] = g.Cx / g.Cy
    L += ["## Network mechanics at native branching", "", md(g.round(5)), ""]
    cc = cell[cell.source == "collagen"][["collagen", "mode", "dose", "E_lin_Pa", "YAP_NC", "prestress_ratio", "mc_F",
                                          "recovery_rate_per_h", "mc_traction_entropy_bits",
                                          "mc_entropy_prod_kB_per_s", "self_supporting", "bistable"]]
    L += ["## Cell (tensegrity + motor-clutch + YAP)", "", md(cc.round(3)), ""]
    L += ["## Tissues by age", "", md(organ.round(4)), ""]
    L += ["## Heart", "", md(heart.round(3)), ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/local")
    a = ap.parse_args()
    res = Path(a.results)
    out = res / "figures"
    out.mkdir(parents=True, exist_ok=True)
    net, fail = pd.read_csv(res / "network.csv"), pd.read_csv(res / "failure.csv")
    cell, organ = pd.read_csv(res / "cell.csv"), pd.read_csv(res / "organ.csv")
    trans, heart = pd.read_csv(res / "transport.csv"), pd.read_csv(res / "heart.csv")
    fig_branching(net, out)
    fig_stiffening(fail, out)
    fig_failure(fail, out)
    fig_cell(cell, out)
    fig_tissues(organ, cell, trans, heart, out)
    (res / "SUMMARY.md").write_text(summary(res, fail, cell, organ, heart, trans))
    print("figures ->", out)


if __name__ == "__main__":
    main()
