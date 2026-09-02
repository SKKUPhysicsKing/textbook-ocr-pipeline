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
    parser.add_argument("--lang", default="eng", help="Tesseract languages (use kor+eng for mixed Korean/English pages)")
    parser.add_argument("--psm", type=int, default=3, help="Tesseract page segmentation mode")
    parser.add_argument("--column-psm", type=int, default=6, help="Tesseract PSM used for detected columns")
    parser.add_argument("--pdf-dpi", type=int, default=300)
    parser.add_argument("--layout", choices=("auto", "single", "columns"), default="auto")
    parser.add_argument("--preprocess", choices=("raw", "grayscale", "binary"), default="raw")
    parser.add_argument("--upscale-width", type=int, default=0, help="Optionally upscale smaller pages to this width; 0 disables upscaling")
    parser.add_argument("--max-width", type=int, default=2400, help="Downscale pages wider than this; 0 disables resizing")
    parser.add_argument("--min-page-width", type=int, default=1600, help="Warn when an input page is narrower; 0 disables the warning")
    parser.add_argument("--low-confidence-threshold", type=float, default=70.0)
    parser.add_argument("--threshold", type=int, choices=range(0, 256), metavar="0-255")
    parser.add_argument("--deskew", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--save-processed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.threshold is not None and args.preprocess != "binary":
        parser.error("--threshold can only be used with --preprocess binary")
    config = PipelineConfig(
        language=args.lang,
        psm=args.psm,
        column_psm=args.column_psm,
        pdf_dpi=args.pdf_dpi,
        save_processed=args.save_processed,
        layout=args.layout,
        min_page_width=args.min_page_width,
        low_confidence_threshold=args.low_confidence_threshold,
        preprocess=PreprocessConfig(
            mode=args.preprocess,
            upscale_width=args.upscale_width,
            max_width=args.max_width,
            threshold=args.threshold,
            deskew=args.deskew,
            denoise=args.denoise,
        ),
    )
    try:
        manifest = run_pipeline(args.input, args.output, config=config)
    except (FileNotFoundError, ValueError, TesseractError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    print(f"Processed {manifest['page_count']} page(s).")
    print(f"Output: {Path(args.output).expanduser().resolve()}")
    for page in manifest["pages"]:
        for warning in page["warnings"]:
            print(f"warning: page {page['index']}: {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()
