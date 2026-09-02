import unittest

from PIL import Image, ImageDraw

from textbook_ocr.visuals import detect_figures, detect_tables


class VisualDetectionTest(unittest.TestCase):
    def test_detects_ruled_table_and_cell_boundaries(self):
        image = Image.new("RGB", (600, 400), "white")
        draw = ImageDraw.Draw(image)
        for x in (100, 300, 500):
            draw.line((x, 80, x, 280), fill="black", width=3)
        for y in (80, 180, 280):
            draw.line((100, y, 500, y), fill="black", width=3)

        tables = detect_tables(image)

        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0].row_boundaries), 3)
        self.assertEqual(len(tables[0].column_boundaries), 3)
        self.assertAlmostEqual(tables[0].left, 100, delta=3)
        self.assertAlmostEqual(tables[0].top, 80, delta=3)

    def test_detects_large_non_text_figure(self):
        image = Image.new("RGB", (600, 400), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((160, 80, 440, 300), outline="black", width=5)
        draw.line((170, 280, 250, 180, 330, 240, 430, 100), fill="black", width=7)
        draw.ellipse((260, 130, 350, 220), outline="black", width=6)

        figures = detect_figures(image, min_area_ratio=0.003)

        self.assertEqual(len(figures), 1)
        self.assertLessEqual(figures[0].left, 160)
        self.assertGreaterEqual(figures[0].right, 440)


if __name__ == "__main__":
    unittest.main()
