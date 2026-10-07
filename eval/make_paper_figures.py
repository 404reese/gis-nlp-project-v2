"""Paper figures sized for one column of the IEEE template (3.4 in wide).

Reads the CSVs already written by eval/weight_study.py and the (optional) benchmark results,
and writes PNGs to paper-publication/figures/:

  weight_tau_bar.png         Kendall's tau vs the hand-picked baseline, per weighting scheme
  weight_oat_sensitivity.png one-at-a-time sensitivity: each weight changed by up to +/-30 %

Run:  python eval/make_paper_figures.py
Deps: matplotlib, pandas (global env, like weight_study.py)
"""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "eval" / "results" / "weight_study"
OUT = ROOT / "paper-publication" / "figures"

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, BLUE_LIGHT, ORANGE = "#2a78d6", "#9ec5f4", "#eb6834"

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "figure.dpi": 150, "savefig.dpi": 300,
})


def tau_bar():
    d = pd.read_csv(WS / "A4_site_rank_agreement.csv")
    d = d[~d["scheme"].str.startswith("Baseline")].sort_values("kendall_tau")
    labels = [s.replace(" (baseline w)", "").replace("Scenario: ", "Scenario ") for s in d["scheme"]]
    colors = [BLUE if o == 5 else (BLUE_LIGHT if o >= 1 else ORANGE) for o in d["top5_overlap"]]
    colors = [ORANGE if t < 0.1 else c for t, c in zip(d["kendall_tau"], colors)]

    fig, ax = plt.subplots(figsize=(3.4, 2.55))
    bars = ax.barh(labels, d["kendall_tau"], color=colors, height=0.66)
    for b, tau, ov in zip(bars, d["kendall_tau"], d["top5_overlap"]):
        ax.text(max(tau, 0) + 0.02, b.get_y() + b.get_height() / 2, f"{tau:.2f}  ({int(ov)}/5)",
                va="center", ha="left", fontsize=6, color=INK2)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlim(-0.2, 1.3)
    ax.set_xlabel("Kendall's $\\tau$ vs hand-picked weights (top-5 overlap)")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (BLUE, BLUE_LIGHT, ORANGE)]
    ax.legend(handles, ["Same top 5", "Top 5 partly differs", "No rank agreement"],
              loc="lower right", fontsize=6, frameon=False)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "weight_tau_bar.png")
    plt.close(fig)


def oat_sensitivity():
    d = pd.read_csv(WS / "A5_site_oat_sensitivity.csv")
    colors = {"footfall": "#2a78d6", "youth": "#eb6834", "access": "#1baf7a",
              "rent": "#eda100", "competition": "#e87ba4"}
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    for crit, g in d.groupby("criterion", sort=False):
        g = g.sort_values("change_pct")
        ax.plot(g["change_pct"], g["kendall_tau"], marker="o", ms=3, lw=1.3,
                color=colors.get(crit, INK2), label=crit)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xticks([-30, -20, -10, 0, 10, 20, 30])
    ax.set_xlabel("Change in one criterion's weight (%)")
    ax.set_ylabel("Kendall's $\\tau$ vs hand-picked weights")
    ax.legend(fontsize=6, frameon=False, ncol=2, loc="lower center")
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "weight_oat_sensitivity.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tau_bar()
    oat_sensitivity()
    print("wrote", *sorted(p.name for p in OUT.glob("*.png")))
