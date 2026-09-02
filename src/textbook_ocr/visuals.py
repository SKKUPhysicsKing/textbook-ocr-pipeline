from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np
from PIL import Image, ImageFilter

from .models import OcrWord


VisualMode = Literal["off", "detect"]


@dataclass(frozen=True)
class VisualRegion:
    kind: Literal["table", "figure"]
    left: int
    top: int
    width: int
    height: int
    row_boundaries: tuple[int, ...] = ()
    column_boundaries: tuple[int, ...] = ()

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }
        if self.row_boundaries:
            payload["row_boundaries"] = list(self.row_boundaries)
        if self.column_boundaries:
            payload["column_boundaries"] = list(self.column_boundaries)
        return payload


@dataclass(frozen=True)
class _Line:
    position: int
    start: int
    stop: int


def _runs(values: np.ndarray) -> list[tuple[int, int]]:
    padded = np.pad(values.astype(np.int8), (1, 1))
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    stops = np.flatnonzero(changes == -1)
    return [(int(start), int(stop)) for start, stop in zip(starts, stops)]


def _long_lines(ink: np.ndarray, horizontal: bool, minimum_length: int) -> list[_Line]:
    scan = ink if horizontal else ink.T
    raw: list[_Line] = []
    for position, values in enumerate(scan):
        candidates = [(start, stop) for start, stop in _runs(values) if stop - start >= minimum_length]
        if candidates:
            start, stop = max(candidates, key=lambda item: item[1] - item[0])
            raw.append(_Line(position, start, stop))

    merged: list[_Line] = []
    for line in raw:
        if merged and line.position <= merged[-1].position + 2:
            previous = merged[-1]
            overlap = min(previous.stop, line.stop) - max(previous.start, line.start)
            shortest = min(previous.stop - previous.start, line.stop - line.start)
            if shortest > 0 and overlap / shortest >= 0.65:
                merged[-1] = _Line(
                    round((previous.position + line.position) / 2),
                    min(previous.start, line.start),
                    max(previous.stop, line.stop),
                )
                continue
        merged.append(line)
    return merged


def _cluster_positions(values: Iterable[int], tolerance: int = 4) -> tuple[int, ...]:
    ordered = sorted(values)
    if not ordered:
        return ()
    clusters: list[list[int]] = [[ordered[0]]]
    for value in ordered[1:]:
        if value - clusters[-1][-1] <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return tuple(round(sum(cluster) / len(cluster)) for cluster in clusters)


def detect_tables(image: Image.Image, min_area_ratio: float = 0.006) -> tuple[VisualRegion, ...]:
    """Detect ruled tables and recover their row/column separator positions.

    This deliberately targets tables with visible rules. Borderless tables are
    left to the text OCR rather than guessed, which keeps false positives low.
    """

    gray = np.asarray(image.convert("L"))
    height, width = gray.shape
    if width < 120 or height < 120:
        return ()
    ink = gray < 190
    horizontal = _long_lines(ink, True, max(30, round(width * 0.12)))
    vertical = _long_lines(ink, False, max(30, round(height * 0.06)))
    if len(horizontal) < 2 or len(vertical) < 2:
        return ()

    # Join horizontal and vertical rules that intersect. Each connected group
    # is a candidate grid, so separate tables on the same page stay separate.
    line_count = len(horizontal) + len(vertical)
    parents = list(range(line_count))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(first: int, second: int) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for h_index, h_line in enumerate(horizontal):
        for v_index, v_line in enumerate(vertical):
            if h_line.start - 3 <= v_line.position <= h_line.stop + 3 and v_line.start - 3 <= h_line.position <= v_line.stop + 3:
                union(h_index, len(horizontal) + v_index)

    groups: dict[int, tuple[list[_Line], list[_Line]]] = {}
    for index, line in enumerate(horizontal):
        groups.setdefault(find(index), ([], []))[0].append(line)
    for index, line in enumerate(vertical):
        groups.setdefault(find(len(horizontal) + index), ([], []))[1].append(line)

    tables: list[VisualRegion] = []
    for horizontal_group, vertical_group in groups.values():
        # A plain rectangular picture frame has two rules in each direction.
        # Requiring a third separator in either direction distinguishes a grid.
        if len(horizontal_group) < 2 or len(vertical_group) < 2:
            continue
        if len(horizontal_group) < 3 and len(vertical_group) < 3:
            continue
        rows = _cluster_positions(line.position for line in horizontal_group)
        columns = _cluster_positions(line.position for line in vertical_group)
        if len(rows) < 2 or len(columns) < 2:
            continue
        left, right = min(columns), max(columns)
        top, bottom = min(rows), max(rows)
        row_gaps = np.diff(rows)
        column_gaps = np.diff(columns)
        minimum_row_gap = max(8, round(height * 0.008))
        minimum_column_gap = max(8, round(width * 0.008))
        if row_gaps.min() < minimum_row_gap or column_gaps.min() < minimum_column_gap:
            continue
        # Grid rules must actually span most of the candidate table. This
        # rejects book edges joined transitively to underlines or text strokes.
        row_coverage = [float(ink[max(0, row - 1) : min(height, row + 2), left : right + 1].mean()) for row in rows]
        column_coverage = [float(ink[top : bottom + 1, max(0, column - 1) : min(width, column + 2)].mean()) for column in columns]
        strong_rows = sum(value >= 0.50 for value in row_coverage)
        strong_columns = sum(value >= 0.50 for value in column_coverage)
        if strong_rows < 2 or strong_columns < 2:
            continue
        if strong_rows < 3 and strong_columns < 3:
            continue
        if (right - left) * (bottom - top) < width * height * min_area_ratio:
            continue
        tables.append(
            VisualRegion(
                "table",
                left,
                top,
                right - left + 1,
                bottom - top + 1,
                tuple(value - top for value in rows),
                tuple(value - left for value in columns),
            )
        )
    return tuple(sorted(tables, key=lambda item: (item.top, item.left)))


