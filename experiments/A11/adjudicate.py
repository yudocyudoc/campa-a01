#!/usr/bin/env python3
"""A11 post-freeze WORLD evaluator: endogenous orders, full closed-loop actions."""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path
from experiments.A08.g5_extended_core import WORLD_CASES,simulate_world_case
from experiments.A11.contract import (DECISION_T,HORIZON_T,OPTIONS,BASELINE,
    MARKET_SHOCK_AT_T8,FORECAST_FIELDS,SCORING_VARS,SCALING,NOISE_ARMS)

W=WORLD_CASES["W016"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def read_csv(path):
    with path.open(newline="",encoding="utf-8") as fp:
        r=csv.DictReader(fp);return tuple(r.fieldnames),list(r)

def actual_policy(k):
    df,_=simulate_world_case(W["primitive"],W["truth"],
        params={"months":HORIZON_T,"nominal_capacity":BASELINE,
                "market_shock_orders":MARKET_SHOCK_AT_T8},
        capacity_mode="transient",stress_start=float(DECISION_T),
        stress_end=float(HORIZON_T+1),stress_capacity=float(k))
    return [{"policy_k":float(k),"t":float(t),
      **{name:float(df.loc[float(t),name]) for name in FORECAST_FIELDS
         if name not in ("policy_k","t")}} for t in range(DECISION_T,HORIZON_T+1)]

def rms(xs):return math.sqrt(sum(x*x for x in xs)/len(xs))

def adjudicate(public:Path,analyst:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    freeze_path=analyst/"analyst_freeze.json"
    freeze=json.loads(freeze_path.read_text())
    if freeze["phase"]!="FORECASTS_FROZEN_BEFORE_ANY_INTERVENTION_WORLD" or not freeze["NO_FUTURE_ORDERS_READ"]:
        raise ValueError("Missing trustworthy frozen-forecast phase")
    for source,expected in (
        (public/"manifest.json",freeze["public_manifest_sha256"]),
        (public/"predecision_snapshot.csv",freeze["snapshot_sha256"]),
        (analyst/"closedloop_forecasts.csv",freeze["forecast_sha256"]),
        (analyst/"training_optimizer_attempts.json",freeze["attempts_sha256"])
    ):
        if sha(source)!=expected:raise ValueError(f"Modified predecision artifact: {source}")
    fields,entries=read_csv(analyst/"closedloop_forecasts.csv")
    if fields!=("arm","candidate_family")+FORECAST_FIELDS:
        raise ValueError("Forecast output schema drift")
    expected_size=len(NOISE_ARMS)*2*len(OPTIONS)*(HORIZON_T-DECISION_T+1)
    if len(entries)!=expected_size:raise ValueError("Missing intervention predictions")
    predictions={}
    for row in entries:
        arm,family,k,t=row["arm"],row["candidate_family"],float(row["policy_k"]),float(row["t"])
        key=(arm,family,k,t)
        if key in predictions:raise ValueError("Duplicate forecast")
        predictions[key]={field:float(row[field]) for field in FORECAST_FIELDS}
    complete={(a,f,k,float(t)) for a in NOISE_ARMS for f in ("diff_c","ratio_p")
       for k in OPTIONS for t in range(DECISION_T,HORIZON_T+1)}
    if set(predictions)!=complete:raise ValueError("Missing policies/time points")
    # WORLD outcomes are FIRST GENERATED HERE, after all frozen-forecast checks.
    actuals={k:actual_policy(k) for k in OPTIONS}
    _,pre_rows=read_csv(public/"predecision_snapshot.csv")
    if len(pre_rows)!=1:raise ValueError("Wrong snapshot")
    for k,trajectory in actuals.items():
        for name in ("customer_base","backlog","receivables","cash"):
            if abs(trajectory[0][name]-float(pre_rows[0][name]))>1e-7:
                raise ValueError(f"World predecision stock differs for K={k}, {name}")
    oracle_best=min(OPTIONS,key=lambda k:(-actuals[k][-1]["cash"],k))
    scores=[]
    for arm in NOISE_ARMS:
        for family in ("diff_c","ratio_p"):
            for k in OPTIONS:
                rows=actuals[k]
                errors={v:rms([
                    (predictions[(arm,family,k,float(t))][v]-true[v])/SCALING[v]
                    for t,true in enumerate(rows,start=DECISION_T)
                ]) for v in SCORING_VARS}
                scores.append({"arm":arm,"candidate_family":family,"policy_k":k,
                    **{f"rms_{v}":e for v,e in errors.items()},
                    "true_cash_t24":rows[-1]["cash"],
                    "pred_cash_t24":predictions[(arm,family,k,float(HORIZON_T))]["cash"],
                    "true_orders_t24":rows[-1]["incoming_orders"],
                    "pred_orders_t24":predictions[(arm,family,k,float(HORIZON_T))]["incoming_orders"]})
    decisions={}
    for arm in NOISE_ARMS:
        choice=freeze["selected_policies_by_arm"][arm]
        selected=float(choice["chosen_policy_k"])
        if selected not in OPTIONS:raise ValueError("Unknown selected policy")
        realized=actuals[selected][-1]["cash"]
        oracle=actuals[oracle_best][-1]["cash"]
        baseline=actuals[BASELINE][-1]["cash"]
        family=choice["selected_family"]
        decisions[arm]={
            "selected_family_before_oracle":family,
            "chosen_policy_before_oracle":selected,
            "oracle_best_policy_ex_post":oracle_best,
            "chosen_cash_t24_true":realized,
            "no_change_cash_t24_true":baseline,
            "oracle_best_cash_t24_true":oracle,
            "regret_cash":oracle-realized,
            "actual_cash_gain_vs_no_change":realized-baseline,
            "counterfactual_action_agrees_with_oracle":selected==oracle_best,
            "forecast_rms_selected_family":next((
                {key:v for key,v in row.items() if key.startswith("rms_")}
                for row in scores if row["arm"]==arm and
                row["candidate_family"]==family and row["policy_k"]==selected),None),
        }
        if oracle-realized< -1e-6:raise AssertionError("Negative oracle regret")
    true_file=out/"world_policy_outcomes.csv"
    with true_file.open("w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=FORECAST_FIELDS)
        w.writeheader()
        for k in OPTIONS:w.writerows(actuals[k])
    score_file=out/"forecast_error_by_policy.csv"
    with score_file.open("w",newline="",encoding="utf-8") as fp:
        w=csv.DictWriter(fp,fieldnames=tuple(scores[0]))
        w.writeheader();w.writerows(scores)
    result={
        "experiment":"A11","status":"ADJUDICATED",
        "true_world":"W016 first_order_relaxation ratio",
        "policy_menu":OPTIONS,"shock_assumed_known":MARKET_SHOCK_AT_T8,
        "decision_time":DECISION_T,"terminal_time":HORIZON_T,
        "oracle_best_ex_post":oracle_best,
        "true_policy_terminal_cash":{str(k):actuals[k][-1]["cash"] for k in OPTIONS},
        "decisions":decisions,
        "scientific_claim":"PROSPECTIVE_SCENARIO_PREDICTION_WITH_STIPULATED_BUSINESS_MODEL",
        "limits":[
            "All non-response business feedback equations and coefficients are supplied to the analyst.",
            "Response candidate grammar includes the exact WORLD family; not blind structural discovery.",
            "Past cases and interventions share a publicly known synthetic world W016.",
            "Future market shock magnitude and the selected capacity are given as exogenous inputs.",
            "Future orders are NEVER given to the analyst; they are forecast from endogenous customer feedback.",
            "Regret compares only four predefined capacities on terminal cash, not general strategic optimality.",
            "The future WORLD is noiseless; noise on historical training observations only.",
        ],
        "sha256":{
            "world_policy_outcomes.csv":sha(true_file),
            "forecast_error_by_policy.csv":sha(score_file),
            "analyst_freeze.json":sha(freeze_path),
        },
    }
    (out/"adjudication.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("A11_RESULT",json.dumps({"oracle_best":oracle_best,"decisions":decisions,
        "true_cash":result["true_policy_terminal_cash"]}),flush=True)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--public",required=True,type=Path)
    p.add_argument("--analyst",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    o=p.parse_args()
    adjudicate(o.public,o.analyst,o.out)
