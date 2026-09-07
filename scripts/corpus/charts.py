"""Matplotlib chart rendering shared by reports and decks.

Every chart pins its own metadata so PNG bytes are stable across runs;
matplotlib otherwise stamps a software string that can vary by version.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_PNG_METADATA = {"Software": "corpus-gen"}
_ACCENT = "#3b5bdb"
_MUTED = "#868e96"
_ALERT = "#e03131"


def _save(fig: "plt.Figure", path: Path) -> None:
    fig.savefig(path, dpi=150, metadata=_PNG_METADATA, bbox_inches="tight")
    plt.close(fig)


def bar_chart(
    path: Path,
    categories: list[str],
    values: list[float],
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(categories, values, color=_ACCENT)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    _save(fig, path)


def line_chart(
    path: Path,
    x_labels: list[str],
    series: dict[str, list[float]],
    title: str,
    ylabel: str,
) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    colors = [_ACCENT, _MUTED, _ALERT]
    for i, (name, values) in enumerate(series.items()):
        ax.plot(x_labels, values, marker="o", label=name, color=colors[i % 3])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    if len(series) > 1:
        ax.legend(frameon=False)
    fig.tight_layout()
    _save(fig, path)


def funnel_chart(path: Path, stages: list[str], values: list[float]) -> None:
    """Horizontal funnel: widest bar first, no axis numbers restated as text.

    Labels sit above each bar in ink, not inside it, so a narrow late-stage
    bar never clips white-on-color text.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    max_val = max(values)
    for i, (stage, value) in enumerate(zip(stages, values)):
        width = value / max_val
        left = (1 - width) / 2
        ax.barh(i, width, left=left, height=0.6, color=_ACCENT, alpha=1 - i * 0.12)
        ax.text(0.5, i - 0.45, stage, ha="center", va="bottom",
                color="#18181b", fontsize=13)
    ax.set_xlim(0, 1)
    ax.set_ylim(len(stages) - 0.3, -0.7)
    ax.axis("off")
    fig.tight_layout()
    _save(fig, path)


def pie_chart(path: Path, labels: list[str], values: list[float], title: str) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    colors = [_ACCENT, _MUTED, _ALERT, "#f08c00", "#2f9e44"]
    ax.pie(values, labels=labels, colors=colors[: len(labels)], autopct="%1.0f%%")
    ax.set_title(title)
    fig.tight_layout()
    _save(fig, path)
