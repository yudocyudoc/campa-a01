#!/usr/bin/env python3
"""A12 gate: candidate-only, symmetric model-conditional decision value.

Never imports or executes a WORLD generator. Loads only A11 frozen fitted
candidate params and PREDECISION snapshot, then asks whether knowing which
candidate is right would change action by a material amount for BOTH models.
"""
from __future__ import annotations

import argparse,csv,hashlib,json,math
from collections import Counter
from pathlib import Path

from experiments.A11.contract import (
    BASELINE, BUSINESS, forecast as a11_forecast,
)
from experiments.A12.design import (
    SHOCKS,CAPACITIES,ARMS,FAMILIES,INITIAL_BASE_CAPACITY,
    MATERIAL_FRACTION,MIN_SHOCK_COUNT,CASH_TIE_TOL,BASELINES,
    NO_POLICY_FUTURE_OUTCOMES_IN_GATE,A11_SOURCE_RUN,check_design,
)
from experiments.A12.forecast import candidate_forecast,terminal_cash

A11_FROZEN=Path("experiments/A11/evidence/analyst/analyst_freeze.json")
A11_SNAPSHOT=Path("experiments/A11/evidence/public/predecision_snapshot.csv")
# The checked-in A11 forecast is a source independent of the WORLD generator.
A11_FORECASTS=Path("experiments/A11/evidence/analyst/closedloop_forecasts.csv")


def checksum(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_records(path:Path)->tuple[tuple[str,...],list[dict]]:
    with path.open(newline="",encoding="utf-8") as fp:
        reader=csv.DictReader(fp)
        return tuple(reader.fieldnames or ()),list(reader)


def nearest_capacity(value:float)->float:
    return min(CAPACITIES,key=lambda k:(abs(k-value),k))


def pure_peak_demand_proxy(snapshot:dict,shock:float)->float:
    """Naive uncongested-demand proxy; NO model-of-capacity driver.

    Customer base increases each month by marketing acquisition minus base
    churn, ignoring all loss from backlog cancellations. It is a naive
    optimistic peak demand forecast, NOT future WORLD demand.
    """
    months=24-8
    base_now=float(snapshot["customer_base"])
    uncrowded_base=(base_now+months*(
        BUSINESS["marketing_intensity"]*BUSINESS["acquisition_per_marketing_unit"]
        -BUSINESS["base_churn"]
    ))
    return uncrowded_base*BUSINESS["base_order_rate"]+shock


def argmax_tolerant(cash:dict[float,float])->float:
    high=max(cash.values())
    return min(k for k,v in cash.items() if high-v<=CASH_TIE_TOL)


def best_gains(model_cash:dict[str,dict[float,float]],snapshot:dict,shock:float):
    opts={}
    best={}
    ranges={}
    for fam in FAMILIES:
        arr=model_cash[fam]
        optimal=argmax_tolerant(arr)
        best[fam]=optimal
        ranges[fam]=max(arr.values())-min(arr.values())
        opts[fam]=arr[optimal]
    if min(ranges.values())<=1e-9:
        raise ValueError("Degenerate cash objective range")
    own={"ratio_p":best["ratio_p"],"diff_c":best["diff_c"]}
    wrong_regrets={
        "ratio_p":max(0.,opts["ratio_p"]-model_cash["ratio_p"][own["diff_c"]]),
        "diff_c":max(0.,opts["diff_c"]-model_cash["diff_c"][own["ratio_p"]]),
    }
    scaled={f:wrong_regrets[f]/ranges[f] for f in FAMILIES}
    symmetric=min(scaled.values())
    agrees=own["ratio_p"]==own["diff_c"]
    material=not agrees and all(scaled[f]>=MATERIAL_FRACTION for f in FAMILIES)
    peak=pure_peak_demand_proxy(snapshot,shock)
    policies={
        "no_change_115":INITIAL_BASE_CAPACITY,
        "maximum_capacity_260":CAPACITIES[-1],
        "estimated_uncongested_peak_demand":nearest_capacity(peak),
    }
    naive_regrets={
        name:{
            fam:max(0.,opts[fam]-model_cash[fam][policy])
            for fam in FAMILIES
        }for name,policy in policies.items()
    }
    return {
        "best_policy":best,
        "model_cash_range":ranges,
        "model_based_wrong_choice_regret":wrong_regrets,
        "fractional_wrong_choice_regret":scaled,
        "symmetric_material_fraction":symmetric,
        "same_policy":agrees,
        "material_disagreement":material,
        "naive_policies":policies,
        "naive_regrets_in_each_candidate":naive_regrets,
        "peak_demand_proxy":peak,
    }


def verify_a11_boundary(snap:dict,arms:dict):
    """Drift gate: at A11 original K and shock, simulator must match
    the original equations and the frozen archived pre-oracle predictions.
    """
    fields,preds=csv_records(A11_FORECASTS)
    expected_first=("arm","candidate_family","policy_k","t")
    if fields[:4]!=expected_first:
        raise ValueError("A11 archived forecast schema drift")
    target={(x["arm"],x["candidate_family"],float(x["policy_k"]),float(x["t"])):x for x in preds}
    for arm in ARMS:
        for fam in FAMILIES:
            params=arms[arm]["fit_by_family"][fam]["params"]
            for k in (90.,115.,145.,180.):
                ours=candidate_forecast(k,50.,snap,params,fam)
                direct=a11_forecast(k,snap,params,fam)
                if len(ours)!=len(direct):
                    raise ValueError("A11 original simulator length mismatch")
                for row,reference in zip(ours,direct):
                    for metric in ("incoming_orders","effective_capacity","backlog","customer_base","cash"):
                        a=float(row[metric]);b=float(reference[metric])
                        if not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-7):
                            raise AssertionError("A12 candidate diverged from A11 contract: "+metric)
                    original=target[(arm,fam,k,float(row["t"]))]
                    if not math.isclose(float(row["cash"]),float(original["cash"]),rel_tol=1e-12,abs_tol=1e-6):
                        raise AssertionError("Original A11 frozen forecast was not reproduced")
    return True


