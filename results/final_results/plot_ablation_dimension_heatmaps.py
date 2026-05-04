#!/usr/bin/env python3
"""
从 full98_by_ablation_dimension_model.csv 生成热力图：
- 横轴：模型；纵轴：7 个维度（full_explicit, goal_*, action_*, tool_*）
- 输出：
  - task：Blues，色标 0–1
  - progress：Greens，色标 0–1
  - safe：**YlOrRd**，色标为 **本矩阵 min–max**（把整段色谱压在真实取值区间上，格间差异更明显；格内数字仍为真实 safe）
  - mean_steps：Oranges，色标按本矩阵 min–max
  - tokens_total：Purples，色标按本矩阵 min–max（格内缩写为 M/K）
- PNG 默认写入脚本同级的 **`figures/`** 子目录（`--out-dir` 指定父目录则写入 `<父目录>/figures/`）

图表标题为英文，便于在无 CJK 字体的服务器上导出。

依赖：matplotlib、numpy（若未安装：pip install matplotlib numpy）

字体：只改下面「图内字号」一组常量即可（单位 pt），无需命令行参数。
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Literal

from matplotlib.colors import Colormap

# -----------------------------------------------------------------------------
# 默认维度顺序（与 CSV 中 dimension 字段一致）
# -----------------------------------------------------------------------------
DIMENSION_ORDER: list[str] = [
    "full_explicit",
    "goal_miss",
    "goal_ambiguity",
    "action_miss",
    "action_ambiguity",
    "tool_miss",
    "tool_ambiguity",
]

# CSV 中参与绘图的数值列
_METRIC_KEYS = ("task", "progress", "safe", "mean_steps", "tokens_total")

# -----------------------------------------------------------------------------
# 图内字号（pt）— 需要调大/调小只改这里
# -----------------------------------------------------------------------------
FONT_TITLE = 11.0
FONT_AXIS_LABEL = 10.0
FONT_XTICK = 12
FONT_YTICK = 12
# 模型名斜角：过小易重叠，过大难读；55→35 略抬横轴可读性
XTICK_ROTATION_DEG = 25
FONT_CELL = 10
FONT_CBAR = 10


def read_scores(csv_path: Path) -> tuple[list[str], dict[tuple[str, str], dict[str, float]]]:
    """返回 (models_sorted, (model, dim) -> 各指标浮点值)."""
    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    models = sorted({r["model"] for r in rows if r.get("model")})
    data: dict[tuple[str, str], dict[str, float]] = {}
    for r in rows:
        m, d = r.get("model", ""), r.get("dimension", "")
        if not m or not d:
            continue
        entry: dict[str, float] = {}
        for k in _METRIC_KEYS:
            raw = (r.get(k) or "").strip()
            try:
                entry[k] = float(raw) if raw else float("nan")
            except ValueError:
                entry[k] = float("nan")
        data[(m, d)] = entry
    return models, data


def build_matrix(
    models: list[str],
    dims: list[str],
    data: dict[tuple[str, str], dict[str, float]],
    key: str,
) -> tuple[list[list[float]], list[str]]:
    mat: list[list[float]] = []
    for d in dims:
        row: list[float] = []
        for m in models:
            v = data.get((m, d), {}).get(key, float("nan"))
            row.append(v)
        mat.append(row)
    return mat, models


def _format_cell_text(val: float, scale: Literal["unit01", "data"], vmax: float) -> str:
    import numpy as np

    if np.isnan(val):
        return "—"
    if scale == "unit01":
        return f"{val:.2f}"
    # data scale: compact for large token counts
    if vmax >= 5e5:
        if abs(val) >= 1e6:
            return f"{val / 1e6:.2f}M"
        if abs(val) >= 1e3:
            return f"{val / 1e3:.1f}K"
    if vmax >= 100:
        return f"{val:.1f}"
    return f"{val:.2f}"


def _cell_text_color(val: float, scale: Literal["unit01", "data"], vmin: float, vmax: float) -> str:
    import numpy as np

    if np.isnan(val):
        return "0.35"
    if scale == "unit01":
        return "white" if val > 0.55 else "0.15"
    if vmax <= vmin:
        return "0.15"
    t = (float(val) - vmin) / (vmax - vmin)
    return "white" if t > 0.55 else "0.15"


def plot_heatmap(
    matrix: list[list[float]],
    models: list[str],
    dims: list[str],
    title: str,
    cbar_label: str,
    cmap: str | Colormap,
    out_path: Path,
    *,
    scale: Literal["unit01", "data"] = "unit01",
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    arr = np.array(matrix, dtype=float)
    fig_w = max(10, 0.55 * len(models) + 4)
    fig_h = max(6, 0.45 * len(dims) + 3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    if scale == "unit01":
        vmin, vmax = 0.0, 1.0
    else:
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            vmin, vmax = 0.0, 1.0
        else:
            vmin = float(np.nanmin(finite))
            vmax = float(np.nanmax(finite))
            if vmax <= vmin:
                vmax = vmin + 1e-9

    im = ax.imshow(arr, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(
        models,
        rotation=XTICK_ROTATION_DEG,
        ha="right",
        rotation_mode="anchor",
        fontsize=FONT_XTICK,
    )
    ax.set_yticks(range(len(dims)))
    ax.set_yticklabels(dims, fontsize=FONT_YTICK)
    ax.set_xlabel("Model", fontsize=FONT_AXIS_LABEL)
    ax.set_ylabel("Dimension", fontsize=FONT_AXIS_LABEL)
    ax.set_title(title, fontsize=FONT_TITLE, pad=12)

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label(cbar_label, fontsize=FONT_CBAR)
    cbar.ax.tick_params(labelsize=FONT_CBAR * 0.85)

    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            val = float(arr[i, j])
            txt = _format_cell_text(val, scale, vmax)
            color = _cell_text_color(val, scale, vmin, vmax)
            ax.text(j, i, txt, ha="center", va="center", fontsize=FONT_CELL, color=color)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot metric heatmaps by model x dimension.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Input CSV (default: full98_by_ablation_dimension_model.csv next to this script)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Parent directory for outputs; PNGs under <out-dir>/figures/ (default: script directory)",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    csv_path = args.csv or (here / "full98_by_ablation_dimension_model.csv")
    out_parent = args.out_dir or here
    out_dir = out_parent / "figures"

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    models, data = read_scores(csv_path)
    if not models:
        raise SystemExit("No models found in CSV.")

    dims = [d for d in DIMENSION_ORDER if any((m, d) in data for m in models)]
    if not dims:
        raise SystemExit("No matching dimensions; check CSV dimension column.")

    written: list[Path] = []

    def run_one(
        key: str,
        title: str,
        cbar: str,
        cmap: str | Colormap,
        fname: str,
        scale: Literal["unit01", "data"],
    ) -> None:
        mat, _ = build_matrix(models, dims, data, key)
        path = out_dir / fname
        plot_heatmap(mat, models, dims, title, cbar, cmap, path, scale=scale)
        written.append(path)

    run_one(
        "task",
        "Task completion (task) vs model × dimension — full98",
        "task",
        "Blues",
        "heatmap_task_by_model_dimension.png",
        "unit01",
    )
    run_one(
        "progress",
        "Task progress vs model × dimension — full98",
        "progress",
        "Greens",
        "heatmap_progress_by_model_dimension.png",
        "unit01",
    )
    run_one(
        "safe",
        "Safety (safe) vs model × dimension — full98\n(color scale: min–max in this matrix)",
        "safe",
        "YlOrRd",
        "heatmap_safe_by_model_dimension.png",
        "data",
    )
    run_one(
        "mean_steps",
        "Steps vs model × dimension — full98",
        "steps",
        "Oranges",
        "heatmap_mean_steps_by_model_dimension.png",
        "data",
    )
    run_one(
        "tokens_total",
        "Token usage (tokens_total) vs model × dimension — full98",
        "tokens",
        "Purples",
        "heatmap_tokens_total_by_model_dimension.png",
        "data",
    )

    print("Wrote:")
    for p in written:
        print(f"  {p}")


if __name__ == "__main__":
    main()
