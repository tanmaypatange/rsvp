import unittest

import tests  # noqa: F401
import bands


class WilsonBand(unittest.TestCase):
    def test_doc_examples_reproduce_in_rounded_percent(self):
        # The five checks named in the kit design.
        cases = {(4, 10): (17, 69), (12, 30): (25, 58), (0, 30): (0, 11),
                 (30, 30): (89, 100), (103, 349): (25, 35)}
        for (k, n), expected in cases.items():
            with self.subTest(k=k, n=n):
                self.assertEqual(bands.band_pct(k, n), expected)

    def test_doc_run_count_table(self):
        # The "what does a run count buy" table on the Runs and sample size page.
        table = {
            (1, 10): (2, 40), (3, 10): (11, 60), (5, 10): (24, 76), (7, 10): (40, 89),
            (3, 30): (3, 26), (9, 30): (17, 48), (15, 30): (33, 67), (21, 30): (52, 83),
            (10, 100): (6, 17), (30, 100): (22, 40), (50, 100): (40, 60), (70, 100): (60, 78),
            (36, 360): (7, 14), (108, 360): (25, 35), (180, 360): (45, 55), (252, 360): (65, 75),
        }
        for (k, n), expected in table.items():
            with self.subTest(k=k, n=n):
                self.assertEqual(bands.band_pct(k, n), expected)

    def test_doc_headline_examples(self):
        # Sample report headline figures: visibility, mention and citation bands.
        self.assertEqual(bands.band_pct(120, 349), (30, 40))
        self.assertEqual(bands.band_pct(98, 346), (24, 33))
        self.assertEqual(bands.band_pct(182, 348), (47, 57))
        self.assertEqual(bands.band_pct(70, 349), (16, 25))

    def test_band_stays_inside_0_and_1(self):
        for n in (1, 2, 5, 30):
            for k in range(n + 1):
                lo, hi = bands.wilson(k, n)
                self.assertTrue(0.0 <= lo <= k / n <= hi <= 1.0)

    def test_no_band_without_valid_runs(self):
        with self.assertRaises(ValueError):
            bands.wilson(0, 0)

    def test_half_up_rounding(self):
        self.assertEqual(bands.pct(0.125), 13)
        self.assertEqual(bands.pct(0.135), 14)

    def test_overlap_rule(self):
        self.assertTrue(bands.bands_overlap((103, 349), (82, 345)))   # 25 to 35 and 20 to 29
        self.assertFalse(bands.bands_overlap((150, 348), (66, 346)))  # 38 to 48 and 15 to 24


class OtherStatistics(unittest.TestCase):

    def test_jaccard(self):
        self.assertEqual(bands.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        self.assertIsNone(bands.jaccard(set(), set()))
        self.assertAlmostEqual(bands.mean_pairwise_jaccard([["a"], ["a"], []]), (1 + 0 + 0) / 3)
        self.assertIsNone(bands.mean_pairwise_jaccard([[], []]))

    def test_cell_classes(self):
        self.assertEqual(bands.cell_class(0, 30), "never")
        self.assertEqual(bands.cell_class(1, 30), "rarely")
        self.assertEqual(bands.cell_class(9, 30), "flipping")    # exactly 30%
        self.assertEqual(bands.cell_class(21, 30), "flipping")   # exactly 70%
        self.assertEqual(bands.cell_class(22, 30), "mostly")
        self.assertEqual(bands.cell_class(29, 30), "mostly")
        self.assertEqual(bands.cell_class(30, 30), "always")
        self.assertIsNone(bands.cell_class(0, 0))

    def test_rotation_cut(self):
        self.assertFalse(bands.rotates(1, 10))   # 10% is not more than 10%
        self.assertTrue(bands.rotates(2, 10))
        self.assertTrue(bands.rotates(8, 10))
        self.assertFalse(bands.rotates(9, 10))   # 90% is not fewer than 90%


if __name__ == "__main__":
    unittest.main()
