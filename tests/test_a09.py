"""A09 mathematical necessary-condition and state-classifier tests (stdlib only)."""
import math
import unittest

from experiments.A09.regimes import (
    activation_regime, output_regime, identify_regime,
    world_excess, diff_c_excess, beta, world_slope_at_k,
    cross_k_slope_obstruction, distinct_values,
)


class A09AnalyticTests(unittest.TestCase):
    def test_world_stress_matches_original_ratio_threshold(self):
        theta=0.217463
        for k in (90.,115.,145.,220.):
            for d in (70.,90.,115.,150.,210.):
                original=max((d/k-0.75)/0.25-theta,0.0)
                self.assertAlmostEqual(world_excess(d,k,theta),original,places=12)
        self.assertAlmostEqual(beta(theta),0.80436575,places=7)

    def test_rival_effective_threshold_and_shape(self):
        d,k,c,tau=125.,115.,1.0070633,-24.75272
        expected=max(d-c*k-tau,0.)
        self.assertAlmostEqual(diff_c_excess(d,k,c,tau),expected)

    def test_conditional_obstruction_requires_two_k_and_positive_gain(self):
        gain=0.439562
        condition=cross_k_slope_obstruction([115.,145.],gain)
        self.assertTrue(condition["conditional_model_level_obstruction"])
        required=condition["required_single_rival_gain_by_K"]
        self.assertGreater(required["115.0"],required["145.0"])
        self.assertAlmostEqual(required["115.0"],4*gain/115.)
        self.assertFalse(condition["certificate_for_actual_finite_A08_observations"]
                         if "certificate_for_actual_finite_A08_observations" in condition else False)
        self.assertFalse(cross_k_slope_obstruction([115.,115.],gain)["conditional_model_level_obstruction"])
        with self.assertRaises(ValueError):
            cross_k_slope_obstruction([115.,145.],0.)

    def test_activity_and_clipping_are_orthogonal(self):
        self.assertEqual(activation_regime(0.),"inactive")
        self.assertEqual(activation_regime(0.03),"active")
        self.assertEqual(output_regime(0.60,0.40),"clipped")
        self.assertEqual(output_regime(0.10,0.40),"unclipped")
        self.assertEqual(identify_regime(0.2,0.7,0.4),{
            "input_state":"active","output_state":"clipped",
            "active_unclipped":False,
        })
        self.assertEqual(identify_regime(0.2,0.2,0.4)["active_unclipped"],True)
        # A latent state may remain clipped after the forcing turns inactive.
        self.assertEqual(identify_regime(0.,0.8,0.4)["input_state"],"inactive")
        self.assertEqual(identify_regime(0.,0.8,0.4)["output_state"],"clipped")

    def test_nested_ratio_power_reproduces_weighted_world_forcing(self):
        # Not causal discovery: p=1 algebraically CONTAINS the WORLD.
        theta=0.217463058
        world_gain=0.4395624912697545
        tau=beta(theta)
        nested_gain=4.0*world_gain
        for k in (90.,115.,145.,180.,220.):
            for d in (60.,90.,120.,150.,210.,260.):
                world_forcing=world_gain*world_excess(d,k,theta)
                nested_forcing=nested_gain*max(d/(k**1.0)-tau,0.0)
                self.assertAlmostEqual(world_forcing,nested_forcing,places=12)

    def test_slope_scaling_of_ratio_power_requires_p_one_for_two_k(self):
        k1,k2=115.,145.
        world_gain=0.4395624912697545
        # For equality on open active demand intervals, slopes must match.
        for p in (0.8,1.2):
            implied_gain_k1=world_slope_at_k(k1,world_gain)*k1**p
            implied_gain_k2=world_slope_at_k(k2,world_gain)*k2**p
            self.assertFalse(math.isclose(implied_gain_k1,implied_gain_k2,rel_tol=1e-10))
        implied_gain_k1=world_slope_at_k(k1,world_gain)*k1
        implied_gain_k2=world_slope_at_k(k2,world_gain)*k2
        self.assertAlmostEqual(implied_gain_k1,implied_gain_k2,places=12)

    def test_sparse_demand_is_not_an_open_interval_certificate(self):
        self.assertEqual(distinct_values([115.,115.000000000001,132.,132.]),2)
        self.assertAlmostEqual(world_slope_at_k(145.,0.439562),4*0.439562/145.)

if __name__=="__main__":
    unittest.main()
