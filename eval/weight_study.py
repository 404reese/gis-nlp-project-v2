"""Weight-sensitivity study for the paper's comparative-results section.

Two scoring models in the project use hand-picked weights:

  A. Site ranking  — app/main.py::rank_locations
       0.30*footfall + 0.25*youth + 0.20*access + 0.15*(10-rent) + 0.10*(10-competition)
  B. Women-safety  — frontend/src/components/SafetyMap.tsx::calculateWomenSafetyScore
       penalty weights 0.35/0.25/0.20/0.12/0.05/0.03 over six crime components

For each model this script compares the hand-picked weights against standard MCDM
weighting schemes (equal, rank-order centroid, AHP, entropy, CRITIC) and an alternative
aggregation method (TOPSIS), then measures how stable the resulting rankings are:

  * top-5 per scheme, top-5 overlap (Jaccard) and Kendall's tau / Spearman's rho vs baseline
  * one-at-a-time (OAT) sensitivity: each weight perturbed ±10/20/30 %, others renormalised
  * Monte Carlo: N random weight vectors (Dirichlet) -> how often each area stays top-5
  * safety model only: Spearman correlation of each score with raw crime counts and with the
    dataset's independent `safety_score` field (external validity check)

Run:   python eval/weight_study.py [--runs 1000] [--seed 42]
Out:   eval/results/weight_study/*.csv, *.png, summary.md
Deps:  numpy, pandas, scipy, matplotlib (all in the global env, not app/venv)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data" / "crime.json"
OUT = ROOT / "eval" / "results" / "weight_study"
TOP_K = 5

# ── Chart styling (paper figures: light surface, fixed categorical order) ─────────────
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "figure.dpi": 150,
})


# ═══════════════════════════════ weighting schemes ═══════════════════════════════════

def normalise(w) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    return w / w.sum()


def rank_order_centroid(n: int) -> np.ndarray:
    """ROC weights for criteria already listed in priority order (Barron & Barrett 1996)."""
    return np.array([sum(1 / j for j in range(i, n + 1)) / n for i in range(1, n + 1)])


# Saaty random index for n = 1..10
_RI = [0, 0, 0.58, 0.90, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49]


def ahp(matrix) -> tuple[np.ndarray, float]:
    """Principal-eigenvector AHP weights + consistency ratio (Saaty 1980). CR < 0.10 is OK."""
    m = np.asarray(matrix, dtype=float)
    vals, vecs = np.linalg.eig(m)
    i = np.argmax(vals.real)
    w = normalise(np.abs(vecs[:, i].real))
    n = len(m)
    ci = (vals[i].real - n) / (n - 1)
    return w, (ci / _RI[n - 1] if _RI[n - 1] else 0.0)


def entropy_weights(X: np.ndarray) -> np.ndarray:
    """Shannon-entropy weights: criteria that vary more across alternatives weigh more."""
    X = X - X.min(axis=0) + 1e-9          # shift to positive (benefit-oriented matrix)
    P = X / X.sum(axis=0)
    E = -(P * np.log(P)).sum(axis=0) / np.log(len(X))
    d = 1 - E
    return normalise(d) if d.sum() > 0 else np.full(X.shape[1], 1 / X.shape[1])


def critic_weights(X: np.ndarray) -> np.ndarray:
    """CRITIC (Diakoulaki 1995): contrast (std) x conflict (1 - correlation)."""
    rng = X.max(axis=0) - X.min(axis=0)
    Z = np.where(rng > 0, (X - X.min(axis=0)) / np.where(rng > 0, rng, 1), 0)
    std = Z.std(axis=0, ddof=1)
    with np.errstate(invalid="ignore"):
        R = np.nan_to_num(np.corrcoef(Z, rowvar=False))
    return normalise(std * (1 - R).sum(axis=0) + 1e-12)


def topsis(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """TOPSIS closeness (Hwang & Yoon 1981) on a benefit-oriented matrix. Higher = better."""
    V = X / np.where(np.linalg.norm(X, axis=0) > 0, np.linalg.norm(X, axis=0), 1) * w
    d_best = np.linalg.norm(V - V.max(axis=0), axis=1)
    d_worst = np.linalg.norm(V - V.min(axis=0), axis=1)
    return d_worst / np.where(d_best + d_worst > 0, d_best + d_worst, 1)


# ═══════════════════════════════ ranking statistics ══════════════════════════════════

def ranks_of(scores: np.ndarray) -> np.ndarray:
    """1 = best. Ties broken by original order (stable), matching Python's list.sort."""
    order = np.argsort(-scores, kind="stable")
    r = np.empty(len(scores), dtype=int)
    r[order] = np.arange(1, len(scores) + 1)
    return r


