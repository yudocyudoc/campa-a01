"""A06 stdlib-only tests: runnable even in the minimal global smoke workflow."""
import math
import unittest

from experiments.A06.design import K0, PROBES, deterministic_selection, normalized_signals


class A06Tests(unittest.TestCase):
    def test_same_capacity_ratio_and_diff_are_identical_for_all_demand(self):
        for orders in (80.0, 90.0, 115.0, 140.0, 185.0):
            ratio, diff = normalized_signals(orders, K0)
            self.assertAlmostEqual(ratio, diff, places=12)

    def test_changing_capacity_exposes_difference_except_at_orders_equals_capacity(self):
        capacity = 90.0
        for orders in (95.0, 115.0, 140.0):
            ratio, diff = normalized_signals(orders, capacity)
            self.assertFalse(math.isclose(ratio, diff, abs_tol=1e-12))
        # A second exact algebraic equality surface exists: orders == capacity.
        same_at_balance = normalized_signals(capacity, capacity)
        self.assertAlmostEqual(same_at_balance[0], same_at_balance[1], places=12)

    def test_selection_is_deterministic_from_candidate_disagreement_only(self):
        table = [
            {"probe": p["id"], "kind": p["kind"],
             "candidate_disagreement": float(i)}
            for i, p in enumerate(PROBES)
        ]
        selected = deterministic_selection(table)
        self.assertEqual(len(selected), 4)
        self.assertEqual(len(set(selected)), 4)
        self.assertEqual(selected, deterministic_selection(table))
        self.assertTrue(all(
            next(p for p in PROBES if p["id"] == name)["kind"]
            in ("crossed", "transient") for name in selected
        ))

    def test_probe_catalog_includes_demand_capacity_crossings_and_time_pulses(self):
        self.assertEqual(len(PROBES), 23)
        kinds = {p["kind"] for p in PROBES}
        self.assertEqual(kinds, {"control", "demand_only", "crossed", "transient"})
        self.assertEqual(K0, 115.0)


if __name__ == "__main__":
    unittest.main()
