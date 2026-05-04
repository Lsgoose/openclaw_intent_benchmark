#!/usr/bin/env python3
"""
从 full98_by_ablation_dimension_model.csv 为每个模型画 **堆叠柱**：

在 **7 个消融维度** 上分别求 **task**、**safe** 的算术平均；自下而上为 **Task/2**（蓝）+ **Safe/2**（橙），
柱总高 **(task+safe)/2**，在各自 0–1 时上界为 **1**（不是按比例归一成整柱 100%）。
模型按该总分 **从高到低** 排序后画柱；柱顶显示 **Safe/(Task+Safe)** 百分比。

不再使用 CSV 中的 oracle **score** 列。

PNG 默认写入 `<脚本目录>/figures/bar_model_mean_task_safe_composite.png`。

依赖：matplotlib、numpy
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

DIMENSION_ORDER: list[str] = [
    "full_explicit",
    "goal_miss",
    "goal_ambiguity",
    "action_miss",
    "action_ambiguity",
    "tool_miss",
    "tool_ambiguity",
]

FONT_TITLE = 12.5
FONT_AXIS_LABEL = 11.0
FONT_XTICK = 10.5
FONT_LEGEND = 10.5
FONT_PCT = 10.5

# 参考图：底部偏灰蓝、顶部偏鲑橙
COLOR_TASK = "#6b8ebf"
COLOR_SAFE = "#e59866"


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def short_model_name(full: str) -> str:
    return full.split("/")[-1] if "/" in full else full


def aggregate_per_model(
    rows: list[dict[str, str]],
) -> tuple[list[str], list[float], list[float]]:
    """返回 (models_sorted, mean_task_per_dim, mean_safe_per_dim)。"""
    from collections import defaultdict

    sums: dict[str, dict[str, float]] = defaultdict(lambda: {"task": 0.0, "safe": 0.0, "n": 0})
    for r in rows:
        m, d = r.get("model", ""), r.get("dimension", "")
        if not m or d not in DIMENSION_ORDER:
            continue
        try:
            t = float((r.get("task") or "").strip() or "nan")
            s = float((r.get("safe") or "").strip() or "nan")
        except ValueError:
            continue
        if math.isnan(t) or math.isnan(s):
            continue
        sums[m]["task"] += t
        sums[m]["safe"] += s
        sums[m]["n"] += 1

    models = sorted(sums.keys())
    mean_tasks: list[float] = []
    mean_safes: list[float] = []
    for m in models:
        n = sums[m]["n"]
        if n == 0:
            mean_tasks.append(0.0)
            mean_safes.append(0.0)
        else:
            mean_tasks.append(sums[m]["task"] / n)
            mean_safes.append(sums[m]["safe"] / n)
    return models, mean_tasks, mean_safes


def plot_bars(
    models: list[str], mean_tasks: list[float], mean_safes: list[float], out_path: Path
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    triples = list(zip(models, mean_tasks, mean_safes))
    triples.sort(key=lambda t: (-(t[1] + t[2]) / 2.0, t[0]))
    models = [t[0] for t in triples]
    mean_tasks = [t[1] for t in triples]
    mean_safes = [t[2] for t in triples]

    labels = [short_model_name(m) for m in models]
    tasks = np.asarray(mean_tasks, dtype=float)
    safes = np.asarray(mean_safes, dtype=float)
    h_task = tasks / 2.0
    h_safe = safes / 2.0
    heights = h_task + h_safe
    totals_raw = tasks + safes
    x = np.arange(len(models))

    fig_w = max(10.0, 0.55 * len(models) + 3.5)
    bar_w = min(0.58, 0.72 / max(len(models) ** 0.35, 1))

    rc = {
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

    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(fig_w, 6.2))

        ax.bar(
            x,
            h_task,
            bar_w,
            label="Task",
            color=COLOR_TASK,
            edgecolor="white",
            linewidth=0.65,
            zorder=2,
        )
        ax.bar(
            x,
            h_safe,
            bar_w,
            bottom=h_task,
            label="Safe",
            color=COLOR_SAFE,
            edgecolor="white",
            linewidth=0.65,
            zorder=2,
        )

        y_hi = 1.12
        ax.set_ylim(0, y_hi)
        pct_dy = 0.028

        for i in range(len(models)):
            tot = float(totals_raw[i])
            h = float(heights[i])
            if tot < 1e-9:
                pct_s = "—"
                y_text = pct_dy
            else:
                pct_s = f"{100.0 * float(safes[i]) / tot:.0f}%"
                y_text = h + pct_dy
            ax.text(
                x[i],
                y_text,
                pct_s,
                ha="center",
                va="bottom",
                fontsize=FONT_PCT,
                color=COLOR_SAFE,
                fontweight="semibold",
                clip_on=False,
            )

        ax.set_ylabel("Score", fontsize=FONT_AXIS_LABEL)
        ax.set_xlabel("Model", fontsize=FONT_AXIS_LABEL)
        ax.set_title("Score over 98 cases", fontsize=FONT_TITLE, pad=14)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=42, ha="right", fontsize=FONT_XTICK)

        ax.set_axisbelow(True)
        ax.yaxis.grid(True, linestyle="--", linewidth=0.9, alpha=0.85)
        ax.xaxis.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(True)

        ax.legend(
            fontsize=FONT_LEGEND,
            loc="upper right",
            frameon=True,
            fancybox=False,
            edgecolor="black",
            facecolor="white",
        )

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.22)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stacked bars: task/2 + safe/2 per model (7-dim means), max height 1."
    )
    parser.add_argument("--csv", type=Path, default=None, help="Input CSV (default: alongside script)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Parent directory; PNG under <out-dir>/figures/ (default: script dir)",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    csv_path = args.csv or (here / "full98_by_ablation_dimension_model.csv")
    out_parent = args.out_dir or here
    out_png = out_parent / "figures" / "bar_model_mean_task_safe_composite.png"

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    rows = read_rows(csv_path)
    models, mean_tasks, mean_safes = aggregate_per_model(rows)
    if not models:
        raise SystemExit("No model aggregates; check CSV.")

    plot_bars(models, mean_tasks, mean_safes, out_png)
    print(f"Wrote: {out_png}")


if __name__ == "__main__":
    main()