def mask_regions(image: Image.Image, regions: Iterable[VisualRegion], padding: int = 2) -> Image.Image:
    array = np.asarray(image.convert("RGB")).copy()
    height, width = array.shape[:2]
    for region in regions:
        left = max(0, region.left - padding)
        top = max(0, region.top - padding)
        right = min(width, region.right + padding)
        bottom = min(height, region.bottom + padding)
        array[top:bottom, left:right] = 255
    return Image.fromarray(array, mode="RGB")


def _connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, int, int, int, int]] = []
    for start_y, start_x in zip(*np.nonzero(mask & ~seen)):
        if seen[start_y, start_x]:
            continue
        stack = [(int(start_x), int(start_y))]
        seen[start_y, start_x] = True
        left = right = int(start_x)
        top = bottom = int(start_y)
        count = 0
        while stack:
            x, y = stack.pop()
            count += 1
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            for next_x, next_y in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= next_x < width and 0 <= next_y < height and mask[next_y, next_x] and not seen[next_y, next_x]:
                    seen[next_y, next_x] = True
                    stack.append((next_x, next_y))
        components.append((left, top, right + 1, bottom + 1, count))
    return components


def _overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    first_area = max(1, (first[2] - first[0]) * (first[3] - first[1]))
    return intersection / first_area


def detect_figures(
    image: Image.Image,
    words: Iterable[OcrWord] = (),
    excluded: Iterable[VisualRegion] = (),
    min_area_ratio: float = 0.01,
) -> tuple[VisualRegion, ...]:
    """Find large non-text graphics after masking OCR words and table grids."""

    original_width, original_height = image.size
    if original_width < 120 or original_height < 120:
        return ()
    scale = min(1.0, 800 / original_width)
    preview_width = max(1, round(original_width * scale))
    preview_height = max(1, round(original_height * scale))
    preview = image.convert("L").resize((preview_width, preview_height), Image.Resampling.BILINEAR)
    ink = np.asarray(preview) < 205

    # Remove recognized prose. What remains is primarily plots, diagrams,
    # photographs and decorative rules. A margin also removes character edges.
    for word in words:
        margin = max(2, round(3 * scale))
        left = max(0, round(word.left * scale) - margin)
        top = max(0, round(word.top * scale) - margin)
        right = min(preview_width, round((word.left + word.width) * scale) + margin)
        bottom = min(preview_height, round((word.top + word.height) * scale) + margin)
        ink[top:bottom, left:right] = False
    for region in excluded:
        left, top = round(region.left * scale), round(region.top * scale)
        right, bottom = round(region.right * scale), round(region.bottom * scale)
        ink[max(0, top - 2) : min(preview_height, bottom + 2), max(0, left - 2) : min(preview_width, right + 2)] = False

    # Join nearby strokes so axes, curves and line-art become one component.
    dilated = Image.fromarray(ink.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))
    connected = np.asarray(dilated) > 0
    candidates: list[VisualRegion] = []
    for left, top, right, bottom, count in _connected_components(connected):
        box_width, box_height = right - left, bottom - top
        if box_width < preview_width * 0.12 or box_height < preview_height * 0.07:
            continue
        if count < preview_width * preview_height * min_area_ratio:
            continue
        if box_width > preview_width * 0.94 and box_height > preview_height * 0.94:
            continue
        original_box = (
            max(0, round(left / scale) - 4),
            max(0, round(top / scale) - 4),
            min(original_width, round(right / scale) + 4),
            min(original_height, round(bottom / scale) + 4),
        )
        if any(_overlap_ratio(original_box, region.box) > 0.15 for region in excluded):
            continue
        candidates.append(
            VisualRegion(
                "figure",
                original_box[0],
                original_box[1],
                original_box[2] - original_box[0],
                original_box[3] - original_box[1],
            )
        )
    return tuple(sorted(candidates, key=lambda item: (item.top, item.left)))
