#!/usr/bin/env python3
"""
对比两个 OpenClaw 版本（gpt-5.4）：柱状图，**按指标分子图**，避免把秒、token、0–1 率混在同一纵轴。

输入（默认与脚本同目录）：
- gpt5_4_openclaw_version_overall_2rows.csv
- gpt5_4_by_ablation_dimension_openclaw_version.csv

输出（默认 <脚本目录>/figure_openclaw/）：
- openclaw_gpt54_overall_metrics_bars.png — overall 各指标独立子图、各自 y 轴
- openclaw_gpt54_by_dimension_rates_bars.png — 按维度：task / safe / pass@3 / pass^3（均为 0–1）
- openclaw_gpt54_by_dimension_cost_bars.png — 按维度：latency_s、tokens_total（×10⁶）

字体与 rc 与 plot_model_task_safe_score_bars.py 对齐。
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

FONT_TITLE = 12.5
FONT_AXIS_LABEL = 11.0
FONT_XTICK = 10.5
FONT_LEGEND = 10.5

DIMENSION_ORDER: list[str] = [
    "full_explicit",
    "goal_miss",
    "goal_ambiguity",
    "action_miss",
    "action_ambiguity",
    "tool_miss",
    "tool_ambiguity",
]

COLOR_V1 = "#6b8ebf"
COLOR_V2 = "#e59866"

BAR_RC = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Nimbus Roman", "serif"],
    "axes.facecolor": "#ececec",
    "figure.facecolor": "white",
    "axes.edgecolor": "black",
    "axes.linewidth": 0.9,
    "grid.color": "#b0b0b0",
    "grid.linestyle": "--",
    "grid.alpha": 0.75,
}


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fcell(row: dict[str, str], key: str) -> float:
    v = (row.get(key) or "").strip()
    if not v:
        return float("nan")
    return float(v)


def _style_axis(ax) -> None:
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.9, alpha=0.85)
    ax.xaxis.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(True)


def plot_overall_bars(rows: list[dict[str, str]], out_path: Path) -> None:
    """每个指标一个子图：纵轴只用该指标的物理单位，互不混用。"""
    import matplotlib.pyplot as plt

    by_v = {r["openclaw_version"].strip(): r for r in rows}
    versions = sorted(by_v.keys())
    if len(versions) != 2:
        raise ValueError(f"Expected exactly 2 openclaw_version rows, got {versions!r}")

    # (显示名, CSV 列, 可选 y 轴美化函数)
    metrics: list[tuple[str, str, str | None]] = [
        ("Latency (s)", "latency_s", None),
        ("Tokens total (×10⁶)", "tokens_total", "1e6"),
        ("Mean steps", "mean_steps", None),
        ("Task", "task", None),
        ("Safe", "safe", None),
        ("Score", "score", None),
        ("Progress", "progress", None),
        ("pass@3", "pass_at_k", None),
        (r"pass$^3$", "pass_all_k", None),
    ]

    n = len(metrics)
    ncols = 3
    nrows = int(np.ceil(n / ncols))
    fig_w = 4.2 * ncols
    fig_h = 3.15 * nrows

    with plt.rc_context(BAR_RC):
        fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h))
        axes_flat = np.atleast_1d(axes).ravel()

        x = np.arange(2)
        bar_w = 0.55
        colors = [COLOR_V1, COLOR_V2]

        for ax in axes_flat[n:]:
            ax.set_visible(False)

        for i, (title, col, scale) in enumerate(metrics):
            ax = axes_flat[i]
            vals: list[float] = []
            for v in versions:
                raw = fcell(by_v[v], col)
                if scale == "1e6":
                    vals.append(raw / 1.0e6)
                else:
                    vals.append(raw)
            ax.bar(x, vals, bar_w, color=colors, edgecolor="white", linewidth=0.65, zorder=2)
            ax.set_xticks(x)
            ax.set_xticklabels(versions, fontsize=FONT_XTICK, rotation=18, ha="right")
            ax.set_title(title, fontsize=FONT_TITLE, pad=10)
            _style_axis(ax)
            if col in ("task", "safe", "score", "progress", "pass_at_k", "pass_all_k"):
                ax.set_ylim(0, max(1.05, max(vals, default=0) * 1.08))

        fig.suptitle(
            "GPT-5.4 — OpenClaw versions (overall, n_cases=98)",
            fontsize=FONT_TITLE + 0.5,
            y=1.02,
        )
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.22)
        plt.close(fig)


def plot_by_dimension_rates(rows: list[dict[str, str]], out_path: Path) -> None:
    """0–1 类指标：同一子图纵轴 0–1，按维度分组柱。"""
    import matplotlib.pyplot as plt

    by_vd: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        key = (r["openclaw_version"].strip(), r["dimension"].strip())
        by_vd[key] = r

    versions = sorted({r["openclaw_version"].strip() for r in rows})
    if len(versions) != 2:
        raise ValueError(f"Expected 2 versions, got {versions!r}")

    rate_specs = [
        ("Task", "task"),
        ("Safe", "safe"),
        ("pass@3", "pass_at_k"),
        (r"pass$^3$", "pass_all_k"),
    ]

    x = np.arange(len(DIMENSION_ORDER))
    w = 0.36
    off = w / 2

    with plt.rc_context(BAR_RC):
        fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.2))
        for ax, (ax_title, col) in zip(np.ravel(axes), rate_specs):
            for j, ver in enumerate(versions):
                ys = []
                for d in DIMENSION_ORDER:
                    row = by_vd.get((ver, d))
                    ys.append(fcell(row, col) if row else float("nan"))
                pos = x - off + j * w
                ax.bar(
                    pos,
                    ys,
                    w,
                    label=ver,
                    color=COLOR_V1 if j == 0 else COLOR_V2,
                    edgecolor="white",
                    linewidth=0.55,
                    zorder=2,
                )
            ax.set_title(ax_title, fontsize=FONT_TITLE, pad=8)
            ax.set_xticks(x)
            ax.set_xticklabels(DIMENSION_ORDER, rotation=38, ha="right", fontsize=FONT_XTICK - 0.5)
            ax.set_ylim(0, 1.08)
            ax.set_ylabel("Rate", fontsize=FONT_AXIS_LABEL)
            _style_axis(ax)

        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            fontsize=FONT_LEGEND,
            loc="upper center",
            ncol=2,
            bbox_to_anchor=(0.5, 1.02),
            frameon=True,
            fancybox=False,
            edgecolor="black",
            facecolor="white",
        )
        fig.suptitle(
            "GPT-5.4 — rates by ablation dimension",
            fontsize=FONT_TITLE + 0.5,
            y=1.06,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.22)
        plt.close(fig)


def plot_by_dimension_cost(rows: list[dict[str, str]], out_path: Path) -> None:
    """延迟与 token 与 0–1 不可比：单独图、各一个子图。"""
    import matplotlib.pyplot as plt

    by_vd: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        by_vd[(r["openclaw_version"].strip(), r["dimension"].strip())] = r

    versions = sorted({r["openclaw_version"].strip() for r in rows})
    x = np.arange(len(DIMENSION_ORDER))
    w = 0.36
    off = w / 2

    with plt.rc_context(BAR_RC):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 4.8))

        for j, ver in enumerate(versions):
            lat: list[float] = []
            tok_m: list[float] = []
            for d in DIMENSION_ORDER:
                row = by_vd.get((ver, d))
                if not row:
                    lat.append(float("nan"))
                    tok_m.append(float("nan"))
                else:
                    lat.append(fcell(row, "latency_s"))
                    tok_m.append(fcell(row, "tokens_total") / 1.0e6)
            pos = x - off + j * w
            ax1.bar(pos, lat, w, label=ver, color=COLOR_V1 if j == 0 else COLOR_V2, edgecolor="white", linewidth=0.55, zorder=2)
            ax2.bar(pos, tok_m, w, label=ver, color=COLOR_V1 if j == 0 else COLOR_V2, edgecolor="white", linewidth=0.55, zorder=2)

        for ax, title, ylab in (
            (ax1, "Latency by dimension", "Latency (s)"),
            (ax2, "Tokens total by dimension", "Tokens total (×10⁶)"),
        ):
            ax.set_title(title, fontsize=FONT_TITLE, pad=10)
            ax.set_xticks(x)
            ax.set_xticklabels(DIMENSION_ORDER, rotation=38, ha="right", fontsize=FONT_XTICK - 0.5)
            ax.set_ylabel(ylab, fontsize=FONT_AXIS_LABEL)
            _style_axis(ax)

        ax1.legend(fontsize=FONT_LEGEND, loc="upper right", frameon=True, fancybox=False, edgecolor="black")
        ax2.legend(fontsize=FONT_LEGEND, loc="upper right", frameon=True, fancybox=False, edgecolor="black")
        fig.suptitle(
            "GPT-5.4 — cost metrics by ablation dimension",
            fontsize=FONT_TITLE + 0.5,
            y=1.03,
        )
        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.22)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bar charts comparing two OpenClaw versions (gpt-5.4 rollups).")
    here = Path(__file__).resolve().parent
    parser.add_argument(
        "--overall-csv",
        type=Path,
        default=here / "gpt5_4_openclaw_version_overall_2rows.csv",
        help="2-row overall rollup CSV",
    )
    parser.add_argument(
        "--by-dim-csv",
        type=Path,
        default=here / "gpt5_4_by_ablation_dimension_openclaw_version.csv",
        help="Per-dimension rollup CSV",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Parent directory; PNGs under <parent>/figure_openclaw/ (default: script dir)",
    )
    args = parser.parse_args()

    out_parent = args.out_dir or here
    fig_dir = out_parent / "figure_openclaw"

    if not args.overall_csv.is_file():
        raise SystemExit(f"Missing: {args.overall_csv}")
    if not args.by_dim_csv.is_file():
        raise SystemExit(f"Missing: {args.by_dim_csv}")

    overall_rows = read_rows(args.overall_csv)
    dim_rows = read_rows(args.by_dim_csv)

    plot_overall_bars(overall_rows, fig_dir / "openclaw_gpt54_overall_metrics_bars.png")
    plot_by_dimension_rates(dim_rows, fig_dir / "openclaw_gpt54_by_dimension_rates_bars.png")
    plot_by_dimension_cost(dim_rows, fig_dir / "openclaw_gpt54_by_dimension_cost_bars.png")

    for name in (
        "openclaw_gpt54_overall_metrics_bars.png",
        "openclaw_gpt54_by_dimension_rates_bars.png",
        "openclaw_gpt54_by_dimension_cost_bars.png",
    ):
        print(f"Wrote: {fig_dir / name}")


if __name__ == "__main__":
    main()
