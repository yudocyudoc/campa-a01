"""A08 design frozen before execution; standard-library only.

Scientific scope: W016, original G5 synthetic dynamics.
Both adversaries use EXACTLY three effective shape/gain parameters
(tau, adjustment_rate, g), plus one explicit driver exponent/coefficient.
"""
from __future__ import annotations

from experiments.A07.design import TRAINING, HOLDOUTS

TRAIN = TRAINING["cross_capacity"]  # five conditions including K=115 and 145
PROBES = HOLDOUTS                   # full 17-condition holdout catalog

# (effective threshold tau, adjustment rate a, gain g, driver shape c or p)
# No redundant excursion/degradation factor: excursion=1, degradation=g.
FAMILIES = {
    "diff_c": {
        "bounds": ((-150.0, 0.10, 0.0003, 0.20), (160.0, 1.20, 0.10, 2.00)),
        "local_starts": (
            (-22.5, 0.63, 0.0153, 1.00),
            (-20.0, 0.45, 0.0150, 0.80),
        ),
    },
    "ratio_p": {
        "bounds": ((0.01, 0.10, 0.01, 0.20), (2.50, 1.20, 5.0, 1.80)),
        # Do not seed the optimizer with oracle p=1/tau_true.
        "local_starts": (
            (0.80, 0.50, 1.70, 0.80),
            (0.90, 0.70, 1.90, 1.20),
        ),
    },
}
# Bounded global-heuristic trial and a deterministic local refinement.
# They DO NOT certify the global minimum of a nonconvex loss.
DE_MAXITER = 12
DE_POPSIZE = 4
DE_SEED = 20261011
LOCAL_MAX_NFEV = 60

NOISELESS_TOL = 1e-8         # implementation precision, not noise-calibrated
PRACTICAL_GAP = 0.01         # optional heuristic, NOT a significance criterion
VARS = ("effective_capacity", "backlog", "cash")
SCALES = (115.0, 115.0, 20000.0)
MIN_TIME = 8.0


def validate_design() -> None:
    train_ids = {x["id"] for x in TRAIN}
    holdout_ids = {x["id"] for x in PROBES}
    assert len(TRAIN) == len(train_ids) == 5
    assert len(PROBES) == len(holdout_ids) == 17
    assert not train_ids.intersection(holdout_ids)
    for family in FAMILIES.values():
        lower, upper = family["bounds"]
        assert len(lower) == len(upper) == 4
        assert all(l < u for l, u in zip(lower, upper))
        for start in family["local_starts"]:
            assert all(l <= x <= u for l, x, u in zip(lower, start, upper))
