#!/usr/bin/env python3
"""A10 producer: ONLY exported observable business columns cross analyst barrier.

Trusted producer uses known W016 original G5 WORLD. Two physically meaningful
measurement conditions: exact and 1% nominal capacity Gaussian target noise.
Labels and true generator metadata NEVER enter analyst artifact.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

from experiments.A08.g5_extended_core import WORLD_CASES, simulate_world_case
from experiments.A08.design import TRAIN, PROBES
from experiments.A10.contract import (
    OBSERVED, INPUTS, MIN_CAPACITY_FRACTION,
    NOISE_LEVELS, NOISE_SEED, TRAIN_COUNT, HOLDOUT_COUNT, TIMES,
    validate_contract_fields,
)

WORLD= WORLD_CASES["W016"]
EXTERNAL_FIELDS=("scenario",)+OBSERVED
HOLDOUT_FIELDS=("scenario",)+INPUTS
LABEL_FIELDS=("scenario","t","effective_capacity")
assert "hidden_excess" not in OBSERVED
assert WORLD["primitive"]=="first_order_relaxation"


def save_csv(path,records,fields):
    validate_contract_fields(fields,fields)  # explicit no-oracle token gate
    with path.open("w",encoding="utf-8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=fields,extrasaction="raise")
        w.writeheader()
        w.writerows(records)


def world_case(probe):
    opts={
        "params":{"months":24,"nominal_capacity":probe["capacity"],
                  "market_shock_orders":probe["shock"]},
        "capacity_mode":"transient" if probe["kind"]=="pulse_holdout" else "constant"
    }
    if probe["kind"]=="pulse_holdout":
        opts.update({k:probe[k] for k in ("stress_start","stress_end","stress_capacity")})
    data,_=simulate_world_case(WORLD["primitive"],WORLD["truth"],**opts)
    if len(data)!=TIMES: raise ValueError("Incorrect G5 timeline")
    return data


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def produce(public:Path,sealed:Path):
    public.mkdir(parents=True,exist_ok=True)
    sealed.mkdir(parents=True,exist_ok=True)
    if len(TRAIN)!=TRAIN_COUNT or len(PROBES)!=HOLDOUT_COUNT:
        raise ValueError("A08 split changed")
    rng=np.random.default_rng(NOISE_SEED)
    train_by_noise={level:[] for level in NOISE_LEVELS}
    holdout_labels_by_noise={level:[] for level in NOISE_LEVELS}
    holdout_inputs=[]
    for partition,probes in (("train",TRAIN),("holdout",PROBES)):
        for index,probe in enumerate(probes,1):
            scenario=f"{'T' if partition=='train' else 'H'}{index:02d}"
            df=world_case(probe)
            for t,row in df.iterrows():
                t=float(t)
                base={name:float(row[name]) for name in OBSERVED}
                base["t"]=t
                k=base["nominal_capacity"]
                original=base["effective_capacity"]
                if k<=0 or not MIN_CAPACITY_FRACTION-1e-8<=original/k<=1+1e-8:
                    raise ValueError("Observed capacity violates operating envelope")
                # No noise at t0; keep initial state observable.
                for level in NOISE_LEVELS:
                    observation=original
                    if level>0 and t>0:
                        observation=float(np.clip(original+rng.normal(0,level*k),
                            MIN_CAPACITY_FRACTION*k,k))
                    if partition=="train":
                        train_by_noise[level].append({
                            "scenario":scenario,
                            **{**base,"effective_capacity":observation},
                        })
                    else:
                        holdout_labels_by_noise[level].append({
                            "scenario":scenario,"t":t,
                            "effective_capacity":observation,
                        })
                if partition=="holdout":
                    holdout_inputs.append({
                        "scenario":scenario,
                        "t":t,
                        "incoming_orders":base["incoming_orders"],
                        "nominal_capacity":base["nominal_capacity"],
                        "initial_effective_capacity":original if t==0 else "",
                    })

    checks={}
    for level in NOISE_LEVELS:
        stem="noiseless" if level==0 else "noisy_1pct"
        tp=public/f"train_{stem}.csv"
        lp=sealed/f"holdout_labels_{stem}.csv"
        save_csv(tp,train_by_noise[level],EXTERNAL_FIELDS)
        save_csv(lp,holdout_labels_by_noise[level],LABEL_FIELDS)
        checks[tp.name]=digest(tp)
        checks[lp.name]=digest(lp)
    input_path=public/"holdout_inputs.csv"
    save_csv(input_path,holdout_inputs,HOLDOUT_FIELDS)
    checks[input_path.name]=digest(input_path)
    pub_manifest={
        "experiment":"A10","synthetic_observational_inputs":True,
        "training_scenarios":TRAIN_COUNT,"holdout_scenarios":HOLDOUT_COUNT,
        "timestamps_per_scenario":TIMES,
        "business_visible_columns":OBSERVED,
        "analyst_holdout_columns":INPUTS,
        "outcome_withheld_after_initial_t0":True,
        "noise_conditions":{"noiseless":"no_noise","noisy_1pct":
            "effective_capacity only, Gaussian sd=1% nominal K, clipped to physical envelope"},
        "noise_seed":NOISE_SEED,
        "known_operating_capacity_floor":MIN_CAPACITY_FRACTION,
        "important_limit":"Holdout D/K covariates are endogenously produced by WORLD; this tests conditional reconstruction, not future counterfactual forecasting.",
        "public_sha256":{k:v for k,v in checks.items() if k.startswith("train") or k.startswith("holdout_inputs")}
    }
    sealed_meta={
        "experiment":"A10","generator_case":"W016",
        "generator_family":WORLD["primitive"],
        "generator_true_feature":"incoming_orders/nominal_capacity",
        "labels_sha256":{k:v for k,v in checks.items() if "labels" in k},
        "public_sha256":pub_manifest["public_sha256"],
        "separation_note":"Must NOT be uploaded to the analyst job",
    }
    (public/"public_manifest.json").write_text(json.dumps(pub_manifest,indent=2)+"\n",encoding="utf-8")
    (sealed/"sealed_truth.json").write_text(json.dumps(sealed_meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PACKAGED","train_rows":len(train_by_noise[0.0]),
        "holdout_inputs":len(holdout_inputs),
        "holdout_labels":len(holdout_labels_by_noise[0.0]),
        "public_files":sorted(p.name for p in public.iterdir())}))
    return pub_manifest


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--public",type=Path,default=Path("results/A10/public"))
    p.add_argument("--sealed",type=Path,default=Path("results/A10/sealed"))
    a=p.parse_args()
    produce(a.public,a.sealed)
