#!/usr/bin/env python3
"""Conditional A12 WORLD adjudicator. NEVER called when A12 gate fails.

Truth is first simulated AFTER the candidate-only freeze; the oracle
comparison is limited to policies chosen by candidates and naive benchmarks
at ONE candidate-selected scenario. It is not a general causal certificate.
"""
from __future__ import annotations

import argparse,csv,hashlib,json,math
from pathlib import Path

from experiments.A08.g5_extended_core import WORLD_CASES,simulate_world_case
from experiments.A12.design import (
    CAPACITIES,SHOCKS,ARMS,FAMILIES,BASELINES,
    MATERIAL_FRACTION,MIN_SHOCK_COUNT,check_design,
)

W=WORLD_CASES["W016"]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_csv(path):
    with path.open(newline="",encoding="utf-8") as fp:
        r=csv.DictReader(fp);return tuple(r.fieldnames),list(r)

def evaluate(gate_folder:Path,out:Path):
    check_design()
    out.mkdir(parents=True,exist_ok=True)
    gate_path=gate_folder/"gate.json"
    gate=json.loads(gate_path.read_text(encoding="utf-8"))
    if gate["experiment"]!="A12" or gate["verdict"]!="WORLD_ADJUDICATION_AUTHORIZED":
        raise ValueError("WORLD adjudication forbidden; no material candidate-only gate")
    if not gate["authorization_for_world"] or gate["qualifying_in_both_arms"]<MIN_SHOCK_COUNT:
        raise ValueError("A12 robustness criteria not met")
    if gate["materiality_criterion"]["each_model_regret_at_least_fraction_of_own_cash_range"]!=MATERIAL_FRACTION:
        raise ValueError("Materiality criterion modified")
    if set(gate["grid"]["capacities"])!=set(CAPACITIES) or set(gate["grid"]["shocks"])!=set(SHOCKS):
        raise ValueError("Grid changed")
    for filename,expected in gate["csv_sha256"].items():
        if sha(gate_folder/filename)!=expected:
            raise ValueError("Candidate-only frozen data modified")
    fields,rows=load_csv(gate_folder/"scenarios.csv")
    if len(rows)!=len(SHOCKS)*len(ARMS):
        raise ValueError("Candidate records incomplete")
    choice=gate["world_adjudication_shock_if_authorized"]
    if choice is None or choice not in SHOCKS:
        raise ValueError("No candidate-selected shock")
    chosen_rows={r["arm"]:r for r in rows if float(r["shock"])==choice}
    if set(chosen_rows)!=set(ARMS) or not all(
        r["passes_5pct_symmetric"]=="True" for r in chosen_rows.values()
    ):
        raise ValueError("Selected shock is not qualifying in both arms")
    policies={float(row["ratio_p_k"]) for row in chosen_rows.values()}
    policies.update(float(row["diff_c_k"]) for row in chosen_rows.values())
    for row in chosen_rows.values():
        for k in ("baseline_no_change_k","baseline_max_k","baseline_peak_demand_k"):
            policies.add(float(row[k]))
    if any(k not in CAPACITIES for k in policies):
        raise ValueError("Policy outside candidate-only selection grid")
    # Enforce frozen menu before creating ANY world trajectory.
    selected_policies=sorted(policies)
    world={}
    for k in CAPACITIES:
        df,_=simulate_world_case(
            W["primitive"],W["truth"],
            params={"months":24,"nominal_capacity":115.,
                    "market_shock_orders":choice},
            capacity_mode="transient",stress_start=8.,
            stress_end=25.,stress_capacity=k
        )
        world[k]=float(df.loc[24.,"cash"])
    oracle=max(world.values())
    oracle_k=min(k for k,v in world.items() if math.isclose(v,oracle,rel_tol=0,abs_tol=1e-6))
    comparison=[]
    for arm,record in chosen_rows.items():
        for label,k in {
            "ratio_p":float(record["ratio_p_k"]),
            "diff_c":float(record["diff_c_k"]),
            "no_change_115":float(record["baseline_no_change_k"]),
            "maximum_capacity_260":float(record["baseline_max_k"]),
            "estimated_uncongested_peak_demand":float(record["baseline_peak_demand_k"]),
        }.items():
            comparison.append({
                "arm":arm,"selected_shock":choice,"policy_source":label,
                "chosen_capacity":k,"cash_t24_world":world[k],
                "best_cash_t24_world_on_grid":oracle,
                "regret_vs_world_grid_oracle":oracle-world[k],
                "true_best_capacity_on_grid":oracle_k,
            })
    result={
        "experiment":"A12","status":"ADJUDICATED_AFTER_CANDIDATE_ONLY_GATE",
        "selected_shock":choice,
        "evaluated_menu":list(CAPACITIES),
        "truth_best_capacity_on_grid":oracle_k,
        "world_cash_range":oracle-min(world.values()),
        "cross_model_regret":comparison,
        "selected_policies_and_baselines":selected_policies,
        "frozen_gate_sha256":sha(gate_path),
        "limits":[
            "WORLD executed only because the strict gate passed using candidate-only predictions.",
            "Best outcome is restricted to finite fixed capacity menu and terminal cash t24.",
            "Business equations and world W016 were known from older experiments.",
            "True response family exists within candidate library; this is not discovery of a new causal structure.",
        ],
    }
    target=out/"adjudication.json"
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    csv_path=out/"decision_regrets.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=tuple(comparison[0]))
        w.writeheader();w.writerows(comparison)
    print("A12_WORLD",json.dumps({"selected_shock":choice,"world_optimal_K":oracle_k,
        "evaluated_decisions":comparison}),flush=True)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--gate",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    evaluate(args.gate,args.out)
