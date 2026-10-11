#!/usr/bin/env python3
"""A10b adjudicator: regenerate sealed labels AFTER all analyzer artifacts are frozen.

The original A10 adjudicator is reused unchanged; no candidate refitting occurs.
"""
from __future__ import annotations
import argparse,hashlib,json,statistics,csv
from collections import Counter
from pathlib import Path
from experiments.A10.adjudicate import adjudicate
from experiments.A10b.design import SEEDS,EXPECTED_MARGIN,NOISE_STD_FRACTION,validate
from experiments.A10b.packager import produce

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def evaluate(public:Path,analyst:Path,out:Path):
    validate()
    out.mkdir(parents=True,exist_ok=True)
    batch=json.loads((public/"a10b_public_batch_manifest.json").read_text())
    decisions=json.loads((analyst/"a10b_frozen_decisions.json").read_text())
    if decisions["stage"]!="ALL_DECISIONS_FROZEN_BEFORE_ANY_SEALED_LABELS":
        raise ValueError("Predictions were not frozen")
    if decisions["seeds"]!=list(SEEDS) or batch["seeds"]!=list(SEEDS):
        raise ValueError("Seed list changed")
    if digest(public/"a10b_public_batch_manifest.json")!=decisions["public_batch_sha256"]:
        raise ValueError("Public batch modified after analyst")
    dmap={x["seed"]:x for x in decisions["seed_results"]}
    rows=[]
    reference_noiseless=[]
    for seed in SEEDS:
        original=public/str(seed)
        temp_public=out/"regenerated"/str(seed)/"public"
        sealed=out/"regenerated"/str(seed)/"sealed"
        # No sealed labels existed at any earlier job; generate them NOW.
        produce(temp_public,sealed,seed=seed,include_sealed=True)
        for path in original.iterdir():
            if path.is_file() and digest(path)!=digest(temp_public/path.name):
                raise ValueError(f"Replay of public observations changed: seed={seed}, file={path.name}")
        report_path=analyst/str(seed)
        if digest(report_path/"analyst_report.json")!=dmap[seed]["report_sha256"]:
            raise ValueError("Analyst report was altered")
        if digest(report_path/"predicted_all_holdouts.csv")!=dmap[seed]["predictions_sha256"]:
            raise ValueError("Frozen predictions were altered")
        dest=out/"scores"/str(seed)
        adjud=adjudicate(original,sealed,report_path,dest)
        for condition in ("noiseless","noisy_1pct"):
            x=adjud["results"][condition]
            fit=dmap[seed]
            selected=x["training_only_decision"]
            if condition=="noisy_1pct" and selected!=fit["decision"]:
                raise ValueError("Selected family differs from training freeze")
            row={
                "seed":seed,
                "condition":condition,
                "decision":selected,
                "training_rms_diff_c":adjud["results"][condition].get("unused_train_diff",fit["rms_diff_c"] if condition=="noisy_1pct" else None),
                "training_rms_ratio_p":fit["rms_ratio_p"] if condition=="noisy_1pct" else None,
                "training_margin":fit["training_margin"] if condition=="noisy_1pct" else None,
                "holdout_rms_diff_c":x["holdout_rms_fraction"]["diff_c"],
                "holdout_rms_ratio_p":x["holdout_rms_fraction"]["ratio_p"],
                "holdout_rms_nominal_baseline":x["holdout_rms_fraction"]["baseline"],
                "choice_matches_nested_truth":x["choice_agrees_with_embedded_truth"],
                "predicted_all_inactive_scenarios":x["predicted_all_inactive_scenarios"],
                "predicted_gap_heuristic_scenarios":x["predicted_gap_above_heuristic_scenarios"],
            }
            rows.append(row)
            if condition=="noiseless":
                reference_noiseless.append((row["decision"],row["holdout_rms_ratio_p"]))
        print("ADJUDICATED_NOISY_SEED",seed,dmap[seed]["decision"],flush=True)
    if len({x[0] for x in reference_noiseless})!=1:
        raise AssertionError("The unchanged noiseless design made conflicting selections")
    if max(x[1] for x in reference_noiseless)-min(x[1] for x in reference_noiseless)>1e-9:
        raise AssertionError("Noiseless reference changed unexpectedly")
    chosen=[x for x in rows if x["condition"]=="noisy_1pct"]
    counts=Counter(x["decision"] for x in chosen)
    # Don't turn 10 simulations into a statistical confidence interval.
    def desc(k):
        vals=[x[k] for x in chosen]
        return {
            "min":min(vals),"median":statistics.median(vals),
            "max":max(vals),"mean":statistics.mean(vals),
            "by_seed":{str(x["seed"]):x[k] for x in chosen}
        }
    metrics={
        "experiment":"A10b",
        "execution":"COMPLETED",
        "seeds":list(SEEDS),
        "source_A10_model_and_training_rule":"UNCHANGED",
        "noise_1pct_on_effective_capacity_only":True,
        "labels_regenerated_after_analyst_freeze":True,
        "all_seed_decisions_count":{
            label:int(counts[label]) for label in
            ("ratio_p","diff_c","ABSTAIN_UNRESOLVED")
        },
        "training_margin":desc("training_margin"),
        "holdout_rms_ratio_p":desc("holdout_rms_ratio_p"),
        "holdout_rms_diff_c":desc("holdout_rms_diff_c"),
        "predicted_all_inactive_scenarios":desc("predicted_all_inactive_scenarios"),
        "reported_success_if":"None; all ten seed outcomes are retained without threshold tuning",
        "limitations":[
            "This is still W016 with a known true nested candidate family; not blind causal discovery.",
            "The same observed future endogenous orders remain available to the analyst in each holdout.",
            "Noise changes capacity outcome measurements only, not order inputs or structural parameters.",
            "Ten seeds provide a descriptive distribution, NOT significance or calibrated uncertainty.",
            "Same TRAIN/HOLDOUT split and optimizer settings as A10; no evidence of cross-world generality.",
            "The producer code is public but was absent in analyst checkout; separation is procedural.",
        ],
        "source_artifact_sha256":{
            "public_batch_manifest":digest(public/"a10b_public_batch_manifest.json"),
            "frozen_decisions":digest(analyst/"a10b_frozen_decisions.json")
        },
    }
    result_path=out/"A10b_summary.json"
    result_path.write_text(json.dumps(metrics,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    score_path=out/"all_seed_scores.csv"
    fields=list(rows[0])
    with score_path.open("w",encoding="utf-8",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=fields,extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    print("A10B_FINAL",json.dumps({
        "decisions":metrics["all_seed_decisions_count"],
        "margin":metrics["training_margin"],
        "holdout_ratio":{k:v for k,v in metrics["holdout_rms_ratio_p"].items() if k!="by_seed"}
    },ensure_ascii=False),flush=True)
    return metrics

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--public",type=Path,required=True)
    p.add_argument("--analyst",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path("results/A10b/adjudication"))
    args=p.parse_args()
    evaluate(args.public,args.analyst,args.out)
