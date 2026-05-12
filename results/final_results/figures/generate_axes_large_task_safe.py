#!/usr/bin/env python3
"""
Generate axis-font-enlarged copies for the *original-style* task/safe heatmaps.

Does NOT overwrite the original PNGs.

Outputs:
  heatmap_safe_by_model_dimension_axes_large.png / .pdf
  heatmap_task_by_model_dimension_axes_large.png / .pdf
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "full98_by_ablation_dimension_model.csv"

DIM_ORDER = [
    "full_explicit",
    "goal_miss",
    "goal_ambiguity",
    "action_miss",
    "action_ambiguity",
    "tool_miss",
    "tool_ambiguity",
]

MODEL_ORDER = [
    "anthropic/claude-opus-4.6",
    "anthropic/claude-sonnet-4.6",
    "bailian/qwen3.6-plus",
    "deepseek/deepseek-v3.2",
    "google/gemini-3.1-pro-preview",
    "minimax/minimax-m2.7",
    "moonshotai/kimi-k2.5",
    "openai/gpt-5.4",
    "openai/gpt-5.4-mini",
    "volcengine/doubao-seed-2.0-pro",
    "z-ai/glm-5-turbo",
]


def pivot(df: pd.DataFrame, col: str) -> pd.DataFrame:
    sub = df[df["model"].isin(MODEL_ORDER) & df["dimension"].isin(DIM_ORDER)]
    p = sub.pivot(index="dimension", columns="model", values=col)
    return p.reindex(index=DIM_ORDER, columns=MODEL_ORDER)


def save_fig_png_pdf(fig: plt.Figure, base_path: Path) -> None:
    kwargs = {"bbox_inches": "tight", "facecolor": "white"}
    png = base_path.with_suffix(".png")
    pdf = base_path.with_suffix(".pdf")
    fig.savefig(png, dpi=200, **kwargs)
    fig.savefig(pdf, format="pdf", **kwargs)
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")


def recolor_annots(ax: plt.Axes, data: pd.DataFrame, threshold: float) -> None:
    # seaborn adds texts in row-major order
    vals = data.to_numpy()
    texts = [t for t in ax.texts if t.get_text() != ""]
    if len(texts) != vals.size:
        return
    k = 0
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            v = vals[i, j]
            texts[k].set_color("white" if (v >= threshold) else "black")
            k += 1


def draw_task_axes_large(df: pd.DataFrame) -> None:
    data = pivot(df, "task")
    annot = data.map(lambda x: f"{x:.2f}")

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(15.0, 6.8))
    # Ensure extra left margin so the y-label can sit fully left.
    fig.subplots_adjust(left=0.22)

    # Increase ALL fonts: title/axes/ticks/annotations/colorbar.
    label_fs, tick_fs, title_fs, annot_fs = 22, 22, 19, 20

    sns.heatmap(
        data,
        ax=ax,
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
        annot=annot,
        fmt="",
        linewidths=0.0,  # match original: no visible grid lines
        cbar_kws={"label": "task"},
        square=False,
        annot_kws={"size": annot_fs},
    )
    ax.set_title(
        "Task completion (task) vs model × dimension — full98",
        fontsize=title_fs,
        pad=14,
    )
    ax.set_xlabel("Model", fontsize=label_fs)
    ax.set_ylabel("Dimension", fontsize=label_fs, labelpad=38)
    ax.tick_params(axis="y", labelsize=tick_fs)
    ax.tick_params(axis="x", labelsize=tick_fs)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    recolor_annots(ax, data, threshold=0.5)

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=tick_fs)
    cbar.set_label("task", fontsize=label_fs)

    base = HERE / "heatmap_task_by_model_dimension_axes_large"
    save_fig_png_pdf(fig, base)
    plt.close(fig)


def draw_safe_axes_large(df: pd.DataFrame) -> None:
    data = pivot(df, "safe")
    annot = data.map(lambda x: f"{x:.2f}")

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(15.0, 6.8))
    # Ensure extra left margin so the y-label can sit fully left.
    fig.subplots_adjust(left=0.22)

    # Use EXACT same formatting as task_axes_large.
    label_fs, tick_fs, title_fs, annot_fs = 22, 22, 19, 20
    sns.heatmap(
        data,
        ax=ax,
        cmap="RdPu",
        vmin=0.0,
        vmax=1.0,
        annot=annot,
        fmt="",
        linewidths=0.0,  # match original: no visible grid lines
        cbar_kws={"label": "safe"},
        square=False,
        annot_kws={"size": annot_fs},
    )
    ax.set_title(
        "Safety (safe) vs model × dimension — full98",
        fontsize=title_fs,
        pad=14,
    )
    ax.set_xlabel("Model", fontsize=label_fs)
    ax.set_ylabel("Dimension", fontsize=label_fs, labelpad=38)
    ax.tick_params(axis="y", labelsize=tick_fs)
    ax.tick_params(axis="x", labelsize=tick_fs)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    recolor_annots(ax, data, threshold=0.5)

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=tick_fs)
    cbar.set_label("safe", fontsize=label_fs)

    base = HERE / "heatmap_safe_by_model_dimension_axes_large"
    save_fig_png_pdf(fig, base)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(CSV)
    draw_safe_axes_large(df)
    draw_task_axes_large(df)


if __name__ == "__main__":
    main()

