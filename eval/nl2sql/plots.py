"""Column-width bar charts for the benchmark results (called by run_benchmark.write_summary).

Writes PNGs next to the summary: bench_accuracy.png, bench_by_category.png,
bench_baseline.png, bench_latency.png. matplotlib is optional: if it is missing the
benchmark still completes and only the charts are skipped.
"""
from __future__ import annotations

import statistics
from pathlib import Path

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
LABEL = {"full": "Full engine", "no_repair": "No repair", "table_names_only": "Table names only",
         "direct_llm": "Direct LLM"}


def _style(plt):
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.5, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 7, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "savefig.dpi": 300,
    })


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


def _annotate(ax, bars, fmt="{:.0f}%"):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 1.2, fmt.format(h),
                ha="center", va="bottom", fontsize=5.5, color=INK2)


def make_plots(out: Path, records: list[dict]) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping charts")
        return []
    _style(plt)
    written = []
    engine = [c for c in ("full", "no_repair", "table_names_only") if any(r["config"] == c for r in records)]

    # 1. accuracy by configuration ------------------------------------------------------------
    if engine:
        metrics = [("exact", "Exact match"), ("f1", "Geometry F1"), ("executed", "Executed")]
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        w = 0.8 / len(metrics)
        for i, (key, name) in enumerate(metrics):
            vals = [100 * _mean([r[key] for r in records if r["config"] == c]) for c in engine]
            xs = [j + (i - (len(metrics) - 1) / 2) * w for j in range(len(engine))]
            bars = ax.bar(xs, vals, w * 0.92, color=SERIES[i], label=name)
            _annotate(ax, bars)
        ax.set_xticks(range(len(engine)), [LABEL[c] for c in engine])
        ax.set_ylim(0, 112)
        ax.set_ylabel("% of questions")
        ax.grid(axis="x", visible=False)
        ax.legend(fontsize=6, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13))
        fig.tight_layout(pad=0.4)
        fig.savefig(out / "bench_accuracy.png")
        plt.close(fig)
        written.append("bench_accuracy.png")

    # 2. exact match by question category -----------------------------------------------------
    cats = [c for c in ("filter", "proximity", "area", "ranking", "listing", "compositional")
            if any(r["category"] == c for r in records)]
    if engine and cats:
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        w = 0.8 / len(engine)
        for i, c in enumerate(engine):
            vals = [100 * _mean([r["exact"] for r in records if r["config"] == c and r["category"] == k])
                    for k in cats]
            xs = [j + (i - (len(engine) - 1) / 2) * w for j in range(len(cats))]
            ax.bar(xs, vals, w * 0.92, color=SERIES[i], label=LABEL[c])
        ax.set_xticks(range(len(cats)), [k.capitalize() for k in cats], rotation=20, ha="right")
        ax.set_ylim(0, 112)
        ax.set_ylabel("Exact match (% of questions)")
        ax.grid(axis="x", visible=False)
        ax.legend(fontsize=6, frameon=False, ncol=len(engine), loc="upper center", bbox_to_anchor=(0.5, 1.13))
        fig.tight_layout(pad=0.4)
        fig.savefig(out / "bench_by_category.png")
        plt.close(fig)
        written.append("bench_by_category.png")

    # 3. direct-LLM baseline: how grounded are its answers? -----------------------------------
    direct = [r for r in records if r["config"] == "direct_llm"]
    full = [r for r in records if r["config"] == "full"]
    if direct:
        labels = ["Names in\nthe DB", "Near a real\nfeature", "Near a gold\nfeature"]
        vals = [100 * _mean([r.get("name_grounded") for r in direct]),
                100 * _mean([r.get("coord_grounded") for r in direct]),
                100 * _mean([r.get("precision_gold") for r in direct])]
        colors = [SERIES[1]] * 3
        if full:
            labels.append("Engine\nF1 vs gold")
            vals.append(100 * _mean([r["f1"] for r in full]))
            colors.append(SERIES[0])
        fig, ax = plt.subplots(figsize=(3.4, 2.3))
        bars = ax.bar(range(len(vals)), vals, 0.62, color=colors)
        _annotate(ax, bars)
        ax.set_xticks(range(len(vals)), labels)
        ax.set_ylim(0, 112)
        ax.set_ylabel("%")
        ax.grid(axis="x", visible=False)
        fig.tight_layout(pad=0.4)
        fig.savefig(out / "bench_baseline.png")
        plt.close(fig)
        written.append("bench_baseline.png")

    # 4. latency ------------------------------------------------------------------------------
    cfgs = engine + (["direct_llm"] if direct else [])
    if cfgs:
        med, p95 = [], []
        for c in cfgs:
            xs = sorted(r["latency_s"] for r in records if r["config"] == c and r.get("latency_s") is not None)
            med.append(statistics.median(xs) if xs else 0)
            p95.append(xs[min(len(xs) - 1, int(0.95 * len(xs)))] if xs else 0)
        fig, ax = plt.subplots(figsize=(3.4, 2.1))
        w = 0.36
        b1 = ax.bar([i - w / 2 for i in range(len(cfgs))], med, w * 0.92, color=SERIES[0], label="Median")
        b2 = ax.bar([i + w / 2 for i in range(len(cfgs))], p95, w * 0.92, color=SERIES[3], label="95th percentile")
        for bars in (b1, b2):
            for b in bars:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.1, f"{b.get_height():.1f}",
                        ha="center", va="bottom", fontsize=5.5, color=INK2)
        ax.set_xticks(range(len(cfgs)), [LABEL[c] for c in cfgs])
        ax.set_ylabel("Seconds per question")
        ax.grid(axis="x", visible=False)
        ax.legend(fontsize=6, frameon=False, loc="upper left")
        fig.tight_layout(pad=0.4)
        fig.savefig(out / "bench_latency.png")
        plt.close(fig)
        written.append("bench_latency.png")
    return written
