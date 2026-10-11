"""A11 executable closed-loop tests; no BPTK needed."""
import ast,unittest
from pathlib import Path
from experiments.A11.contract import (forecast,select_policy,OPTIONS,BASELINE,
                                      DECISION_T,HORIZON_T,SCORING_VARS)

ROOT=Path(__file__).resolve().parents[1]


class A11ProspectiveTests(unittest.TestCase):
    def snapshot(self):
        return {"t_decision":8,
                "customer_base":1048.,"backlog":0.,"receivables":18000.,
                "cash":25000.,"previous_effective_capacity":115.,
                "previous_nominal_capacity":115.,"previous_incoming_orders":90.}

    def test_closed_loop_endogenous_orders_respond_to_intervention(self):
        snap=self.snapshot()
        params=(0.8,.6,1.75,1.)
        low=forecast(90.,snap,params,"ratio_p")
        high=forecast(180.,snap,params,"ratio_p")
        self.assertEqual(len(low),17)
        self.assertEqual([r["t"] for r in low],list(range(8,25)))
        # First month demand shares pre-decision customer base.
        self.assertAlmostEqual(low[0]["incoming_orders"],high[0]["incoming_orders"])
        # Backlog / cancellations feed back into customer base and FUTURE orders.
        self.assertNotAlmostEqual(low[-1]["incoming_orders"],high[-1]["incoming_orders"])
        self.assertNotAlmostEqual(low[-1]["backlog"],high[-1]["backlog"])
        self.assertNotAlmostEqual(low[-1]["cash"],high[-1]["cash"])

    def test_no_future_orders_needed_at_all(self):
        params=(0.8,.6,1.75,1.)
        output=forecast(145.,self.snapshot(),params,"ratio_p")
        for row in output:
            self.assertIn("incoming_orders",row)
            self.assertIn("cash",row)
            self.assertIn("customer_base",row)
            self.assertTrue(row["effective_capacity"]>=.4*row["nominal_capacity"])
        with self.assertRaises(ValueError):
            forecast(250.,self.snapshot(),params,"ratio_p")

    def test_abstain_no_policy_change_and_terminal_cash_order(self):
        snap=self.snapshot()
        parms=(0.8,.6,1.75,1.)
        menu={k:forecast(k,snap,parms,"ratio_p") for k in OPTIONS}
        self.assertEqual(select_policy({},"ABSTAIN_UNRESOLVED"),BASELINE)
        selected=select_policy(menu,"ratio_p")
        self.assertIn(selected,OPTIONS)
        self.assertEqual(menu[selected][-1]["cash"],max(v[-1]["cash"] for v in menu.values()))

    def test_latent_clipping_makes_predecision_state_unidentifiable(self):
        clipped=self.snapshot()
        clipped["previous_effective_capacity"]=.4*115
        with self.assertRaisesRegex(ValueError,"not identifiable"):
            forecast(145.,clipped,(0.8,.6,1.75,1.),"ratio_p")

    def test_analyst_imports_no_oracle_and_has_no_intervention_world_reader(self):
        tree=ast.parse((ROOT/"experiments/A11/analyst.py").read_text(encoding="utf-8"))
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            elif isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
        self.assertFalse(any(x.startswith(("experiments.A08","experiments.A09"))
                             for x in imports))
        self.assertNotIn("experiments.A11.adjudicate",imports)


if __name__=="__main__":
    unittest.main()
