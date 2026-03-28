"""
Generate publication-quality roofline plots from parsed ncu JSON data.

Plots each kernel as a dot on the arithmetic intensity vs achieved performance
plane, with the H100 roofline ceiling overlaid.
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.roofline.roofline_config import H100_SXM

# ── Style ─────────────────────────────────────────────────────────────

# Colorblind-safe palette for kernel categories
CATEGORY_COLORS = {
    "attention":     "#E69F00",  # orange
    "gemm":          "#0072B2",  # blue
    "layernorm":     "#009E73",  # green
    "softmax":       "#CC79A7",  # pink
    "activation":    "#56B4E9",  # sky blue
    "rope":          "#D55E00",  # vermilion
    "moe-routing":   "#F0E442",  # yellow
    "moe-dispatch":  "#999999",  # gray
    "communication": "#882255",  # wine
    "sampling":      "#44AA99",  # teal
    "memory":        "#BBBBBB",  # light gray
    "other":         "#666666",  # dark gray
}

BATCH_MARKERS = {
    1:  "o",   # circle
    4:  "s",   # square
    8:  "^",   # triangle up
    16: "D",   # diamond
    32: "p",   # pentagon
    64: "*",   # star
}


def setup_style():
    """Configure matplotlib for publication quality."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
    })


def draw_roofline_ceiling(ax, gpu=H100_SXM, ai_range=(0.1, 10000)):
    """Draw the roofline ceiling on the given axes."""
    ridge = gpu.ridge_point_bf16
    peak = gpu.peak_bf16_tflops
    bw = gpu.hbm_bandwidth_tb_s

    ai = np.logspace(np.log10(ai_range[0]), np.log10(ai_range[1]), 500)

    # Memory-bound slope: perf = bandwidth * AI (in TFLOPS)
    mem_bound = bw * ai  # TB/s * FLOP/byte = TFLOP/s

    # Clip to compute ceiling
    roofline = np.minimum(mem_bound, peak)

    ax.plot(ai, roofline, "k-", linewidth=2, zorder=5)

    # Annotate ridge point
    ax.axvline(ridge, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.annotate(
        f"Ridge: {ridge:.0f} FLOP/B",
        xy=(ridge, peak),
        xytext=(ridge * 2, peak * 0.6),
        fontsize=7,
        arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
        color="gray",
    )

    # Label ceilings
    ax.text(
        ai_range[1] * 0.5, peak * 1.08,
        f"{gpu.name}: {peak:.0f} TFLOPS BF16",
        fontsize=7, ha="right", color="black", style="italic",
    )
    ax.text(
        ai_range[0] * 1.5, bw * ai_range[0] * 1.5 * 1.3,
        f"{bw} TB/s HBM3",
        fontsize=7, rotation=45, color="black", style="italic",
    )


def plot_single(data: dict, output_path: Path, gpu=H100_SXM):
    """Plot roofline for a single (model, phase, batch_size) combination."""
    setup_style()
    fig, ax = plt.subplots(figsize=(7, 5))

    draw_roofline_ceiling(ax)

    kernels = data["kernels"]
    for k in kernels:
        ai = k["arithmetic_intensity"]
        perf = k["achieved_tflops"]
        cat = k["category"]

        if ai <= 0 or perf <= 0:
            continue

        color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["other"])
        ax.scatter(ai, perf, c=color, s=40, alpha=0.7, edgecolors="black",
                   linewidths=0.3, zorder=10, label=cat)

    # Deduplicate legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="lower right",
              framealpha=0.9, ncol=2)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Arithmetic Intensity (FLOP/Byte)")
    ax.set_ylabel("Achieved Performance (TFLOPS)")
    ax.set_title(f"{data['model']} — {data['phase']} (BS={data['batch_size']})")
    ax.set_xlim(0.1, 10000)
    ax.set_ylim(0.01, 2000)

    for fmt in ("pdf", "png"):
        fig.savefig(f"{output_path}.{fmt}")
    plt.close(fig)
    print(f"  Saved: {output_path.name}.{{pdf,png}}")