def topk(scores: np.ndarray, k: int = TOP_K) -> set[int]:
    return set(np.argsort(-scores, kind="stable")[:k])


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b)


def compare(scores: dict[str, np.ndarray], baseline: str) -> pd.DataFrame:
    base = scores[baseline]
    rows = []
    for name, s in scores.items():
        tau, p_tau = kendalltau(base, s)
        rho, _ = spearmanr(base, s)
        rows.append({
            "scheme": name,
            f"top{TOP_K}_overlap": len(topk(base) & topk(s)),
            f"top{TOP_K}_jaccard": round(jaccard(topk(base), topk(s)), 3),
            "kendall_tau": round(tau, 3),
            "kendall_p": float(f"{p_tau:.2g}"),
            "spearman_rho": round(rho, 3),
        })
    return pd.DataFrame(rows)


def oat_sensitivity(score_fn, w0: np.ndarray, names: list[str], steps=(-0.3, -0.2, -0.1, 0.1, 0.2, 0.3)):
    """Perturb one weight by ±x %, renormalise the rest, report rank agreement with baseline."""
    base = score_fn(w0)
    rows = []
    for j, crit in enumerate(names):
        for s in steps:
            w = w0.copy()
            w[j] *= 1 + s
            w = normalise(w)
            sc = score_fn(w)
            rows.append({
                "criterion": crit, "change_pct": int(s * 100),
                "kendall_tau": round(kendalltau(base, sc)[0], 3),
                f"top{TOP_K}_overlap": len(topk(base) & topk(sc)),
            })
    return pd.DataFrame(rows)


def monte_carlo(score_fn, n_crit: int, labels: list[str], runs: int, rng, base_scores):
    """Random weights ~ Dirichlet(1) (uniform on the simplex)."""
    W = rng.dirichlet(np.ones(n_crit), size=runs)
    in_top = np.zeros(len(labels))
    rank_samples = np.zeros((runs, len(labels)), dtype=int)
    taus = np.zeros(runs)
    for i, w in enumerate(W):
        sc = score_fn(w)
        for idx in topk(sc):
            in_top[idx] += 1
        rank_samples[i] = ranks_of(sc)
        taus[i] = kendalltau(base_scores, sc)[0]
    freq = pd.DataFrame({
        "area": labels,
        "baseline_rank": ranks_of(base_scores),
        f"pct_in_top{TOP_K}": np.round(100 * in_top / runs, 1),
        "median_rank": np.median(rank_samples, axis=0).astype(int),
        "rank_p5": np.percentile(rank_samples, 5, axis=0).astype(int),
        "rank_p95": np.percentile(rank_samples, 95, axis=0).astype(int),
    }).sort_values([f"pct_in_top{TOP_K}", "baseline_rank"], ascending=[False, True])
    return freq, rank_samples, taus


# ═══════════════════════════════ plotting helpers ════════════════════════════════════

