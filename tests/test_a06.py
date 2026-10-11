"""A06 tests for precommitted candidate normalization and probe design."""
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "experiments" / "A06"
sys.path.insert(0, str(HERE))
from experiment import (  # noqa: E402
    K0, PROBES, REPAIRS, RATIO_ID, DIFF_ID,
    deterministic_selection, normalized_signals, TRUTH, PRIMITIVE,
)


class A06Tests(unittest.TestCase):
    def test_same_capacity_ratio_and_diff_are_algebraically_identical(self):
        for orders in (80.0, 90.0, 115.0, 140.0, 185.0):
            ratio, diff = normalized_signals(orders, K0)
            self.assertAlmostEqual(ratio, diff, places=12)

    def test_crossing_capacity_breaks_affine_mapping_for_fixed_pair(self):
        for orders in (90.0, 115.0, 140.0):
            ratio, diff = normalized_signals(orders, 90.0)
            self.assertFalse(math.isclose(ratio, diff, abs_tol=1e-12))

    def test_selected_probes_not_from_world_and_precommitted(self):
        table = [
            {"probe": p["id"], "kind": p["kind"],
             "candidate_disagreement": float(i)}
            for i, p in enumerate(PROBES)
        ]
        selected = deterministic_selection(table)
        self.assertEqual(len(selected), 4)
        self.assertTrue(all(
            next(p for p in PROBES if p["id"] == name)["kind"]
            in ("crossed", "transient") for name in selected
        ))
        self.assertEqual(len(set(selected)), 4)

    def test_uses_original_g5_truth_and_identical_primitive_parameters(self):
        self.assertEqual(PRIMITIVE, "first_order_relaxation")
        self.assertTrue(all(
            REPAIRS[RATIO_ID][name] == REPAIRS[DIFF_ID][name]
            for name in TRUTH["truth"]
        ))
        self.assertNotEqual(REPAIRS[RATIO_ID]["baseline"], REPAIRS[DIFF_ID]["baseline"])


if __name__ == "__main__":
    unittest.main()
