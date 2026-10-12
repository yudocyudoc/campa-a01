"""A14 offline controls: A12 continuity, ablations, minimax and no WORLD."""
import ast
import hashlib
import json
import math
import unittest
from pathlib import Path

from experiments.A11 import contract as a11
from experiments.A14 import run as a14


class A14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fits, cls.snapshot = a14.inputs()

    def test_archived_evidence_sha256(self):
        folder = Path(a14.__file__).parent
        m = json.loads((folder/"evidence_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["experiment"], "A14")
        self.assertFalse(m["world_evaluated"])
        for name, expected in m["original_sha256"].items():
            data = (folder/"evidence"/name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected, name)
        summary = json.loads((folder/"evidence"/"summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["cases"], 180)
        self.assertEqual(summary["a12_ratio_p_anchor_predictions"], 630)
        for name in ("policies.csv", "summary.csv"):
            self.assertEqual(summary["output_sha256"][name], m["original_sha256"][name])

    def test_design_and_closed_candidate_only_dependencies(self):
        self.assertEqual(len(a14.CAPACITIES), 35)
        self.assertEqual(len(a14.SHOCKS), 9)
        self.assertEqual(a14.STRESS_POINTS, 201)
        self.assertEqual(a14.STRESS_RELATIVE, .25)
        self.assertEqual(len(a14.MODELS), 5)
        tree = ast.parse(Path(a14.__file__).read_text(encoding="utf-8"))
        imports = []
        for x in ast.walk(tree):
            if isinstance(x, ast.Import):
                imports.extend(a.name for a in x.names)
            if isinstance(x, ast.ImportFrom):
                imports.append(x.module or "")
        self.assertFalse(any(
            x.startswith(("experiments.A08", "experiments.A11.adjudicate",
                          "experiments.A12.adjudicate"))
            for x in imports
        ))

    def test_full_reference_reproduces_all_630_a12_ratio_predictions(self):
        self.assertEqual(a14.check_a12_full_anchor(self.fits, self.snapshot), 630)

    def test_full_configuration_restored(self):
        before = (a11.OPTIONS, a11.MARKET_SHOCK_AT_T8)
        p = self.fits["noiseless"]["fit_by_family"]["ratio_p"]["params"]
        a14.full_curve(70., p, self.snapshot)
        self.assertEqual((a11.OPTIONS, a11.MARKET_SHOCK_AT_T8), before)

    def test_simplified_variants_are_numerically_finite(self):
        p = self.fits["noiseless"]["fit_by_family"]["ratio_p"]["params"]
        for model in a14.MODELS:
            curve = a14.model_curve(model, 70., p, self.snapshot)
            self.assertEqual(set(curve), set(a14.CAPACITIES))
            self.assertTrue(all(math.isfinite(v) for v in curve.values()))
        self.assertNotEqual(
            a14.model_curve("minimal", 70., p, self.snapshot),
            a14.model_curve("full", 70., p, self.snapshot),
        )

    def test_minimax_is_policy_regret_not_minimax_cash(self):
        Ks = a14.CAPACITIES
        c1 = {k: -float((k-120)**2) for k in Ks}
        c2 = {k: -float((k-180)**2) for k in Ks}
        k, worst = a14.minimax_regret([c1, c2])
        self.assertEqual(k, 150.)
        self.assertAlmostEqual(worst[k], 900.)
        self.assertEqual(a14.choose_best(c1), 120.)
        self.assertEqual(a14.choose_best(c2), 180.)

    def test_stress_range_contains_nominal_and_endpoints(self):
        xs = a14.stress_shocks(70.)
        self.assertEqual(len(xs), 201)
        self.assertAlmostEqual(xs[0], 52.5)
        self.assertAlmostEqual(xs[100], 70.)
        self.assertAlmostEqual(xs[-1], 87.5)

    def test_policy_rows_use_one_full_reference(self):
        rows = a14.evaluate_case("noiseless", 70., self.fits, self.snapshot)
        self.assertEqual(len(rows), len(a14.MODELS)*2)
        self.assertTrue(all(r["nominal_regret_under_full"] >= -1e-7 for r in rows))
        self.assertTrue(all(r["worst_regret_under_full"] >= r["nominal_regret_under_full"]-1e-6 for r in rows))
        self.assertEqual({r["model"] for r in rows}, set(a14.MODELS))
        self.assertEqual({r["decision_rule"] for r in rows}, set(a14.POLICIES))
        full_nominal = next(r for r in rows if r["model"]=="full" and r["decision_rule"]=="nominal")
        self.assertEqual(full_nominal["nominal_regret_under_full"], 0.)
        self.assertEqual(full_nominal["selected_k"], 195.)

    def test_simplified_does_not_mutate_frozen_contract(self):
        initial = dict(a11.BUSINESS)
        p = self.fits["noiseless"]["fit_by_family"]["ratio_p"]["params"]
        a14.simplified_curve(80., p, self.snapshot, "minimal")
        self.assertEqual(initial, a11.BUSINESS)

if __name__ == "__main__":
    unittest.main()
