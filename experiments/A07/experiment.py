#!/usr/bin/env python3
"""A07 | Fit a ratio-vs-difference adversary on training worlds, probe out-of-sample.

Prospective numerical experiment, not a claim of family-wide identifiability.
Uses original G5 BPTK-Py stock-flow equations from A06 unchanged.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.A06.g5_model_core import DEFAULT_PARAMS, WORLD_CASES, simulate_world_case, simulate_repair  # noqa: E402
from experiments.A07.design import (  # noqa: E402
    BOUNDS, HOLDOUTS, K0, MAX_NFEV_PER_START, MAX_SELECTED,
    NUMERICAL_FLOOR, PRACTICAL_GAP, TRAINING,
    select_diverse_holdouts, validate_disjointness,
)

CASE_ID = "W016"
TRUTH = WORLD_CASES[CASE_ID]
PRIMITIVE = TRUTH["primitive"]
assert PRIMITIVE == "first_order_relaxation"
assert float(DEFAULT_PARAMS["nominal_capacity"]) == K0
RATIO = "ratio::incoming_orders/nominal_capacity"
DIFFERENCE = "diff::incoming_orders-nominal_capacity"
FEATURES = {
    RATIO: {"kind": "ratio", "x": "incoming_orders", "y": "nominal_capacity"},
    DIFFERENCE: {"kind": "diff", "x": "incoming_orders", "y": "nominal_capacity"},
}
VARIABLES = ("effective_capacity", "backlog", "cash")
SCALES = np.array([K0, K0, 20_000.0], dtype=float)
MIN_POST_TIME = 8.0
# Ratio representation exactly reproduces original world, as confirmed in A06.
TRUE_REPAIR = {
    **TRUTH["truth"],
    "baseline": 0.75, "excursion": 0.25,
    "orientation": 1.0,
    "minimum_fraction": DEFAULT_PARAMS["minimum_capacity_fraction"],
}


def config(probe: dict) -> dict:
    args = {
        "params": {
            "months": 24, "nominal_capacity": probe["capacity"],
            "market_shock_orders": probe["shock"],
        },
        "capacity_mode": "transient" if probe["kind"] == "pulse_holdout" else "constant",
    }
    if probe["kind"] == "pulse_holdout":
        for key in ("stress_start", "stress_end", "stress_capacity"):
            args[key] = probe[key]
    return args


def rival_repair(x: np.ndarray) -> dict:
    """Nonredundant 4D parameterization of original repair model."""
    tau, excursion, rate, gain = map(float, x)
    fixed_threshold = float(TRUTH["truth"]["threshold"])
    return {
        **TRUTH["truth"],
        "threshold": fixed_threshold,
        "baseline": tau - fixed_threshold * excursion,
        "excursion": excursion,
        "adjustment_rate": rate,
        "degradation": gain,
        "orientation": 1.0,
        "minimum_fraction": DEFAULT_PARAMS["minimum_capacity_fraction"],
    }


def world(probe: dict):
    return simulate_world_case(PRIMITIVE, TRUTH["truth"], **config(probe))[0]


def forecast(probe: dict, feature: str, repair: dict):
    return simulate_repair(PRIMITIVE, feature, FEATURES, repair=repair, **config(probe))[0]


def series(frame) -> np.ndarray:
    arr = frame.loc[frame.index >= MIN_POST_TIME, list(VARIABLES)].to_numpy(dtype=float)
    if arr.shape != (17, 3) or not np.isfinite(arr).all():
        raise AssertionError(f"Unexpected signal shape or values: {arr.shape}")
    return arr / SCALES


def diff_vec(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a - b).reshape(-1)


def rms(arr: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(arr))))


def fit_one_arm(arm: str, probes: tuple[dict, ...], observations: dict) -> tuple[dict, list]:
    true_threshold = float(TRUTH["truth"]["threshold"])
    # Strong matched warm start inherited from fixed-capacity equivalence in A06.
    matched_excursion = K0 * 0.25
    matched_baseline = -K0 * 0.25
    true_tau = matched_baseline + true_threshold * matched_excursion
    matched = (
        true_tau, matched_excursion,
        float(TRUTH["truth"]["adjustment_rate"]),
        float(TRUTH["truth"]["degradation"]),
    )
    initial_starts = [
        matched,
        (-15.0, 42.0, 0.50, 0.35),
        (10.0, 65.0, 0.70, 0.50),
    ]
    lows, highs = map(np.array, BOUNDS)
    train_truth = [series(observations[p["id"]]) for p in probes]
    calls = [0]

    def residual(x):
        calls[0] += 1
        cand = rival_repair(x)
        predicted = [
            series(forecast(p, DIFFERENCE, cand))
            for p in probes
        ]
        return np.concatenate([
            diff_vec(a, b) for a, b in zip(predicted, train_truth)
        ])

    trials = []
    for index, initial in enumerate(initial_starts):
        start = np.clip(np.array(initial, dtype=float), lows + 1e-5, highs - 1e-5)
        before = calls[0]
        fit = least_squares(
            residual, start, bounds=(lows, highs), method="trf",
            max_nfev=MAX_NFEV_PER_START,
            ftol=1e-8, xtol=1e-8, gtol=1e-8,
            diff_step=1e-4,
        )
        candidate = {
            "arm": arm, "start": index, "success": bool(fit.success),
            "message": str(fit.message),
            "nfev_scipy": int(fit.nfev),
            "residual_calls_total_with_derivatives": calls[0] - before,
            "train_rmse": rms(fit.fun),
            "tau": float(fit.x[0]), "excursion": float(fit.x[1]),
            "adjustment_rate": float(fit.x[2]), "degradation": float(fit.x[3]),
            "at_parameter_boundary": bool(
                np.any(np.abs(fit.x - lows) < 1e-3)
                or np.any(np.abs(fit.x - highs) < 1e-3)
            ),
        }
        trials.append(candidate)
    # Selection by training error only, deterministic tie break.
    best = min(trials, key=lambda r: (r["train_rmse"], r["start"]))
    return best, trials


def text_file(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def csv_file(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No rows to export")
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out: Path) -> dict:
    validate_disjointness()
    out.mkdir(parents=True, exist_ok=True)
    all_training = {p["id"]: p for arm in TRAINING.values() for p in arm}

    # TRAINING WORLD data are permitted for adversarial calibration.
    observed_training = {id: world(p) for id, p in all_training.items()}
    true_fit_errors = {
        id: rms(diff_vec(series(observed_training[id]),
                         series(forecast(p, RATIO, TRUE_REPAIR))))
        for id, p in all_training.items()
    }
    if max(true_fit_errors.values()) > NUMERICAL_FLOOR:
        raise AssertionError(f"Original G5 ratio model did not match training worlds: {true_fit_errors}")

    fit_records, trained = [], {}
    for arm, probes in TRAINING.items():
        best, trials = fit_one_arm(arm, probes, observed_training)
        fit_records.extend(trials)
        trained[arm] = best
        print(f"Fitted arm {arm}: RMS={best['train_rmse']:.8g}, start={best['start']}", flush=True)

    # Stage 2: select probes by frozen candidate forecasts only.
    prediction_rows, selected = [], {}
    for arm, best in trained.items():
        x = np.array([best[k] for k in (
            "tau", "excursion", "adjustment_rate", "degradation")], dtype=float)
        adversary = rival_repair(x)
        forecasts = []
        for probe in HOLDOUTS:
            ratio_prediction = series(forecast(probe, RATIO, TRUE_REPAIR))
            diff_prediction = series(forecast(probe, DIFFERENCE, adversary))
            gap = rms(diff_vec(ratio_prediction, diff_prediction))
            forecasts.append({
                "arm": arm, "probe": probe["id"], "kind": probe["kind"],
                "stratum": probe["stratum"], "capacity": probe["capacity"],
                "shock": probe["shock"], "candidate_disagreement": gap,
            })
        prediction_rows.extend(forecasts)
        selected[arm] = select_diverse_holdouts(forecasts, MAX_SELECTED)

    # Persist pre-adjudication design before querying ANY held-out WORLD.
    pred_path = out / "candidate_only_probes.csv"
    csv_file(pred_path, prediction_rows)
    precommit = {
        "experiment": "A07",
        "commit_stage": "AFTER_FITTING_BEFORE_HOLDOUT_WORLD",
        "source": "Original CEI c0.0 corrected G5 equations reused from A06",
        "case": CASE_ID,
        "training": TRAINING, "holdouts": HOLDOUTS,
        "parameter_bounds": BOUNDS, "max_nfev_per_start": MAX_NFEV_PER_START,
        "optimizer": "scipy.optimize.least_squares TRF with three deterministic starts",
        "models": {"true_ratio": TRUE_REPAIR, "rival_difference": trained},
        "selection": selected,
        "candidate_predictions_sha256": sha(pred_path),
        "training_true_ratio_rmse": true_fit_errors,
        "numeric_floor": NUMERICAL_FLOOR,
        "practical_gap_not_noise_calibrated": PRACTICAL_GAP,
        "scientific_scope": "LOCAL_ADVERSARIAL_REFIT_TRAIN_TEST_NOT_FAMILY_IDENTIFIABILITY",
    }
    design_path = out / "design_frozen_before_holdout.json"
    text_file(design_path, precommit)

    # Stage 3: WORLD heldout queried only AFTER candidate-only probe selection.
    by_id = {p["id"]: p for p in HOLDOUTS}
    needed = set(name for values in selected.values() for name in values)
    heldout_world = {name: world(by_id[name]) for name in sorted(needed)}
    adjudicated = []
    for arm, best in trained.items():
        fitted = rival_repair(np.array(
            [best[k] for k in ("tau", "excursion", "adjustment_rate", "degradation")],
            dtype=float))
        for rank, pid in enumerate(selected[arm], 1):
            probe = by_id[pid]
            truth = series(heldout_world[pid])
            ratio = series(forecast(probe, RATIO, TRUE_REPAIR))
            diff = series(forecast(probe, DIFFERENCE, fitted))
            ratio_rmse = rms(diff_vec(truth, ratio))
            diff_rmse = rms(diff_vec(truth, diff))
            predicted = rms(diff_vec(ratio, diff))
            adjudicated.append({
                "arm": arm, "rank": rank, "probe": pid,
                "capacity": probe["capacity"], "shock": probe["shock"],
                "predicted_disagreement": predicted,
                "world_error_ratio": ratio_rmse,
                "world_error_refit_difference": diff_rmse,
                "adversarial_generalization_gap": diff_rmse - ratio_rmse,
                "local_numeric_separator": bool(
                    ratio_rmse <= NUMERICAL_FLOOR
                    and diff_rmse - ratio_rmse > NUMERICAL_FLOOR
                ),
                "practical_gap_exceeded": bool(
                    ratio_rmse <= NUMERICAL_FLOOR
                    and diff_rmse - ratio_rmse > PRACTICAL_GAP
                ),
            })

    fits_path = out / "fit_multistart.csv"
    holdout_path = out / "heldout_adjudication.csv"
    csv_file(fits_path, fit_records)
    csv_file(holdout_path, adjudicated)
    arm_results = {}
    for arm in TRAINING:
        selection = [r for r in adjudicated if r["arm"] == arm]
        fit = trained[arm]
        # Pragmatic threshold, not a formal model-fit or noise-calibrated criterion.
        train_credible = fit["train_rmse"] <= PRACTICAL_GAP
        arm_results[arm] = {
            "training_rmse": fit["train_rmse"],
            "train_credibility_heuristic": train_credible,
            "selected": selected[arm],
            "local_separators": sum(r["local_numeric_separator"] for r in selection),
            "above_practical_gap": sum(r["practical_gap_exceeded"] for r in selection),
            "max_out_of_sample_gap": max(r["adversarial_generalization_gap"] for r in selection),
            "interpretation": (
                "LOCAL_ADVERSARY_DISCRIMINATED"
                if train_credible and any(r["practical_gap_exceeded"] for r in selection)
                else "NO_STRONG_CLAIM_TRAIN_FIT_OR_SEPARATION_INSUFFICIENT"
            ),
        }

    summary = {
        "experiment": "A07",
        "computation_status": "COMPLETED",
        "scientific_claim": "FIXED_PARAMETER_DOMAIN_LOCAL_EVIDENCE_ONLY",
        "case": CASE_ID, "arms": arm_results,
        "adjudication": adjudicated,
        "limitations": [
            "The reference truth and true ratio parameters are known, not inferred blindly.",
            "The adversarial difference model is optimized only on training observations; holdout WORLD is not used during fitting or probe design.",
            "Three deterministic starts and finite fit budgets cannot certify a global adversarial optimum.",
            "The practical RMS threshold 0.01 is heuristic, not derived from observation noise or statistical power.",
            "Family-wide nonidentifiability cannot be inferred from an optimizer failure; nor can uniform identifiability from this separator.",
            "G5 historical experiment, outcomes and thresholds are untouched.",
        ],
        "files_sha256": {
            p.name: sha(p) for p in (pred_path, design_path, fits_path, holdout_path)
        },
        "github_sha": os.environ.get("GITHUB_SHA"),
    }
    text_file(out / "summary.json", summary)
    print(json.dumps({
        "computation_status": summary["computation_status"],
        "arms": arm_results,
    }, ensure_ascii=False), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/A07"))
    args = parser.parse_args()
    run(args.out)
