import unittest

from textbook_ocr.engine import _parse_tsv


class ParseTsvTest(unittest.TestCase):
    def test_reconstructs_lines_and_confidence(self):
        tsv = [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t95.0\tHello",
            "5\t1\t1\t1\t1\t2\t35\t10\t20\t10\t85.0\tworld",
            "5\t1\t1\t2\t1\t1\t10\t30\t20\t10\t75.0\tNext",
        ]
        result = _parse_tsv(tsv)
        self.assertEqual(result.text, "Hello world\n\nNext")
        self.assertEqual(len(result.words), 3)
        self.assertAlmostEqual(result.mean_confidence or 0, 85.0)

    def test_unmatched_quote_does_not_merge_tsv_rows(self):
        tsv = [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t90.0\t\"throughput",
            "5\t1\t1\t1\t1\t2\t35\t10\t20\t10\t80.0\tnext",
        ]
        result = _parse_tsv(tsv)
        self.assertEqual([word.text for word in result.words], ['"throughput', "next"])
        self.assertFalse(any("\t" in word.text or "\n" in word.text for word in result.words))


if __name__ == "__main__":
    unittest.main()
