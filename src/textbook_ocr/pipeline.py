from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from PIL import Image

from .engine import TesseractEngine
from .layout import LayoutMode, split_page_regions
from .models import OcrResult, OcrWord
from .preprocess import PreprocessConfig, preprocess_image
from .sources import iter_pages
from .visuals import VisualMode, VisualRegion, detect_figures, detect_tables, mask_regions


class OcrEngine(Protocol):
    def recognize(self, image: Image.Image) -> OcrResult: ...


@dataclass(frozen=True)
class PipelineConfig:
    language: str = "eng"
    psm: int = 3
    column_psm: int = 6
    pdf_dpi: int = 300
    save_processed: bool = False
    layout: LayoutMode = "auto"
    min_page_width: int = 1600
    low_confidence_threshold: float = 70.0
    visuals: VisualMode = "detect"
    table_psm: int = 6
    figure_psm: int = 11
    min_visual_area_ratio: float = 0.01
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _offset_result(result: OcrResult, left: int, top: int) -> OcrResult:
    words = tuple(
        OcrWord(
            word.text,
            word.confidence,
            word.left + left,
            word.top + top,
            word.width,
            word.height,
            word.block,
            word.paragraph,
            word.line,
        )
        for word in result.words
    )
    return OcrResult(result.text, words)


def _text_from_words(words: tuple[OcrWord, ...]) -> str:
    if not words:
        return ""
    parts: list[str] = []
    previous: tuple[int, int, int] | None = None
    for word in words:
        current = (word.block, word.paragraph, word.line)
        if previous is not None:
            if current[:2] != previous[:2]:
                parts.append("\n\n")
            elif current[2] != previous[2]:
                parts.append("\n")
            else:
                parts.append(" ")
        parts.append(word.text)
        previous = current
    return "".join(parts).strip()


def _filter_result(result: OcrResult, excluded: tuple[VisualRegion, ...]) -> OcrResult:
    if not excluded:
        return result
    words = tuple(
        word
        for word in result.words
        if not any(
            region.left <= word.left + word.width / 2 <= region.right
            and region.top <= word.top + word.height / 2 <= region.bottom
            for region in excluded
        )
    )
    return OcrResult(_text_from_words(words), words)


def _cell_box(region: VisualRegion, row: int, column: int) -> tuple[int, int, int, int]:
    left = region.left + region.column_boundaries[column] + 2
    right = region.left + region.column_boundaries[column + 1] - 2
    top = region.top + region.row_boundaries[row] + 2
    bottom = region.top + region.row_boundaries[row + 1] - 2
    return left, top, max(left + 1, right), max(top + 1, bottom)


def _extract_table(image: Image.Image, region: VisualRegion, engine: OcrEngine) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in range(len(region.row_boundaries) - 1):
        values: list[str] = []
        for column in range(len(region.column_boundaries) - 1):
            cell = image.crop(_cell_box(region, row, column))
            text = engine.recognize(cell).text
            values.append(" ".join(text.split()))
        rows.append(values)
    return rows


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        csv.writer(handle).writerows(rows)


