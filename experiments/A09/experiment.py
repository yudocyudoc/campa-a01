#!/usr/bin/env python3
"""A09: replay exact frozen A08 models with internal states exposed, no refitting.

Separates model-level conditional algebra from the evidence present in finite,
discrete, partly inactive or clipped observations. Inputs and candidate scores
come from the 5 TRAIN + 17 HOLDOUT regimes of A08.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.A08.g5_extended_core import (
    build_world, build_repair_model, run_model, WORLD_CASES,
    DEFAULT_PARAMS,
)
from experiments.A08.design import TRAIN, PROBES
from experiments.A08.experiment import (
    FEATURE_IDS, SHAPES, probe_config, repair_parameters, VARS, SCALES,
)
from experiments.A09.regimes import (
    EPS, beta, world_excess, diff_c_excess, identify_regime,
    cross_k_slope_obstruction, distinct_values,
)

HERE = Path(__file__).resolve().parent
SOURCE = json.loads((HERE / "a08_frozen_fit.json").read_text(encoding="utf-8"))
WORLD = WORLD_CASES["W016"]
PRIMITIVE = WORLD["primitive"]
if PRIMITIVE != "first_order_relaxation":
    raise ValueError("Expected W016 first_order_relaxation")

BASE_FIELDS = (
    "incoming_orders", "nominal_capacity", "effective_capacity",
    "primitive_impact", "backlog", "cash",
)
FIELDS = {
    "world": BASE_FIELDS + ("hidden_signal", "hidden_excess", "hidden_state"),
    "diff_c": BASE_FIELDS + ("derived_signal", "stress_excess", "latent_state"),
    "ratio_p": BASE_FIELDS + ("derived_signal", "stress_excess", "latent_state"),
}
MINIMUM_FRACTION = float(DEFAULT_PARAMS["minimum_capacity_fraction"])
NUMERIC_TOL = 1e-7
EXPECTED_TIMES = 25
EXPECTED_OBS_COUNT = 17


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_csv(p: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Cannot export empty records")
    fields = tuple(rows[0])
    if any(tuple(r) != fields for r in rows):
        raise ValueError("Inconsistent CSV columns")
    with p.open("w", newline="", encoding="utf-8") as fp:
        w=csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(p: Path, d: dict) -> None:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
                 encoding="utf-8")


def simulate_internal(probe: dict, model: str):
    cfg = probe_config(probe)
    if model == "world":
        instance = build_world(
            PRIMITIVE, WORLD["truth"], **cfg
        )
    else:
        params = SOURCE[model]
        x = (params["tau"],params["rate"],params["gain"],params["shape"])
        fid = FEATURE_IDS[model]
        instance = build_repair_model(
            PRIMITIVE, fid, {fid: SHAPES[model]},
            repair=repair_parameters(model,x),
            **cfg
        )
    df, backend = run_model(
        instance, FIELDS[model], manager_name="a09_"+model
    )
    if len(df)!=EXPECTED_TIMES:
        raise ValueError(f"Wrong time grid {model}/{probe['id']} ({len(df)})")
    if any(not np.isfinite(df[name].to_numpy(dtype=float)).all()
           for name in FIELDS[model]):
        raise ValueError(f"Nonfinite internal observations {probe['id']} {model}")
    return df, backend


def frame_obs(frame):
    data=frame.loc[frame.index >= 8.0,list(VARS)].to_numpy(dtype=float)
    if data.shape != (EXPECTED_OBS_COUNT,3):
        raise ValueError(f"Unexpected observed shape: {data.shape}")
    return data / np.array(SCALES,dtype=float)


def rms(a, b):
    residual = np.asarray(a)-np.asarray(b)
    return float(np.sqrt(np.mean(residual*residual)))


def rows_for_model(probe,partition,model,df):
    out=[]
    for t,data in df.iterrows():
        demand=float(data["incoming_orders"])
        capacity=float(data["nominal_capacity"])
        impact=float(data["primitive_impact"])
        raw_signal=float(data["hidden_signal"] if model=="world" else data["derived_signal"])
        excess=float(data["hidden_excess"] if model=="world" else data["stress_excess"])
        reg=identify_regime(excess,impact,MINIMUM_FRACTION)
        prediction=(
            world_excess(demand,capacity,float(WORLD["truth"]["threshold"]))
            if model=="world"
            else (
                diff_c_excess(demand,capacity,
                  SOURCE["diff_c"]["shape"],SOURCE["diff_c"]["tau"])
                if model=="diff_c"
                else max(
                    demand/(capacity**SOURCE["ratio_p"]["shape"])-
                    SOURCE["ratio_p"]["tau"],0.0
                )
            )
        )
        if not math.isclose(excess,prediction,rel_tol=5e-8,abs_tol=NUMERIC_TOL):
            raise ValueError(
                f"Driver formula mismatch: {model}/{probe['id']}/{t}: "
                f"stored={excess} predicted={prediction}"
            )
        calculated=max(capacity*(1-impact),capacity*MINIMUM_FRACTION)
        effective=float(data["effective_capacity"])
        if not math.isclose(effective,calculated,rel_tol=1e-8,abs_tol=NUMERIC_TOL):
            raise ValueError(f"Clipping equation mismatch: {probe['id']}/{model}/{t}")
        out.append({
            "probe":probe["id"],"partition":partition,"model":model,
            "t":float(t),"demand":demand,"capacity":capacity,
            "effective_capacity":effective,"backlog":float(data["backlog"]),
            "cash":float(data["cash"]),"driver_signal":raw_signal,
            "excess":excess,"impact":impact,
            "latent_stock":float(data["hidden_state"] if model=="world" else data["latent_state"]),
            "input_state":reg["input_state"],
            "output_state":reg["output_state"],
            "active_unclipped":reg["active_unclipped"],
        })
    return out


def check_euler_identity(rows,model):
    # Stocks in G5 use dt=1 with a first-order relaxation,
    # so impact_(t+1) = (1-a)impact_t + a*gain*stress_t.
    if model=="world":
        gain=float(WORLD["truth"]["degradation"])
        rate=float(WORLD["truth"]["adjustment_rate"])
    else:
        gain=float(SOURCE[model]["gain"])
        rate=float(SOURCE[model]["rate"])
    residual=[]
    for t in range(len(rows)-1):
        p,q=rows[t],rows[t+1]
        if abs(q["t"] -p["t"]-1.0)>1e-8:
            raise ValueError("Non-unit time step")
        expected=(1-rate)*p["impact"]+rate*gain*p["excess"]
        residual.append(abs(q["impact"]-expected))
    return max(residual)


def summarise_regimes(rows,partition,probe,model):
    view=[r for r in rows if r["t"]>=8.0]
    return {
        "partition":partition,"probe":probe,"model":model,
        "total_post_t8":len(view),
        "active_input_n":sum(r["input_state"]=="active" for r in view),
        "inactive_input_n":sum(r["input_state"]=="inactive" for r in view),
        "clipped_output_n":sum(r["output_state"]=="clipped" for r in view),
        "active_unclipped_n":sum(r["active_unclipped"] for r in view),
        "inactive_and_unclipped_n":sum(
            r["input_state"]=="inactive" and r["output_state"]=="unclipped"
            for r in view
        ),
        "distinct_demand_when_active_unclipped":
            distinct_values([r["demand"] for r in view if r["active_unclipped"]]),
        "unique_actual_K":len({round(r["capacity"],7) for r in view}),
    }


def run(out: Path):
    out.mkdir(parents=True,exist_ok=True)
    scenarios=[("train",p) for p in TRAIN]+[("holdout",p) for p in PROBES]
    if len(scenarios)!=22:
        raise ValueError("Expected 22 distinct A08 regimes")
    trajectory_rows=[]
    regime_rows=[]
    score_rows=[]
    euler_rows=[]
    witness=[]
    for partition,probe in scenarios:
        frames={}
        internal={}
        for model in ("world","diff_c","ratio_p"):
            df,backend=simulate_internal(probe,model)
            frames[model]=df
            values=rows_for_model(probe,partition,model,df)
            internal[model]=values
            trajectory_rows.extend(values)
            regime_rows.append(summarise_regimes(values,partition,probe["id"],model))
            euler_rows.append({
                "partition":partition,"probe":probe["id"],"model":model,
                "backend":backend,"euler_max_abs_residual":check_euler_identity(values,model)
            })
        world_view=frame_obs(frames["world"])
        for model in ("diff_c","ratio_p"):
            score=rms(world_view,frame_obs(frames[model]))
            score_rows.append({
                "partition":partition,"probe":probe["id"],"model":model,
                "rms_vs_world":score,
                "rms_above_1e_8":score>1e-8,
                "rms_above_0_01_heuristic":score>0.01,
            })
        # Retrospective common support, not a prospective probe selector:
        for a,b in zip(internal["world"],internal["diff_c"]):
            if (a["t"]>=8 and a["active_unclipped"] and b["active_unclipped"]):
                if not math.isclose(a["demand"],b["demand"],abs_tol=1e-8):
                    raise ValueError("Demand differs across structural candidates")
                witness.append({"partition":partition,"probe":probe["id"],"t":a["t"],
                                "K":round(a["capacity"],7),"D":a["demand"]})

    world_gain=float(WORLD["truth"]["degradation"])
    proof=cross_k_slope_obstruction([115.,145.],world_gain)
    supported={}
    for k in (115.,145.):
        data=[r["D"] for r in witness if r["partition"]=="train" and abs(r["K"]-k)<1e-6]
        supported[str(k)]={
            "joint_active_unclipped_training_samples":len(data),
            "distinct_demand_values":distinct_values(data),
            "sampled_support_for_open_interval_assumption":False,
        }
    # Finite samples alone cannot establish openness, even when D varies.
    proof["observational_support_counts"]=supported
    proof["fitted_rival_rate"]=SOURCE["diff_c"]["rate"]
    proof["world_rate"]=WORLD["truth"]["adjustment_rate"]
    proof["equal_relaxation_rate_assumption_satisfied_by_A08_fit"]=abs(
        float(SOURCE["diff_c"]["rate"])-float(WORLD["truth"]["adjustment_rate"])
    )<=1e-8
    proof["certificate_for_actual_finite_A08_observations"]=False
    proof["reason_no_finite_certificate"]=(
        "Finite sampled demand histories do not establish an open intervention interval; "
        "A08 rival relaxation differs from the world rate, and clipping/inactivity "
        "obstruct inference from observed effective capacity."
    )
    proof["no_global_optimizer_or_new_world_generated"]=True

    by_model={}
    for model in ("diff_c","ratio_p"):
        train=[r["rms_vs_world"] for r in score_rows if r["partition"]=="train" and r["model"]==model]
        held=[r["rms_vs_world"] for r in score_rows if r["partition"]=="holdout" and r["model"]==model]
        by_model[model]={
            "train_rms_all_points":float(np.sqrt(np.mean(np.square(train)))),
            "holdout_median_rms":float(np.median(held)),
            "holdout_max_rms":max(held),
            "holdout_heuristic_gt_0_01":sum(v>0.01 for v in held),
            "holdout_n":len(held),
        }
    # The A08 fitting objective concatenates same-size residuals across probes
    # so RMS across per-probe squared RMS reproduces its aggregate training RMS.
    for model in by_model:
        ref=SOURCE[model]
        if abs(by_model[model]["train_rms_all_points"]-ref["train_rms"])>5e-7:
            raise AssertionError(f"{model} training A08 anchor mismatch")
        if abs(by_model[model]["holdout_median_rms"]-ref["holdout_median_rms"])>5e-7:
            raise AssertionError(f"{model} median A08 anchor mismatch")
        if abs(by_model[model]["holdout_max_rms"]-ref["holdout_max_rms"])>5e-7:
            raise AssertionError(f"{model} maximum A08 anchor mismatch")
        if by_model[model]["holdout_heuristic_gt_0_01"]!=ref["holdout_above_0_01"]:
            raise AssertionError(f"{model} heldout active gap count disagrees with A08")
    if max(r["euler_max_abs_residual"] for r in euler_rows)>5e-6:
        raise AssertionError("Internal first-order Euler identity failed")

    trace=out/"internal_trajectories.csv"
    regimes=out/"regime_counts.csv"
    scores=out/"a08_scores_rechecked.csv"
    eulers=out/"euler_identity.csv"
    write_csv(trace,trajectory_rows)
    write_csv(regimes,regime_rows)
    write_csv(scores,score_rows)
    write_csv(eulers,euler_rows)
    result={
        "experiment":"A09","execution":"COMPLETED",
        "scope":"POSTHOC_CONDITIONAL_STRUCTURAL_ANALYSIS_W016_NOT_BLIND_IDENTIFICATION",
        "sources":{"A08":SOURCE,"scenarios":22,"models":["world","diff_c","ratio_p"]},
        "algebraic_conditional_proposition":proof,
        "scores_reproduced":by_model,
        "euler_max_residual":max(r["euler_max_abs_residual"] for r in euler_rows),
        "input_active_unclipped_by_model":{
            model:sum(r["active_unclipped_n"] for r in regime_rows if r["model"]==model)
            for model in ("world","diff_c","ratio_p")
        },
        "clips_by_model":{
            model:sum(r["clipped_output_n"] for r in regime_rows if r["model"]==model)
            for model in ("world","diff_c","ratio_p")
        },
        "limitations":[
            "Uses oracle-only internal states; not implementable from external measurements without observability assumptions.",
            "Forcing-map slope incompatibility is conditional on active/unclipped open demand intervals and shared relaxation rate.",
            "The A08 best-fit rival has a different relaxation rate; theorem does not directly certify finite observed trajectories.",
            "Zero RMS can arise from inactive or clipped regions; analyze each axis separately.",
            "Retrospective regime labels must not be used to tune probes in A08 or retroactively validate discovery.",
            "No globally certified numerical lower bound, no calibrated noise, and no new worlds.",
        ],
        "file_sha256":{p.name:file_hash(p) for p in (trace,regimes,scores,eulers)}
    }
    write_json(out/"summary.json",result)
    print(json.dumps({
        "execution":result["execution"],
        "conditional_model_obstruction":proof["conditional_model_level_obstruction"],
        "finite_data_certificate":proof["certificate_for_actual_finite_A08_observations"],
        "training_support":supported,
        "model_scores":by_model,
        "clip_counts":result["clips_by_model"],
        "euler_residual":result["euler_max_residual"],
    },ensure_ascii=False),flush=True)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=Path("results/A09"))
    args=parser.parse_args()
    run(args.out)