def plot_multi_batch(datasets: list[dict], output_path: Path, gpu=H100_SXM):
    """Overlay multiple batch sizes for the same model+phase on one roofline."""
    if not datasets:
        return

    setup_style()
    fig, ax = plt.subplots(figsize=(7, 5))
    draw_roofline_ceiling(ax)

    model = datasets[0]["model"]
    phase = datasets[0]["phase"]

    for data in sorted(datasets, key=lambda d: d["batch_size"]):
        bs = data["batch_size"]
        marker = BATCH_MARKERS.get(bs, "o")

        for k in data["kernels"]:
            ai = k["arithmetic_intensity"]
            perf = k["achieved_tflops"]
            cat = k["category"]

            if ai <= 0 or perf <= 0:
                continue

            color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["other"])
            ax.scatter(ai, perf, c=color, s=50, alpha=0.6, marker=marker,
                       edgecolors="black", linewidths=0.3, zorder=10)

    # Build legend: categories (colors) + batch sizes (markers)
    from matplotlib.lines import Line2D

    cat_handles = []
    seen_cats = set()
    for data in datasets:
        for k in data["kernels"]:
            if k["category"] not in seen_cats and k["arithmetic_intensity"] > 0:
                seen_cats.add(k["category"])
                color = CATEGORY_COLORS.get(k["category"], CATEGORY_COLORS["other"])
                cat_handles.append(Line2D([0], [0], marker="o", color="w",
                                          markerfacecolor=color, markersize=8,
                                          label=k["category"]))

    bs_handles = []
    for data in sorted(datasets, key=lambda d: d["batch_size"]):
        bs = data["batch_size"]
        marker = BATCH_MARKERS.get(bs, "o")
        bs_handles.append(Line2D([0], [0], marker=marker, color="w",
                                  markerfacecolor="gray", markersize=8,
                                  label=f"BS={bs}"))

    all_handles = cat_handles + bs_handles
    ax.legend(handles=all_handles, loc="lower right", framealpha=0.9, ncol=2, fontsize=7)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Arithmetic Intensity (FLOP/Byte)")
    ax.set_ylabel("Achieved Performance (TFLOPS)")
    ax.set_title(f"{model} — {phase} (batch size sweep)")
    ax.set_xlim(0.1, 10000)
    ax.set_ylim(0.01, 2000)

    for fmt in ("pdf", "png"):
        fig.savefig(f"{output_path}.{fmt}")
    plt.close(fig)
    print(f"  Saved: {output_path.name}.{{pdf,png}}")


def plot_prefill_vs_decode(prefill_data: list[dict], decode_data: list[dict],
                           output_path: Path, gpu=H100_SXM):
    """Side-by-side prefill vs decode comparison."""
    if not prefill_data or not decode_data:
        return

    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    model = prefill_data[0]["model"]

    for ax, datasets, title in [(ax1, prefill_data, "Prefill"), (ax2, decode_data, "Decode")]:
        draw_roofline_ceiling(ax)

        for data in sorted(datasets, key=lambda d: d["batch_size"]):
            bs = data["batch_size"]
            marker = BATCH_MARKERS.get(bs, "o")

            for k in data["kernels"]:
                ai = k["arithmetic_intensity"]
                perf = k["achieved_tflops"]
                if ai <= 0 or perf <= 0:
                    continue

                color = CATEGORY_COLORS.get(k["category"], CATEGORY_COLORS["other"])
                ax.scatter(ai, perf, c=color, s=50, alpha=0.6, marker=marker,
                           edgecolors="black", linewidths=0.3, zorder=10)

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Arithmetic Intensity (FLOP/Byte)")
        ax.set_title(f"{title}")
        ax.set_xlim(0.1, 10000)
        ax.set_ylim(0.01, 2000)

    ax1.set_ylabel("Achieved Performance (TFLOPS)")
    fig.suptitle(f"{model} — Prefill vs Decode", fontsize=14, y=1.02)
    fig.tight_layout()

    for fmt in ("pdf", "png"):
        fig.savefig(f"{output_path}.{fmt}")
    plt.close(fig)
    print(f"  Saved: {output_path.name}.{{pdf,png}}")


