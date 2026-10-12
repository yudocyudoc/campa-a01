"""A13 regression, integrity, and interpretation tests. Stdlib only."""
import ast
import hashlib
import json
import unittest
from pathlib import Path

from experiments.A11 import contract as c
from experiments.A13 import run as a13

class A13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fits, cls.snapshot = a13.inputs()
        cls.business = dict(c.BUSINESS)

    def test_permanent_evidence_sha256(self):
        root = Path(a13.__file__).parent
        manifest = json.loads((root/"evidence_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["experiment"], "A13")
        self.assertEqual(set(manifest["sha256"]), {"cases.csv", "sources.csv", "summary.json"})
        for name, expected in manifest["sha256"].items():
            actual = hashlib.sha256((root/"evidence"/name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, name)
        summary = json.loads((root/"evidence"/"summary.json").read_text(encoding="utf-8"))
        for name in ("cases.csv", "sources.csv"):
            self.assertEqual(summary["csv_sha256"][name], manifest["sha256"][name])

    def test_design_and_no_oracle_imports(self):
        self.assertEqual(len(a13.SHOCKS), 9)
        self.assertEqual(len(a13.KS), 35)
        self.assertEqual(a13.MULTIPLIERS, (0.50, 0.75, 1.25, 1.50))
        tree = ast.parse((Path(a13.__file__).parent/"run.py").read_text(encoding="utf-8"))
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                mods.append(node.module or "")
        self.assertFalse(any(
            x.startswith(("experiments.A08", "experiments.A11.adjudicate",
                          "experiments.A12.adjudicate"))
            for x in mods
        ))

    def test_full_a12_1260_forecasts_reproduced(self):
        self.assertEqual(
            a13.check_a12_anchor(self.fits, self.snapshot, self.business),
            1260,
        )

    def test_cross_family_and_missing_driver_reproduce_claude(self):
        fit = self.fits["noiseless"]["fit_by_family"]
        true_p = fit["ratio_p"]["params"]
        for shock, diff_regret, zero_regret in (
            (70., 937.604008, 21800.),
            (80., 2204.717172, 23500.),
        ):
            reference = a13.cash_curve(shock, "ratio_p", true_p, self.business, self.snapshot)
            rival = a13.cash_curve(shock, "diff_c", fit["diff_c"]["params"], self.business, self.snapshot)
            p0 = list(true_p)
            p0[2] = 0.0
            absent = a13.cash_curve(shock, "ratio_p", p0, self.business, self.snapshot)
            self.assertAlmostEqual(
                a13.score(reference, rival)["regret_under_nominal"], diff_regret, places=3
            )
            self.assertGreater(
                a13.score(reference, absent)["regret_under_nominal"], zero_regret
            )

    def test_fixed_cost_can_bias_cash_without_changing_policy(self):
        p = self.fits["noiseless"]["fit_by_family"]["ratio_p"]["params"]
        original = a13.cash_curve(70., "ratio_p", p, self.business, self.snapshot)
        changed = self.business.copy()
        changed["fixed_cost"] *= 1.5
        candidate = a13.cash_curve(70., "ratio_p", p, changed, self.snapshot)
        result = a13.score(original, candidate)
        self.assertEqual(result["regret_under_nominal"], 0.)
        self.assertEqual(result["chosen_k"], result["nominal_optimal_k"])
        self.assertGreater(abs(result["candidate_error_at_chosen"]), 10000.)

    def test_contract_globals_restored(self):
        initial_business = dict(c.BUSINESS)
        initial_options = c.OPTIONS
        initial_shock = c.MARKET_SHOCK_AT_T8
        p = self.fits["noiseless"]["fit_by_family"]["ratio_p"]["params"]
        changed = self.business.copy()
        changed["base_order_rate"] *= 0.75
        _ = a13.cash_curve(70., "ratio_p", p, changed, self.snapshot)
        self.assertEqual(dict(c.BUSINESS), initial_business)
        self.assertEqual(c.OPTIONS, initial_options)
        self.assertEqual(c.MARKET_SHOCK_AT_T8, initial_shock)

    def test_one_case_matrix_and_no_extra_threshold(self):
        rows = a13.experiments_for_case(
            "noiseless", 70., self.fits, self.snapshot, self.business
        )
        self.assertEqual(len(rows), 2+len(self.business)*4+4)
        self.assertTrue(all(row["regret_under_nominal"] >= 0 for row in rows))
        self.assertEqual(sum(row["category"] == "shock_uncertainty" for row in rows), 4)
        self.assertEqual(sum(row["category"] == "coefficient" for row in rows),
                         len(self.business)*4)

if __name__ == "__main__":
    unittest.main()
