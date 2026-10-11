"""A07 frozen protocol, independent of scientific engines and WORLD observations."""
from __future__ import annotations

K0 = 115.0
SHOCKS = (0.0, 25.0, 50.0, 70.0)
CAPACITIES = (90.0, 145.0, 180.0, 220.0)

TRAINING = {
    "fixed_capacity": (
        {"id": "train_K115_S0", "kind": "fixed_training", "capacity": K0, "shock": 0.0},
        {"id": "train_K115_S25", "kind": "fixed_training", "capacity": K0, "shock": 25.0},
        {"id": "train_K115_S70", "kind": "fixed_training", "capacity": K0, "shock": 70.0},
    ),
    "cross_capacity": (
        {"id": "train_K115_S0", "kind": "fixed_training", "capacity": K0, "shock": 0.0},
        {"id": "train_K115_S25", "kind": "fixed_training", "capacity": K0, "shock": 25.0},
        {"id": "train_K115_S70", "kind": "fixed_training", "capacity": K0, "shock": 70.0},
        {"id": "train_K145_S25", "kind": "cross_training", "capacity": 145.0, "shock": 25.0},
        {"id": "train_K145_S50", "kind": "cross_training", "capacity": 145.0, "shock": 50.0},
    ),
}

HOLDOUTS = tuple(
    {"id": f"holdout_K{int(k)}_S{int(s)}",
     "kind": "cross_holdout", "capacity": k, "shock": s,
     "stratum": f"K{int(k)}"}
    for k in CAPACITIES for s in SHOCKS
    if not (k == 145.0 and s in (25.0, 50.0))
) + (
    {"id": "pulse_K80_S25", "kind": "pulse_holdout",
     "capacity": 115.0, "shock": 25.0, "stratum": "pulse",
     "stress_capacity": 80.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K90_S50", "kind": "pulse_holdout",
     "capacity": 145.0, "shock": 50.0, "stratum": "pulse",
     "stress_capacity": 90.0, "stress_start": 8.0, "stress_end": 12.0},
    {"id": "pulse_K250_S70", "kind": "pulse_holdout",
     "capacity": 180.0, "shock": 70.0, "stratum": "pulse",
     "stress_capacity": 250.0, "stress_start": 8.0, "stress_end": 12.0},
)

# Effective reparameterization: tau = baseline + threshold*excursion.
# Stress = max((difference - tau)/excursion, 0).
# This permits the same stress functions as free baseline+threshold at any given
# positive excursion, but avoids a redundant optimizer dimension.
BOUNDS = (
    (-100.0, 10.0, 0.10, 0.05),  # tau, excursion, adjustment rate, degradation
    (100.0, 120.0, 1.20, 0.90),
)
MAX_NFEV_PER_START = 42
NUMERICAL_FLOOR = 1e-8
PRACTICAL_GAP = 0.01  # dimensionless RMS; heuristic, NOT noise-calibrated
MAX_SELECTED = 4


def select_diverse_holdouts(candidate_rows: list[dict], count: int = MAX_SELECTED) -> list[str]:
    """Candidate-only selection, at most one per stratum, no WORLD fields."""
    by_stratum = {}
    for row in candidate_rows:
        category = row["stratum"]
        score = float(row["candidate_disagreement"])
        if score < 0 or score != score:
            raise ValueError("Invalid predicted disagreement")
        current = by_stratum.get(category)
        if current is None or (-score, row["probe"]) < (
            -float(current["candidate_disagreement"]), current["probe"]
        ):
            by_stratum[category] = row
    best = sorted(
        by_stratum.values(),
        key=lambda row: (-float(row["candidate_disagreement"]), row["probe"]),
    )
    return [row["probe"] for row in best[:count]]


def validate_disjointness() -> None:
    held = {p["id"] for p in HOLDOUTS}
    assert len(held) == len(HOLDOUTS)
    for probes in TRAINING.values():
        assert not held.intersection(p["id"] for p in probes)
        assert len(set(p["id"] for p in probes)) == len(probes)
    assert len({p["stratum"] for p in HOLDOUTS}) >= MAX_SELECTED
