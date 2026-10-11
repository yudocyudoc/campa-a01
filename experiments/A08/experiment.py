#!/usr/bin/env python3
"""A08: generalized adversaries, nonredundant parameterization, 17 full holdouts.

Original G5 world/stock flow model is unchanged; G5 model driver constructors are
extended ONLY with diff_c and ratio_p (g5_extended_core.py). No claim of a
certified global minimum or blind oracle-independent inference is made.
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
from scipy.optimize import differential_evolution, least_squares

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.A08.g5_extended_core import (  # noqa: E402
    DEFAULT_PARAMS, WORLD_CASES, simulate_world_case, simulate_repair,
)
from experiments.A08.design import (  # noqa: E402
    TRAIN, PROBES, FAMILIES, DE_MAXITER, DE_POPSIZE, DE_SEED,
    LOCAL_MAX_NFEV, NOISELESS_TOL, PRACTICAL_GAP, VARS, SCALES,
    MIN_TIME, validate_design,
)

CASE = "W016"
WORLD = WORLD_CASES[CASE]
PRIMITIVE = WORLD["primitive"]
if PRIMITIVE != "first_order_relaxation":
    raise ValueError("A08 W016 family mismatch")
THRESHOLD = float(WORLD["truth"]["threshold"])
TRUE_TAU_RATIO = 0.75 + 0.25 * THRESHOLD
TRUE_GAIN_RATIO = float(WORLD["truth"]["degradation"]) / 0.25
TRUE_RATE = float(WORLD["truth"]["adjustment_rate"])
TARGET = "effective_capacity"
SHAPES = {
    "diff_c": {
        "kind": "diff_c", "x": "incoming_orders", "y": "nominal_capacity"
    },
    "ratio_p": {
        "kind": "ratio_p", "x": "incoming_orders", "y": "nominal_capacity"
    },
}
FEATURE_IDS = {
    "diff_c": "diff_c::incoming_orders-c*nominal_capacity",
    "ratio_p": "ratio_p::incoming_orders/nominal_capacity**p",
}


def probe_config(probe: dict) -> dict:
    params = {
        "months": 24,
        "nominal_capacity": probe["capacity"],
        "market_shock_orders": probe["shock"],
    }
    pulse = probe["kind"] == "pulse_holdout"
    opts = {"params": params, "capacity_mode": "transient" if pulse else "constant"}
    if pulse:
        opts.update({k: probe[k] for k in ("stress_start", "stress_end", "stress_capacity")})
    return opts


def sim_world(probe: dict):
    return simulate_world_case(PRIMITIVE, WORLD["truth"], **probe_config(probe))[0]


def repair_parameters(family: str, params) -> dict:
    """Exactly three effective dynamic parameters, plus one driver shape."""
    tau, rate, gain, shape = map(float, params)
    repair = {
        **WORLD["truth"],
        "threshold": THRESHOLD,
        "baseline": tau - THRESHOLD,
        "excursion": 1.0,
        "orientation": 1.0,
        "adjustment_rate": rate,
        "degradation": gain,
        "minimum_fraction": DEFAULT_PARAMS["minimum_capacity_fraction"],
    }
    if family == "diff_c":
        repair["capacity_coefficient"] = shape
    elif family == "ratio_p":
        repair["capacity_exponent"] = shape
    else:
        raise ValueError(family)
    return repair


def sim_candidate(family: str, params, probe: dict):
    feature_id = FEATURE_IDS[family]
    return simulate_repair(
        primitive=PRIMITIVE,
        feature_id=feature_id,
        feature_meta={feature_id: SHAPES[family]},
        repair=repair_parameters(family, params),
        **probe_config(probe),
    )[0]


def frame_matrix(frame) -> np.ndarray:
    arr = frame.loc[frame.index >= MIN_TIME, list(VARS)].to_numpy(dtype=float)
    if arr.shape != (17, 3) or not np.all(np.isfinite(arr)):
        raise ValueError(f"Nonfinite or wrong observation shape: {arr.shape}")
    return arr / np.asarray(SCALES)


def rms(residual) -> float:
    arr = np.asarray(residual, dtype=float).ravel()
    return float(np.sqrt(np.mean(arr * arr)))


def delta(a, b):
    return (a - b).reshape(-1)


def save_json(path: Path, obj: object) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def save_csv(path: Path, records: list[dict]) -> None:
    if not records:
        raise ValueError("Cannot write empty CSV")
    fields = tuple(records[0])
    if any(tuple(record) != fields for record in records):
        raise ValueError("CSV fields changed across rows")
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_family(family: str, train_truth: list[np.ndarray]) -> tuple[dict,list[dict]]:
    low, high = FAMILIES[family]["bounds"]
    bounds = list(zip(low, high))
    records = []
    counter = [0]
    def residual_vector(values):
        counter[0] += 1
        candidate = [
            frame_matrix(sim_candidate(family, values, p))
            for p in TRAIN
        ]
        arr = np.concatenate([
            delta(x, y) for x, y in zip(candidate, train_truth)
        ])
        if not np.all(np.isfinite(arr)):
            raise ValueError("Nonfinite optimizer residual")
        return arr

    def objective(values):
        return rms(residual_vector(values))

    global_run = differential_evolution(
        objective, bounds, seed=DE_SEED, maxiter=DE_MAXITER,
        popsize=DE_POPSIZE, polish=False,
        workers=1, updating="immediate", tol=0.001,
    )
    records.append({
        "family": family, "method": "differential_evolution",
        "start": "seed_20261011", "solver_success": bool(global_run.success),
        "status_message": str(global_run.message),
        "solver_nfev": int(global_run.nfev),
        "actual_residual_calls": int(counter[0]),
        "train_rms": float(global_run.fun),
        "tau": float(global_run.x[0]), "rate": float(global_run.x[1]),
        "gain": float(global_run.x[2]), "shape": float(global_run.x[3]),
    })

    # Three deterministic local fits, initialized separately. Ground truth
    # is *not* supplied as a start to the optimizer, even for nested ratio_p.
    starts = [
        tuple(float(v) for v in global_run.x),
        *FAMILIES[family]["local_starts"],
    ]
    for i, start in enumerate(starts):
        before = counter[0]
        local = least_squares(
            residual_vector, np.array(start, dtype=float),
            bounds=(np.asarray(low), np.asarray(high)),
            method="trf", max_nfev=LOCAL_MAX_NFEV,
            ftol=1e-9, xtol=1e-9, gtol=1e-9,
            diff_step=1e-4,
        )
        records.append({
            "family": family, "method": "least_squares",
            "start": str(i), "solver_success": bool(local.success),
            "status_message": str(local.message),
            "solver_nfev": int(local.nfev),
            "actual_residual_calls": int(counter[0] - before),
            "train_rms": rms(local.fun),
            "tau": float(local.x[0]), "rate": float(local.x[1]),
            "gain": float(local.x[2]), "shape": float(local.x[3]),
        })
    best = min(records, key=lambda r: (r["train_rms"],r["method"]!="least_squares",r["start"]))
    return best, records


def execute(out: Path) -> dict:
    validate_design()
    out.mkdir(parents=True, exist_ok=True)

    # TRAIN observations are admissible; no HOLDOUT oracle is queried here.
    truth_frames = [frame_matrix(sim_world(p)) for p in TRAIN]

    # Nested true ratio model is an analytic, separately flagged control:
    # this is NOT a recovery by the optimizer.
    true_nested = np.array([TRUE_TAU_RATIO, TRUE_RATE, TRUE_GAIN_RATIO, 1.0])
    nested_train_rmse = rms(
        np.concatenate([
            delta(frame_matrix(sim_candidate("ratio_p",true_nested,p)), obs)
            for p,obs in zip(TRAIN,truth_frames)
        ])
    )
    if nested_train_rmse > NOISELESS_TOL:
        raise AssertionError(
            f"Analytically nested true ratio did not reproduce WORLD: {nested_train_rmse}"
        )

    fits, best_params = [], {}
    for family in FAMILIES:
        best, trials = fit_family(family, truth_frames)
        fits.extend(trials)
        best_params[family] = best
        print(
            f"FIT {family}: RMS={best['train_rms']:.9g}; "
            f"driver shape={best['shape']:.9g}; start={best['start']}",
            flush=True,
        )

    # Persist optimized parameters and design while holdout WORLD is still unqueried.
    fit_file = out / "fit_attempts.csv"
    save_csv(fit_file, fits)
    frozen_file = out / "design_before_holdout.json"
    save_json(frozen_file, {
        "phase": "TRAINING_AND_FIT_DONE_BEFORE_ANY_HOLDOUT_WORLD",
        "case": CASE,
        "world_is_known_not_blind": True,
        "original_g5_equations": True,
        "design": {
            "training": TRAIN, "holdouts": PROBES,
            "families_and_bounds": FAMILIES,
            "global_optimizer": {
                "name": "scipy.differential_evolution",
                "seed": DE_SEED, "maxiter": DE_MAXITER,
                "popsize": DE_POPSIZE, "polish": False,
            },
            "local_max_nfev": LOCAL_MAX_NFEV,
            "scales": SCALES, "variables": VARS,
            "numeric_tolerance": NOISELESS_TOL,
            "heuristic_not_noise_calibrated": PRACTICAL_GAP,
        },
        "best_training_only": best_params,
        "nested_ratio_analytic_control_rmse": nested_train_rmse,
        "fit_attempts_sha256": sha256(fit_file),
        "github_sha": os.getenv("GITHUB_SHA"),
    })

    # Now evaluate ALL 17 holdouts, not a selected top four.
    world_holdouts = {p["id"]: frame_matrix(sim_world(p)) for p in PROBES}
    holdout_rows = []
    for family,best in best_params.items():
        values = [best[k] for k in ("tau","rate","gain","shape")]
        for p in PROBES:
            y=world_holdouts[p["id"]]
            pred=frame_matrix(sim_candidate(family,values,p))
            holdout_rows.append({
                "family": family, "probe": p["id"],
                "stratum": p["stratum"], "kind": p["kind"],
                "capacity": p["capacity"], "shock": p["shock"],
                "holdout_rms": rms(delta(y,pred)),
                "above_numeric_floor": rms(delta(y,pred)) > NOISELESS_TOL,
                "above_heuristic_gap": rms(delta(y,pred)) > PRACTICAL_GAP,
            })
    holdout_file = out / "all_17_holdouts.csv"
    save_csv(holdout_file,holdout_rows)

    family_results={}
    for family,best in best_params.items():
        rr=[r for r in holdout_rows if r["family"]==family]
        values=np.array([r["holdout_rms"] for r in rr])
        family_results[family]={
            "best_fit":best,
            "train_rms":float(best["train_rms"]),
            "holdout_count":len(rr),
            "holdout_mean_rms":float(values.mean()),
            "holdout_median_rms":float(np.median(values)),
            "holdout_max_rms":float(values.max()),
            "above_numeric_floor":int(np.sum(values>NOISELESS_TOL)),
            "above_heuristic_gap":int(np.sum(values>PRACTICAL_GAP)),
            "numerical_training_separated":bool(best["train_rms"]>NOISELESS_TOL),
            "scientific_limit":"SEARCHED_MINIMUM_NOT_CERTIFIED_GLOBAL_MINIMUM",
        }

    result = {
        "experiment": "A08",
        "computation": "COMPLETED",
        "scientific_scope": "ONE_KNOWN_SYNTHETIC_WORLD_TWO_NESTED_OR_GENERALIZED_FAMILIES",
        "analytic_nested_ratio_control_rms_train":nested_train_rmse,
        "family_results":family_results,
        "limitations":[
            "All 17 holdouts are scored; no top-4 max selection.",
            "Original true-world parameters are known; this is not blind causal recovery.",
            "Global heuristic and local optimizer cannot certify global error lower bounds.",
            "No calibrated noise/power or evidence on other 39 worlds.",
            "For ratio_p, p=1 contains truth; near-zero training RMS is an expected nested control.",
            "The full stock-flow model can saturate and mask raw-driver differences.",
            "Historical G5/A07 data and classifications are unchanged.",
        ],
        "files_sha256":{
            p.name:sha256(p) for p in (fit_file,frozen_file,holdout_file)
        },
        "github_sha":os.getenv("GITHUB_SHA"),
    }
    save_json(out/"summary.json",result)
    print(json.dumps({
        "computation":result["computation"],
        "nested_control":nested_train_rmse,
        "families":{k:{
            "training":r["train_rms"],"holdout_median":r["holdout_median_rms"],
            "holdout_max":r["holdout_max_rms"],"above_heuristic":r["above_heuristic_gap"],
            "shape":r["best_fit"]["shape"]
        } for k,r in family_results.items()},
    },ensure_ascii=False),flush=True)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=Path("results/A08"))
    args=parser.parse_args()
    execute(args.out)
