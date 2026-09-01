from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class PageInput:
    source: Path
    source_page: int
    image: Image.Image


@dataclass(frozen=True)
class OcrWord:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int
    block: int
    paragraph: int
    line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OcrResult:
    text: str
    words: tuple[OcrWord, ...]

    @property
    def mean_confidence(self) -> float | None:
        values = [word.confidence for word in self.words if word.confidence >= 0]
        return sum(values) / len(values) if values else None

