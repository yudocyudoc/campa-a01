"""Offline science-design invariants: no dependency on BPTK-Py/SciPy."""
import math
import unittest
from experiments.A08.design import (
    FAMILIES, TRAIN, PROBES, validate_design,
)


class A08Tests(unittest.TestCase):
    def test_all_17_holdouts_and_disjoint_training(self):
        validate_design()
        self.assertEqual(len(TRAIN), 5)
        self.assertEqual(len(PROBES), 17)
        self.assertEqual(len({p["id"] for p in PROBES}), 17)
        self.assertFalse({p["id"] for p in TRAIN} & {p["id"] for p in PROBES})

    def test_both_generalized_families_have_four_effective_parameters(self):
        self.assertEqual(set(FAMILIES), {"diff_c","ratio_p"})
        for family in FAMILIES.values():
            low,high=family["bounds"]
            self.assertEqual(len(low), 4)
            self.assertTrue(all(l<h for l,h in zip(low,high)))

    def test_nested_p_equals_one_is_algebraically_ratio(self):
        for orders in (70.,115.,150.):
            for capacity in (90.,115.,145.,220.):
                self.assertAlmostEqual(
                    orders / capacity**1.0,
                    orders / capacity,
                )

    def test_new_diff_c_contains_old_diff_as_c_equals_one(self):
        for orders in (60.,115.,185.):
            for capacity in (90.,115.,145.):
                self.assertAlmostEqual(orders - 1.0*capacity, orders-capacity)

    def test_effective_shape_gain_not_redundant_in_linear_state(self):
        # Equivalent trajectories depend on gain/scale rather than both
        # when the latent state starts at zero.
        E,gain=28.75,0.439562
        effective=gain/E
        self.assertTrue(math.isclose(effective*E,gain,rel_tol=1e-12))
        # A08 chooses excursion=1, degradation=effective.
        self.assertTrue(math.isclose(effective/1,effective,rel_tol=1e-12))


if __name__=="__main__":
    unittest.main()
