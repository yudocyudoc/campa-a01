"""Offline tests: A03 must not silently weaken its historical adjudicator."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "experiments" / "A03"))
from verify_reproduction import (  # noqa: E402
    CASE_FILES, EXPECTED_COUNTS, NUMERIC_ANCHORS,
    REFERENCE_PATH, TOP_FILES, verify,
)


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_fixture(directory, ref):
    expected = ref["cases"]
    fields = ("case_id", "true_primitive", "predicted_primitive", "winner_feature", "primary_outcome")
    write_csv(directory / "generalization_summary.csv", fields, expected)
    for name in TOP_FILES:
        if name == "generalization_summary.csv":
            continue
        (directory / name).write_text("placeholder\n", encoding="utf-8")
    write_csv(directory / "protocol_gate.csv", ("check", "pass"),
              [{"check": f"gate{i}", "pass": True} for i in range(6)])
    for name, values in NUMERIC_ANCHORS.items():
        write_csv(directory / name, tuple(values), [values])
    for case in expected:
        case_dir = directory / case["case_id"]
        case_dir.mkdir()
        for name in CASE_FILES:
            (case_dir / name).write_text("placeholder\n", encoding="utf-8")


class G5ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))

    def test_historical_fixture_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_fixture(root, self.reference)
            res = verify(root, self.reference)
            self.assertEqual(res["status"], "REPRODUCED", res["issues"])
            self.assertEqual(res["exact_case_matches"], 40)
            self.assertEqual(res["outcomes"]["COMMIT_WRONG"], 25)

    def test_changed_case_is_rejected_even_if_totals_same(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_fixture(root, self.reference)
            path = root / "generalization_summary.csv"
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rows[0]["winner_feature"] = "fabricated"
            write_csv(path, tuple(rows[0]), rows)
            res = verify(root, self.reference)
            self.assertEqual(res["status"], "NOT_REPRODUCED")
            self.assertTrue(res["case_differences"])

    def test_no_invented_abstention(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_fixture(root, self.reference)
            path = root / "generalization_summary.csv"
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            rows[0]["primary_outcome"] = "ABSTAIN"
            write_csv(path, tuple(rows[0]), rows)
            res = verify(root, self.reference)
            self.assertEqual(res["status"], "NOT_REPRODUCED")
            self.assertIn("ABSTAIN", res["outcomes"])


if __name__ == "__main__":
    unittest.main()
