import unittest

from PIL import Image, ImageDraw

from textbook_ocr.layout import detect_column_gutter, split_page_regions


class LayoutTest(unittest.TestCase):
    def _two_column_page(self) -> Image.Image:
        image = Image.new("L", (1000, 800), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((100, 25, 900, 45), fill="black")
        for top in range(120, 740, 25):
            draw.rectangle((60, top, 430, top + 8), fill="black")
            draw.rectangle((570, top, 940, top + 8), fill="black")
        return image

    def test_detects_center_gutter(self):
        detected = detect_column_gutter(self._two_column_page())
        self.assertIsNotNone(detected)
        gutter, body_top = detected or (0, 0)
        self.assertTrue(450 <= gutter <= 550)
        self.assertTrue(40 <= body_top <= 120)

    def test_splits_header_then_left_and_right_columns(self):
        regions = split_page_regions(self._two_column_page(), mode="auto")
        self.assertEqual([region.role for region in regions], ["header", "left_column", "right_column"])
        self.assertEqual(regions[1].left, 0)
        self.assertGreater(regions[2].left, 0)

    def test_single_mode_never_splits(self):
        regions = split_page_regions(self._two_column_page(), mode="single")
        self.assertEqual(len(regions), 1)


if __name__ == "__main__":
    unittest.main()
