#!/usr/bin/env python3
"""
Write axis-font-enlarged copies of heatmaps without modifying the original PNGs.

Outputs:
  heatmap_safe_by_model_dimension_axes_large.png
  heatmap_mean_steps_by_model_dimension_axes_large.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
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


def draw_safe_axes_large() -> None:
    df = pd.read_csv(CSV)
    safe = pivot(df, "safe")
    annot = safe.map(lambda x: f"{x:.2f}")

    label_fs, tick_fs, title_fs = 18, 15, 17

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(15.0, 6.8))

    sns.heatmap(
        safe,
        ax=ax,
        cmap="Purples",
        vmin=0.0,
        vmax=1.0,
        annot=annot,
        fmt="",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "safe", "shrink": 0.85},
        square=False,
        annot_kws={"size": 9},
    )
    ax.set_title(
        "Safety (safe) vs model × dimension — full98",
        fontsize=title_fs,
        pad=14,
    )
    ax.set_xlabel("Model", fontsize=label_fs)
    ax.set_ylabel("Dimension", fontsize=label_fs)
    ax.tick_params(axis="y", labelsize=tick_fs)
    ax.tick_params(axis="x", labelsize=tick_fs)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=tick_fs)
    cbar.set_label("safe", fontsize=label_fs)

    out = HERE / "heatmap_safe_by_model_dimension_axes_large.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


def draw_mean_steps_axes_large() -> None:
    df = pd.read_csv(CSV)
    steps = pivot(df, "mean_steps")
    annot = steps.map(lambda x: f"{x:.2f}")

    vmin = float(np.nanmin(steps.values))
    vmax = float(np.nanmax(steps.values))

    label_fs, tick_fs, title_fs = 18, 15, 17

    sns.set_theme(style="white")
    fig, ax = plt.subplots(figsize=(15.0, 6.8))

    sns.heatmap(
        steps,
        ax=ax,
        cmap="Oranges",
        vmin=vmin,
        vmax=vmax,
        annot=annot,
        fmt="",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "steps", "shrink": 0.85},
        square=False,
        annot_kws={"size": 9},
    )
    ax.set_title(
        "Steps vs model × dimension — full98",
        fontsize=title_fs,
        pad=14,
    )
    ax.set_xlabel("Model", fontsize=label_fs)
    ax.set_ylabel("Dimension", fontsize=label_fs)
    ax.tick_params(axis="y", labelsize=tick_fs)
    ax.tick_params(axis="x", labelsize=tick_fs)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=tick_fs)
    cbar.set_label("steps", fontsize=label_fs)
    span = vmax - vmin
    if span >= 8:
        cbar.ax.yaxis.set_major_locator(mticker.MultipleLocator(2.0))
    elif span >= 2:
        cbar.ax.yaxis.set_major_locator(mticker.MaxNLocator(nbins=8))

    out = HERE / "heatmap_mean_steps_by_model_dimension_axes_large.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    draw_safe_axes_large()
    draw_mean_steps_axes_large()


if __name__ == "__main__":
    main()
