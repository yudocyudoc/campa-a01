#!/usr/bin/env python3
"""A11 producer: public *pre-decision* state only; no future scenario outputs.

Historical training is copied exactly from A10 evidence. No counterfactual
outcomes are created until the adjudicator runs AFTER forecasts are frozen.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil
from pathlib import Path

from experiments.A08.g5_extended_core import WORLD_CASES,simulate_world_case
from experiments.A11.contract import (
    DECISION_T,OPTIONS,BASELINE,MARKET_SHOCK_AT_T8,
    BUSINESS,SNAPSHOT_FIELDS,
)

W=WORLD_CASES["W016"]
HIST=Path("experiments/A10/evidence/public")


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def package(out:Path):
    out.mkdir(parents=True,exist_ok=True)
    for arm in ("noiseless","noisy_1pct"):
        name=f"train_{arm}.csv"
        shutil.copyfile(HIST/name,out/name)
        if sha(out/name)!=sha(HIST/name):raise AssertionError("Historical training data mismatch")
    # Simulate ONLY up to decision time. The t8 BUSINESS STOCKS are pre-flow
    # states and independent of the subsequently imposed K policy.
    df,_=simulate_world_case(
        W["primitive"],W["truth"],
        params={"months":DECISION_T,"nominal_capacity":BASELINE,
                "market_shock_orders":MARKET_SHOCK_AT_T8},
        capacity_mode="constant")
    if list(df.index)!=list(range(DECISION_T+1)):
        raise AssertionError("Predecision grid mismatch")
    last=df.loc[DECISION_T]
    prev=df.loc[DECISION_T-1]
    snap={"t_decision":DECISION_T,
          "customer_base":float(last["customer_base"]),
          "backlog":float(last["backlog"]),
          "receivables":float(last["receivables"]),
          "cash":float(last["cash"]),
          "previous_effective_capacity":float(prev["effective_capacity"]),
          "previous_nominal_capacity":float(prev["nominal_capacity"])}
    if snap["previous_effective_capacity"]/snap["previous_nominal_capacity"]<=BUSINESS["minimum_fraction"]+1e-8:
        raise ValueError("Cannot infer predecision impact from clipping")
    if float(last["nominal_capacity"])!=BASELINE:
        raise AssertionError("Original baseline nominal capacity changed")
    with (out/"predecision_snapshot.csv").open("w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=SNAPSHOT_FIELDS,extrasaction="raise")
        w.writeheader()
        w.writerow(snap)
    spec={
        "experiment":"A11",
        "data_boundary":"Historical training and predecision business stocks ONLY",
        "snapshot_time":DECISION_T,"future_orders_in_public_data":False,
        "future_outcomes_in_public_data":False,
        "policy_options":OPTIONS,
        "baseline_capacity":BASELINE,
        "known_market_shock_from_t8":MARKET_SHOCK_AT_T8,
        "business_accounting_assumptions_known":BUSINESS,
        "source_training":"Historical A10 public evidence: 5 regimes, 25 observations each",
        "public_file_sha256":{p.name:sha(p) for p in sorted(out.glob("*.csv"))},
    }
    (out/"manifest.json").write_text(json.dumps(spec,indent=2,allow_nan=False)+"\n")
    print("A11_PUBLIC_READY",json.dumps({
        "decision_t":DECISION_T,"public_file_names":sorted(p.name for p in out.iterdir()),
        "state_t8":snap,"NO_OUTCOMES_AHEAD":True
    }),flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    package(ap.parse_args().out)