def _markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    escaped = [[cell.replace("|", "\\|").replace("\n", " ") for cell in row] for row in normalized]
    output = ["| " + " | ".join(escaped[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    output.extend("| " + " | ".join(row) + " |" for row in escaped[1:])
    return "\n".join(output)


def _caption_near(region: VisualRegion, words: tuple[OcrWord, ...], page_height: int) -> str:
    candidates = [
        word
        for word in words
        if region.bottom <= word.top <= region.bottom + page_height * 0.08
        and word.left + word.width >= region.left
        and word.left <= region.right
    ]
    if not candidates:
        return ""
    first_line = candidates[0].line
    line = " ".join(word.text for word in candidates if word.line == first_line).strip()
    return line if re.match(r"^(fig(?:ure)?\.?|table)\s*\d*", line, re.IGNORECASE) else ""


def _quality_warnings(image: Image.Image, result: OcrResult, config: PipelineConfig) -> list[str]:
    warnings: list[str] = []
    if config.min_page_width > 0 and image.width < config.min_page_width:
        warnings.append(
            f"low_resolution: page width is {image.width}px; "
            f"at least {config.min_page_width}px is recommended"
        )
    if result.mean_confidence is not None and result.mean_confidence < config.low_confidence_threshold:
        warnings.append(
            f"low_confidence: mean word confidence is {result.mean_confidence:.1f}; "
            f"review results below {config.low_confidence_threshold:.1f}"
        )
    if config.language == "eng" and re.search(r"[가-힣]", result.text):
        warnings.append("unexpected_script: Hangul was detected while using the English model")
    if any("\t" in word.text or "\r" in word.text or "\n" in word.text for word in result.words):
        warnings.append("invalid_token: an OCR token contains a control character")
    return warnings


def run_pipeline(input_path: str | Path, output_dir: str | Path, config: PipelineConfig | None = None, engine: OcrEngine | None = None) -> dict[str, object]:
    config = config or PipelineConfig()
    if config.visuals not in {"off", "detect"}:
        raise ValueError(f"Unsupported visuals mode: {config.visuals}")
    if not 0 < config.min_visual_area_ratio <= 1:
        raise ValueError("min_visual_area_ratio must be greater than 0 and no greater than 1")
    supplied_engine = engine
    page_engine = engine or TesseractEngine(language=config.language, psm=config.psm)
    column_engine: OcrEngine | None = None
    table_engine: OcrEngine | None = None
    figure_engine: OcrEngine | None = None
    output = Path(output_dir).expanduser().resolve()
    pages_dir = output / "pages"
    processed_dir = output / "processed"
    pages_dir.mkdir(parents=True, exist_ok=True)
    if config.save_processed:
        processed_dir.mkdir(parents=True, exist_ok=True)
    manifest_pages: list[dict[str, object]] = []
    combined: list[str] = []
    combined_markdown: list[str] = []
    for index, page in enumerate(iter_pages(input_path, pdf_dpi=config.pdf_dpi), start=1):
        prepared = preprocess_image(page.image, config.preprocess)
        tables = detect_tables(prepared, min_area_ratio=config.min_visual_area_ratio) if config.visuals == "detect" else ()
        body_image = mask_regions(prepared, tables) if tables else prepared
        regions = split_page_regions(body_image, mode=config.layout)
        if len(regions) > 1 and supplied_engine is None and column_engine is None:
            column_engine = TesseractEngine(language=config.language, psm=config.column_psm)
        active_engine = column_engine or page_engine
        region_payloads: list[dict[str, object]] = []
        region_results: list[OcrResult] = []
        for region in regions:
            region_result = active_engine.recognize(region.image)
            shifted = _offset_result(region_result, region.left, region.top)
            region_results.append(shifted)
            region_payloads.append(
                {
                    "role": region.role,
                    "left": region.left,
                    "top": region.top,
                    "width": region.image.width,
                    "height": region.image.height,
                    "mean_confidence": region_result.mean_confidence,
                }
            )
        preliminary = OcrResult(
            "\n\n".join(part.text for part in region_results if part.text).strip(),
            tuple(word for part in region_results for word in part.words),
        )
        figures = (
            detect_figures(
                prepared,
                preliminary.words,
                excluded=tables,
                min_area_ratio=config.min_visual_area_ratio,
            )
            if config.visuals == "detect"
            else ()
        )
        filtered_parts = [_filter_result(part, figures) for part in region_results]
        result = OcrResult(
            "\n\n".join(part.text for part in filtered_parts if part.text).strip(),
            tuple(word for part in filtered_parts for word in part.words),
        )
        warnings = _quality_warnings(page.image, result, config)
        stem = f"page_{index:04d}"
        text_path = pages_dir / f"{stem}.txt"
        json_path = pages_dir / f"{stem}.json"
        markdown_path = pages_dir / f"{stem}.md"
        visual_payloads: list[dict[str, object]] = []
        plain_parts = [result.text] if result.text else []
        markdown_parts = [result.text] if result.text else []
        if tables or figures:
            assets_dir = output / "assets" / stem
            assets_dir.mkdir(parents=True, exist_ok=True)
        if tables:
            if table_engine is None:
                table_engine = supplied_engine or TesseractEngine(language=config.language, psm=config.table_psm)
            for visual_index, table in enumerate(tables, start=1):
                name = f"table_{visual_index:03d}"
                image_path = assets_dir / f"{name}.png"
                csv_path = assets_dir / f"{name}.csv"
                prepared.crop(table.box).save(image_path)
                rows = _extract_table(prepared, table, table_engine)
                _write_csv(csv_path, rows)
                plain_table = "\n".join("\t".join(row) for row in rows)
                plain_parts.append(f"[TABLE {visual_index}]\n{plain_table}".rstrip())
                markdown_parts.append(f"## Table {visual_index}\n\n{_markdown_table(rows)}".rstrip())
                visual_payloads.append(
                    table.to_dict()
                    | {
                        "index": visual_index,
                        "image_file": str(image_path.relative_to(output)),
                        "csv_file": str(csv_path.relative_to(output)),
                        "rows": rows,
                    }
                )
        if figures:
            if figure_engine is None:
                figure_engine = supplied_engine or TesseractEngine(language=config.language, psm=config.figure_psm)
            for visual_index, figure in enumerate(figures, start=1):
                name = f"figure_{visual_index:03d}"
                image_path = assets_dir / f"{name}.png"
                figure_text_path = assets_dir / f"{name}.txt"
                crop = prepared.crop(figure.box)
                crop.save(image_path)
                embedded_text = figure_engine.recognize(crop).text.strip()
                figure_text_path.write_text(embedded_text + ("\n" if embedded_text else ""), encoding="utf-8")
                caption = _caption_near(figure, preliminary.words, prepared.height)
                description = "\n".join(part for part in (caption, embedded_text) if part)
                plain_parts.append(f"[FIGURE {visual_index}]\n{description}".rstrip())
                relative_image = image_path.relative_to(output).as_posix()
                markdown_parts.append(
                    f"## Figure {visual_index}\n\n![Figure {visual_index}]({relative_image})"
                    + (f"\n\n{description}" if description else "")
                )
                visual_payloads.append(
                    figure.to_dict()
                    | {
                        "index": visual_index,
                        "image_file": str(image_path.relative_to(output)),
                        "text_file": str(figure_text_path.relative_to(output)),
                        "caption": caption,
                        "embedded_text": embedded_text,
                    }
                )
        page_text = "\n\n".join(part for part in plain_parts if part).strip()
        page_markdown = "\n\n".join(part for part in markdown_parts if part).strip()
        text_path.write_text(page_text + "\n", encoding="utf-8")
        markdown_path.write_text(page_markdown + "\n", encoding="utf-8")
        page_payload = {"index": index, "source": str(page.source), "source_page": page.source_page, "width": prepared.width, "height": prepared.height, "mean_confidence": result.mean_confidence, "layout": "columns" if len(regions) > 1 else "single", "regions": region_payloads, "visuals": visual_payloads, "warnings": warnings, "text_file": str(text_path.relative_to(output)), "markdown_file": str(markdown_path.relative_to(output)), "words": [word.to_dict() for word in result.words]}
        _write_json(json_path, page_payload)
        if config.save_processed:
            prepared.save(processed_dir / f"{stem}.png")
        manifest_pages.append(page_payload | {"json_file": str(json_path.relative_to(output))})
        combined.append(page_text)
        combined_markdown.append(page_markdown)
    if not manifest_pages:
        raise ValueError("No pages were produced from the input.")
    (output / "combined.txt").write_text("\n\n\f\n\n".join(combined) + "\n", encoding="utf-8")
    (output / "combined.md").write_text("\n\n---\n\n".join(combined_markdown) + "\n", encoding="utf-8")
    manifest: dict[str, object] = {"created_at": datetime.now(timezone.utc).isoformat(), "input": str(Path(input_path).expanduser().resolve()), "output": str(output), "language": config.language, "psm": config.psm, "column_psm": config.column_psm, "pdf_dpi": config.pdf_dpi, "layout": config.layout, "preprocess": config.preprocess.mode, "visuals": config.visuals, "table_psm": config.table_psm, "figure_psm": config.figure_psm, "page_count": len(manifest_pages), "pages": manifest_pages}
    _write_json(output / "manifest.json", manifest)
    return manifest
