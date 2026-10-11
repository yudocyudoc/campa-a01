#!/usr/bin/env python3
"""A11 pre-decision analyst: fit observable A10 histories, forecast full closed loop.

No imports of W016 generator, true WORLD parameters, or future counterfactuals.
Both candidate policies and predicted endogenous orders are frozen before
adjudicator creates any intervention trajectories.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

from experiments.A10.analyst import load,optimize
from experiments.A10.contract import OBSERVED
from experiments.A11.contract import (
    NOISE_ARMS,OPTIONS,ABSTENTION_MARGIN,BASELINE,
    SNAPSHOT_FIELDS,FORECAST_FIELDS,forecast,select_policy,
)

TRAIN_COLS=("scenario",)+OBSERVED


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_snapshot(path):
    with path.open(newline="",encoding="utf-8") as fp:
        reader=csv.DictReader(fp)
        if tuple(reader.fieldnames)!=SNAPSHOT_FIELDS:
            raise ValueError("Invalid predecision schema")
        rows=list(reader)
    if len(rows)!=1:raise ValueError("Need one predecision snapshot")
    return {k:float(v) for k,v in rows[0].items()}


def analyze(public:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    source=json.loads((public/"manifest.json").read_text())
    if source["future_orders_in_public_data"] or source["future_outcomes_in_public_data"]:
        raise ValueError("Future outcome leakage declared in public manifest")
    if set(source["policy_options"])!=set(OPTIONS):
        raise ValueError("Policy menu mutated")
    for name,checksum in source["public_file_sha256"].items():
        if digest(public/name)!=checksum:raise ValueError("Modified predecision file")
    snapshot=read_snapshot(public/"predecision_snapshot.csv")
    by_arm={}
    trials=[]
    forecasts=[]
    for arm in NOISE_ARMS:
        train=load(public/f"train_{arm}.csv",TRAIN_COLS,5)
        if any(not k.startswith("T") for k in train):
            raise ValueError("Unexpected training scenario IDs")
        fits={}
        for family in ("diff_c","ratio_p"):
            best,runs=optimize(family,train)
            fits[family]=best
            trials.extend([{"arm":arm,**trial} for trial in runs])
        ordered=sorted(fits,key=lambda f:fits[f]["train_rms"])
        margin=fits[ordered[1]]["train_rms"]-fits[ordered[0]]["train_rms"]
        family=ordered[0] if margin>ABSTENTION_MARGIN else "ABSTAIN_UNRESOLVED"
        all_predictions={}
        terminal={}
        for candidate in ("diff_c","ratio_p"):
            params=fits[candidate]["params"]
            simulated={k:forecast(k,snapshot,params,candidate) for k in OPTIONS}
            all_predictions[candidate]=simulated
            terminal[candidate]={str(k):{
                "predicted_final_cash":simulated[k][-1]["cash"],
                "predicted_final_backlog":simulated[k][-1]["backlog"],
                "predicted_final_orders":simulated[k][-1]["incoming_orders"],
                "predicted_final_effective_capacity":simulated[k][-1]["effective_capacity"]
                } for k in OPTIONS}
            for k,rows in simulated.items():
                for row in rows:
                    forecasts.append({"arm":arm,"candidate_family":candidate,**row})
        policy=select_policy(
            all_predictions[family] if family!="ABSTAIN_UNRESOLVED" else {},
            family
        )
        by_arm[arm]={
            "fit_by_family":fits,"training_gap":margin,
            "abstention_threshold":ABSTENTION_MARGIN,
            "selected_family":family,"chosen_policy_k":policy,
            "benchmark_no_change_capacity":BASELINE,
            "predicted_terminal_by_family":terminal,
            "chosen_policy_rule":"max predicted cash_t24, tied -> smaller K; abstention -> K115",
        }
        print("A11_DECISION",json.dumps({
            "arm":arm,"selected_family":family,"margin":margin,
            "chosen_capacity":policy,"predicted_terminal":terminal.get(family),
        }),flush=True)
    predicted_path=out/"closedloop_forecasts.csv"
    fields=("arm","candidate_family")+FORECAST_FIELDS
    with predicted_path.open("w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=fields,extrasaction="raise")
        w.writeheader()
        w.writerows(forecasts)
    attempts_path=out/"training_optimizer_attempts.json"
    attempts_path.write_text(json.dumps(trials,indent=2,allow_nan=False)+"\n")
    report={
        "experiment":"A11","phase":"FORECASTS_FROZEN_BEFORE_ANY_INTERVENTION_WORLD",
        "selected_policies_by_arm":by_arm,
        "public_manifest_sha256":digest(public/"manifest.json"),
        "snapshot_sha256":digest(public/"predecision_snapshot.csv"),
        "forecast_sha256":digest(predicted_path),
        "attempts_sha256":digest(attempts_path),
        "NO_FUTURE_ORDERS_READ":True,
        "explicit_nonblind_assumption":"The business feedback equations and coefficients are stipulated; only the response model family and its parameters were fitted.",
    }
    (out/"analyst_freeze.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    if len(forecasts)!=len(NOISE_ARMS)*2*len(OPTIONS)*17:
        raise AssertionError("Missing intervention predictions")
    print("A11_FROZEN",len(forecasts),flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--public",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    analyze(a.public,a.out)