def run(out:Path)->dict:
    check_design()
    if not NO_POLICY_FUTURE_OUTCOMES_IN_GATE:
        raise AssertionError("Gate must not run a WORLD")
    out.mkdir(parents=True,exist_ok=True)
    src=json.loads(A11_FROZEN.read_text(encoding="utf-8"))
    if src["experiment"]!="A11" or src["phase"]!="FORECASTS_FROZEN_BEFORE_ANY_INTERVENTION_WORLD":
        raise ValueError("Unrecognized A11 freeze")
    arms=src["selected_policies_by_arm"]
    if set(arms)!=set(ARMS):
        raise ValueError("Missing A11 arms")
    flds,records=csv_records(A11_SNAPSHOT)
    if len(records)!=1:
        raise ValueError("Pre-decision snapshot not unique")
    snap={k:float(v) for k,v in records[0].items()}
    verify_a11_boundary(snap,arms)
    scenario_records=[]
    all_model_cash=[]
    for arm in ARMS:
        frozen=arms[arm]
        for shock in SHOCKS:
            cash={}
            for fam in FAMILIES:
                p=frozen["fit_by_family"][fam]["params"]
                cash[fam]={}
                for k in CAPACITIES:
                    sim=candidate_forecast(k,shock,snap,p,fam)
                    score=terminal_cash(sim)
                    cash[fam][k]=score
                    all_model_cash.append({
                        "arm":arm,"shock":shock,"family":fam,
                        "policy_k":k,"predicted_cash_t24":score,
                    })
            adjud=best_gains(cash,snap,shock)
            scenario_records.append({
                "arm":arm,"shock":shock,
                "ratio_p_k":adjud["best_policy"]["ratio_p"],
                "diff_c_k":adjud["best_policy"]["diff_c"],
                "ratio_p_cash_range":adjud["model_cash_range"]["ratio_p"],
                "diff_c_cash_range":adjud["model_cash_range"]["diff_c"],
                "wrong_policy_regret_under_ratio_p":adjud["model_based_wrong_choice_regret"]["ratio_p"],
                "wrong_policy_regret_under_diff_c":adjud["model_based_wrong_choice_regret"]["diff_c"],
                "relative_regret_ratio_p":adjud["fractional_wrong_choice_regret"]["ratio_p"],
                "relative_regret_diff_c":adjud["fractional_wrong_choice_regret"]["diff_c"],
                "symmetric_min_regret_fraction":adjud["symmetric_material_fraction"],
                "models_disagree":not adjud["same_policy"],
                "passes_5pct_symmetric":adjud["material_disagreement"],
                "baseline_no_change_k":adjud["naive_policies"]["no_change_115"],
                "baseline_max_k":adjud["naive_policies"]["maximum_capacity_260"],
                "baseline_peak_demand_k":adjud["naive_policies"]["estimated_uncongested_peak_demand"],
                "naive_peak_proxy":adjud["peak_demand_proxy"],
                **{f"baseline_{name}_{fam}_regret":adjud["naive_regrets_in_each_candidate"][name][fam]
                    for name in BASELINES for fam in FAMILIES},
            })
    count={arm:sum(r["passes_5pct_symmetric"] for r in scenario_records if r["arm"]==arm) for arm in ARMS}
    # A shock must qualify in BOTH noisy/noiseless arms to count toward the
    # one-third robustness gate; two disjoint qualifying sets are insufficient.
    common_qualified=[shock for shock in SHOCKS if all(
        r["passes_5pct_symmetric"] for r in scenario_records
        if r["shock"]==shock
    )]
    qualified=len(common_qualified)>=MIN_SHOCK_COUNT
    # Robust selection uses MIN across arms of same shock, with deterministic ties.
    ranked=[]
    for shock in SHOCKS:
        s=[r for r in scenario_records if r["shock"]==shock]
        ranked.append({
            "shock":shock,
            "robust_symmetric_fraction":min(r["symmetric_min_regret_fraction"] for r in s),
            "passes_both_arms":all(r["passes_5pct_symmetric"] for r in s)
        })
    ranked.sort(key=lambda x:(-x["robust_symmetric_fraction"],x["shock"]))
    candidate_choice=ranked[0]["shock"]
    # PASS only when >=3/9 material shocks in EACH arm.
    outcome="WORLD_ADJUDICATION_AUTHORIZED" if qualified else "NO_MATERIAL_DECISION_DISAGREEMENT"
    for name,values in (
        ("scenarios.csv",scenario_records),
        ("candidate_policy_cash.csv",all_model_cash)
    ):
        with (out/name).open("w",newline="",encoding="utf-8") as fp:
            w=csv.DictWriter(fp,fieldnames=tuple(values[0]),extrasaction="raise")
            w.writeheader();w.writerows(values)
    result={
        "experiment":"A12","stage":"CANDIDATE_ONLY_DECISION_VALUE_GATE",
        "verdict":outcome,"world_evaluated_in_gate":False,
        "grid":{"shocks":SHOCKS,"capacities":CAPACITIES,"arms":ARMS,"families":FAMILIES},
        "materiality_criterion":{
            "each_model_regret_at_least_fraction_of_own_cash_range":MATERIAL_FRACTION,
            "qualifying_shocks_required_in_both_arms":MIN_SHOCK_COUNT,
            "required_fraction_of_shocks":MIN_SHOCK_COUNT/len(SHOCKS),
            "regret_definition":"Model's optimum cash minus cash when following other model's preferred policy",
            "both_models_must_prefer_different_capacity":True,
            "reason":"Screen meaningful decision differences, not visual mechanism gaps",
        },
        "qualifying_by_arm":count,
        "qualifying_in_both_arms":len(common_qualified),
        "qualifying_shock_values":common_qualified,
        "different_recommendations_by_arm":{
            arm:sum(r["models_disagree"] for r in scenario_records if r["arm"]==arm)
            for arm in ARMS
        },
        "candidate_only_best_exploratory_shock":candidate_choice,
        "world_adjudication_shock_if_authorized":(
            next((r["shock"] for r in ranked if r["passes_both_arms"]),None)
            if qualified else None
        ),
        "ranked_candidate_shocks":ranked,
        "authorization_for_world":qualified,
        "naive_benchmarks":list(BASELINES),
        "checks":{"a11_equations_and_frozen_forecasts_reproduced":True},
        "source_sha256":{
            "a11_analyst_freeze":checksum(A11_FROZEN),
            "a11_predecision_snapshot":checksum(A11_SNAPSHOT),
            "a11_frozen_forecasts":checksum(A11_FORECASTS),
        },
        "limitations":[
            "This is a post-A11 exploratory selection study; the materiality threshold is a design choice, not a statistical calibration.",
            "All scores, regrets and naive comparisons are CANDIDATE-PREDICTED; no WORLD truth in gate.",
            "Two hypotheses share stipulated, exactly correct business feedback equations.",
            "ratio_p contains generating feature; only one known synthetic W016 world was used in earlier experiments.",
            "Cash range is over this fixed 35-policy menu; results can change with policy set and objective.",
            "The uncongested peak-demand heuristic deliberately ignores backlog-related churn.",
            "A negative gate speaks only to this grid, this objective and these two fitted candidates.",
        ],
        "csv_sha256":{name:checksum(out/name) for name in ("scenarios.csv","candidate_policy_cash.csv")}
    }
    (out/"gate.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("A12_GATE",json.dumps({
        "verdict":outcome,"qualifying_by_arm":count,
        "different_policies":result["different_recommendations_by_arm"],
        "best_candidate_only_shock":candidate_choice,
        "max_robust_normalized_regret":ranked[0]["robust_symmetric_fraction"],
        "authorization_for_world":qualified
    },ensure_ascii=False),flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=Path("results/A12/gate"))
    args=p.parse_args()
    run(args.out)
