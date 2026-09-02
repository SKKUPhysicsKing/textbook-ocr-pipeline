from __future__ import annotations

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
    supplied_engine = engine
    page_engine = engine or TesseractEngine(language=config.language, psm=config.psm)
    column_engine: OcrEngine | None = None
    output = Path(output_dir).expanduser().resolve()
    pages_dir = output / "pages"
    processed_dir = output / "processed"
    pages_dir.mkdir(parents=True, exist_ok=True)
    if config.save_processed:
        processed_dir.mkdir(parents=True, exist_ok=True)
    manifest_pages: list[dict[str, object]] = []
    combined: list[str] = []
    for index, page in enumerate(iter_pages(input_path, pdf_dpi=config.pdf_dpi), start=1):
        prepared = preprocess_image(page.image, config.preprocess)
        regions = split_page_regions(prepared, mode=config.layout)
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
        result = OcrResult(
            "\n\n".join(part.text for part in region_results if part.text).strip(),
            tuple(word for part in region_results for word in part.words),
        )
        warnings = _quality_warnings(page.image, result, config)
        stem = f"page_{index:04d}"
        text_path = pages_dir / f"{stem}.txt"
        json_path = pages_dir / f"{stem}.json"
        text_path.write_text(result.text + "\n", encoding="utf-8")
        page_payload = {"index": index, "source": str(page.source), "source_page": page.source_page, "width": prepared.width, "height": prepared.height, "mean_confidence": result.mean_confidence, "layout": "columns" if len(regions) > 1 else "single", "regions": region_payloads, "warnings": warnings, "text_file": str(text_path.relative_to(output)), "words": [word.to_dict() for word in result.words]}
        _write_json(json_path, page_payload)
        if config.save_processed:
            prepared.save(processed_dir / f"{stem}.png")
        manifest_pages.append(page_payload | {"json_file": str(json_path.relative_to(output))})
        combined.append(result.text)
    if not manifest_pages:
        raise ValueError("No pages were produced from the input.")
    (output / "combined.txt").write_text("\n\n\f\n\n".join(combined) + "\n", encoding="utf-8")
    manifest: dict[str, object] = {"created_at": datetime.now(timezone.utc).isoformat(), "input": str(Path(input_path).expanduser().resolve()), "output": str(output), "language": config.language, "psm": config.psm, "column_psm": config.column_psm, "pdf_dpi": config.pdf_dpi, "layout": config.layout, "preprocess": config.preprocess.mode, "page_count": len(manifest_pages), "pages": manifest_pages}
    _write_json(output / "manifest.json", manifest)
    return manifest
