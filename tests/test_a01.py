"""Offline A01 checks; intentionally independent of GitHub and Cloudflare."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "A01"))
from experiment import CONDITIONS, DT_DAYS, HORIZON_DAYS, MECHANISMS, run_experiment, simulate, stable_hash


class A01Tests(unittest.TestCase):
    def test_distinct_rules_same_initial_state(self):
        constant = simulate(MECHANISMS[0], CONDITIONS["baseline"])
        responsive = simulate(MECHANISMS[1], CONDITIONS["baseline"])
        self.assertEqual(len(constant), HORIZON_DAYS)
        self.assertEqual(constant[0]["inventory_before_pan"], 100.0)
        self.assertEqual(responsive[0]["inventory_before_pan"], 100.0)
        self.assertNotEqual(constant[-1]["inventory_after_pan"], responsive[-1]["inventory_after_pan"])

    def test_balance_nonnegative_and_reproducible(self):
        for mechanism in MECHANISMS:
            for stock in CONDITIONS.values():
                first = simulate(mechanism, stock)
                self.assertEqual(stable_hash(first), stable_hash(simulate(mechanism, stock)))
                for day in first:
                    self.assertGreaterEqual(day["inventory_after_pan"], 0.0)
                    expected = day["inventory_before_pan"] + DT_DAYS * (
                        day["production_pan_per_day"] - day["sales_pan_per_day"] - day["waste_pan_per_day"]
                    )
                    self.assertAlmostEqual(day["inventory_after_pan"], expected)

    def test_shock_only_changes_initial_stock(self):
        for mechanism in MECHANISMS:
            baseline = simulate(mechanism, CONDITIONS["baseline"])
            shocked = simulate(mechanism, CONDITIONS["initial_stock_plus_10"])
            self.assertEqual(shocked[0]["inventory_before_pan"] - baseline[0]["inventory_before_pan"], 10.0)
            for before, after in zip(baseline, shocked):
                self.assertEqual(before["production_pan_per_day"], after["production_pan_per_day"])

    def test_manifest_and_csv_are_emitted(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            manifest = run_experiment(output)
            saved = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, manifest)
            self.assertEqual(len(saved["scenarios"]), 4)
            self.assertTrue((output / "trajectories.csv").is_file())
            self.assertEqual(saved["status"], "TECHNICAL_SMOKE_NOT_CAUSAL_VALIDATION")


if __name__ == "__main__":
    unittest.main()
