import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
