#!/usr/bin/env python3
"""A06: prospectively separate ratio vs difference using the original G5 equations.

This is a controlled fixed-parameter feasibility test, NOT a general
identifiability certificate or a blind recovery of an unknown mechanism.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path

from g5_model_core import (
    DEFAULT_PARAMS, WORLD_CASES, TRUE_DERIVED_ID,
    simulate_world_case, simulate_repair,
)

CASE_ID = "W016"
TRUTH = WORLD_CASES[CASE_ID]
assert TRUTH["primitive"] == "first_order_relaxation"
PRIMITIVE = TRUTH["primitive"]
K0 = float(DEFAULT_PARAMS["nominal_capacity"])  # 115
RATIO_ID = TRUE_DERIVED_ID
DIFF_ID = "diff::incoming_orders-nominal_capacity"
FEATURE_META = {
    RATIO_ID: {"kind": "ratio", "x": "incoming_orders", "y": "nominal_capacity"},
    DIFF_ID: {"kind": "diff", "x": "incoming_orders", "y": "nominal_capacity"},
}
SCORE_VARS = ("effective_capacity", "backlog", "cash")
# Fixed and declared before computing the probes; units of each observed series.
SCALES = {"effective_capacity": K0, "backlog": K0, "cash": 20_000.0}
EXCITATION_FLOOR = 1e-9  # numerical/noiseless flag, NOT calibrated detection threshold

# Define ALL candidate interventions in advance.
PROBES = [
    {"id": "control_K115_S25", "kind": "control", "capacity": 115.0, "shock": 25.0},
    {"id": "demand_K115_S0", "kind": "demand_only", "capacity": 115.0, "shock": 0.0},
    {"id": "demand_K115_S50", "kind": "demand_only", "capacity": 115.0, "shock": 50.0},
    {"id": "demand_K115_S70", "kind": "demand_only", "capacity": 115.0, "shock": 70.0},
    *[
        {"id": f"cross_K{int(k)}_S{int(shock)}", "kind": "crossed", "capacity": k, "shock": shock}
        for k in (90.0, 145.0, 180.0, 220.0)
        for shock in (0.0, 25.0, 50.0, 70.0)
    ],
    {"id": "pulse_K80_S25", "kind": "transient", "capacity": 115.0, "shock": 25.0,
     "stress_capacity": 80.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K160_S25", "kind": "transient", "capacity": 115.0, "shock": 25.0,
     "stress_capacity": 160.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K90_S50", "kind": "transient", "capacity": 145.0, "shock": 50.0,
     "stress_capacity": 90.0, "stress_start": 8.0, "stress_end": 12.0},
]

# Two candidates deliberately normalized to be IDENTICAL at K=K0.
# In the original WORLD: normalized feature = (orders/K - 0.75) / 0.25.
# For diff, (orders-K + 0.25*K0) / (0.25*K0) agrees only when K=K0.
REPAIR_COMMON = {
    **TRUTH["truth"], "minimum_fraction": DEFAULT_PARAMS["minimum_capacity_fraction"],
    "orientation": 1.0,
}
REPAIRS = {
    RATIO_ID: {**REPAIR_COMMON, "baseline": 0.75, "excursion": 0.25},
    DIFF_ID: {**REPAIR_COMMON, "baseline": -0.25 * K0, "excursion": 0.25 * K0},
}


def normalized_signals(orders: float, capacity: float) -> tuple[float, float]:
    """Pre-given, pair-matched feature geometry. No fitted parameters."""
    ratio = (orders / capacity - 0.75) / 0.25
    diff = (orders - capacity + 0.25 * K0) / (0.25 * K0)
    return ratio, diff


def kwargs_for(probe: dict) -> dict:
    cfg = {
        "params": {"months": 24, "nominal_capacity": probe["capacity"],
                   "market_shock_orders": probe["shock"]},
        "capacity_mode": "transient" if probe["kind"] == "transient" else "constant",
    }
    if probe["kind"] == "transient":
        for name in ("stress_start", "stress_end", "stress_capacity"):
            cfg[name] = probe[name]
    return cfg


def simulate_candidate(probe: dict, feature: str):
    return simulate_repair(
        primitive=PRIMITIVE, feature_id=feature,
        feature_meta=FEATURE_META, repair=REPAIRS[feature],
        **kwargs_for(probe),
    )[0]


def post_shock(df):
    return df.loc[df.index >= 8.0]


def distance(a, b) -> tuple[float, dict]:
    """Common-horizon RMS difference in declared, fixed, physical scales."""
    x = post_shock(a)
    y = post_shock(b)
    if list(x.index) != list(y.index):
        raise ValueError("Different time grids")
    contributions = {}
    for metric in SCORE_VARS:
        diffs = ((x[metric] - y[metric]) / SCALES[metric]).astype(float)
        values = diffs.to_numpy()
        contributions[metric] = math.sqrt(float((values * values).mean()))
    total = math.sqrt(sum(v*v for v in contributions.values()) / len(contributions))
    if not math.isfinite(total):
        raise AssertionError("Non-finite separation")
    return total, contributions


def deterministic_selection(table: list[dict]) -> list[str]:
    eligible = [r for r in table if r["kind"] in ("crossed", "transient")]
    # Fixed ranking on candidate-prediction-only discrepancy; never consult WORLD.
    eligible.sort(key=lambda r: (-r["candidate_disagreement"], r["probe"]))
    return [r["probe"] for r in eligible[:4]]


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, records: list[dict]):
    if not records:
        raise ValueError("No CSV records")
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    candidate_records = []
    trajectories = []
    forecast = {}
    # Stage 1: ALL candidate predictions only, no access to WORLD.
    for probe in PROBES:
        ratio = simulate_candidate(probe, RATIO_ID)
        diff = simulate_candidate(probe, DIFF_ID)
        forecast[probe["id"]] = (ratio, diff)
        score, metrics = distance(ratio, diff)
        candidate_records.append({
            "probe": probe["id"], "kind": probe["kind"],
            "capacity": probe["capacity"], "shock": probe["shock"],
            "candidate_disagreement": score,
            **{f"disagreement_{key}": value for key, value in metrics.items()},
        })

    selected = deterministic_selection(candidate_records)
    # The control and its different demand regimes are predetermined checks.
    checked = [p["id"] for p in PROBES if p["capacity"] == K0 and p["kind"] != "transient"]
    adjudication_ids = list(dict.fromkeys(checked + selected))

    # Stage 2: WORLD is consulted only AFTER ranking is frozen.
    adjudicated = []
    for probe in PROBES:
        if probe["id"] not in adjudication_ids:
            continue
        world, _ = simulate_world_case(
            PRIMITIVE, TRUTH["truth"], **kwargs_for(probe))
        ratio, diff = forecast[probe["id"]]
        err_ratio, _ = distance(world, ratio)
        err_diff, _ = distance(world, diff)
        score, _ = distance(ratio, diff)
        adjudicated.append({
            "probe": probe["id"],
            "kind": probe["kind"],
            "candidate_disagreement": score,
            "world_error_ratio": err_ratio,
            "world_error_diff": err_diff,
            "ratio_matches_world": err_ratio <= EXCITATION_FLOOR,
            "diff_matches_world": err_diff <= EXCITATION_FLOOR,
            "local_separator_found": score > EXCITATION_FLOOR,
        })
        for model_name, frame in (("world", world), ("ratio", ratio), ("diff", diff)):
            for t, row in frame.iterrows():
                trajectories.append({
                    "probe": probe["id"], "model": model_name, "t": float(t),
                    **{name: float(row[name]) for name in (
                        "incoming_orders", "nominal_capacity", "effective_capacity",
                        "backlog", "cash")},
                })

    control_scores = [r["candidate_disagreement"] for r in candidate_records
                      if r["capacity"] == K0 and r["kind"] != "transient"]
    active_selected = [r for r in adjudicated if r["probe"] in selected
                       and r["local_separator_found"]]
    control_equal = bool(control_scores) and max(control_scores) <= EXCITATION_FLOOR
    oracle_fit = all(r["ratio_matches_world"] for r in adjudicated)
    local_separator = bool(active_selected)
    # Tests only of a concrete fixed pair, NOT family-wide identifiability.
    status = ("LOCAL_SEPARATOR_FOUND" if control_equal and oracle_fit and local_separator
              else "UNRESOLVED_OR_IMPLEMENTATION_MISMATCH")

    design = {
        "source_model": "original G5 C0.0 stock-flow equations; W016 synthetic truth",
        "world_truth_case": CASE_ID, "primitive": PRIMITIVE,
        "reference_capacity": K0, "ratio_true_expression": RATIO_ID,
        "difference_alternative": DIFF_ID,
        "candidate_parameters_frozen": REPAIRS,
        "metric_scales_frozen": SCALES,
        "numeric_floor_not_noise_calibrated": EXCITATION_FLOOR,
        "probe_library": PROBES, "selected_by_candidates_only": selected,
        "world_checked_probes": adjudication_ids,
        "no_refitting": True,
    }
    design_path = output / "design.json"
    design_path.write_text(json.dumps(design, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    write_csv(output / "candidate_predictions.csv", candidate_records)
    write_csv(output / "world_adjudication.csv", adjudicated)
    write_csv(output / "selected_trajectories.csv", trajectories)
    summary = {
        "experiment": "A06", "status": status,
        "scientific_scope": "FIXED_PARAMETER_LOCAL_SEPARABILITY_NOT_FAMILY_IDENTIFIABILITY",
        "control_fixed_capacity_equal": control_equal,
        "ratio_world_matches_all_adjudicated": oracle_fit,
        "selected_probe_count": len(selected),
        "selected_with_nonzero_separation": len(active_selected),
        "max_selected_disagreement": max((r["candidate_disagreement"] for r in active_selected), default=0.0),
        "case": CASE_ID, "true_primitive": PRIMITIVE,
        "adjudicated": adjudicated,
        "files_sha256": {
            p.name: checksum(p) for p in [
                design_path, output / "candidate_predictions.csv",
                output / "world_adjudication.csv", output / "selected_trajectories.csv"]},
        "github_sha": os.environ.get("GITHUB_SHA"),
        "limitations": [
            "The test uses known W016 truth and constructed matched parameters: it is not blind recovery.",
            "A single fixed parameter pair can be separated without establishing uniform family identifiability.",
            "No noise model or statistical detection threshold is calibrated.",
            "The ranking uses candidate responses, and checks WORLD only after probes are selected.",
            "No G5 benchmark results, thresholds or historical labels are altered.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({
        "status": status, "control_equal": control_equal,
        "world_ratio_fit": oracle_fit,
        "local_separators": len(active_selected), "max_gap": summary["max_selected_disagreement"],
        "selected": selected}, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/A06"))
    args = parser.parse_args()
    result = run(args.out)
    if result["status"] == "UNRESOLVED_OR_IMPLEMENTATION_MISMATCH":
        raise SystemExit(1)
