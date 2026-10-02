import json
import unittest
from pathlib import Path

from abtest import (
    peeking_false_positive_rate,
    sample_ratio_mismatch,
    sample_size_per_group,
    two_proportion_ztest,
)

CASES = json.loads((Path(__file__).parent / "cases.json").read_text(encoding="utf-8"))


class ReferenceCases(unittest.TestCase):
    """Shared with the JavaScript tests, so the browser calculator and this module agree."""

    def test_ztest(self):
        for c in CASES["ztest"]:
            with self.subTest(c["name"]):
                r = two_proportion_ztest(*c["args"])
                self.assertAlmostEqual(r.z, c["z"], delta=1e-3)
                self.assertAlmostEqual(r.p_value, c["p"], delta=5e-4)
                self.assertAlmostEqual(r.ci_low, c["ci_low"], delta=5e-4)
                self.assertAlmostEqual(r.ci_high, c["ci_high"], delta=5e-4)
                self.assertEqual(r.significant, c["significant"])

    def test_sample_size(self):
        for c in CASES["sample_size"]:
            with self.subTest(c["name"]):
                self.assertAlmostEqual(sample_size_per_group(c["baseline"], c["mde"]), c["expect"], delta=c["tolerance"])

    def test_sample_ratio_mismatch(self):
        for c in CASES["srm"]:
            with self.subTest(c["name"]):
                self.assertAlmostEqual(sample_ratio_mismatch(*c["args"]), c["p"], delta=5e-4)


class Behaviour(unittest.TestCase):
    def test_swapping_groups_flips_the_sign_but_not_the_p_value(self):
        a = two_proportion_ztest(200, 2000, 240, 2000)
        b = two_proportion_ztest(240, 2000, 200, 2000)
        self.assertAlmostEqual(a.z, -b.z)
        self.assertAlmostEqual(a.p_value, b.p_value)
        self.assertAlmostEqual(a.ci_low, -b.ci_high)

    def test_identical_groups_are_not_significant(self):
        r = two_proportion_ztest(50, 500, 50, 500)
        self.assertEqual(r.z, 0.0)
        self.assertEqual(r.p_value, 1.0)
        self.assertFalse(r.significant)

    def test_zero_conversions_everywhere_does_not_divide_by_zero(self):
        r = two_proportion_ztest(0, 100, 0, 100)
        self.assertEqual(r.p_value, 1.0)
        self.assertIsNone(r.rel_lift)

    def test_a_significant_result_has_a_confidence_interval_that_excludes_zero(self):
        r = two_proportion_ztest(200, 2000, 280, 2000)
        self.assertTrue(r.significant)
        self.assertGreater(r.ci_low, 0)

    def test_a_stricter_alpha_makes_a_borderline_result_not_significant(self):
        self.assertTrue(two_proportion_ztest(200, 2000, 240, 2000, alpha=0.05).significant)
        self.assertFalse(two_proportion_ztest(200, 2000, 240, 2000, alpha=0.01).significant)

    def test_smaller_effects_need_more_visitors(self):
        self.assertGreater(sample_size_per_group(0.10, 0.01), sample_size_per_group(0.10, 0.02))

    def test_higher_power_needs_more_visitors(self):
        self.assertGreater(sample_size_per_group(0.10, 0.02, power=0.9), sample_size_per_group(0.10, 0.02, power=0.8))

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            two_proportion_ztest(11, 10, 1, 10)
        with self.assertRaises(ValueError):
            two_proportion_ztest(1, 0, 1, 10)
        with self.assertRaises(ValueError):
            sample_size_per_group(0.10, 0.0)
        with self.assertRaises(ValueError):
            sample_size_per_group(0.99, 0.05)


class Simulation(unittest.TestCase):
    def test_a_single_look_keeps_the_false_positive_rate_near_alpha(self):
        rate = peeking_false_positive_rate(trials=4000, looks=1, per_look=1000, seed=11)
        self.assertGreater(rate, 0.035)
        self.assertLess(rate, 0.065)

    def test_peeking_ten_times_inflates_the_false_positive_rate(self):
        rate = peeking_false_positive_rate(trials=2000, looks=10, per_look=200, seed=11)
        self.assertGreater(rate, 0.12)  # nominally 5%, in practice close to 20%

    def test_the_simulation_is_reproducible(self):
        a = peeking_false_positive_rate(trials=300, seed=4)
        b = peeking_false_positive_rate(trials=300, seed=4)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
