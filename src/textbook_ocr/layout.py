from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image


LayoutMode = Literal["auto", "single", "columns"]


@dataclass(frozen=True)
class ImageRegion:
    image: Image.Image
    left: int
    top: int
    role: str


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    window = max(1, min(window, len(values)))
    kernel = np.ones(window, dtype=np.float64) / window
    return np.convolve(values, kernel, mode="same")


def _spanning_header_boundary(gray: np.ndarray) -> int:
    """Find a horizontal rule that separates a full-width chapter header."""

    height, width = gray.shape
    last_rule_row = -1
    for row_index, row in enumerate(gray[: round(height * 0.12)]):
        dark = row < 190
        padded = np.pad(dark.astype(np.int8), (1, 1))
        transitions = np.diff(padded)
        starts = np.flatnonzero(transitions == 1)
        stops = np.flatnonzero(transitions == -1)
        longest_run = int((stops - starts).max()) if starts.size else 0
        if longest_run >= width * 0.45:
            last_rule_row = row_index
    if last_rule_row < 0:
        return 0
    return min(height - 1, last_rule_row + max(5, height // 200))


def detect_column_gutter(image: Image.Image) -> tuple[int, int] | None:
    """Return ``(gutter_x, body_top)`` when a two-column body is detected."""

    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    if width < 400 or height < 300:
        return None

    body_top = _spanning_header_boundary(gray)
    analysis_top = body_top or round(height * 0.05)
    body_bottom = max(analysis_top + 1, round(height * 0.96))
    body = gray[analysis_top:body_bottom]
    column_ink = (255.0 - body.astype(np.float32)).mean(axis=0)
    smoothed = _smooth(column_ink, max(9, width // 80))

    search_start = round(width * 0.35)
    search_stop = round(width * 0.65)
    central = smoothed[search_start:search_stop]
    minimum = float(central.min())

    left_band = smoothed[round(width * 0.15) : round(width * 0.35)]
    right_band = smoothed[round(width * 0.65) : round(width * 0.85)]
    if left_band.size == 0 or right_band.size == 0:
        return None
    text_ink = min(float(np.median(left_band)), float(np.median(right_band)))
    # Photographed books often show faint text from the reverse side inside the
    # gutter, so the gutter is not perfectly white. A 0.8 ratio still rejects
    # ordinary single-column whitespace while accepting realistic book photos.
    if text_ink <= 0 or minimum > text_ink * 0.80:
        return None

    # Pick the middle of the broadest low-ink run instead of one arbitrary edge
    # of a flat gutter. This leaves balanced whitespace around both columns.
    low = np.flatnonzero(central <= minimum + max(0.5, text_ink * 0.05))
    runs: list[tuple[int, int]] = []
    run_start = int(low[0])
    previous = run_start
    for value in low[1:]:
        current = int(value)
        if current != previous + 1:
            runs.append((run_start, previous))
            run_start = current
        previous = current
    runs.append((run_start, previous))
    center = (width / 2) - search_start
    best_start, best_end = max(runs, key=lambda run: (run[1] - run[0], -abs((run[0] + run[1]) / 2 - center)))
    gutter = search_start + round((best_start + best_end) / 2)
    return gutter, body_top


def split_page_regions(image: Image.Image, mode: LayoutMode = "auto") -> tuple[ImageRegion, ...]:
    if mode not in {"auto", "single", "columns"}:
        raise ValueError(f"Unsupported layout mode: {mode}")
    if mode == "single":
        return (ImageRegion(image, 0, 0, "page"),)

    detected = detect_column_gutter(image)
    if detected is None:
        if mode == "auto":
            return (ImageRegion(image, 0, 0, "page"),)
        detected = (image.width // 2, 0)

    gutter, body_top = detected
    left = image.crop((0, body_top, gutter, image.height))
    right = image.crop((gutter, body_top, image.width, image.height))
    columns = (
        ImageRegion(left, 0, body_top, "left_column"),
        ImageRegion(right, gutter, body_top, "right_column"),
    )
    if body_top == 0:
        return columns
    header = image.crop((0, 0, image.width, body_top))
    return (ImageRegion(header, 0, 0, "header"),) + columns
