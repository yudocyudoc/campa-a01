"""A09 analytical conditions and classifiers, Python stdlib only.

These are properties of the stipulated first-order model, NOT a proof that a
particular finite, sampled, clipped dataset identifies the generating mechanism.
"""
from __future__ import annotations

import math

EPS = 1e-9
ACTIVE = "active"
INACTIVE = "inactive"
CLIPPED = "clipped"
UNCLIPPED = "unclipped"


def beta(threshold: float) -> float:
    """WORLD ratio-driver activation condition: demand > beta*K."""
    return 0.75 + 0.25 * float(threshold)


def world_excess(demand: float, capacity: float, threshold: float) -> float:
    if capacity <= 0:
        raise ValueError("Capacity must be positive")
    return max(4.0 * (demand / capacity - beta(threshold)), 0.0)


def diff_c_excess(demand: float, capacity: float, c: float, tau: float) -> float:
    return max(demand - c * capacity - tau, 0.0)


def world_slope_at_k(k: float, world_gain: float) -> float:
    """Slope of gain-weighted WORLD forcing w.r.t. demand in active region."""
    if k <= 0:
        raise ValueError("Capacity must be positive")
    return 4.0 * world_gain / k


def rival_slope(gain: float) -> float:
    """Slope of gain-weighted diff_c forcing in active region."""
    return float(gain)


def activation_regime(excess: float, eps: float = EPS) -> str:
    return ACTIVE if excess > eps else INACTIVE


def output_regime(impact: float, minimum_fraction: float, eps: float = EPS) -> str:
    if not 0 < minimum_fraction < 1:
        raise ValueError("Minimum capacity fraction must be between 0 and 1")
    return CLIPPED if impact >= 1.0 - minimum_fraction - eps else UNCLIPPED


def cross_k_slope_obstruction(
    capacities: list[float], world_gain: float,
    tol: float = 1e-12,
) -> dict:
    """Exact algebraic incompatibility for active response maps at two K values.

    Assumes gain>0, same first-order response rate, a single rival gain,
    genuinely active and unclipped input/output regimes, and equality as a
    function of varying demand over a nonzero interval in EACH regime.
    Does not assert those assumptions hold in the sampled time series.
    """
    unique = sorted(set(float(k) for k in capacities))
    if any(k <= 0 for k in unique):
        raise ValueError("All capacities must be positive")
    if world_gain <= 0:
        raise ValueError("World gain must be positive")
    required = {str(k): world_slope_at_k(k, world_gain) for k in unique}
    values = list(required.values())
    difference = max(values) - min(values) if values else 0.0
    return {
        "conditional_model_level_obstruction": len(unique) >= 2 and difference > tol,
        "capacities": unique,
        "required_single_rival_gain_by_K": required,
        "required_gain_range": difference,
        "assumptions": [
            "Both drivers are active for a nonzero open demand interval in each K.",
            "The observation is unclipped and the first-order response rate is shared.",
            "The rival uses one fixed gain across fields, and WORLD gain is positive.",
            "Demand can be varied independently of capacity within those active regions.",
        ],
        "not_a_finite_data_global_certificate": True,
    }


def identify_regime(excess: float, impact: float, minimum_fraction: float) -> dict:
    return {
        "input_state": activation_regime(excess),
        "output_state": output_regime(impact, minimum_fraction),
        "active_unclipped": (
            activation_regime(excess) == ACTIVE
            and output_regime(impact, minimum_fraction) == UNCLIPPED
        ),
    }


def distinct_values(values: list[float], tol: float = 1e-8) -> int:
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Nonfinite demand")
    ordered = sorted(values)
    unique = []
    for v in ordered:
        if not unique or abs(v - unique[-1]) > tol:
            unique.append(v)
    return len(unique)
