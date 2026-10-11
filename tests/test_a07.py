"""A07 prospective split/selection invariants; standard library only."""
import math
import unittest

from experiments.A07.design import (
    BOUNDS, CAPACITIES, HOLDOUTS, K0, MAX_SELECTED, MAX_NFEV_PER_START,
    TRAINING, select_diverse_holdouts, validate_disjointness,
)


class A07DesignTests(unittest.TestCase):
    def test_disjoint_training_and_holdouts(self):
        validate_disjointness()
        self.assertEqual(len(TRAINING["fixed_capacity"]), 3)
        self.assertEqual(len(TRAINING["cross_capacity"]), 5)
        self.assertEqual(len(HOLDOUTS), 17)
        self.assertEqual({p["capacity"] for p in HOLDOUTS if p["kind"] == "cross_holdout"}, set(CAPACITIES))
        self.assertTrue(all(p["capacity"] == K0 for p in TRAINING["fixed_capacity"]))

    def test_selector_uses_only_candidate_disagreement_and_balances_strata(self):
        rows = [
            {"probe": p["id"], "stratum": p["stratum"], "candidate_disagreement": float(i + 1)}
            for i, p in enumerate(HOLDOUTS)
        ]
        selected = select_diverse_holdouts(rows)
        self.assertEqual(len(selected), MAX_SELECTED)
        self.assertEqual(len(selected), len(set(selected)))
        self.assertEqual(len({next(p["stratum"] for p in HOLDOUTS if p["id"] == name)
                              for name in selected}), MAX_SELECTED)
        self.assertEqual(selected, select_diverse_holdouts(rows))

    def test_selector_rejects_invalid_predictions(self):
        for invalid in (math.nan, -0.1):
            with self.assertRaises(ValueError):
                select_diverse_holdouts([{
                    "probe": "probe", "stratum": "stratum",
                    "candidate_disagreement": invalid
                }])

    def test_fixed_parameter_bounds_and_optimizer_budget(self):
        lows, highs = BOUNDS
        self.assertEqual(len(lows), 4)
        self.assertTrue(all(l < u for l, u in zip(lows, highs)))
        self.assertGreater(MAX_NFEV_PER_START, 0)


if __name__ == "__main__":
    unittest.main()
