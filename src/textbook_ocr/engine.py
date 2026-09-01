from __future__ import annotations

import csv
import shutil
import subprocess
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from .models import OcrResult, OcrWord


class TesseractError(RuntimeError):
    pass


class TesseractEngine:
    def __init__(self, language: str = "kor+eng", psm: int = 3) -> None:
        self.language = language
        self.psm = psm

    def _executable(self) -> str:
        executable = shutil.which("tesseract")
        if executable is None:
            raise TesseractError("Tesseract was not found. Install Tesseract and ensure it is on PATH.")
        return executable

    def _check_languages(self, executable: str) -> None:
        completed = subprocess.run([executable, "--list-langs"], check=False, capture_output=True, text=True)
        available = {line.strip() for line in completed.stdout.splitlines()[1:] if line.strip()}
        missing = sorted(set(self.language.split("+")) - available)
        if missing:
            raise TesseractError("Missing Tesseract language data: " + ", ".join(missing))

    def recognize(self, image: Image.Image) -> OcrResult:
        executable = self._executable()
        self._check_languages(executable)
        with tempfile.TemporaryDirectory(prefix="textbook-ocr-") as temporary_dir:
            image_path = Path(temporary_dir) / "page.png"
            image.save(image_path)
            completed = subprocess.run([executable, str(image_path), "stdout", "-l", self.language, "--psm", str(self.psm), "tsv"], check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise TesseractError(completed.stderr.strip() or "Tesseract OCR failed.")
        return _parse_tsv(completed.stdout.splitlines())


def _parse_tsv(lines: Iterable[str]) -> OcrResult:
    reader = csv.DictReader(lines, delimiter="\t")
    words: list[OcrWord] = []
    grouped: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            block = int(row.get("block_num", "0"))
            paragraph = int(row.get("par_num", "0"))
            line = int(row.get("line_num", "0"))
            word = OcrWord(text, float(row.get("conf", "-1")), int(row.get("left", "0")), int(row.get("top", "0")), int(row.get("width", "0")), int(row.get("height", "0")), block, paragraph, line)
        except (TypeError, ValueError):
            continue
        words.append(word)
        grouped[(block, paragraph, line)].append(text)
    output_lines: list[str] = []
    previous_paragraph: tuple[int, int] | None = None
    for (block, paragraph, _line), tokens in grouped.items():
        current_paragraph = (block, paragraph)
        if previous_paragraph is not None and current_paragraph != previous_paragraph:
            output_lines.append("")
        output_lines.append(" ".join(tokens))
        previous_paragraph = current_paragraph
    return OcrResult("\n".join(output_lines).strip(), tuple(words))

