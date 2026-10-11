"""Unit tests for audit reproduction checks, independent of BPTK-Py."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments" / "A04"))
from experiments.A04.verify_reproduction import (  # noqa: E402
    HISTORICAL, TOP_OUTPUTS, WORLD_IDS, WORLD_OUTPUT, audit, is_true
)


def write_rows(path, fields, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        w = csv.DictWriter(stream, fieldnames=fields)
        w.writeheader()
        w.writerows(records)


def fixture(folder):
    ref = HISTORICAL["summary"]
    for name in TOP_OUTPUTS:
        (folder / name).write_text("placeholder\n", encoding="utf-8")
    write_rows(folder / "all_probe_class_separability.csv",
               ("case_id", "true_primitive", "truth_class_is_best"),
               [{"case_id": world, "true_primitive": family, "truth_class_is_best": i < 9}
                for i, (world, family) in enumerate(zip(
                    WORLD_IDS,
                    ["accumulation"] * 3 + ["smooth_delay"] * 3 +
                    ["reinforcing"] * 3 + ["pipeline_delay"] * 3
                ))])
    write_rows(folder / "global_vs_class_separation.csv", ("case_id",),
               [{"case_id": w} for w in WORLD_IDS])
    write_rows(folder / "feature_equivalence_pairs.csv", ("feature_a", "feature_b"),
               [{"feature_a": "a", "feature_b": "b"}] * ref["feature_equivalent_pairs"])
    write_rows(folder / "static_target_dependency.csv",
               ("feature_id", "uses_target_directly"),
               [{"feature_id": name, "uses_target_directly": True}
                for name in HISTORICAL["direct_target_feature_ids"]] +
               [{"feature_id": f"other_{i}", "uses_target_directly": False}
                for i in range(ref["n_expressions"] - 3)])
    write_rows(folder / "reinforcing_transfer_grid.csv", ("regime",),
               [{"regime": "stable_first_order"}] * 12 +
               [{"regime": "net_reinforcing"}] * 4)
    write_rows(folder / "target_proxy_audit.csv", ("case_id",),
               [{"case_id": w} for w in WORLD_IDS for _ in range(10 * 57)])
    for world in WORLD_IDS:
        p = folder / world / WORLD_OUTPUT
        p.parent.mkdir()
        p.write_text("synthetic fixture\n", encoding="utf-8")


class A04AdjudicationTests(unittest.TestCase):
    def test_reference_reproduction_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            fixture(path)
            result = audit(path)
            self.assertEqual(result["reproduction_status"], "REPRODUCED", result["issues"])
            self.assertEqual(result["scientific_verdict"], "NOT_ISSUED_ORIGINAL_A1_IS_DIAGNOSTIC")

    def test_feature_equivalence_count_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            fixture(path)
            with (path / "feature_equivalence_pairs.csv").open("a", encoding="utf-8") as stream:
                stream.write("a,b\n")
            result = audit(path)
            self.assertEqual(result["reproduction_status"], "NOT_REPRODUCED")
            self.assertTrue(any("feature_equivalent_pairs" in x for x in result["issues"]))

    def test_unknown_scientific_status_is_not_inferred(self):
        self.assertTrue(is_true("True"))
        self.assertFalse(is_true("UNRESOLVED"))
        with tempfile.TemporaryDirectory() as d:
            result = audit(Path(d))
            self.assertEqual(result["reproduction_status"], "NOT_REPRODUCED")
            self.assertEqual(result["scientific_verdict"], "NOT_ISSUED_ORIGINAL_A1_IS_DIAGNOSTIC")


if __name__ == "__main__":
    unittest.main()