def plot_weights(wdf: pd.DataFrame, title: str, path: Path):
    schemes, crits = list(wdf.index), list(wdf.columns)
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = np.arange(len(crits))
    bw = 0.8 / len(schemes)
    for i, s in enumerate(schemes):
        ax.bar(x + (i - (len(schemes) - 1) / 2) * bw, wdf.loc[s], bw * 0.9,
               color=SERIES[i % len(SERIES)], label=s, edgecolor=SURFACE, linewidth=1)
    ax.set_xticks(x, crits)
    ax.set_ylabel("Weight")
    ax.set_title(title, loc="left")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, ncol=min(len(schemes), 4), fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_tau_heatmap(scores: dict[str, np.ndarray], title: str, path: Path):
    names = list(scores)
    M = np.array([[kendalltau(scores[a], scores[b])[0] for b in names] for a in names])
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    fig, ax = plt.subplots(figsize=(0.62 * len(names) + 2, 0.55 * len(names) + 1.4))
    im = ax.imshow(M, cmap=cmap, vmin=min(0, M.min()), vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=40, ha="right")
    ax.set_yticks(range(len(names)), names)
    ax.grid(False)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="#ffffff" if M[i, j] > 0.6 else INK)
    ax.set_title(title, loc="left")
    fig.colorbar(im, ax=ax, fraction=0.04, label="Kendall's τ")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_oat(oat: pd.DataFrame, title: str, path: Path):
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for i, (crit, g) in enumerate(oat.groupby("criterion", sort=False)):
        ax.plot(g["change_pct"], g["kendall_tau"], marker="o", ms=4.5, lw=2,
                color=SERIES[i % len(SERIES)], label=crit)
    ax.axvline(0, color="#c3c2b7", lw=1)
    ax.set_xlabel("Change in one criterion's weight (%)")
    ax.set_ylabel("Kendall's τ vs baseline")
    ax.set_title(title, loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_stability(freq: pd.DataFrame, runs: int, title: str, path: Path, n: int = 15):
    top = freq.head(n).iloc[::-1]
    col = f"pct_in_top{TOP_K}"
    fig, ax = plt.subplots(figsize=(6.4, 0.28 * n + 1.2))
    colors = [SERIES[0] if r <= TOP_K else "#86b6ef" for r in top["baseline_rank"]]
    ax.barh(top["area"], top[col], color=colors, height=0.7, edgecolor=SURFACE, linewidth=1)
    for y, v in enumerate(top[col]):
        ax.text(v + 1, y, f"{v:.0f}%", va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(0, 110)
    ax.set_xlabel(f"% of {runs} random weight sets where the area is in the top {TOP_K}")
    ax.set_title(title, loc="left")
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=SERIES[0], label=f"Top {TOP_K} under baseline weights"),
                       Patch(color="#86b6ef", label="Not top 5 under baseline")],
              frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_tau_hist(taus: np.ndarray, title: str, path: Path):
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    ax.hist(taus, bins=30, color=SERIES[0], edgecolor=SURFACE, linewidth=1)
    ax.axvline(np.median(taus), color=INK, lw=1.2, ls="--")
    ax.text(np.median(taus), ax.get_ylim()[1] * 0.92, f"  median τ = {np.median(taus):.2f}",
            fontsize=8, color=INK)
    ax.set_xlabel("Kendall's τ vs baseline ranking")
    ax.set_ylabel("Weight sets")
    ax.set_title(title, loc="left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ═══════════════════════════════ A. site ranking ═════════════════════════════════════

SITE_CRITERIA = ["footfall", "youth", "access", "rent", "competition"]
SITE_COST = {"rent", "competition"}       # lower raw value is better
SITE_BASELINE = np.array([0.30, 0.25, 0.20, 0.15, 0.10])

# AHP pairwise judgments (Saaty 1-9 scale), rows/cols in SITE_CRITERIA order.
# These encode the same priority order as the hand-picked weights — edit them to reflect
# your own (or surveyed experts') judgments; the consistency ratio is reported.
SITE_AHP = [
    [1,   2,   2,   3,   4],
    [1/2, 1,   1,   2,   3],
    [1/2, 1,   1,   2,   2],
    [1/3, 1/2, 1/2, 1,   2],
    [1/4, 1/3, 1/2, 1/2, 1],
]

# Business-scenario weights (what a user persona would care about).
SITE_SCENARIOS = {
    "Budget":  [0.15, 0.15, 0.20, 0.35, 0.15],
    "Student": [0.20, 0.40, 0.20, 0.15, 0.05],
    "Premium": [0.40, 0.15, 0.25, 0.00, 0.20],
}


def site_study(locs: list[dict], runs: int, rng) -> dict:
    names = [l["name"] for l in locs]
    raw = np.array([[float(l.get(c, 0)) for c in SITE_CRITERIA] for l in locs])
    # Benefit-oriented matrix exactly as rank_locations uses it: cost criteria -> (10 - x).
    X = raw.copy()
    for j, c in enumerate(SITE_CRITERIA):
        if c in SITE_COST:
            X[:, j] = 10 - X[:, j]

    wsm = lambda w: X @ w  # noqa: E731 — the production formula (weighted sum)

    w_ahp, cr = ahp(SITE_AHP)
    weights = {
        "Baseline (hand-picked)": SITE_BASELINE,
        "Equal": np.full(5, 0.2),
        "ROC": rank_order_centroid(5),
        "AHP": w_ahp,
        "Entropy": entropy_weights(X),
        "CRITIC": critic_weights(X),
        **{f"Scenario: {k}": normalise(v) for k, v in SITE_SCENARIOS.items()},
    }
    wdf = pd.DataFrame(weights, index=SITE_CRITERIA).T.round(3)

    scores = {k: wsm(w) for k, w in weights.items()}
    scores["TOPSIS (baseline w)"] = topsis(X, SITE_BASELINE)
    base = scores["Baseline (hand-picked)"]

    top_table = pd.DataFrame({
        k: [f"{names[i]} ({s[i]:.2f})" for i in np.argsort(-s, kind="stable")[:TOP_K]]
        for k, s in scores.items()
    }, index=[f"#{i}" for i in range(1, TOP_K + 1)])
    rank_table = pd.DataFrame({k: ranks_of(s) for k, s in scores.items()}, index=names)
    rank_table = rank_table.sort_values("Baseline (hand-picked)")

    cmp = compare(scores, "Baseline (hand-picked)")
    oat = oat_sensitivity(wsm, SITE_BASELINE, SITE_CRITERIA)
    freq, _, taus = monte_carlo(wsm, 5, names, runs, rng, base)

    wdf.to_csv(OUT / "A1_site_weights.csv")
    top_table.to_csv(OUT / "A2_site_top5_by_scheme.csv")
    rank_table.to_csv(OUT / "A3_site_full_ranks.csv")
    cmp.to_csv(OUT / "A4_site_rank_agreement.csv", index=False)
    oat.to_csv(OUT / "A5_site_oat_sensitivity.csv", index=False)
    freq.to_csv(OUT / "A6_site_montecarlo_stability.csv", index=False)

    plot_weights(wdf.loc[["Baseline (hand-picked)", "Equal", "AHP", "Entropy", "CRITIC"]],
                 "Site ranking — weights per scheme", OUT / "A1_site_weights.png")
    plot_tau_heatmap(scores, "Site ranking — rank agreement between schemes",
                     OUT / "A4_site_tau_heatmap.png")
    plot_oat(oat, "Site ranking — one-at-a-time weight sensitivity", OUT / "A5_site_oat.png")
    plot_stability(freq, runs, f"Site ranking — top-{TOP_K} stability (Monte Carlo)",
                   OUT / "A6_site_stability.png")
    plot_tau_hist(taus, "Site ranking — agreement under random weights",
                  OUT / "A7_site_tau_distribution.png")

    return {"weights": wdf, "top": top_table, "cmp": cmp, "oat": oat, "freq": freq,
            "taus": taus, "ahp_cr": cr}


# ═══════════════════════════════ B. women-safety score ═══════════════════════════════

SAFETY_COMPONENTS = ["violent", "harassment", "kidnapping", "cyber", "ndps", "brothel"]
SAFETY_BASELINE = np.array([0.35, 0.25, 0.20, 0.12, 0.05, 0.03])


def safety_components(loc: dict) -> np.ndarray:
    """Mirror of calculateWomenSafetyScore's component estimates (SafetyMap.tsx)."""
    c = loc.get("crime_data", {}) or {}
    g = lambda k: float(c.get(k, 0) or 0)  # noqa: E731
    return np.array([
        g("ndps_cases") * 0.05 + g("eow_cases") * 0.02,          # violent proxy
        g("cheating_fraud") * 0.3,                                # harassment proxy
        0.0,                                                      # kidnapping (no data)
        g("sextortion") * 2 + g("cyber_crime_cases") * 0.1,       # cyber vs women
        g("ndps_cases"),
        g("brothel_cases"),
    ])


def area_modifier(loc: dict) -> float:
    m = 0.0
    if str(loc.get("area_type", "")).lower() == "commercial":
        m -= 5
    if float(loc.get("footfall", 0)) >= 8:
        m -= 3
    if float(loc.get("youth", 0)) >= 8:
        m -= 2
    if float(loc.get("access", 0)) <= 6:
        m -= 4
    if float(loc.get("traffic", 0)) >= 8:
        m += 2
    return m


CASE_KEYS = ["eow_cases", "ndps_cases", "cyber_crime_cases", "cheating_fraud",
             "credit_card_fraud", "crypto_fraud", "loan_fraud", "sextortion", "brothel_cases"]


def safety_study(locs: list[dict], runs: int, rng) -> dict:
    names = [l["name"] for l in locs]
    C = np.array([safety_components(l) for l in locs])     # penalties: higher = worse
    mod = np.array([area_modifier(l) for l in locs])

    def score(w):  # identical to the TSX formula, clamped 0..100; higher = safer
        return np.clip(100 - C @ w + mod, 0, 100)

    def score_unclamped(w):  # for ranking stats — clamping creates artificial ties
        return 100 - C @ w + mod

    weights = {
        "Baseline (hand-picked)": SAFETY_BASELINE,
        "Equal": np.full(6, 1 / 6),
        "ROC": rank_order_centroid(6),
        "Entropy": entropy_weights(C),
        "CRITIC": critic_weights(C),
    }
    wdf = pd.DataFrame(weights, index=SAFETY_COMPONENTS).T.round(3) + 0.0  # no "-0"
    scores = {k: score_unclamped(w) for k, w in weights.items()}

    # External validity: does the score move against actual crime?
    total_cases = np.array([sum(float((l.get("crime_data") or {}).get(k, 0) or 0)
                                for k in CASE_KEYS) for l in locs])
    ref_safety = np.array([float((l.get("crime_data") or {}).get("safety_score", np.nan))
                           for l in locs])
    ok = ~np.isnan(ref_safety)
    validity = []
    for k, s in scores.items():
        r_cases, p_cases = spearmanr(s, total_cases)
        r_ref, p_ref = spearmanr(s[ok], ref_safety[ok])
        validity.append({
            "scheme": k,
            "spearman_vs_total_cases": round(r_cases, 3), "p_cases": float(f"{p_cases:.2g}"),
            "spearman_vs_dataset_safety_score": round(r_ref, 3), "p_ref": float(f"{p_ref:.2g}"),
            "n_clamped_to_0": int((score(weights[k]) <= 0).sum()),
        })
    validity = pd.DataFrame(validity)

    base = scores["Baseline (hand-picked)"]
    cmp = compare(scores, "Baseline (hand-picked)").merge(validity, on="scheme")
    # Kidnapping has no data (always 0) so its weight is dead mass — excluded from OAT/MC.
    live = [i for i, c in enumerate(SAFETY_COMPONENTS) if c != "kidnapping"]
    live_names = [SAFETY_COMPONENTS[i] for i in live]

    def score_live(w_live):
        w = np.zeros(6)
        w[live] = w_live
        return score_unclamped(w)

    oat = oat_sensitivity(score_live, normalise(SAFETY_BASELINE[live]), live_names)
    freq, _, taus = monte_carlo(score_live, len(live), names, runs, rng,
                                score_live(normalise(SAFETY_BASELINE[live])))
    freq = freq.rename(columns={f"pct_in_top{TOP_K}": f"pct_in_safest{TOP_K}"})

    per_area = pd.DataFrame({"area": names, "zone": [l.get("zone") for l in locs],
                             "total_cases": total_cases, "dataset_safety_score": ref_safety,
                             **{k: np.round(score(w), 1) for k, w in weights.items()}})
    per_area = per_area.sort_values("Baseline (hand-picked)", ascending=False)

    wdf.to_csv(OUT / "B1_safety_weights.csv")
    per_area.to_csv(OUT / "B2_safety_scores_by_area.csv", index=False)
    cmp.to_csv(OUT / "B3_safety_agreement_and_validity.csv", index=False)
    oat.to_csv(OUT / "B4_safety_oat_sensitivity.csv", index=False)
    freq.to_csv(OUT / "B5_safety_montecarlo_stability.csv", index=False)

    plot_weights(wdf, "Women-safety score — weights per scheme", OUT / "B1_safety_weights.png")
    plot_tau_heatmap(scores, "Women-safety score — rank agreement between schemes",
                     OUT / "B3_safety_tau_heatmap.png")
    plot_oat(oat, "Women-safety score — one-at-a-time weight sensitivity",
             OUT / "B4_safety_oat.png")
    plot_stability(freq.rename(columns={f"pct_in_safest{TOP_K}": f"pct_in_top{TOP_K}"}), runs,
                   f"Women-safety score — safest-{TOP_K} stability (Monte Carlo)",
                   OUT / "B5_safety_stability.png")

    # Validity scatter: baseline score vs total cases
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.scatter(total_cases, score(SAFETY_BASELINE), s=36, color=SERIES[0],
               edgecolor=SURFACE, linewidth=1.5, zorder=3)
    r = validity.loc[validity.scheme == "Baseline (hand-picked)", "spearman_vs_total_cases"].iloc[0]
    ax.set_xlabel("Total reported cases (all categories)")
    ax.set_ylabel("Women-safety score (baseline)")
    ax.set_title(f"Score vs recorded crime (Spearman ρ = {r:.2f})", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "B6_safety_vs_cases.png")
    plt.close(fig)

    return {"weights": wdf, "cmp": cmp, "oat": oat, "freq": freq, "taus": taus}


# ═══════════════════════════════ summary ════════════════════════════════════════════

def md(df: pd.DataFrame, index=False) -> str:
    return df.to_markdown(index=index)


def write_summary(a: dict, b: dict, runs: int, seed: int, n: int):
    ta, tb = a["taus"], b["taus"]
    oat_a = a["oat"].groupby("criterion", sort=False)["kendall_tau"].min().sort_values()
    oat_b = b["oat"].groupby("criterion", sort=False)["kendall_tau"].min().sort_values()
    s = f"""# Weight-sensitivity study

Generated by `eval/weight_study.py` (runs={runs}, seed={seed}, n_areas={n}, top-k={TOP_K}).
Every number below is computed from `app/data/crime.json`; re-run the script to regenerate.

## A. Site ranking (`rank_locations`)

### A1. Weights per scheme
AHP consistency ratio = **{a['ahp_cr']:.3f}** ({'acceptable, < 0.10' if a['ahp_cr'] < 0.10 else 'INCONSISTENT, revise SITE_AHP'}).

{md(a['weights'], index=True)}

### A2. Top-{TOP_K} areas per scheme
{md(a['top'], index=True)}

### A3. Agreement with the hand-picked baseline
{md(a['cmp'])}

### A4. One-at-a-time sensitivity: worst-case τ for ±30 % on a single weight
{md(oat_a.rename('min_kendall_tau').to_frame(), index=True)}

### A5. Monte Carlo ({runs} random weight sets, Dirichlet(1))
Kendall's τ vs baseline: median **{np.median(ta):.3f}**, 5th pct {np.percentile(ta, 5):.3f},
95th pct {np.percentile(ta, 95):.3f}.

{md(a['freq'].head(10))}

## B. Women-safety score (`calculateWomenSafetyScore`)

Note: the "kidnapping" component is always 0 (no data), so its 0.20 weight never affects the
score — it is excluded from the OAT and Monte Carlo analyses.

### B1. Weights per scheme
{md(b['weights'], index=True)}

### B2. Agreement with baseline + external validity
`spearman_vs_total_cases` should be **negative** (safer = fewer cases).
`spearman_vs_dataset_safety_score` should be **positive**; that field is independent of the formula.

{md(b['cmp'])}

### B3. One-at-a-time sensitivity: worst-case τ for ±30 % on a single weight
{md(oat_b.rename('min_kendall_tau').to_frame(), index=True)}

### B4. Monte Carlo ({runs} random weight sets)
Kendall's τ vs baseline: median **{np.median(tb):.3f}**, 5th pct {np.percentile(tb, 5):.3f},
95th pct {np.percentile(tb, 95):.3f}.

{md(b['freq'].head(10))}

## Figures
| File | Suggested caption |
|---|---|
| A1_site_weights.png | Weights assigned to each criterion under subjective and objective schemes |
| A4_site_tau_heatmap.png | Pairwise Kendall's τ between rankings produced by each scheme |
| A5_site_oat.png | Ranking stability when one weight is varied ±30 % |
| A6_site_stability.png | Share of {runs} random weight sets in which each area remains top-{TOP_K} |
| A7_site_tau_distribution.png | Distribution of rank agreement under random weights |
| B1_safety_weights.png | Safety-score weights per scheme |
| B3_safety_tau_heatmap.png | Rank agreement between safety-weighting schemes |
| B4_safety_oat.png | Safety ranking stability under single-weight perturbation |
| B5_safety_stability.png | Share of random weight sets in which each area remains safest-{TOP_K} |
| B6_safety_vs_cases.png | Baseline safety score against total recorded cases |

## Methods references
- AHP: Saaty, T. L. (1980). *The Analytic Hierarchy Process*. McGraw-Hill.
- Entropy weights: Shannon (1948); applied to MCDM in Zeleny (1982).
- CRITIC: Diakoulaki, Mavrotas & Papayannakis (1995), *Computers & OR* 22(7).
- ROC weights: Barron & Barrett (1996), *Management Science* 42(11).
- TOPSIS: Hwang & Yoon (1981), *Multiple Attribute Decision Making*. Springer.
- Monte Carlo weight sensitivity for GIS-MCDA: Chen, Yu & Khan (2010), *Env. Modelling & Software* 25(12).
"""
    (OUT / "summary.md").write_text(s, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=1000, help="Monte Carlo weight samples")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    locs = payload["locations"] if isinstance(payload, dict) else payload
    rng = np.random.default_rng(args.seed)

    a = site_study(locs, args.runs, rng)
    b = safety_study(locs, args.runs, rng)
    write_summary(a, b, args.runs, args.seed, len(locs))
    print(f"Wrote results for {len(locs)} areas to {OUT.relative_to(ROOT)}")
    print(f"  Site   MC median tau={np.median(a['taus']):.3f}   AHP CR={a['ahp_cr']:.3f}")
    print(f"  Safety MC median tau={np.median(b['taus']):.3f}")


if __name__ == "__main__":
    main()
