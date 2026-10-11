#!/usr/bin/env python3
"""A10 adjudicator: only here may holdout outcomes and generator key be joined.

No selection, fitting or tuning can occur here. Analyst output must already be
frozen and supplied as a separate artifact from the isolated analysis job.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

from experiments.A10.contract import (
    MIN_CAPACITY_FRACTION,START_EVAL,DECISION_GAP,
    TRAIN_COUNT,HOLDOUT_COUNT,TIMES,
)
EXPECTED_PRED_COLS=(
    "condition","scenario","t","capacity","orders",
    "predicted_fraction_diff_c","predicted_fraction_ratio_p",
    "predicted_capacity_diff_c","predicted_capacity_ratio_p",
    "model_disagreement_fraction","both_inputs_inactive",
    "diff_c_input_active","ratio_p_input_active",
    "diff_c_output_clipped_predicted","ratio_p_output_clipped_predicted",
)


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding="utf-8",newline="") as fp:
        reader=csv.DictReader(fp)
        return tuple(reader.fieldnames),list(reader)


def rms(x):
    return float(np.sqrt(np.mean(np.square(np.array(x,dtype=float)))))


def adjudicate(public:Path,sealed:Path,analyst:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((public/"public_manifest.json").read_text())
    truth=json.loads((sealed/"sealed_truth.json").read_text())
    report=json.loads((analyst/"analyst_report.json").read_text())
    if not report.get("analyst_has_no_WORLD_or_holdout_labels"):
        raise ValueError("Analyst report does not attest to sealed boundary")
    if truth["generator_case"]!="W016" or truth["generator_true_feature"]!="incoming_orders/nominal_capacity":
        raise ValueError("Unexpected test generator")
    for filename,expected in truth["public_sha256"].items():
        if hash_file(public/filename)!=expected:
            raise ValueError("Public data not identical to sealed source")
    for filename,expected in truth["labels_sha256"].items():
        if hash_file(sealed/filename)!=expected:
            raise ValueError("Sealed labels mutated")
    for filename,expected in report["data_sha256"].items():
        if hash_file(public/filename)!=expected:
            raise ValueError("Analyst fitted on different public data")
    path=analyst/"predicted_all_holdouts.csv"
    if hash_file(path)!=report["prediction_sha256"]:
        raise ValueError("Prediction file changed after fit")
    fields,pred_rows=csv_rows(path)
    if fields!=EXPECTED_PRED_COLS:
        raise ValueError("Prediction schema drift")
    if len(pred_rows)!=2*HOLDOUT_COUNT*TIMES:
        raise ValueError("All holdouts must be predicted")
    index={}
    for row in pred_rows:
        key=(row["condition"],row["scenario"],float(row["t"]))
        if key in index: raise ValueError("Duplicate prediction")
        index[key]=row
    outcomes={}
    per_scenario=[]
    for condition in ("noiseless","noisy_1pct"):
        _,labels=csv_rows(sealed/f"holdout_labels_{condition}.csv")
        if len(labels)!=HOLDOUT_COUNT*TIMES:
            raise ValueError("Incorrect holdout label count")
        expected_keys={(condition,r["scenario"],float(r["t"])) for r in labels}
        if set(k for k in index if k[0]==condition)!=expected_keys:
            raise ValueError("Prediction keys differ from sealed outcomes")
        by_scenario=defaultdict(list)
        for label in labels:
            t=float(label["t"])
            if t<START_EVAL: continue
            pred=index[(condition,label["scenario"],t)]
            k=float(pred["capacity"])
            actual=float(label["effective_capacity"])
            e1=(float(pred["predicted_capacity_diff_c"])-actual)/k
            e2=(float(pred["predicted_capacity_ratio_p"])-actual)/k
            eb=1.0-actual/k
            by_scenario[label["scenario"]].append({
                "diff_c":e1,"ratio_p":e2,"baseline":eb,
                "predicted_gap":float(pred["model_disagreement_fraction"]),
                "both_inactive_pred":pred["both_inputs_inactive"]=="True",
                "observed_floor":abs(actual/k-MIN_CAPACITY_FRACTION)<0.005,
            })
        abs_err={kind:[] for kind in ("diff_c","ratio_p","baseline")}
        scenario_metrics={}
        for scenario,records in sorted(by_scenario.items()):
            if len(records)!=TIMES-int(START_EVAL):
                raise ValueError("Incomplete evaluation horizon")
            metrics={
                kind:rms([r[kind] for r in records])
                for kind in ("diff_c","ratio_p","baseline")
            }
            metrics.update({
                "predicted_both_inactive_steps":sum(r["both_inactive_pred"] for r in records),
                "observed_at_floor_steps":sum(r["observed_floor"] for r in records),
                "mean_predicted_disagreement":float(np.mean([r["predicted_gap"] for r in records])),
                "model_disagreement_exceeds_heuristic_steps":sum(
                    r["predicted_gap"]>DECISION_GAP for r in records),
            })
            scenario_metrics[scenario]=metrics
            per_scenario.append({"condition":condition,"scenario":scenario,**metrics})
            for kind in abs_err:
                abs_err[kind].extend(r[kind] for r in records)
        train_choice=report["noise_conditions"][condition]["selected_from_training_only"]
        eval_choice=train_choice if train_choice in abs_err else None
        overall={kind:rms(abs_err[kind]) for kind in abs_err}
        near_zero=sum(
            sc["predicted_both_inactive_steps"]==TIMES-int(START_EVAL)
            for sc in scenario_metrics.values()
        )
        outcomes[condition]={
            "training_only_decision":train_choice,
            "selection_abstained":eval_choice is None,
            "truth_is_in_ratio_p_family":True,
            "choice_agrees_with_embedded_truth":eval_choice=="ratio_p" if eval_choice else None,
            "holdout_rms_fraction":overall,
            "holdout_vs_constant_baseline_improvement":(
                overall["baseline"]-overall[eval_choice] if eval_choice else None),
            "predicted_all_inactive_scenarios":near_zero,
            "predicted_gap_above_heuristic_scenarios":sum(
                v["model_disagreement_exceeds_heuristic_steps"]>0
                for v in scenario_metrics.values()),
            "scenario_metrics":scenario_metrics,
        }
    payload={
        "experiment":"A10","adjudication_status":"COMPLETED",
        "source_generator":"W016 G5 synthetic, true driver D/K",
        "results":outcomes,
        "claims":[
            "Candidate families and thresholds were specified in advance.",
            "The analyst process had no generator file or heldout effective capacity after t0.",
            "Holdout orders were observed from a world with endogenous feedback; scores are conditional input-output reconstruction, NOT prospective policy forecasting.",
            "The true D/K mechanism belongs to ratio_p at p=1, so matching truth is partly by construction.",
            "Only capacity observation was made noisy; noise is synthetic and thresholds heuristic.",
            "No proof of unique causal identification or cross-world transfer.",
        ],
        "analyst_artifact_sha256":{
            "analyst_report.json":hash_file(analyst/"analyst_report.json"),
            "predicted_all_holdouts.csv":hash_file(path),
            "training_optimizers.json":hash_file(analyst/"training_optimizers.json"),
        }
    }
    result_path=out/"adjudication.json"
    result_path.write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    with (out/"scenario_scores.csv").open("w",encoding="utf-8",newline="") as fp:
        fields=("condition","scenario","diff_c","ratio_p","baseline",
                "predicted_both_inactive_steps","observed_at_floor_steps",
                "mean_predicted_disagreement","model_disagreement_exceeds_heuristic_steps")
        w=csv.DictWriter(fp,fieldnames=fields)
        w.writeheader()
        w.writerows(per_scenario)
    print(json.dumps({
        "status":"COMPLETED",
        "results":{condition:{
            "training_choice":v["training_only_decision"],
            "holdout_rms":v["holdout_rms_fraction"],
            "inactive_predictions":v["predicted_all_inactive_scenarios"]
        }for condition,v in outcomes.items()}
    },ensure_ascii=False))
    return payload


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--public",required=True,type=Path)
    parser.add_argument("--sealed",required=True,type=Path)
    parser.add_argument("--analyst",required=True,type=Path)
    parser.add_argument("--out",default=Path("results/A10/adjudicated"),type=Path)
    args=parser.parse_args()
    adjudicate(args.public,args.sealed,args.analyst,args.out)
