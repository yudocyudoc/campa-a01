#!/usr/bin/env python3
"""A10 analyst: no WORLD import or true parameters, no access to holdout labels.

Fit candidate input-output dynamics using TRAIN external observations ONLY;
predict FULL 17 holdouts conditional on observed future orders/capacity inputs.
A decision may be ABSTAIN. All evidence labels remain outside this process.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.optimize import differential_evolution,least_squares
from experiments.A10.contract import (
    OBSERVED,INPUTS,TARGET,START_EVAL,MIN_CAPACITY_FRACTION,
    NOISE_LEVELS,NOISE_SEED,TRAIN_COUNT,HOLDOUT_COUNT,TIMES,
    NUMERIC_TOL,DECISION_GAP,FAMILIES,DE_MAXITER,DE_POPSIZE,
    LOCAL_MAX_NFEV,simulate_fraction,forcing,candidate_activity,validate_contract_fields,
)
# No import of generator, W016, WORLD_CASES, or prior latent instrumentation.
TRAIN_COLUMNS=("scenario",)+OBSERVED
HOLDOUT_COLUMNS=("scenario",)+INPUTS
PRED_COLUMNS=("condition","scenario","t","capacity","orders",
    "predicted_fraction_diff_c","predicted_fraction_ratio_p",
    "predicted_capacity_diff_c","predicted_capacity_ratio_p",
    "model_disagreement_fraction","both_inputs_inactive",
    "diff_c_input_active","ratio_p_input_active",
    "diff_c_output_clipped_predicted","ratio_p_output_clipped_predicted")


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path:Path,fields:tuple[str,...],expected:int)->dict[str,list[dict]]:
    with path.open("r",encoding="utf-8",newline="") as fp:
        reader=csv.DictReader(fp)
        validate_contract_fields(reader.fieldnames,fields)
        all_rows=list(reader)
    if len(all_rows)!=expected*TIMES:
        raise ValueError(f"{path}: expected {expected*TIMES} rows, got {len(all_rows)}")
    groups=defaultdict(list)
    for raw in all_rows:
        scenario=raw["scenario"]
        converted={"scenario":scenario}
        for name in fields[1:]:
            v=raw[name]
            if not v and name=="initial_effective_capacity":
                converted[name]=""
            else:
                converted[name]=float(v)
        groups[scenario].append(converted)
    if len(groups)!=expected:
        raise ValueError("Wrong number of scenarios")
    for scenario,rows in groups.items():
        rows.sort(key=lambda r:r["t"])
        if len(rows)!=TIMES or any(abs(r["t"]-t)>1e-8 for t,r in enumerate(rows)):
            raise ValueError(f"Scenario {scenario} incomplete")
        if TARGET not in rows[0] and ("initial_effective_capacity" not in rows[0] or
                                        rows[0]["initial_effective_capacity"]==""):
            raise ValueError("No t0 observed initial condition")
        if "initial_effective_capacity" in rows[0]:
            if any(r["initial_effective_capacity"]!="" for r in rows[1:]):
                raise ValueError("Holdout future outcomes/initial states leaked")
    return dict(sorted(groups.items()))


def rms(array): return float(np.sqrt(np.mean(np.square(np.asarray(array,dtype=float)))))


def optimize(kind:str,groups:dict[str,list[dict]]):
    low,high=FAMILIES[kind]["bounds"]
    observations={key:np.array(
        [r[TARGET]/r["nominal_capacity"] for r in rows if r["t"]>=START_EVAL]
    ) for key,rows in groups.items()}
    calls=[0]
    def residual(p):
        calls[0]+=1
        errors=[]
        for key,rows in groups.items():
            forecast=simulate_fraction(rows,p,kind)[int(START_EVAL):]
            errors.extend(np.asarray(forecast)-observations[key])
        arr=np.asarray(errors,dtype=float)
        if not np.all(np.isfinite(arr)): raise ValueError("Nonfinite optimizer objective")
        return arr
    trials=[]
    de=differential_evolution(
        lambda p:rms(residual(p)),list(zip(low,high)),
        maxiter=DE_MAXITER,popsize=DE_POPSIZE,
        seed=NOISE_SEED,polish=False,tol=0.001,
        workers=1,updating="immediate",
    )
    trials.append({
        "family":kind,"method":"DE","start":"seed","train_rms":float(de.fun),
        "nfev":int(de.nfev),"calls_including_jacobian":int(calls[0]),
        "success":bool(de.success),"params":list(map(float,de.x)),
    })
    starts=[de.x,*FAMILIES[kind]["starts"]]
    for i,start in enumerate(starts):
        before=calls[0]
        fit=least_squares(
            residual,np.asarray(start,dtype=float),bounds=(low,high),
            method="trf",max_nfev=LOCAL_MAX_NFEV,
            ftol=1e-9,xtol=1e-9,gtol=1e-9,diff_step=1e-4,
        )
        trials.append({
            "family":kind,"method":"TRF","start":str(i),"train_rms":rms(fit.fun),
            "nfev":int(fit.nfev),"calls_including_jacobian":int(calls[0]-before),
            "success":bool(fit.success),"params":list(map(float,fit.x)),
        })
    best=min(trials,key=lambda r:(r["train_rms"],r["method"]!="TRF",r["start"]))
    return best,trials


def save_csv(path,rows,fields):
    with path.open("w",encoding="utf-8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=fields,extrasaction="raise")
        w.writeheader()
        w.writerows(rows)


def analyze(public:Path,out:Path)->dict:
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((public/"public_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("experiment")!="A10" or not manifest.get("outcome_withheld_after_initial_t0"):
        raise ValueError("Missing sealed-outcome public contract")
    if "generator_true_feature" in manifest or "generator_family" in manifest:
        raise ValueError("Oracle details leaked in manifest")
    holdouts=load(public/"holdout_inputs.csv",HOLDOUT_COLUMNS,HOLDOUT_COUNT)
    if any(not k.startswith("H") for k in holdouts):
        raise ValueError("Unexpected holdout IDs")
    results={}
    rows_pred=[]
    all_tries=[]
    for level in NOISE_LEVELS:
        condition="noiseless" if level==0 else "noisy_1pct"
        train=load(public/f"train_{condition}.csv",TRAIN_COLUMNS,TRAIN_COUNT)
        if any(not k.startswith("T") for k in train): raise ValueError("Unexpected train IDs")
        trained={}
        for kind in FAMILIES:
            best,attempts=optimize(kind,train)
            trained[kind]=best
            all_tries.extend([{"condition":condition,**entry} for entry in attempts])
        ranking=sorted(FAMILIES,key=lambda kind:trained[kind]["train_rms"])
        first,second=ranking
        margin=trained[second]["train_rms"]-trained[first]["train_rms"]
        decision=first if margin>DECISION_GAP else "ABSTAIN_UNRESOLVED"
        stats=[]
        for scenario,items in holdouts.items():
            p={k:simulate_fraction(items,trained[k]["params"],k) for k in FAMILIES}
            informative=0
            both_inactive=0
            disagreements=[]
            for index,row in enumerate(items):
                d,k=row["incoming_orders"],row["nominal_capacity"]
                active={name:candidate_activity(d,k,trained[name]["params"],name)
                        for name in FAMILIES}
                clip={name:p[name][index]<=MIN_CAPACITY_FRACTION+NUMERIC_TOL
                      for name in FAMILIES}
                disagreement=abs(p["diff_c"][index]-p["ratio_p"][index])
                if index>=int(START_EVAL):
                    disagreements.append(disagreement)
                    both_inactive+=not any(active.values())
                    informative+=bool(disagreement>DECISION_GAP and not all(clip.values()))
                rows_pred.append({
                    "condition":condition,"scenario":scenario,"t":row["t"],
                    "capacity":k,"orders":d,
                    "predicted_fraction_diff_c":p["diff_c"][index],
                    "predicted_fraction_ratio_p":p["ratio_p"][index],
                    "predicted_capacity_diff_c":k*p["diff_c"][index],
                    "predicted_capacity_ratio_p":k*p["ratio_p"][index],
                    "model_disagreement_fraction":disagreement,
                    "both_inputs_inactive":not any(active.values()),
                    "diff_c_input_active":active["diff_c"],
                    "ratio_p_input_active":active["ratio_p"],
                    "diff_c_output_clipped_predicted":clip["diff_c"],
                    "ratio_p_output_clipped_predicted":clip["ratio_p"],
                })
            stats.append({
                "scenario":scenario,"post_t8_informative_predicted":informative,
                "post_t8_both_inactive_predicted":both_inactive,
                "post_t8_mean_candidate_disagreement":float(np.mean(disagreements)),
                "post_t8_max_candidate_disagreement":max(disagreements),
            })
        results[condition]={
            "fit_by_family":trained,
            "selected_from_training_only":decision,
            "training_rms_gap":margin,
            "threshold_heuristic":DECISION_GAP,
            "holdout_selection_source":"candidate predictions only, no labels",
            "scenario_informativeness":stats,
        }
        print(json.dumps({
            "condition":condition,
            "decision":decision,
            "fit":{k:trained[k]["train_rms"] for k in FAMILIES},
            "margin":margin,
            "predicted_informative":sum(x["post_t8_informative_predicted"] for x in stats),
        }),flush=True)
    preds=out/"predicted_all_holdouts.csv"
    save_csv(preds,rows_pred,PRED_COLUMNS)
    trials_path=out/"training_optimizers.json"
    trials_path.write_text(json.dumps(all_tries,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    summary={
        "experiment":"A10","analysis_status":"COMPLETED",
        "epistemic_claim":"CONDITIONAL_OBSERVABLE_INPUT_OUTPUT_COMPARISON_NOT_CAUSAL_DISCOVERY",
        "analyst_has_no_WORLD_or_holdout_labels":True,
        "known_source_limit":"Public repository historically contains the WORLD generator, but the analysis job has only A10 code and packaged data.",
        "holdout_inputs_are_endogenous":True,
        "models_use_conditional_orders_and_capacity_not_autonomous_forecasts":True,
        "uses_no_hidden_variables":True,
        "noise_conditions":results,
        "limitations":[
            "Training and holdout have shared synthetic generator and same world W016.",
            "Observed holdout incoming_orders are endogenous to the real system; this is a conditional input-output prediction with future covariates, not an intervention forecast.",
            "Candidate first-order structure and capacity floor are supplied to the analyst; model family discovery is not blind.",
            "Observed capacity is the outcome to fit; no latent hidden_excess/impact from oracle is used.",
            "Noise injected only on observed effective capacity, not business inputs; power not calibrated.",
            "Training error rankings do not prove unique mechanism identity; ambiguous cases explicitly abstain.",
            "All 17 holdouts are evaluated by a separate adjudicator, not selected ex post.",
        ],
        "data_sha256":{
            p.name:sha(p) for p in (
                public/"public_manifest.json",
                public/"train_noiseless.csv",
                public/"train_noisy_1pct.csv",
                public/"holdout_inputs.csv",
            )
        },
        "prediction_sha256":sha(preds),
    }
    target=out/"analyst_report.json"
    target.write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--public",type=Path,required=True)
    parser.add_argument("--out",type=Path,default=Path("results/A10/analyst"))
    opt=parser.parse_args()
    analyze(opt.public,opt.out)
