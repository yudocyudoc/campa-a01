"""A10 boundary and actual observable response tests; stdlib only."""
import ast
import csv
import tempfile
import unittest
from pathlib import Path

from experiments.A10.contract import (
    OBSERVED,INPUTS,MIN_CAPACITY_FRACTION,
    candidate_activity,forcing,simulate_fraction,validate_contract_fields,
)


class A10ContractTests(unittest.TestCase):
    def test_schema_rejects_latent_labels_and_target_leak(self):
        self.assertTrue(validate_contract_fields(("scenario",)+OBSERVED,("scenario",)+OBSERVED))
        self.assertTrue(validate_contract_fields(("scenario",)+INPUTS,("scenario",)+INPUTS))
        for forbidden in ("hidden_excess","latent_state","world_truth","primitive_impact"):
            with self.assertRaises(ValueError):
                validate_contract_fields(("scenario",forbidden),("scenario",forbidden))
        with self.assertRaises(ValueError):
            validate_contract_fields(("scenario","t","effective_capacity"),
                                     ("scenario",)+INPUTS)

    def test_response_recursion_matches_observed_first_order_example(self):
        # Not algebra-only: integrates the 25-step state and capacity clipping.
        # diff_c input D-cK with D=125,K=100,c=1,tau=0 -> stress=25
        # g=.02, a=.5, so forcing=.5; impact evolves 0, .25, .375...
        params=(0.,.5,.02,1.)
        rows=[{"t":float(t),"incoming_orders":125.,"nominal_capacity":100.,
               "effective_capacity":100.} for t in range(25)]
        fractions=simulate_fraction(rows,params,"diff_c")
        self.assertAlmostEqual(fractions[0],1.)
        self.assertAlmostEqual(fractions[1],.75)
        self.assertAlmostEqual(fractions[2],.625)
        self.assertAlmostEqual(fractions[3],.5625)
        self.assertTrue(all(x>=MIN_CAPACITY_FRACTION for x in fractions))
        self.assertTrue(candidate_activity(125.,100.,params,"diff_c"))
        self.assertFalse(candidate_activity(50.,100.,params,"diff_c"))

    def test_holdout_only_t0_effective_capacity_is_enough(self):
        params=(0.,.5,.02,1.)
        rows=[{"t":float(t),"incoming_orders":125.,"nominal_capacity":100.,
               "initial_effective_capacity":100. if t==0 else ""} for t in range(25)]
        self.assertAlmostEqual(simulate_fraction(rows,params,"diff_c")[2],.625)

    def test_candidate_families_use_distinct_drivers(self):
        # At p=1 the ratio candidate scales with K, diff-c does not.
        for k in (90.,115.,145.):
            r=forcing(130.,k,(0.,.5,1.,1.),"ratio_p")
            d=forcing(130.,k,(0.,.5,1.,1.),"diff_c")
            self.assertNotAlmostEqual(r,d,places=6)

    def test_analyst_source_has_no_oracle_import(self):
        path=Path(__file__).resolve().parents[1]/"experiments/A10/analyst.py"
        tree=ast.parse(path.read_text(encoding="utf-8"))
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node,ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any(s.startswith(("experiments.A06",
            "experiments.A07","experiments.A08","experiments.A09"))
                             for s in imports))
        self.assertFalse(any(s in path.read_text(encoding="utf-8")
                             for s in ("WORLD_CASES","hidden_excess","primitive_impact")))


if __name__=="__main__":
    unittest.main()
