#!/usr/bin/env python3
"""
从 full98_by_ablation_dimension_model.csv 为 **每个模型单独** 绘制一张经典 **三角雷达图**
（一个圆、三条轴各占一角：安全 / 鲁棒 / 效率）。

指标定义：
- **安全**：7 个消融维度上 `safe` 的算术平均（0–1）。
- **鲁棒**：除 `full_explicit` 外 6 维上 **`pass_all_k`** 的算术平均（0–1），直接用 CSV 列，不由 `task` 重算。
- **效率**：7 维平均步数与平均 `tokens_total`，对 log10 后在全体模型间 min–max 反转后取平均（0–1）。

默认输出：
- **`<脚本目录>/radar_figures/`**：每模型一张雷达 PNG。
- **`<脚本目录>/figures/capability_tradeoff_scatter.png`**：横轴 **Robustness**、纵轴 **Efficiency**（含 steps+tokens 的综合效率）；**散点大小 ∝ mean task**（7 维平均）；颜色 **Safety**（coolwarm）；Safety 与 Efficiency 共同体现 safety–efficiency 谱系，**无 colorbar**。
- **`figures/capability_tradeoff_safe_vs_task.png`**：Safety × task，颜色为 **efficiency**，带 **colorbar**。
- **`figures/capability_tradeoff_safe_vs_tokens.png`**：纵轴 **Safety**、横轴 **Efficiency**；颜色为 **mean tokens（×10⁶）**。

图内轴标签为英文；无 CJK 字体环境可导出。

依赖：matplotlib、numpy
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path

import numpy as np

DIMENSION_ORDER: list[str] = [
    "full_explicit",
    "goal_miss",
    "goal_ambiguity",
    "action_miss",
    "action_ambiguity",
    "tool_miss",
    "tool_ambiguity",
]

HARD_DIMENSIONS: list[str] = [d for d in DIMENSION_ORDER if d != "full_explicit"]

FONT_AXIS = 10.0  # 预留；雷达图轴数字见 FONT_RADAR_VALUE
# 单模型雷达：标题 + 三角三轴名 + 同心圆刻度与顶点分数
FONT_RADAR_TITLE = 17.0
FONT_RADAR_LABEL = 14.5
FONT_RADAR_VALUE = 12.5

# 所有 `figures/capability_tradeoff_*.png` 散点图共用字号（含坐标轴、刻度、标题、标注）
FONT_TRADEOFF_TITLE = 14.0
FONT_TRADEOFF_AXIS_LABEL = 12.0
FONT_TRADEOFF_TICK = 10.5
FONT_TRADEOFF_ANNOTATE = 12
FONT_TRADEOFF_TITLE_PAD = 12


def _tradeoff_rc_context():
    """matplotlib rc：与显式 fontsize 一致，避免刻度等漏控。"""
    import matplotlib.pyplot as plt

    return plt.rc_context(
        {
            "font.size": FONT_TRADEOFF_TICK,
            "axes.labelsize": FONT_TRADEOFF_AXIS_LABEL,
            "axes.titlesize": FONT_TRADEOFF_TITLE,
            "xtick.labelsize": FONT_TRADEOFF_TICK,
            "ytick.labelsize": FONT_TRADEOFF_TICK,
        }
    )


def _finalize_tradeoff_axes(
    ax,
    *,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    """三张 trade-off 图统一的标题 / 轴 / 刻度字号。"""
    ax.set_xlabel(xlabel, fontsize=FONT_TRADEOFF_AXIS_LABEL)
    ax.set_ylabel(ylabel, fontsize=FONT_TRADEOFF_AXIS_LABEL)
    ax.set_title(title, fontsize=FONT_TRADEOFF_TITLE, pad=FONT_TRADEOFF_TITLE_PAD)
    ax.tick_params(axis="both", labelsize=FONT_TRADEOFF_TICK)


AXIS_LABELS = ("Safety", "Robustness", "Efficiency")

RADAR_LINE = "#2c5282"
RADAR_FILL = "#5b7fa8"


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def short_model_name(full: str) -> str:
    return full.split("/")[-1] if "/" in full else full


def tradeoff_label_sep_dx_pt(model_id: str) -> float:
    """
    散点接近时标签左右错开（offset points，正为向右）。
    minimax↔gemini、claude sonnet↔opus 用更大间距；glm 较宽右移防压点；其它 ±sep；doubao 单独布局。
    """
    sm = short_model_name(model_id).lower()
    sep = 14.0
    sep_minimax_gemini = 44.0
    sep_claude_pair = 28.0
    sep_glm = 26.0
    if "sonnet" in sm and "claude" in sm:
        return -sep_claude_pair
    if "opus" in sm and "claude" in sm:
        return sep_claude_pair
    if "minimax" in sm:
        return -sep_minimax_gemini
    if "gemini" in sm:
        return sep_minimax_gemini
    if "doubao" in sm:
        return 0.0
    if "glm" in sm:
        return sep_glm
    return 0.0


def _safe_vs_task_label_preset(model_id: str) -> tuple[float, float, str, str] | None:
    """
    Safety×mean task 图专用：固定偏移（points）与对齐，避免与邻点/散点重叠。
    返回 (dx, dy, ha, va)；None 表示沿用默认径向 + tradeoff_label_sep 逻辑。
    """
    sm = short_model_name(model_id).lower()
    if "minimax" in sm:
        return (0.0, 15.0, "center", "bottom")
    if "5.4-mini" in sm:
        return (-5.0, -22.0, "center", "top")
    if "kimi" in sm and "k2.5" in sm:
        return (-28.0, 2.0, "right", "center")
    if "qwen" in sm:
        return (22.0, 1.0, "left", "center")
    return None


def _safe_vs_tokens_label_preset(model_id: str) -> tuple[float, float, str, str] | None:
    """
    Safety×mean tokens 图专用：固定偏移（points）与对齐。
    须在匹配 `gpt-5.4-mini` 之后再匹配 `gpt-5.4`。
    """
    sm = short_model_name(model_id).lower()
    if "5.4-mini" in sm:
        return (0.0, 15.0, "center", "bottom")
    if sm.startswith("gpt-5.4") and "mini" not in sm:
        return (0.0, 15.0, "center", "bottom")
    if "kimi" in sm:
        return (0.0, 15.0, "center", "bottom")
    if "minimax" in sm:
        return (0.0, -17.0, "center", "top")
    if "qwen" in sm:
        return (-26.0, 1.0, "right", "center")
    if "deepseek" in sm:
        return (-26.0, -3.0, "right", "center")
    if "sonnet" in sm and "claude" in sm:
        return (0.0, -17.0, "center", "top")
    return None


def _spread_axis_limits(
    arr: np.ndarray,
    *,
    pad_ratio: float = 0.18,
    min_span: float | None = None,
) -> tuple[float, float]:
    """坐标略放宽；点挤在一起时可用 min_span 拉大刻度跨度。"""
    arr = np.asarray(arr, dtype=float)
    lo = float(np.nanmin(arr))
    hi = float(np.nanmax(arr))
    span = hi - lo
    if not math.isfinite(span):
        return 0.0, 1.0
    if min_span is not None and span < min_span:
        mid = (lo + hi) / 2.0
        lo = mid - min_span / 2.0
        hi = mid + min_span / 2.0
        span = min_span
    pad = span * pad_ratio + 1e-12
    return lo - pad, hi + pad


def _annotate_tradeoff_labels(
    ax,
    models: list[str],
    x: np.ndarray,
    y: np.ndarray,
    *,
    layout: str = "default",
) -> None:
    """径向 + 豆包/gemini 等特殊避让；safe_vs_task / safe_vs_tokens 各自有专用预设。"""
    x = np.asarray(x)
    y = np.asarray(y)
    n_m = len(models)
    cx = float(np.mean(x))
    cy = float(np.mean(y))
    for i, m in enumerate(models):
        px, py = float(x[i]), float(y[i])

        if layout == "safe_vs_task":
            preset = _safe_vs_task_label_preset(m)
        elif layout == "safe_vs_tokens":
            preset = _safe_vs_tokens_label_preset(m)
        else:
            preset = None
        if preset is not None:
            dx, dy, ha_use, va_use = preset
        else:
            vx = px - cx
            vy = py - cy
            hn = math.hypot(vx, vy)
            if hn < 1e-12:
                vx, vy = 1.0, 0.0
                hn = 1.0
            vx, vy = vx / hn, vy / hn
            span = math.pi / max(n_m + 5, 7)
            rot = span * (i - (n_m - 1) / 2.0)
            cr, sr = math.cos(rot), math.sin(rot)
            ox = vx * cr - vy * sr
            oy = vx * sr + vy * cr
            rad_pt = 13.0 + (i % 7) * 1.6
            dx = ox * rad_pt
            dy = oy * rad_pt
            tx, ty = -oy, ox
            bump = (((i * 5) % 13) - 6) * 2.0
            dx += bump * tx
            dy += bump * ty

            sm = short_model_name(m).lower()
            ha_use = "center"
            va_use = "center"
            if "doubao" in sm:
                dx = -14.0
                dy = 4.0
                ha_use = "right"
                va_use = "center"
            elif "gemini" in m.lower():
                # 仍在点上方；在 minimax↔gemini 的 sep 基础上整体左移，避免贴色条或偏右
                dx = -26.0
                dy = 13.0
                ha_use = "center"
                va_use = "bottom"

            dx += tradeoff_label_sep_dx_pt(m)

            if layout == "safe_vs_task":
                sm2 = short_model_name(m).lower()
                if "glm" in sm2:
                    dx += 18.0
                    dy += 10.0
                elif "sonnet" in sm2 and "claude" in sm2:
                    dx -= 16.0
                    dy -= 14.0

        ax.annotate(
            short_model_name(m),
            (px, py),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha_use,
            va=va_use,
            fontsize=FONT_TRADEOFF_ANNOTATE,
            color="#222222",
            zorder=9,
            annotation_clip=False,
        )


def filename_slug(model_id: str) -> str:
    s = model_id.strip().replace("/", "__").replace(" ", "_")
    s = re.sub(r'[<>:"|?*\\]', "_", s)
    return s or "model"


def _f(row: dict[str, str], key: str) -> float | None:
    try:
        v = float((row.get(key) or "").strip() or "nan")
    except ValueError:
        return None
    if math.isnan(v):
        return None
    return v


def compute_capability_scores(
    rows: list[dict[str, str]],
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    from collections import defaultdict

    by_model: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        m = r.get("model", "").strip()
        d = r.get("dimension", "").strip()
        if not m or d not in DIMENSION_ORDER:
            continue
        by_model[m].append(r)

    models = sorted(by_model.keys())
    n = len(models)
    safety = np.zeros(n)
    robustness = np.zeros(n)
    mean_task = np.zeros(n)
    mean_steps = np.zeros(n)
    mean_toks = np.zeros(n)

    for i, m in enumerate(models):
        rs = by_model[m]
        safe_vals: list[float] = []
        pass_all_k_hard: list[float] = []
        task_vals: list[float] = []
        steps: list[float] = []
        toks: list[float] = []

        for r in rs:
            d = r.get("dimension", "").strip()
            sv = _f(r, "safe")
            pk = _f(r, "pass_all_k")
            tv = _f(r, "task")
            st = _f(r, "mean_steps")
            tt = _f(r, "tokens_total")
            if sv is not None:
                safe_vals.append(sv)
            if d in HARD_DIMENSIONS and pk is not None:
                pass_all_k_hard.append(pk)
            if tv is not None:
                task_vals.append(tv)
            if st is not None:
                steps.append(st)
            if tt is not None:
                toks.append(tt)

        safety[i] = float(np.mean(safe_vals)) if safe_vals else 0.0
        robustness[i] = float(np.mean(pass_all_k_hard)) if pass_all_k_hard else 0.0
        mean_task[i] = float(np.mean(task_vals)) if task_vals else 0.0
        mean_steps[i] = float(np.mean(steps)) if steps else float("nan")
        mean_toks[i] = float(np.mean(toks)) if toks else float("nan")

    log_s = np.array([math.log10(max(mean_steps[i], 1e-9)) for i in range(n)])
    log_t = np.array([math.log10(max(mean_toks[i], 1.0)) for i in range(n)])

    def minmax_inv(arr: np.ndarray) -> np.ndarray:
        lo, hi = np.nanmin(arr), np.nanmax(arr)
        if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
            return np.ones(n)
        return (hi - arr) / (hi - lo)

    eff_s = minmax_inv(log_s)
    eff_t = minmax_inv(log_t)
    efficiency = (eff_s + eff_t) / 2.0

    return models, safety, robustness, efficiency, mean_task, mean_toks


def _radar_angles(n_axes: int) -> np.ndarray:
    """与 `set_theta_zero_location('N')` + `set_theta_direction(-1)` 配合：第一轴在正上方，均分整圆。"""
    return np.linspace(0, 2 * np.pi, n_axes, endpoint=False)


def plot_one_model_radar(
    model_full: str,
    safety: float,
    robustness: float,
    efficiency: float,
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    n_axes = 3
    angles = _radar_angles(n_axes)
    angles_closed = np.concatenate([angles, angles[:1]])
    vals = np.array([safety, robustness, efficiency])
    vals_closed = np.concatenate([vals, vals[:1]])

    fig, ax = plt.subplots(figsize=(8.0, 8.0), subplot_kw=dict(projection="polar"))

    # 标准「雷达图」朝向：0° 在正北，顺时针递增（与常见商业雷达图一致）
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.plot(angles_closed, vals_closed, color=RADAR_LINE, linewidth=2.2)
    ax.fill(angles_closed, vals_closed, color=RADAR_FILL, alpha=0.35)

    ax.set_xticks(angles)
    ax.set_xticklabels(AXIS_LABELS, fontsize=FONT_RADAR_LABEL)

    # 径向刻度 0–1，多圈同心圆（参考图里的同心网格）
    ax.set_ylim(0, 1.0)
    radial_ticks = np.linspace(0.2, 1.0, 5)
    ax.set_yticks(radial_ticks)
    ax.set_yticklabels(
        [f"{t:.1f}" for t in radial_ticks],
        fontsize=FONT_RADAR_VALUE,
        color="gray",
    )
    ax.grid(True, linestyle="-", linewidth=0.8, alpha=0.45)

    # 关键：勿根据三角形数据自动收窄 θ 范围，否则会只剩一扇形 / 「四分之一圆」观感
    ax.set_thetamin(0)
    ax.set_thetamax(360)

    title = short_model_name(model_full)
    # 极坐标下 ax.set_title 易被裁切，改用 fig.suptitle 并压低子图顶边
    fig.suptitle(title, fontsize=FONT_RADAR_TITLE, y=0.96, ha="center")

    # 顶点分数：放在略高于数据点的半径处，避免挤在中心
    label_r = min(ax.get_ylim()[1] * 1.08, 1.12)
    ax.set_ylim(0, label_r)
    for ang, v in zip(angles, vals):
        rr = min(v + 0.09, label_r - 0.02)
        ax.text(
            ang,
            rr,
            f"{v:.2f}",
            ha="center",
            va="center",
            fontsize=FONT_RADAR_VALUE,
            color="#333333",
            clip_on=False,
        )

    fig.subplots_adjust(left=0.09, right=0.91, top=0.80, bottom=0.09)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # polar + bbox_inches='tight' 极易把圆裁成扇形，改用固定边距
    fig.savefig(out_path, dpi=160, bbox_inches=None, pad_inches=0.15)
    plt.close(fig)


def plot_tradeoff_scatter(
    models: list[str],
    safety: np.ndarray,
    robustness: np.ndarray,
    efficiency: np.ndarray,
    mean_task: np.ndarray,
    out_path: Path,
) -> None:
    """横轴 Robustness、纵轴 Efficiency；散点大小为 mean task；颜色为 Safety（无 colorbar）。大点先画、小点上叠。"""
    import matplotlib.pyplot as plt

    x = np.asarray(robustness)
    y = np.asarray(efficiency)
    c = np.asarray(safety)
    mt = np.asarray(mean_task)

    t_lo, t_hi = float(np.min(mt)), float(np.max(mt))
    if t_hi > t_lo:
        t_norm = (mt - t_lo) / (t_hi - t_lo)
    else:
        t_norm = np.full_like(mt, 0.5, dtype=float)
    s_min, s_max = 75.0, 340.0
    sizes = s_min + t_norm * (s_max - s_min)

    # 颜色仍映射 safety，仅不显示色条
    c_lo = float(np.min(c))
    c_hi = float(np.max(c))
    pad_c = max(0.005, (c_hi - c_lo) * 0.15)

    order = np.argsort(sizes)  # 小点在后绘制，避免被大块完全挡住

    with _tradeoff_rc_context():
        fig, ax = plt.subplots(figsize=(11.5, 8.4))
        ax.scatter(
            x[order],
            y[order],
            c=c[order],
            s=sizes[order],
            cmap="coolwarm",
            alpha=0.95,
            edgecolors="white",
            linewidths=1.0,
            vmin=c_lo - pad_c,
            vmax=c_hi + pad_c,
            zorder=10,
        )

        _annotate_tradeoff_labels(ax, models, x, y)

        _finalize_tradeoff_axes(
            ax,
            title=(
                "Capability trade-off — Robustness vs Efficiency · full98\n"
                "Marker size ∝ mean task (7-dim); color ∝ safety; "
                "y-axis ∝ efficiency (steps+tokens, higher is better)"
            ),
            xlabel="Robustness",
            ylabel="Efficiency",
        )
        pad = 0.18
        ax.set_xlim(-pad, 1.0 + pad)
        ax.set_ylim(-pad, 1.0 + pad)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, linestyle="-", alpha=0.38)

        from matplotlib.lines import Line2D

        # scatter 的 s 为面积 pt²；Line2D markersize 约为直径 pt，用于示意 task 大小区间
        def _ms_for_s(area_pt2: float) -> float:
            return max(4.0, math.sqrt(max(area_pt2, 1.0)) / 2.2)

        ax.legend(
            handles=[
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="#666666",
                    markersize=_ms_for_s(s_min),
                    linestyle="None",
                    label=f"Low task ({t_lo:.2f})",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="#666666",
                    markersize=_ms_for_s(s_max),
                    linestyle="None",
                    label=f"High task ({t_hi:.2f})",
                ),
            ],
            loc="lower right",
            fontsize=FONT_TRADEOFF_TICK,
            framealpha=0.92,
            title="Task (size)",
        )

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.35)
        plt.close(fig)


def plot_safe_vs_task_scatter(
    models: list[str],
    mean_task: np.ndarray,
    safety: np.ndarray,
    efficiency: np.ndarray,
    out_path: Path,
) -> None:
    """纵轴 Safety，横轴 7 维平均 task；颜色为 efficiency 排名（viridis）。"""
    import matplotlib.pyplot as plt

    x = np.asarray(mean_task)
    y = np.asarray(safety)
    c = np.asarray(efficiency)

    with _tradeoff_rc_context():
        fig, ax = plt.subplots(figsize=(11.5, 8.4))
        sc = ax.scatter(
            x,
            y,
            c=c,
            s=140,
            cmap="viridis",
            alpha=0.95,
            vmin=0.0,
            vmax=1.0,
            edgecolors="white",
            linewidths=1.0,
            zorder=10,
        )
        _annotate_tradeoff_labels(
            ax, models, x, y, layout="safe_vs_task"
        )

        _finalize_tradeoff_axes(
            ax,
            title="Safety vs task · full98",
            xlabel="Task score",
            ylabel="Safety score",
        )
        ax.set_xlim(_spread_axis_limits(x, pad_ratio=0.18, min_span=0.08))
        ax.set_ylim(_spread_axis_limits(y, pad_ratio=0.20, min_span=0.10))
        ax.grid(True, linestyle="-", alpha=0.38)

        cbar = fig.colorbar(
            sc,
            ax=ax,
            fraction=0.035,
            pad=0.03,
        )
        cbar.set_label(
            "Efficiency",
            fontsize=FONT_TRADEOFF_AXIS_LABEL,
        )
        cbar.ax.tick_params(labelsize=FONT_TRADEOFF_TICK)

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.35)
        plt.close(fig)


def plot_safe_vs_tokens_scatter(
    models: list[str],
    mean_toks: np.ndarray,
    safety: np.ndarray,
    efficiency: np.ndarray,
    out_path: Path,
) -> None:
    """纵轴 Safety，横轴 Efficiency；颜色为 7 维平均 tokens_total（×10⁶）。"""
    import matplotlib.pyplot as plt

    x = np.asarray(efficiency)
    y = np.asarray(safety)
    c = np.asarray(mean_toks) / 1e6
    c_lo = float(np.min(c))
    c_hi = float(np.max(c))
    pad_c = max((c_hi - c_lo) * 0.06, (c_hi + 1e-12) * 0.02)

    with _tradeoff_rc_context():
        fig, ax = plt.subplots(figsize=(11.5, 8.4))
        sc = ax.scatter(
            x,
            y,
            c=c,
            s=140,
            cmap="viridis",
            alpha=0.95,
            vmin=c_lo - pad_c,
            vmax=c_hi + pad_c,
            edgecolors="white",
            linewidths=1.0,
            zorder=10,
        )
        _annotate_tradeoff_labels(
            ax, models, x, y, layout="safe_vs_tokens"
        )

        _finalize_tradeoff_axes(
            ax,
            title="Safety vs efficiency (color: tokens) · full98",
            xlabel="Efficiency",
            ylabel="Safety",
        )
        ax.set_xlim(_spread_axis_limits(x, pad_ratio=0.16, min_span=0.08))
        ax.set_ylim(_spread_axis_limits(y, pad_ratio=0.20, min_span=0.10))
        ax.grid(True, linestyle="-", alpha=0.38)

        cbar = fig.colorbar(
            sc,
            ax=ax,
            fraction=0.035,
            pad=0.03,
        )
        cbar.set_label(
            "Tokens ×10⁶",
            fontsize=FONT_TRADEOFF_AXIS_LABEL,
        )
        cbar.ax.tick_params(labelsize=FONT_TRADEOFF_TICK)

        fig.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=160, bbox_inches="tight", pad_inches=0.35)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One radar PNG per model under radar_figures/."
    )
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Parent directory; radar_figures/ + figures/capability_tradeoff_*.png",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    csv_path = args.csv or (here / "full98_by_ablation_dimension_model.csv")
    out_parent = args.out_dir or here
    radar_dir = out_parent / "radar_figures"
    figures_dir = out_parent / "figures"
    tradeoff_png = figures_dir / "capability_tradeoff_scatter.png"
    safe_task_png = figures_dir / "capability_tradeoff_safe_vs_task.png"
    safe_tok_png = figures_dir / "capability_tradeoff_safe_vs_tokens.png"

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    rows = read_rows(csv_path)
    models, safety, robustness, efficiency, mean_task, mean_toks = compute_capability_scores(rows)
    if not models:
        raise SystemExit("No models in CSV.")

    plot_tradeoff_scatter(models, safety, robustness, efficiency, mean_task, tradeoff_png)
    print(f"Wrote: {tradeoff_png}")

    plot_safe_vs_task_scatter(models, mean_task, safety, efficiency, safe_task_png)
    print(f"Wrote: {safe_task_png}")
    plot_safe_vs_tokens_scatter(models, mean_toks, safety, efficiency, safe_tok_png)
    print(f"Wrote: {safe_tok_png}")

    written: list[Path] = []
    for i, m in enumerate(models):
        slug = filename_slug(m)
        path = radar_dir / f"{slug}.png"
        plot_one_model_radar(m, float(safety[i]), float(robustness[i]), float(efficiency[i]), path)
        written.append(path)

    for p in written:
        print(f"Wrote: {p}")


if __name__ == "__main__":
    main()
