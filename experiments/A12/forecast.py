"""A12 generalized policy/market scenario simulator, candidate models ONLY.

Uses the stipulated business equations and dynamic driver from A11, not G5
WORLD or anything from A08/A09. It MUST match A11 at shock=50 and K in
{90,115,145,180}, as tested and checked at runtime.
"""
from __future__ import annotations

import math
from experiments.A11.contract import (
    BUSINESS, BASELINE, DECISION_T, HORIZON_T, _driver,
)
from experiments.A12.design import SHOCKS,CAPACITIES


def candidate_forecast(
    capacity:float,market_shock:float,snapshot:dict,
    parameters:list[float]|tuple[float,...],family:str,
)->list[dict]:
    k=float(capacity)
    shock=float(market_shock)
    if k not in CAPACITIES or shock not in SHOCKS:
        raise ValueError("Policy/shock outside preregistered A12 grid")
    if float(snapshot["t_decision"])!=DECISION_T:
        raise ValueError("A11 pre-decision snapshot changed")
    if family not in ("diff_c","ratio_p"):
        raise ValueError("Unknown feature family")
    if len(parameters)!=4:raise ValueError("Expected four A11 fitted parameters")
    tau,rate,gain,shape=map(float,parameters)
    if not all(math.isfinite(v) for v in (tau,rate,gain,shape)):
        raise ValueError("Nonfinite parameters")
    if not 0<rate<2 or gain<0:raise ValueError("Unstable first order dynamic")

    b=BUSINESS
    stocks={field:float(snapshot[field]) for field in (
        "customer_base","backlog","receivables","cash"
    )}
    prev_k=float(snapshot["previous_nominal_capacity"])
    prev_effective=float(snapshot["previous_effective_capacity"])
    prev_orders=float(snapshot["previous_incoming_orders"])
    if prev_k<=0:raise ValueError("Invalid prehistory capacity")
    prev_frac=prev_effective/prev_k
    if prev_frac<=b["minimum_fraction"]+1e-8 or prev_frac>1+1e-8:
        raise ValueError("Latent state not recoverable at the clipped initial state")
    # Identical pre-t8 latent reconstruction rule to A11:
    prev_impact=max(0.,1-prev_frac)
    latent=(1-rate)*prev_impact+rate*_driver(
        prev_orders,prev_k,parameters,family
    )
    output=[]
    for t in range(DECISION_T,HORIZON_T+1):
        orders=stocks["customer_base"]*b["base_order_rate"]+shock
        effective=k*max(1-latent,b["minimum_fraction"])
        fulfilled=min(stocks["backlog"]+orders,effective)
        cancelled=stocks["backlog"]*b["cancel_rate"]
        churn=b["base_churn"]+cancelled*b["customer_loss_per_cancel"]
        collections=stocks["receivables"]/b["collection_delay"]
        additional=max(k-BASELINE,0.)*b["capacity_cost_per_extra_unit"]
        cost=(b["fixed_cost"]+fulfilled*b["variable_cost_per_order"]+
              b["marketing_intensity"]*b["marketing_cost_per_unit"]+additional)
        output.append({
            "policy_k":k,"t":float(t),
            "incoming_orders":orders,"nominal_capacity":k,
            "effective_capacity":effective,"fulfilled":fulfilled,
            "backlog":stocks["backlog"],"cancellations":cancelled,
            "customer_base":stocks["customer_base"],
            "receivables":stocks["receivables"],"cash":stocks["cash"],
        })
        # Pre-flow A11/G5 Euler semantics. No WORLD values are referenced.
        next_stocks={
            "customer_base":stocks["customer_base"]+
                b["marketing_intensity"]*b["acquisition_per_marketing_unit"]-churn,
            "backlog":stocks["backlog"]+orders-fulfilled-cancelled,
            "receivables":stocks["receivables"]+fulfilled*b["price"]-collections,
            "cash":stocks["cash"]+collections-cost,
        }
        latent=(1-rate)*latent+rate*_driver(orders,k,parameters,family)
        if any(not math.isfinite(x) for x in (*next_stocks.values(),latent)):
            raise ValueError("Unstable simulation")
        stocks=next_stocks
    return output


def terminal_cash(rows:list[dict])->float:
    if len(rows)!=HORIZON_T-DECISION_T+1:
        raise ValueError("Expected 17 prospective time steps")
    return float(rows[-1]["cash"])
