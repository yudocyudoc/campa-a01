#!/usr/bin/env python3
"""A13: exploratory candidate-only decision sensitivity by source of model error.

Reference is the *fitted* A11 noiseless/noisy ratio_p model, NOT independent
WORLD truth. Every comparison is conditional on that nominal reference.
No oracle calls, no re-fitting, no new materiality gate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from experiments.A11 import contract as c

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "experiments/A11/evidence/analyst/analyst_freeze.json"
SNAPSHOT = ROOT / "experiments/A11/evidence/public/predecision_snapshot.csv"
A12_CURVES = ROOT / "experiments/A12/evidence/candidate_policy_cash.csv"
A11_CONTRACT = ROOT / "experiments/A11/contract.py"

SHOCKS = tuple(float(x) for x in range(20, 101, 10))
KS = tuple(float(x) for x in range(90, 261, 5))
ARMS = ("noiseless", "noisy_1pct")
MULTIPLIERS = (0.50, 0.75, 1.25, 1.50)
REFERENCE_FAMILY = "ratio_p"
COLUMNS = (
    "arm", "shock", "category", "source", "factor", "assumed_shock",
    "nominal_optimal_k", "chosen_k", "delta_k",
    "regret_under_nominal", "nominal_optimal_cash",
    "nominal_cash_at_chosen", "candidate_cash_at_chosen",
    "candidate_error_at_chosen", "candidate_error_at_nominal_optimal",
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def inputs():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze["experiment"] != "A11" or freeze["phase"] != "FORECASTS_FROZEN_BEFORE_ANY_INTERVENTION_WORLD":
        raise ValueError("A11 fitted candidates not frozen")
    snapshot_rows = read_csv(SNAPSHOT)
    if len(snapshot_rows) != 1:
        raise ValueError("Expected one predecision snapshot")
    snapshot = {key: float(val) for key, val in snapshot_rows[0].items()}
    fits = freeze["selected_policies_by_arm"]
    if set(fits) != set(ARMS):
        raise ValueError("A11 arms changed")
    return fits, snapshot

def cash_curve(shock: float, family: str, params: list[float],
               business: dict, snapshot: dict) -> dict[float, float]:
    """Evaluate specified scenario with the disclosed business equations only.

    A11.contract uses mutable module configuration. Restore it even on failure.
    """
    saved_business = dict(c.BUSINESS)
    saved_options = c.OPTIONS
    saved_shock = c.MARKET_SHOCK_AT_T8
    try:
        c.BUSINESS.clear()
        c.BUSINESS.update(business)
        c.OPTIONS = KS
        c.MARKET_SHOCK_AT_T8 = float(shock)
        return {
            k: float(c.forecast(k, snapshot, params, family)[-1]["cash"])
            for k in KS
        }
    finally:
        c.BUSINESS.clear()
        c.BUSINESS.update(saved_business)
        c.OPTIONS = saved_options
        c.MARKET_SHOCK_AT_T8 = saved_shock

def best_k(curve: dict[float, float]) -> float:
    optimum = max(curve.values())
    return min(k for k, value in curve.items() if optimum - value <= 1e-6)

def score(reference: dict[float, float], candidate: dict[float, float]) -> dict:
    if set(reference) != set(KS) or set(candidate) != set(KS):
        raise ValueError("Policy menu changed")
    true_k = best_k(reference)
    chosen = best_k(candidate)
    regret = reference[true_k] - reference[chosen]
    if regret < -1e-6:
        raise AssertionError("Negative policy regret")
    return {
        "nominal_optimal_k": true_k, "chosen_k": chosen,
        "delta_k": chosen - true_k,
        "regret_under_nominal": max(0.0, regret),
        "nominal_optimal_cash": reference[true_k],
        "nominal_cash_at_chosen": reference[chosen],
        "candidate_cash_at_chosen": candidate[chosen],
        "candidate_error_at_chosen": candidate[chosen] - reference[chosen],
        "candidate_error_at_nominal_optimal": candidate[true_k] - reference[true_k],
    }

def check_a12_anchor(fits: dict, snapshot: dict, business: dict) -> int:
    """Compare all 1,260 unperturbed forecasts to permanent A12 evidence."""
    original = read_csv(A12_CURVES)
    if len(original) != len(ARMS)*len(SHOCKS)*2*len(KS):
        raise AssertionError("A12 archived candidate curves incomplete")
    observed = {}
    for arm in ARMS:
        for shock in SHOCKS:
            for family in ("ratio_p", "diff_c"):
                params = fits[arm]["fit_by_family"][family]["params"]
                curve = cash_curve(shock, family, params, business, snapshot)
                for k, value in curve.items():
                    observed[(arm, shock, family, k)] = value
    if len(observed) != len(original):
        raise AssertionError("Unexpected A13 reference predictions")
    for row in original:
        key = (row["arm"], float(row["shock"]), row["family"], float(row["policy_k"]))
        if key not in observed or not math.isclose(
            observed[key], float(row["predicted_cash_t24"]), rel_tol=0, abs_tol=1e-6
        ):
            raise AssertionError("A13 drift from frozen A12 forecasts: " + str(key))
    return len(original)

def experiments_for_case(arm: str, shock: float, fits: dict,
                         snapshot: dict, business: dict) -> list[dict]:
    fit = fits[arm]["fit_by_family"]
    params = list(map(float, fit[REFERENCE_FAMILY]["params"]))
    reference = cash_curve(shock, REFERENCE_FAMILY, params, business, snapshot)
    tests = [("family", "diff_c", 1.0, shock, "diff_c",
              list(map(float, fit["diff_c"]["params"])), business)]
    zero_gain = params.copy()
    zero_gain[2] = 0.0
    tests.append(("driver_presence", "gain_zero", 0.0, shock,
                  REFERENCE_FAMILY, zero_gain, business))
    for name, nominal in business.items():
        for factor in MULTIPLIERS:
            modified = business.copy()
            modified[name] = nominal * factor
            tests.append(("coefficient", name, factor, shock,
                          REFERENCE_FAMILY, params, modified))
    for factor in MULTIPLIERS:
        tests.append(("shock_uncertainty", "future_shock", factor, shock*factor,
                      REFERENCE_FAMILY, params, business))
    rows = []
    for category, source, factor, assumed, family, p, b in tests:
        candidate = cash_curve(assumed, family, p, b, snapshot)
        rows.append({
            "arm": arm, "shock": shock, "category": category, "source": source,
            "factor": factor, "assumed_shock": assumed,
            **score(reference, candidate),
        })
    return rows

def summarize(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["category"], row["source"])].append(row)
    summary = []
    for (category, source), group in groups.items():
        regrets = [float(r["regret_under_nominal"]) for r in group]
        biggest = max(group, key=lambda r: (r["regret_under_nominal"], -r["shock"]))
        summary.append({
            "category": category, "source": source, "cases": len(group),
            "different_k": sum(r["chosen_k"] != r["nominal_optimal_k"] for r in group),
            "mean_regret_across_design_grid": statistics.mean(regrets),
            "median_regret_across_design_grid": statistics.median(regrets),
            "max_regret": max(regrets),
            "worst_shock": biggest["shock"], "worst_arm": biggest["arm"],
            "worst_factor": biggest["factor"],
            "max_abs_prediction_error_at_chosen": max(
                abs(r["candidate_error_at_chosen"]) for r in group
            ),
        })
    summary.sort(key=lambda r: (-r["mean_regret_across_design_grid"], r["source"]))
    return summary

def run(out: Path) -> dict:
    fits, snapshot = inputs()
    business = dict(c.BUSINESS)
    anchor_count = check_a12_anchor(fits, snapshot, business)
    rows = [
        row
        for arm in ARMS for shock in SHOCKS
        for row in experiments_for_case(arm, shock, fits, snapshot, business)
    ]
    expected_cases = len(ARMS)*len(SHOCKS)*(2 + len(business)*len(MULTIPLIERS) + len(MULTIPLIERS))
    if len(rows) != expected_cases:
        raise AssertionError("Incomplete perturbation matrix")
    out.mkdir(parents=True, exist_ok=True)
    with (out/"cases.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    rank = summarize(rows)
    with (out/"sources.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=tuple(rank[0].keys()))
        writer.writeheader()
        writer.writerows(rank)
    result = {
        "experiment": "A13",
        "status": "EXPLORATORY_CONDITIONAL_MODEL_SENSITIVITY",
        "reference": "frozen fitted ratio_p for each A11 arm; NOT independent WORLD",
        "target": "cash at pre-flow t24",
        "anchor_a12_candidate_predictions_checked": anchor_count,
        "shocks": SHOCKS,
        "capacities": KS,
        "arms": ARMS,
        "multipliers": MULTIPLIERS,
        "rows": len(rows),
        "coefficient_count": len(business),
        "no_new_training": True,
        "world_generator_accessed": False,
        "no_materiality_gate": True,
        "ranking": rank,
        "source_sha256": {
            "a11_contract": sha256(A11_CONTRACT),
            "a11_fit": sha256(FREEZE),
            "a11_snapshot": sha256(SNAPSHOT),
            "a12_curves": sha256(A12_CURVES),
        },
        "limitations": [
            "A13 is a post-A12 exploratory sensitivity study: shocks 70/80 were already highlighted by A12.",
            "Nominal fitted ratio_p is a counterfactual reference, not newly adjudicated WORLD truth.",
            "Business equations, predecision state and nominal coefficients are stipulated.",
            "All errors are one-at-a-time; no joint uncertainty or probability distribution.",
            "Multipliers and shock grid are design scenarios, not calibrated uncertainty probabilities.",
            "Mean regret across the design grid is descriptive, not expected monetary value or VoI.",
            "Regret measures wrong POLICY under nominal assumptions; financial forecast error is separate.",
            "Gain zero is an intentionally simple structural ablation, not a fair general business baseline.",
        ],
        "csv_sha256": {
            "cases.csv": sha256(out/"cases.csv"),
            "sources.csv": sha256(out/"sources.csv"),
        },
    }
    (out/"summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
        encoding="utf-8",
    )
    print("A13_COMPLETE", json.dumps({
        "cases": len(rows), "a12_anchor": anchor_count,
        "ranking_top5": [
            {k: record[k] for k in ("category", "source", "mean_regret_across_design_grid", "max_regret")}
            for record in rank[:5]
        ],
    }, ensure_ascii=False), flush=True)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/A13"))
    run(parser.parse_args().out)
