from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import TesseractError
from .pipeline import PipelineConfig, run_pipeline
from .preprocess import PreprocessConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="textbook-ocr", description="Convert photographed textbook pages or PDFs to TXT and JSON.")
    parser.add_argument("input", type=Path, help="Image, PDF, or directory to process")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"))
    parser.add_argument("--lang", default="kor+eng", help="Tesseract languages")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract page segmentation mode")
    parser.add_argument("--pdf-dpi", type=int, default=300)
    parser.add_argument("--threshold", type=int, choices=range(0, 256), metavar="0-255")
    parser.add_argument("--no-deskew", action="store_true")
    parser.add_argument("--no-denoise", action="store_true")
    parser.add_argument("--save-processed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = PipelineConfig(language=args.lang, psm=args.psm, pdf_dpi=args.pdf_dpi, save_processed=args.save_processed, preprocess=PreprocessConfig(threshold=args.threshold, deskew=not args.no_deskew, denoise=not args.no_denoise))
    try:
        manifest = run_pipeline(args.input, args.output, config=config)
    except (FileNotFoundError, ValueError, TesseractError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(f"Processed {manifest['page_count']} page(s).")
    print(f"Output: {Path(args.output).expanduser().resolve()}")


if __name__ == "__main__":
    main()

