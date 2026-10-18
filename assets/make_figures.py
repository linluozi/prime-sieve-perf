"""Render the README figures from the measured JSON, so numbers cannot drift."""

from __future__ import annotations

import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

INK = "#2b2119"
PAPER = "#faf6f0"
AMBER = "#c8892b"
TERRACOTTA = "#b4552f"
OLIVE = "#6b6b3a"
MUTED = "#8a7a68"

plt.rcParams.update(
    {
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

results = json.loads((ROOT / "benchmarks" / "results.json").read_text(encoding="utf-8"))
work = json.loads((ROOT / "benchmarks" / "work_count.json").read_text(encoding="utf-8"))
summary = results["summary"]


def label_n(n: int) -> str:
    return f"{n:,}"


def memory_figure() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    labels = [label_n(row["n"]) for row in summary]
    base = [row["baseline_peak_bytes"] / 1024**2 for row in summary]
    opt = [row["optimized_peak_bytes"] / 1024**2 for row in summary]
    x = range(len(labels))
    width = 0.36

    bars_b = ax.bar(
        [i - width / 2 for i in x],
        base,
        width,
        color=TERRACOTTA,
        label="upstream (full flag list)",
    )
    bars_o = ax.bar(
        [i + width / 2 for i in x], opt, width, color=AMBER, label="odd-only bytearray"
    )

    for bars, values in ((bars_b, base), (bars_o, opt)):
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.25,
                f"{value:.2f} MiB",
                ha="center",
                va="bottom",
                fontsize=10,
                color=INK,
            )

    for i, row in enumerate(summary):
        ax.text(
            i,
            base[i] + 1.15,
            f"-{row['peak_reduction_percent']:.1f}%",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color=OLIVE,
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"n = {label}" for label in labels])
    ax.set_ylabel("Peak traced Python allocation (MiB)")
    ax.set_ylim(0, max(base) * 1.28)
    ax.set_title(
        "Flag storage drops by two thirds",
        loc="left",
        fontsize=15,
        fontweight="bold",
        pad=38,
    )
    ax.text(
        0,
        1.02,
        "tracemalloc peak, deterministic across runs",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.0))
    ax.grid(axis="y", color=MUTED, alpha=0.22, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ASSETS / "memory.png", dpi=200)
    plt.close(fig)


def work_figure() -> None:
    rows = work["rows"][::-1]
    fig, ax = plt.subplots(figsize=(9.6, 4.6))
    y = range(len(rows))
    height = 0.34
    base = [row["baseline_python_line_events"] for row in rows]
    opt = [row["optimized_python_line_events"] for row in rows]

    ax.barh(
        [i + height / 2 for i in y],
        base,
        height,
        color=TERRACOTTA,
        label="upstream (Python loop per multiple)",
    )
    ax.barh(
        [i - height / 2 for i in y],
        opt,
        height,
        color=AMBER,
        label="odd-only bytearray (C-level slice)",
    )

    for i in range(len(rows)):
        ax.text(
            base[i] * 1.12,
            i + height / 2,
            f"{base[i]:,}",
            va="center",
            fontsize=10,
            color=INK,
        )
        ax.text(
            opt[i] * 1.12,
            i - height / 2,
            f"{opt[i]:,}",
            va="center",
            fontsize=10,
            color=INK,
        )

    ax.set_xscale("log")
    ax.set_yticks(list(y))
    ax.set_yticklabels(
        [f"n = {label_n(row['n'])}\n{row['ratio']:,.0f}x fewer lines" for row in rows]
    )
    ax.set_xlabel("Python line events executed (log scale)")
    ax.set_xlim(300, max(base) * 3.2)
    ax.set_title(
        "The marking loop leaves Python entirely",
        loc="left",
        fontsize=15,
        fontweight="bold",
        pad=38,
    )
    ax.text(
        0,
        1.02,
        "sys.settrace line events; identical output for every n",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax.grid(axis="x", color=MUTED, alpha=0.22, linewidth=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(ASSETS / "python-work.png", dpi=200)
    plt.close(fig)


def speedup_figure() -> None:
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    y = range(len(summary))
    for i, row in enumerate(summary):
        sessions = [
            entry["speedup_median_of_per_round_ratios"]
            for session in results["sessions"]
            for entry in session["benchmarks"]
            if entry["n"] == row["n"]
        ]
        ax.plot(
            [row["speedup_min"], row["speedup_max"]],
            [i, i],
            color=MUTED,
            linewidth=2.2,
            solid_capstyle="round",
            zorder=1,
        )
        ax.scatter(
            sessions,
            [i] * len(sessions),
            s=46,
            color=AMBER,
            edgecolor=PAPER,
            linewidth=1.0,
            zorder=3,
        )
        ax.scatter(
            [row["speedup_per_round_median"]],
            [i],
            s=150,
            color=TERRACOTTA,
            marker="|",
            linewidth=2.6,
            zorder=4,
        )
        ax.text(
            row["speedup_max"] + 0.42,
            i,
            f"{row['speedup_per_round_median']:.2f}x",
            va="center",
            fontsize=11,
            fontweight="bold",
            color=INK,
        )

    ax.axvline(1.0, color=OLIVE, linestyle=(0, (4, 3)), linewidth=1.2)
    ax.text(
        1.08,
        1.0,
        "no change",
        color=OLIVE,
        fontsize=9,
        rotation=90,
        va="center",
        ha="left",
    )
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"n = {label_n(row['n'])}" for row in summary])
    ax.set_xlabel("Speedup, median of per-round ratios (5 sessions x 25 rounds)")
    ax.set_xlim(0.8, max(row["speedup_max"] for row in summary) + 1.3)
    ax.set_title(
        "Faster on every run, on a busy machine",
        loc="left",
        fontsize=15,
        fontweight="bold",
        pad=38,
    )
    ax.text(
        0,
        1.02,
        "dots are individual sessions; the bar is the min-max span; "
        "CPU was 40-100% busy with unrelated work",
        transform=ax.transAxes,
        fontsize=10,
        color=MUTED,
    )
    ax.grid(axis="x", color=MUTED, alpha=0.22, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}x"))
    fig.tight_layout()
    fig.savefig(ASSETS / "speedup.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    memory_figure()
    work_figure()
    speedup_figure()
    for name in ("memory.png", "python-work.png", "speedup.png"):
        path = ASSETS / name
        print(f"{name}: {path.stat().st_size:,} bytes")
    sys.exit(0)
