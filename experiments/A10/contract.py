"""A10 public contract: only business-visible signals cross the analysis boundary.

No import of A06-A09, WORLD_CASES, latent fields or generator metadata.
Runtime analyst receives full TRAIN outcomes plus HOLDOUT D/K inputs only.
"""
from __future__ import annotations

import math

OBSERVED=("t","incoming_orders","nominal_capacity","effective_capacity",
          "backlog","cancellations","customer_base","cash")
INPUTS=("t","incoming_orders","nominal_capacity","initial_effective_capacity")
TARGET="effective_capacity"
MIN_CAPACITY_FRACTION=0.40  # Externally stipulated business rule, not inferred latent state
TRAIN_COUNT=5
HOLDOUT_COUNT=17
TIMES=25
START_EVAL=8.
SCALE=1.0                  # score on capacity fraction (dimensionless)
NUMERIC_TOL=1e-8
DECISION_GAP=0.005         # effect-size only; no noise/power calibration
NOISE_LEVELS=(0.0,0.01)   # 1% of nominal capacity, observed target only, public seed
NOISE_SEED=20261011
FAMILIES={
    "diff_c":{
        "bounds":((-150.,0.10,0.0003,0.2),(160.,1.2,0.10,2.0)),
        "starts":((-20.,0.50,0.012,1.0),(-30.,0.7,0.02,0.8)),
    },
    "ratio_p":{
        "bounds":((0.01,0.10,0.01,0.2),(2.5,1.2,5.,1.8)),
        "starts":((0.7,0.45,1.2,0.8),(0.9,0.75,2.2,1.2)),
    },
}
DE_MAXITER=16
DE_POPSIZE=5
LOCAL_MAX_NFEV=55


def forcing(orders:float,capacity:float,params,kind:str)->float:
    tau,rate,gain,shape=(float(v) for v in params)
    if capacity<=0 or not all(math.isfinite(v) for v in (orders,capacity,*params)):
        raise ValueError("Invalid observable or parameter")
    if kind=="diff_c":
        raw=orders-shape*capacity
    elif kind=="ratio_p":
        raw=orders/(capacity**shape)
    else:
        raise ValueError("Unknown candidate family")
    return gain*max(raw-tau,0.0)


def candidate_activity(orders:float,capacity:float,params,kind:str)->bool:
    return forcing(orders,capacity,params,kind)>NUMERIC_TOL


def simulate_fraction(rows:list[dict],params,kind:str)->list[float]:
    """Conditional input-output response; not closed-loop intervention forecast.

    At t0 state impact is initialized from OBSERVED capacity fraction.
    We do not observe, reconstruct, or request hidden WORLD state variables.
    """
    if len(rows)!=TIMES:
        raise ValueError(f"Expected {TIMES} consecutive observations")
    tau,rate,gain,shape=(float(v) for v in params)
    if not 0<rate<=1 or gain<0:
        raise ValueError("Invalid rate/gain")
    times=[float(r["t"]) for r in rows]
    if any(abs(t-i)>1e-7 for i,t in enumerate(times)):
        raise ValueError("Missing/invalid time grid")
    first=rows[0]
    if TARGET not in first and "initial_effective_capacity" not in first:
        raise ValueError("Observed initial capacity required as initial condition")
    k0=float(first["nominal_capacity"])
    if k0<=0: raise ValueError("Nonpositive initial capacity")
    initial=first.get("initial_effective_capacity",first.get(TARGET))
    y0=float(initial)/k0
    if not math.isfinite(y0) or y0>1+1e-7 or y0<MIN_CAPACITY_FRACTION-1e-7:
        raise ValueError("Invalid observable initial capacity ratio")
    state=max(0.,1-y0)
    output=[]
    for r in rows:
        d,k=float(r["incoming_orders"]),float(r["nominal_capacity"])
        if k<=0: raise ValueError("Nonpositive nominal capacity")
        output.append(max(1-state,MIN_CAPACITY_FRACTION))
        state=(1-rate)*state+rate*forcing(d,k,params,kind)
        if not math.isfinite(state): raise ValueError("Nonfinite simulated response")
    return output


def validate_contract_fields(fields,expected):
    if tuple(fields)!=tuple(expected):
        raise ValueError(f"Schema boundary: expected {expected}, got {fields}")
    forbidden=("hidden","latent","primitive","world","truth","excess","impact","threshold")
    if any(any(x in name.lower() for x in forbidden) for name in fields):
        raise ValueError("Oracle/latent schema field forbidden")
    return True
