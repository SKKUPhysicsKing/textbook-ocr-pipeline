import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from textbook_ocr.models import OcrResult, OcrWord
from textbook_ocr.pipeline import PipelineConfig, run_pipeline
from textbook_ocr.preprocess import PreprocessConfig


class FakeEngine:
    def recognize(self, image: Image.Image) -> OcrResult:
        return OcrResult("test page", (OcrWord("test", 99.0, 0, 0, 10, 10, 1, 1, 1),))


class PipelineTest(unittest.TestCase):
    def test_writes_text_json_and_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "page.png"
            output = root / "output"
            Image.new("RGB", (120, 80), "white").save(source)
            config = PipelineConfig(save_processed=True, preprocess=PreprocessConfig(deskew=False, denoise=False))
            manifest = run_pipeline(source, output, config=config, engine=FakeEngine())
            self.assertEqual(manifest["page_count"], 1)
            self.assertEqual((output / "combined.txt").read_text().strip(), "test page")
            self.assertTrue((output / "processed" / "page_0001.png").exists())
            saved = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["pages"][0]["mean_confidence"], 99.0)
            self.assertEqual(saved["pages"][0]["layout"], "single")
            self.assertTrue(saved["pages"][0]["warnings"][0].startswith("low_resolution:"))
            self.assertEqual(saved["preprocess"], "raw")
            self.assertEqual(saved["visuals"], "detect")
            self.assertTrue((output / "combined.md").exists())

    def test_exports_table_image_csv_and_structured_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "table.png"
            output = root / "output"
            image = Image.new("RGB", (600, 400), "white")
            draw = ImageDraw.Draw(image)
            for x in (100, 300, 500):
                draw.line((x, 80, x, 280), fill="black", width=3)
            for y in (80, 180, 280):
                draw.line((100, y, 500, y), fill="black", width=3)
            image.save(source)

            manifest = run_pipeline(source, output, engine=FakeEngine())

            visual = manifest["pages"][0]["visuals"][0]
            self.assertEqual(visual["kind"], "table")
            self.assertEqual(len(visual["rows"]), 2)
            self.assertTrue((output / visual["image_file"]).exists())
            self.assertTrue((output / visual["csv_file"]).exists())
            self.assertIn("## Table 1", (output / "combined.md").read_text(encoding="utf-8"))

    def test_exports_figure_image_and_embedded_text(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "figure.png"
            output = root / "output"
            image = Image.new("RGB", (600, 400), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((160, 80, 440, 300), outline="black", width=5)
            draw.line((170, 280, 250, 180, 330, 240, 430, 100), fill="black", width=7)
            draw.ellipse((260, 130, 350, 220), outline="black", width=6)
            image.save(source)

            manifest = run_pipeline(
                source,
                output,
                config=PipelineConfig(min_visual_area_ratio=0.003),
                engine=FakeEngine(),
            )

            visual = manifest["pages"][0]["visuals"][0]
            self.assertEqual(visual["kind"], "figure")
            self.assertEqual(visual["embedded_text"], "test page")
            self.assertTrue((output / visual["image_file"]).exists())
            self.assertTrue((output / visual["text_file"]).exists())
            self.assertIn("![Figure 1]", (output / "combined.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
