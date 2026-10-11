#!/usr/bin/env python3
"""A06 predeclared probes and candidate-only design geometry (Python stdlib).

When K != K0, the ratio/diff coordinates STILL agree exactly at orders == K.
No WORLD or numerical engine is imported by this module.
"""
K0 = 115.0  # Original G5 default nominal capacity; verified by experiment.py

PROBES = [
    {"id": "control_K115_S25", "kind": "control", "capacity": 115.0, "shock": 25.0},
    {"id": "demand_K115_S0", "kind": "demand_only", "capacity": 115.0, "shock": 0.0},
    {"id": "demand_K115_S50", "kind": "demand_only", "capacity": 115.0, "shock": 50.0},
    {"id": "demand_K115_S70", "kind": "demand_only", "capacity": 115.0, "shock": 70.0},
    *[
        {"id": f"cross_K{int(k)}_S{int(shock)}", "kind": "crossed", "capacity": k, "shock": shock}
        for k in (90.0, 145.0, 180.0, 220.0)
        for shock in (0.0, 25.0, 50.0, 70.0)
    ],
    {"id": "pulse_K80_S25", "kind": "transient", "capacity": 115.0, "shock": 25.0,
     "stress_capacity": 80.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K160_S25", "kind": "transient", "capacity": 115.0, "shock": 25.0,
     "stress_capacity": 160.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K90_S50", "kind": "transient", "capacity": 145.0, "shock": 50.0,
     "stress_capacity": 90.0, "stress_start": 8.0, "stress_end": 12.0},
]


def normalized_signals(orders: float, capacity: float) -> tuple[float, float]:
    """Pre-given, pair-matched feature geometry. No fitted parameters."""
    ratio = (orders / capacity - 0.75) / 0.25
    diff = (orders - capacity + 0.25 * K0) / (0.25 * K0)
    return ratio, diff



def deterministic_selection(table: list[dict]) -> list[str]:
    eligible = [r for r in table if r["kind"] in ("crossed", "transient")]
    # Fixed ranking on candidate-prediction-only discrepancy; never consult WORLD.
    eligible.sort(key=lambda r: (-r["candidate_disagreement"], r["probe"]))
    return [r["probe"] for r in eligible[:4]]


