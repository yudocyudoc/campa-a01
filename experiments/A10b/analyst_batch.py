#!/usr/bin/env python3
"""A10b isolated analyst: rerun UNCHANGED A10 analyzer for every frozen seed.

This module imports only observable A10 analyst/contract and A10b design.
No generator, truth labels, or prior experiment model files.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from experiments.A10.analyst import analyze
from experiments.A10b.design import SEEDS,validate

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main(public:Path,out:Path):
    validate()
    out.mkdir(parents=True,exist_ok=True)
    public_manifest=json.loads((public/"a10b_public_batch_manifest.json").read_text(encoding="utf-8"))
    if public_manifest["seeds"]!=list(SEEDS) or not public_manifest["sealed_labels_not_generated_or_published"]:
        raise ValueError("Public precommit was changed")
    rows=[]
    for seed in SEEDS:
        folder=public/str(seed)
        if not folder.is_dir():raise ValueError("Seed data absent")
        for name,expected in public_manifest["per_seed"][SEEDS.index(seed)]["checksums"].items():
            if sha(folder/name)!=expected:raise ValueError("Public dataset modified")
        dest=out/str(seed)
        report=analyze(folder,dest)
        if not report["analyst_has_no_WORLD_or_holdout_labels"]:
            raise ValueError("Analyst boundary not attested")
        noise=report["noise_conditions"]["noisy_1pct"]
        choice=noise["selected_from_training_only"]
        if choice not in ("ratio_p","diff_c","ABSTAIN_UNRESOLVED"):raise ValueError("Bad decision")
        rows.append({
            "seed":seed,"decision":choice,
            "rms_diff_c":noise["fit_by_family"]["diff_c"]["train_rms"],
            "rms_ratio_p":noise["fit_by_family"]["ratio_p"]["train_rms"],
            "training_margin":noise["training_rms_gap"],
            "predicted_informative_steps":sum(x["post_t8_informative_predicted"]
               for x in noise["scenario_informativeness"]),
            "predicted_all_inactive_scenarios":sum(
               x["post_t8_both_inactive_predicted"]==17
               for x in noise["scenario_informativeness"]),
            "report_sha256":sha(dest/"analyst_report.json"),
            "predictions_sha256":sha(dest/"predicted_all_holdouts.csv"),
        })
        print("ANALYST_SEED",json.dumps(rows[-1],sort_keys=True),flush=True)
    (out/"a10b_frozen_decisions.json").write_text(json.dumps({
        "experiment":"A10b","seeds":list(SEEDS),"stage":"ALL_DECISIONS_FROZEN_BEFORE_ANY_SEALED_LABELS",
        "optimizer_and_abstention_rules":"UNCHANGED_A10",
        "seed_results":rows,
        "public_batch_sha256":sha(public/"a10b_public_batch_manifest.json"),
        "no_generator_or_sealed_outcomes_available":True,
    },indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("A10B_ANALYST_COMPLETE",len(rows),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--public",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path("results/A10b/analyst"))
    args=p.parse_args()
    main(args.public,args.out)
