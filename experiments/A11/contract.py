"""A11 disclosed input-output + business-feedback contract; stdlib-only.

Only the response parameterization is inferred. The surrounding operating
equations and business coefficients are deliberately KNOWN TO THE ANALYST,
not inferred or discovered, and are fixed before adjudication.
"""
from __future__ import annotations
import math

DECISION_T=8
HORIZON_T=24
OPTIONS=(90.,115.,145.,180.)
BASELINE=115.
MARKET_SHOCK_AT_T8=50.0
NOISE_ARMS=("noiseless","noisy_1pct")
ABSTENTION_MARGIN=0.005  # SAME A10 rule; if ambiguous choose no-change K115
TARGET="cash_t24"         # policy ranking objective; no oracle tuning
SCORING_VARS=("incoming_orders","effective_capacity","backlog","customer_base","cash")
SCALING={"incoming_orders":115.,"effective_capacity":115.,"backlog":115.,
         "customer_base":1000.,"cash":20000.}
# Stipulated business-accounting model shared between forecaster and generator.
# These are common operating parameters, NOT W016 hidden driver parameters.
BUSINESS={
 "base_order_rate":0.09,
 "acquisition_per_marketing_unit":8.0,"marketing_intensity":1.0,
 "cancel_rate":0.06,"base_churn":2.0,"customer_loss_per_cancel":0.40,
 "price":100.0,"variable_cost_per_order":50.0,"fixed_cost":4000.0,
 "marketing_cost_per_unit":800.0,"capacity_cost_per_extra_unit":10.0,
 "collection_delay":2.0,"minimum_fraction":0.40,
}
FORECAST_FIELDS=("policy_k","t","incoming_orders","nominal_capacity",
                 "effective_capacity","fulfilled","backlog","cancellations",
                 "customer_base","receivables","cash")
SNAPSHOT_FIELDS=("t_decision","customer_base","backlog","receivables","cash",
                 "previous_effective_capacity","previous_nominal_capacity")
FIT_FAMILIES=("diff_c","ratio_p")


def _driver(orders:float,k:float,p:tuple[float,...],family:str)->float:
    tau,rate,gain,shape=(float(v) for v in p)
    if family=="diff_c":raw=orders-shape*k
    elif family=="ratio_p":raw=orders/k**shape
    else:raise ValueError("Unknown family")
    return gain*max(raw-tau,0.)


def forecast(policy_k:float,snapshot:dict,params,kind:str)->list[dict]:
    """Closed-loop Euler forward simulation, endogenous orders at EVERY step.

    Uses no oracle future covariates, response latent state or WORLD parameters.
    Hidden impact at decision t8 is inferred from *observed* t7 capacity,
    permitted here only if it was not at the capacity floor.
    """
    if float(policy_k) not in OPTIONS:raise ValueError("Unsupported policy")
    if int(snapshot["t_decision"])!=DECISION_T:raise ValueError("Wrong decision time")
    b=BUSINESS
    c={name:float(snapshot[name]) for name in
       ("customer_base","backlog","receivables","cash")}
    prev_frac=float(snapshot["previous_effective_capacity"])/float(snapshot["previous_nominal_capacity"])
    if prev_frac<=b["minimum_fraction"]+1e-8:
        raise ValueError("Latent initial state not identifiable from clipped prehistory")
    if not b["minimum_fraction"]<=prev_frac<=1+1e-8:
        raise ValueError("Invalid pre-decision observed capacity")
    z=max(0.,1.-prev_frac)
    tau,rate,gain,shape=map(float,params)
    if not (0<rate<2 and gain>=0 and math.isfinite(rate+gain+tau+shape)):
        raise ValueError("Unstable or invalid parameters")
    out=[]
    for t in range(DECISION_T,HORIZON_T+1):
        K=float(policy_k)
        D=c["customer_base"]*b["base_order_rate"]+MARKET_SHOCK_AT_T8
        cap=K*max(1-z,b["minimum_fraction"])
        fulfilled=min(c["backlog"]+D,cap)
        cancellations=c["backlog"]*b["cancel_rate"]
        churn=b["base_churn"]+cancellations*b["customer_loss_per_cancel"]
        collections=c["receivables"]/b["collection_delay"]
        extra=max(K-BASELINE,0.)*b["capacity_cost_per_extra_unit"]
        operating_cost=(b["fixed_cost"]+fulfilled*b["variable_cost_per_order"]
                        +b["marketing_intensity"]*b["marketing_cost_per_unit"]+extra)
        out.append({"policy_k":K,"t":float(t),"incoming_orders":D,
                    "nominal_capacity":K,"effective_capacity":cap,"fulfilled":fulfilled,
                    "backlog":c["backlog"],"cancellations":cancellations,
                    "customer_base":c["customer_base"],
                    "receivables":c["receivables"],"cash":c["cash"]})
        # All updates use time t state, as in the Euler G5 business system.
        next_base=c["customer_base"]+b["marketing_intensity"]*b["acquisition_per_marketing_unit"]-churn
        next_backlog=c["backlog"]+D-fulfilled-cancellations
        next_receivables=c["receivables"]+fulfilled*b["price"]-collections
        next_cash=c["cash"]+collections-operating_cost
        z=(1-rate)*z+rate*_driver(D,K,params,kind)
        c={"customer_base":next_base,"backlog":next_backlog,
           "receivables":next_receivables,"cash":next_cash}
        if not all(math.isfinite(v) for v in (*c.values(),z)):
            raise ValueError("Nonfinite simulated closed loop")
    return out


def select_policy(predictions:dict[float,list[dict]],selected_family:str)->float:
    if selected_family=="ABSTAIN_UNRESOLVED":
        return BASELINE
    if set(predictions)!=set(OPTIONS):
        raise ValueError("Need all policies, not a selected subset")
    # Freeze decision rule before seeing WORLD trajectories.
    return min(OPTIONS,key=lambda k:(-predictions[k][-1]["cash"],k))


def rms_errors(actual:list[dict],forecast_rows:list[dict])->dict:
    if len(actual)!=len(forecast_rows)!=HORIZON_T-DECISION_T+1:
        raise ValueError("Wrong forecast length")
    return {v:math.sqrt(sum(
        ((float(a[v])-float(p[v]))/SCALING[v])**2
        for a,p in zip(actual,forecast_rows)
    )/len(actual)) for v in SCORING_VARS}
