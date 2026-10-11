"""A10b stdlib-only boundary tests and protocol invariants."""
import ast
import unittest
from pathlib import Path

from experiments.A10b.design import (
    SEEDS,ORIGINAL_A10_SEED,EXPECTED_MARGIN,NOISE_STD_FRACTION,
    TRAIN_SCENARIOS,HOLDOUT_SCENARIOS,validate,
)
from experiments.A10.contract import DECISION_GAP,NOISE_LEVELS,simulate_fraction

ROOT=Path(__file__).resolve().parents[1]

class A10bTests(unittest.TestCase):
    def test_preregistered_seeds_and_original_anchor(self):
        validate()
        self.assertEqual(len(SEEDS),10)
        self.assertEqual(SEEDS[0],ORIGINAL_A10_SEED)
        self.assertEqual(list(SEEDS),list(range(20261011,20261021)))

    def test_identical_a10_model_and_decision_rule(self):
        self.assertEqual(EXPECTED_MARGIN,DECISION_GAP)
        self.assertEqual(NOISE_STD_FRACTION,NOISE_LEVELS[1])
        self.assertEqual((TRAIN_SCENARIOS,HOLDOUT_SCENARIOS),(5,17))
        rows=[{"t":float(t),"incoming_orders":125.,"nominal_capacity":100.,
               "initial_effective_capacity":100. if t==0 else ""} for t in range(25)]
        self.assertAlmostEqual(simulate_fraction(rows,(0.,0.5,0.02,1.),"diff_c")[2],0.625)

    def test_analyst_module_never_imports_oracle_or_adjudicator(self):
        tree=ast.parse((ROOT/"experiments/A10b/analyst_batch.py").read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            if isinstance(node,ast.Import):imports.extend(i.name for i in node.names)
        self.assertNotIn("experiments.A10b.packager",imports)
        self.assertNotIn("experiments.A10b.adjudicate_batch",imports)
        self.assertNotIn("experiments.A10.adjudicate",imports)
        self.assertFalse(any(x.startswith(("experiments.A08","experiments.A09"))
                             for x in imports))

    def test_packager_can_omit_sealed_outputs(self):
        tree=ast.parse((ROOT/"experiments/A10b/packager.py").read_text())
        defs={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
        self.assertIn("produce",defs)
        args=defs["produce"].args
        names=[a.arg for a in args.args]
        self.assertIn("include_sealed",names)
        self.assertIn("seed",names)
        text=(ROOT/"experiments/A10b/public_batch.py").read_text()
        self.assertIn("include_sealed=False",text)

    def test_adjudicator_requires_frozen_analyst_evidence(self):
        source=(ROOT/"experiments/A10b/adjudicate_batch.py").read_text()
        self.assertIn("ALL_DECISIONS_FROZEN_BEFORE_ANY_SEALED_LABELS",source)
        self.assertIn("include_sealed=True",source)
        self.assertIn("public_batch_sha256",source)

if __name__=="__main__":unittest.main()
