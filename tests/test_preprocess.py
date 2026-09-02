import unittest

import numpy as np
from PIL import Image

from textbook_ocr.preprocess import PreprocessConfig, preprocess_image


class PreprocessTest(unittest.TestCase):
    def test_raw_mode_preserves_color_and_size(self):
        source = Image.new("RGBA", (120, 80), (10, 20, 30, 255))
        result = preprocess_image(source, PreprocessConfig(mode="raw", upscale_width=0))
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.size, source.size)

    def test_small_page_is_upscaled_for_ocr(self):
        source = Image.new("RGB", (800, 1000), "white")
        result = preprocess_image(source, PreprocessConfig(mode="raw", upscale_width=1600))
        self.assertEqual(result.size, (1600, 2000))

    def test_grayscale_mode_does_not_force_binarization(self):
        source = Image.new("L", (20, 20), 128)
        result = preprocess_image(
            source,
            PreprocessConfig(mode="grayscale", autocontrast=False),
        )
        self.assertEqual(result.getpixel((0, 0)), 128)

    def test_binary_mode_returns_only_black_and_white(self):
        source = Image.new("L", (20, 20), 128)
        result = preprocess_image(
            source,
            PreprocessConfig(mode="binary", threshold=127, autocontrast=False),
        )
        self.assertEqual(set(np.asarray(result).ravel()), {255})


if __name__ == "__main__":
    unittest.main()
