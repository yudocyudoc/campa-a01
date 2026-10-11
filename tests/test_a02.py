"""Unit checks for archived C0.0 result adjudication, without BPTK-Py."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "A02"))
from verify_reproduction import CHECKS, EXPECTED, EXPECTED_OUTPUTS, validate


def write_data(directory, *, mismatch=False, missing_gate=False):
    for filename in EXPECTED_OUTPUTS:
        (directory / filename).write_text("example\n", encoding="utf-8")
    with (directory / "gate_c00.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "pass"])
        writer.writeheader()
        for check in CHECKS[: -1 if missing_gate else None]:
            writer.writerow({"check": check, "pass": True})
    keys = ("scenario", *next(iter(EXPECTED.values())).keys())
    fields = ["scenario", *sorted({key for row in EXPECTED.values() for key in row})]
    with (directory / "scenario_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for scenario, row in EXPECTED.items():
            values = {"scenario": scenario, **row}
            if mismatch and scenario == "baseline":
                values["cash_final"] = 10000
            writer.writerow(values)


class ReproductionValidatorTests(unittest.TestCase):
    def test_exact_archived_checks_and_numeric_anchors_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            write_data(path)
            result = validate(path)
            self.assertEqual(result["status"], "REPRODUCED")
            self.assertEqual(result["observed_pass_count"], 14)
            self.assertEqual(result["numerical_matches"], result["numerical_anchor_count"])

    def test_numeric_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            write_data(path, mismatch=True)
            result = validate(path)
            self.assertEqual(result["status"], "NOT_REPRODUCED")
            self.assertTrue(any("Numeric mismatch" in problem for problem in result["issues"]))

    def test_missing_original_check_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            write_data(path, missing_gate=True)
            result = validate(path)
            self.assertEqual(result["status"], "NOT_REPRODUCED")
            self.assertTrue(any("Gate names/count" in problem for problem in result["issues"]))


if __name__ == "__main__":
    unittest.main()
