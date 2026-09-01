from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import fitz
from PIL import Image

from .models import PageInput


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def _load_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return image.copy()


def _pdf_pages(path: Path, dpi: int) -> Iterator[PageInput]:
    scale = dpi / 72.0
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            yield PageInput(path, page_number, image)


def iter_pages(input_path: str | Path, pdf_dpi: int = 300) -> Iterator[PageInput]:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input does not exist: {path}")
    if path.is_dir():
        candidates = sorted(candidate for candidate in path.rglob("*") if candidate.is_file() and (candidate.suffix.lower() in IMAGE_SUFFIXES or candidate.suffix.lower() == ".pdf"))
        if not candidates:
            raise ValueError(f"No supported images or PDFs found in: {path}")
        for candidate in candidates:
            yield from iter_pages(candidate, pdf_dpi=pdf_dpi)
        return
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        yield PageInput(path, 1, _load_image(path))
    elif suffix == ".pdf":
        yield from _pdf_pages(path, dpi=pdf_dpi)
    else:
        raise ValueError(f"Unsupported input type: {suffix or '(no extension)'}")

