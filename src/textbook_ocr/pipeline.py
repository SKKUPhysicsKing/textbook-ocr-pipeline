from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from PIL import Image

from .engine import TesseractEngine
from .models import OcrResult
from .preprocess import PreprocessConfig, preprocess_image
from .sources import iter_pages


class OcrEngine(Protocol):
    def recognize(self, image: Image.Image) -> OcrResult: ...


@dataclass(frozen=True)
class PipelineConfig:
    language: str = "kor+eng"
    psm: int = 3
    pdf_dpi: int = 300
    save_processed: bool = False
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_pipeline(input_path: str | Path, output_dir: str | Path, config: PipelineConfig | None = None, engine: OcrEngine | None = None) -> dict[str, object]:
    config = config or PipelineConfig()
    engine = engine or TesseractEngine(language=config.language, psm=config.psm)
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
        result = engine.recognize(prepared)
        stem = f"page_{index:04d}"
        text_path = pages_dir / f"{stem}.txt"
        json_path = pages_dir / f"{stem}.json"
        text_path.write_text(result.text + "\n", encoding="utf-8")
        page_payload = {"index": index, "source": str(page.source), "source_page": page.source_page, "width": prepared.width, "height": prepared.height, "mean_confidence": result.mean_confidence, "text_file": str(text_path.relative_to(output)), "words": [word.to_dict() for word in result.words]}
        _write_json(json_path, page_payload)
        if config.save_processed:
            prepared.save(processed_dir / f"{stem}.png")
        manifest_pages.append(page_payload | {"json_file": str(json_path.relative_to(output))})
        combined.append(result.text)
    if not manifest_pages:
        raise ValueError("No pages were produced from the input.")
    (output / "combined.txt").write_text("\n\n\f\n\n".join(combined) + "\n", encoding="utf-8")
    manifest: dict[str, object] = {"created_at": datetime.now(timezone.utc).isoformat(), "input": str(Path(input_path).expanduser().resolve()), "output": str(output), "language": config.language, "psm": config.psm, "pdf_dpi": config.pdf_dpi, "page_count": len(manifest_pages), "pages": manifest_pages}
    _write_json(output / "manifest.json", manifest)
    return manifest

