#!/usr/bin/env python3
"""A14: decision value of a minimal SD skeleton plus minimax-regret capacity.

Candidate only. A11 fitted ratio_p is a CONDITIONAL nominal reference, NOT WORLD.
The reference evaluates policies but never selects policies for simplified variants.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from experiments.A11 import contract as a11

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "experiments/A11/evidence/analyst/analyst_freeze.json"
SNAPSHOT = ROOT / "experiments/A11/evidence/public/predecision_snapshot.csv"
A12_CURVES = ROOT / "experiments/A12/evidence/candidate_policy_cash.csv"
ARMS = ("noiseless", "noisy_1pct")
SHOCKS = tuple(float(s) for s in range(20, 101, 10))
CAPACITIES = tuple(float(k) for k in range(90, 261, 5))
# Exploratory convention inspired by Claude's post-A13 robustness probe.
STRESS_RELATIVE = 0.25
STRESS_POINTS = 201
MODELS = ("full", "minimal", "no_cancellations", "no_churn_feedback", "immediate_collections")
POLICIES = ("nominal", "minimax_regret")
FIELDS = (
    "arm", "shock_nominal", "model", "decision_rule",
    "selected_k", "reference_nominal_optimal_k", "delta_k",
    "nominal_regret_under_full", "worst_regret_under_full",
    "mean_regret_over_stress_grid_under_full",
    "worst_regret_under_candidate",
    "nominal_prediction_error_at_selected_k",
    "reference_nominal_cash_at_selected_k", "candidate_nominal_cash_at_selected_k",
)
_SUMMARY_KEYS = ("arm", "shock_nominal", "model")

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inputs():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["phase"] == "FORECASTS_FROZEN_BEFORE_ANY_INTERVENTION_WORLD"
    with SNAPSHOT.open(newline="", encoding="utf-8") as f:
        history = list(csv.DictReader(f))
    if len(history) != 1:
        raise ValueError("Unexpected number of predecision snapshots")
    snapshot = {k: float(v) for k, v in history[0].items()}
    fits = freeze["selected_policies_by_arm"]
    if set(fits) != set(ARMS):
        raise ValueError("Unexpected frozen A11 arms")
    return fits, snapshot

def _driver(orders: float, capacity: float, params) -> float:
    tau, rate, gain, shape = map(float, params)
    # No access to WORLD: ratio_p is the frozen A11 fitted response family.
    return gain*max(orders / capacity**shape - tau, 0.0)

def full_curve(shock: float, params, snapshot: dict) -> dict[float, float]:
    saved_opts, saved_shock = a11.OPTIONS, a11.MARKET_SHOCK_AT_T8
    try:
        a11.OPTIONS = CAPACITIES
        a11.MARKET_SHOCK_AT_T8 = shock
        return {k: float(a11.forecast(k, snapshot, params, "ratio_p")[-1]["cash"])
                for k in CAPACITIES}
    finally:
        a11.OPTIONS, a11.MARKET_SHOCK_AT_T8 = saved_opts, saved_shock

def simplified_curve(shock: float, params, snapshot: dict,
                     model: str) -> dict[float, float]:
    """Explicitly specified four SD variants.

    No-cancellations: zero cancellation FLOW; backlog remains a stock and
        there is no cancellation-induced churn (a bundled ablation).
    No-churn-feedback: cancellations still reduce backlog, but do not
        reduce customer base.
    Immediate-collections: historic t8 receivables are still collected
        under disclosed collection_delay; NEW fulfillment is paid immediately.
        The historic receivable stream is K-independent. No new receivables.
    Minimal: all three changes simultaneously. Capacity erosion driver,
        customer-base stock, backlog, and all operating costs retained.

    No variant is re-fitted. Every variant uses identical frozen response
    params and observed predecision state.
    """
    if model not in MODELS or model == "full":
        raise ValueError("Not a simplified A14 variant")
    b = a11.BUSINESS
    cancel_off = model in ("minimal", "no_cancellations")
    churn_off = model in ("minimal", "no_churn_feedback")
    immediate = model in ("minimal", "immediate_collections")
    tau, rate, gain, shape = map(float, params)
    prev_frac = snapshot["previous_effective_capacity"]/snapshot["previous_nominal_capacity"]
    if prev_frac <= b["minimum_fraction"]+1e-8:
        raise ValueError("Cannot infer initial impact in clipped prehistory")
    old_imp = max(0.0, 1-prev_frac)
    initial_driver = _driver(snapshot["previous_incoming_orders"],
                             snapshot["previous_nominal_capacity"], params)
    initial_z = (1-rate)*old_imp+rate*initial_driver
    results = {}
    for k in CAPACITIES:
        customers = snapshot["customer_base"]
        backlog = snapshot["backlog"]
        receivables = snapshot["receivables"]
        cash = snapshot["cash"]
        z = initial_z
        for t in range(a11.DECISION_T, a11.HORIZON_T+1):
            orders = customers*b["base_order_rate"] + shock
            effective = k*max(1-z, b["minimum_fraction"])
            fulfilled = min(backlog+orders, effective)
            cancellations = 0.0 if cancel_off else backlog*b["cancel_rate"]
            churn = b["base_churn"] if churn_off else (
                b["base_churn"]+cancellations*b["customer_loss_per_cancel"]
            )
            # Historic receivables are collected in both variants, but
            # immediate-collection variants DO NOT create new receivables.
            collections = receivables/b["collection_delay"]
            operating_cost = (
                b["fixed_cost"]+fulfilled*b["variable_cost_per_order"]
                +b["marketing_intensity"]*b["marketing_cost_per_unit"]
                +max(k-a11.BASELINE, 0.0)*b["capacity_cost_per_extra_unit"]
            )
            # A11's t24 is PRE-FLOW cash, not the balance after t24 operations.
            if t == a11.HORIZON_T:
                results[k] = float(cash)
                break
            customers += b["marketing_intensity"]*b["acquisition_per_marketing_unit"]-churn
            backlog += orders-fulfilled-cancellations
            if immediate:
                receivables -= collections
                cash += collections + fulfilled*b["price"]-operating_cost
            else:
                receivables += fulfilled*b["price"]-collections
                cash += collections-operating_cost
            z = (1-rate)*z+rate*_driver(orders, k, params)
            if not all(math.isfinite(v) for v in (customers, backlog, cash, z, receivables)):
                raise ValueError("Non-finite simplified simulation")
    return results

def model_curve(model: str, shock: float, params, snapshot: dict):
    if model == "full":
        return full_curve(shock, params, snapshot)
    return simplified_curve(shock, params, snapshot, model)

def choose_best(curve: dict[float, float]) -> float:
    peak = max(curve.values())
    return min(k for k, v in curve.items() if peak-v <= 1e-6)

def stress_shocks(nominal: float):
    return tuple(nominal*(1-STRESS_RELATIVE+2*STRESS_RELATIVE*i/(STRESS_POINTS-1))
                 for i in range(STRESS_POINTS))

def minimax_regret(curves: list[dict[float, float]]):
    worst = {k: 0.0 for k in CAPACITIES}
    for curve in curves:
        peak = max(curve.values())
        for k in CAPACITIES:
            worst[k] = max(worst[k], peak-curve[k])
    minimum = min(worst.values())
    return min(k for k, val in worst.items() if val-minimum <= 1e-6), worst

def check_a12_full_anchor(fits: dict, snapshot: dict) -> int:
    """Check all nine shocks, both arms, 35 K, ratio_p A12 candidates."""
    with A12_CURVES.open(newline="", encoding="utf-8") as f:
        archived = list(csv.DictReader(f))
    archived = [r for r in archived if r["family"] == "ratio_p"]
    if len(archived) != len(ARMS)*len(SHOCKS)*len(CAPACITIES):
        raise AssertionError("Wrong A12 anchor size")
    calc = {}
    for arm in ARMS:
        p = fits[arm]["fit_by_family"]["ratio_p"]["params"]
        for shock in SHOCKS:
            for k, cash in full_curve(shock, p, snapshot).items():
                calc[(arm, shock, k)] = cash
    for r in archived:
        key = (r["arm"], float(r["shock"]), float(r["policy_k"]))
        if key not in calc or not math.isclose(
                calc[key], float(r["predicted_cash_t24"]), abs_tol=1e-7, rel_tol=0):
            raise AssertionError("Drift from A12 at "+str(key))
    return len(archived)

def evaluate_case(arm: str, nominal: float, fits: dict, snapshot: dict) -> list[dict]:
    p = fits[arm]["fit_by_family"]["ratio_p"]["params"]
    stress = stress_shocks(nominal)
    # Shared *evaluation* oracle, NOT used in simplified policy selection.
    # It is the complete fitted A11 model, not hidden WORLD.
    reference_curves = [full_curve(s, p, snapshot) for s in stress]
    reference_nominal = full_curve(nominal, p, snapshot)
    k_reference = choose_best(reference_nominal)
    reference_best_per_stress = [max(curve.values()) for curve in reference_curves]
    rows = []
    for model in MODELS:
        candidate_curves = reference_curves if model == "full" else [
            simplified_curve(s, p, snapshot, model) for s in stress
        ]
        candidate_nominal = reference_nominal if model == "full" else simplified_curve(
            nominal, p, snapshot, model
        )
        nominal_k = choose_best(candidate_nominal)
        robust_k, predicted_worst = minimax_regret(candidate_curves)
        for policy, selected in (("nominal", nominal_k), ("minimax_regret", robust_k)):
            full_regrets = [
                max(0.0, peak-curve[selected])
                for peak, curve in zip(reference_best_per_stress, reference_curves)
            ]
            rows.append({
                "arm": arm, "shock_nominal": nominal, "model": model,
                "decision_rule": policy, "selected_k": selected,
                "reference_nominal_optimal_k": k_reference,
                "delta_k": selected-k_reference,
                "nominal_regret_under_full": max(
                    0.0, reference_nominal[k_reference]-reference_nominal[selected]
                ),
                "worst_regret_under_full": max(full_regrets),
                "mean_regret_over_stress_grid_under_full": sum(full_regrets)/len(full_regrets),
                "worst_regret_under_candidate": predicted_worst[selected],
                "nominal_prediction_error_at_selected_k": (
                    candidate_nominal[selected]-reference_nominal[selected]
                ),
                "reference_nominal_cash_at_selected_k": reference_nominal[selected],
                "candidate_nominal_cash_at_selected_k": candidate_nominal[selected],
            })
    return rows

def summarize(rows):
    output = []
    for model in MODELS:
        for rule in POLICIES:
            group = [r for r in rows if r["model"] == model and r["decision_rule"] == rule]
            if len(group) != len(ARMS)*len(SHOCKS):
                raise AssertionError("Incomplete rows")
            def avg(field): return sum(float(r[field]) for r in group)/len(group)
            output.append({
                "model": model, "decision_rule": rule, "cases": len(group),
                "mean_nominal_regret_under_full": avg("nominal_regret_under_full"),
                "mean_worst_regret_under_full": avg("worst_regret_under_full"),
                "max_worst_regret_under_full": max(float(r["worst_regret_under_full"]) for r in group),
                "mean_abs_delta_k": avg("delta_k") if rule == "minimax_regret" else avg("delta_k"),
                "mean_abs_nominal_prediction_error": sum(
                    abs(float(r["nominal_prediction_error_at_selected_k"])) for r in group
                )/len(group),
            })
    return output

def write_csv(path: Path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def run(out: Path):
    fits, snapshot = inputs()
    anchor = check_a12_full_anchor(fits, snapshot)
    rows = [
        result for arm in ARMS for shock in SHOCKS
        for result in evaluate_case(arm, shock, fits, snapshot)
    ]
    if len(rows) != len(ARMS)*len(SHOCKS)*len(MODELS)*len(POLICIES):
        raise AssertionError("Incomplete A14 design")
    summary_rows = summarize(rows)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out/"policies.csv", rows, FIELDS)
    write_csv(out/"summary.csv", summary_rows, tuple(summary_rows[0].keys()))
    summary = {
        "experiment": "A14", "status": "EXPLORATORY_CANDIDATE_ONLY",
        "reference": "A11 frozen ratio_p fitted model per arm, NOT WORLD",
        "a12_ratio_p_anchor_predictions": anchor,
        "shocks": SHOCKS, "capacities": CAPACITIES,
        "arms": ARMS, "models": MODELS,
        "policies": POLICIES,
        "stress_relative": STRESS_RELATIVE,
        "stress_points": STRESS_POINTS,
        "cases": len(rows),
        "cash_t": "PRE-FLOW t24",
        "no_world_access": True,
        "selection_independent_of_full_reference_for_minimal_models": True,
        "no_refitting": True, "no_new_materiality_gate": True,
        "summary": summary_rows,
        "source_sha256": {
            "a11_contract": sha256(ROOT/"experiments/A11/contract.py"),
            "a11_fit": sha256(FREEZE),
            "snapshot": sha256(SNAPSHOT),
            "a12_candidates": sha256(A12_CURVES),
        },
        "limitations": [
            "All outcomes are evaluated by the fitted full ratio_p reference; WORLD is never called.",
            "The minimal model retains the fitted ratio_p response parameters, hence mechanism knowledge is privileged.",
            "No-cancellations also removes cancellation-induced churn (bundled ablation).",
            "Immediate-collections retains only repayment of OLD observed t8 receivables, and takes payment for new deliveries immediately.",
            "Cross-model cash absolute levels are not comparable because collection timing differs; policies are evaluated with one full reference.",
            "201 evenly spaced stress shocks represent a grid, not probabilities or a realistic uncertainty model.",
            "Minimax-regret is optimized on EACH candidate's own model and then evaluated by the full fitted reference.",
            "All business coefficients except the ablated processes remain disclosed, not learned.",
            "Shocks/capacity grid are exploratory following A13; results are not blind confirmation."
        ],
    }
    summary["output_sha256"] = {
        "policies.csv": sha256(out/"policies.csv"),
        "summary.csv": sha256(out/"summary.csv"),
    }
    (out/"summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False)+"\n",
        encoding="utf-8"
    )
    print("A14_COMPLETE "+json.dumps({
        "cases": len(rows), "anchor": anchor,
        "table": summary_rows, "sha256": summary["output_sha256"],
    }, ensure_ascii=False), flush=True)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/A14"))
    run(parser.parse_args().out)