def plot_category_breakdown(datasets: list[dict], output_path: Path):
    """Stacked bar chart showing time breakdown by kernel category across batch sizes."""
    if not datasets:
        return

    setup_style()
    fig, ax = plt.subplots(figsize=(8, 4))

    model = datasets[0]["model"]
    phase = datasets[0]["phase"]
    batch_sizes = sorted(set(d["batch_size"] for d in datasets))

    # Collect all categories
    all_cats = set()
    for d in datasets:
        all_cats.update(d["category_summary"].keys())
    all_cats = sorted(all_cats)

    # Build stacked bars
    bottom = np.zeros(len(batch_sizes))
    for cat in all_cats:
        pcts = []
        for bs in batch_sizes:
            data = next((d for d in datasets if d["batch_size"] == bs), None)
            if data and cat in data["category_summary"]:
                pcts.append(data["category_summary"][cat]["duration_pct"])
            else:
                pcts.append(0)

        color = CATEGORY_COLORS.get(cat, CATEGORY_COLORS["other"])
        ax.bar([str(bs) for bs in batch_sizes], pcts, bottom=bottom,
               label=cat, color=color, edgecolor="white", linewidth=0.5)
        bottom += np.array(pcts)

    ax.set_xlabel("Batch Size")
    ax.set_ylabel("Time (%)")
    ax.set_title(f"{model} — {phase} Kernel Time Breakdown")
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
    ax.set_ylim(0, 100)
    fig.tight_layout()

    for fmt in ("pdf", "png"):
        fig.savefig(f"{output_path}.{fmt}")
    plt.close(fig)
    print(f"  Saved: {output_path.name}.{{pdf,png}}")


def main():
    parser = argparse.ArgumentParser(description="Generate roofline plots")
    parser.add_argument("--input", type=str, required=True,
                        help="Input JSON file or glob pattern")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: results/roofline/figures/)")
    parser.add_argument("--style", type=str, default="all",
                        choices=["single", "multi-batch", "prefill-vs-decode", "breakdown", "all"],
                        help="Plot style")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = Path(args.output_dir) if args.output_dir else project_root / "results" / "roofline" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    input_path = Path(args.input)
    if "*" in args.input:
        files = sorted(input_path.parent.glob(input_path.name))
    else:
        files = [input_path]

    all_data = []
    for f in files:
        if not f.exists():
            continue
        all_data.append(json.loads(f.read_text()))

    if not all_data:
        print("No data files found.")
        return

    print(f"Loaded {len(all_data)} dataset(s)")

    # Group by model and phase
    groups: dict[str, dict[str, list]] = {}
    for d in all_data:
        model = d["model"]
        phase = d["phase"]
        groups.setdefault(model, {}).setdefault(phase, []).append(d)

    for model, phases in groups.items():
        print(f"\n═══ {model} ═══")

        # Single plots
        if args.style in ("single", "all"):
            for phase, datasets in phases.items():
                for d in datasets:
                    out = output_dir / f"{model}_{phase}_bs{d['batch_size']}_roofline"
                    plot_single(d, out)

        # Multi-batch overlay
        if args.style in ("multi-batch", "all"):
            for phase, datasets in phases.items():
                if len(datasets) > 1:
                    out = output_dir / f"{model}_{phase}_multi_batch_roofline"
                    plot_multi_batch(datasets, out)

        # Prefill vs decode
        if args.style in ("prefill-vs-decode", "all"):
            prefill = phases.get("prefill", [])
            decode = phases.get("decode", [])
            if prefill and decode:
                out = output_dir / f"{model}_prefill_vs_decode_roofline"
                plot_prefill_vs_decode(prefill, decode, out)

        # Category breakdown
        if args.style in ("breakdown", "all"):
            for phase, datasets in phases.items():
                if len(datasets) > 1:
                    out = output_dir / f"{model}_{phase}_breakdown"
                    plot_category_breakdown(datasets, out)

    print("\nDone.")


if __name__ == "__main__":
    main()
