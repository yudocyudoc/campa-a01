"""A12 candidate-only decision-value gate. Frozen BEFORE A12 WORLD adjudication.

Numbers are an A12 policy choice after reviewing exploratory A11, not a
statistical preregistration blind to W016. No generator, no oracle score data.
"""
from __future__ import annotations

SHOCKS=tuple(float(k) for k in range(20,101,10))  # nine scenarios
CAPACITIES=tuple(float(k) for k in range(90,261,5))  # 35 policies
ARMS=("noiseless","noisy_1pct")
FAMILIES=("ratio_p","diff_c")
INITIAL_BASE_CAPACITY=115.
MATERIAL_FRACTION=0.05  # >=5% of each model's own cash range
MIN_SHOCK_FRACTION=1/3  # >=3 of 9 shocks, in EACH arm
MIN_SHOCK_COUNT=3
CASH_TIE_TOL=1e-6
EVALUATION_TARGET="cash at pre-flow t24"
BASELINES=("no_change_115","maximum_capacity_260","estimated_uncongested_peak_demand")
NO_POLICY_FUTURE_OUTCOMES_IN_GATE=True
A11_SOURCE_RUN=38183774855


def check_design():
    if len(SHOCKS)!=9 or len(CAPACITIES)!=35:
        raise ValueError("A12 grid changed")
    if SHOCKS!=tuple(float(k) for k in range(20,101,10)):
        raise ValueError("A12 shocks modified")
    if CAPACITIES!=tuple(float(k) for k in range(90,261,5)):
        raise ValueError("A12 capacity choices modified")
    if not (0<MATERIAL_FRACTION<1) or MIN_SHOCK_COUNT!=3:
        raise ValueError("A12 gate threshold changed")
    if len(ARMS)!=2 or len(FAMILIES)!=2:
        raise ValueError("A12 candidate families/arms changed")
