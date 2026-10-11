"""A12 candidate-only gate contract and real closed-loop regression tests."""
import ast
import math
import unittest
from pathlib import Path

from experiments.A11.contract import forecast as original_forecast
from experiments.A12.design import (
    SHOCKS,CAPACITIES,ARMS,MATERIAL_FRACTION,MIN_SHOCK_COUNT,check_design
)
from experiments.A12.forecast import candidate_forecast,terminal_cash
from experiments.A12.gate import best_gains,nearest_capacity,pure_peak_demand_proxy,argmax_tolerant

ROOT=Path(__file__).resolve().parents[1]


class TestA12(unittest.TestCase):
    def snapshot(self):
        return {
            "t_decision":8,"customer_base":1048.,"backlog":0.,
            "receivables":18578.53125,"cash":-222.53125,
            "previous_effective_capacity":114.09650131034218,
            "previous_nominal_capacity":115.,
            "previous_incoming_orders":93.78,
        }

    def test_design_frozen(self):
        check_design()
        self.assertEqual(len(SHOCKS),9)
        self.assertEqual(len(CAPACITIES),35)
        self.assertEqual(len(ARMS),2)
        self.assertEqual(MATERIAL_FRACTION,0.05)
        self.assertEqual(MIN_SHOCK_COUNT,3)

    def test_generalized_candidate_matches_original_a11_at_all_original_policies(self):
        p=(0.8043657644788427,.6341171854167286,1.7582499650781587,
           .9999999999998082)
        q=(-16.25200177143108,.6254945424005154,.013841890725307456,
           .9317350878254456)
        for family,params in (("ratio_p",p),("diff_c",q)):
            for k in (90.,115.,145.,180.):
                a=candidate_forecast(k,50.,self.snapshot(),params,family)
                b=original_forecast(k,self.snapshot(),params,family)
                self.assertEqual(len(a),17)
                for j in range(len(a)):
                    for field in ("incoming_orders","effective_capacity",
                                  "backlog","customer_base","cash"):
                        self.assertAlmostEqual(a[j][field],b[j][field],places=6)
                self.assertEqual(terminal_cash(a),a[-1]["cash"])

    def test_regret_symmetric_and_disagreement_not_automatically_material(self):
        # ratio_p wants 145, diff_c wants 150. Both have a range of 200.
        # One loses 20 and the other loses 2, so 5% two-sided gate FAILS.
        m={
            "ratio_p":{k:0. for k in CAPACITIES},
            "diff_c":{k:0. for k in CAPACITIES},
        }
        m["ratio_p"].update({145.:200.,150.:180.,260.:10.})
        m["diff_c"].update({145.:198.,150.:200.,260.:10.})
        # Use small hand-coded menu to test gate algebra in isolation.
        x=best_gains(m,self.snapshot(),50.)
        self.assertFalse(x["same_policy"])
        self.assertAlmostEqual(x["fractional_wrong_choice_regret"]["ratio_p"],.10)
        self.assertAlmostEqual(x["fractional_wrong_choice_regret"]["diff_c"],.01)
        self.assertFalse(x["material_disagreement"])

    def test_two_sided_material_opportunity_is_recognized(self):
        m={
            "ratio_p":{k:0. for k in CAPACITIES},
            "diff_c":{k:0. for k in CAPACITIES},
        }
        m["ratio_p"].update({145.:200.,150.:180.,260.:10.})
        m["diff_c"].update({145.:180.,150.:200.,260.:10.})
        x=best_gains(m,self.snapshot(),50.)
        self.assertTrue(x["material_disagreement"])
        self.assertAlmostEqual(x["symmetric_material_fraction"],.10)
        self.assertEqual(x["best_policy"]["ratio_p"],145.)
        self.assertEqual(x["best_policy"]["diff_c"],150.)

    def test_naive_peak_uses_only_predecision_business_state(self):
        # In absence of backlog cancellation, customer_base 1048 grows by
        # 8 acquisitions - 2 churn per step, over 16 steps to t24.
        proxy=pure_peak_demand_proxy(self.snapshot(),50.)
        self.assertAlmostEqual(proxy,(1048.+16*6)*.09+50.)
        self.assertEqual(nearest_capacity(proxy),155.)
        self.assertEqual(argmax_tolerant({100.:200.,105.:200.+1e-7}),100.)

    def test_no_world_access_from_candidate_scan(self):
        files=("experiments/A12/design.py","experiments/A12/forecast.py",
               "experiments/A12/gate.py")
        for file in files:
            tree=ast.parse((ROOT/file).read_text(encoding="utf-8"))
            imports=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    imports.extend(x.name for x in n.names)
                elif isinstance(n,ast.ImportFrom):
                    imports.append(n.module or "")
            self.assertFalse(any(x.startswith((
                "experiments.A08","experiments.A09",
                "experiments.A11.adjudicate","experiments.A12.adjudicate",
            )) for x in imports),file)

    def test_out_of_menu_and_inactivity_can_be_scored(self):
        p=(0.8043657644788427,.6341171854167286,1.7582499650781587,1.)
        with self.assertRaises(ValueError):
            candidate_forecast(125.,50.,self.snapshot(),p,"ratio_p")
        with self.assertRaises(ValueError):
            candidate_forecast(145.,55.,self.snapshot(),p,"ratio_p")


if __name__=="__main__":
    unittest.main()
