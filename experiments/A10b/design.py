"""A10b: prospectively frozen seeds, no alteration of A10 model/selection rule.

All 10 seeds are evaluated, even if some favor diff_c or abstention.
The original A10 seed is included as a reproduction anchor.
"""
from __future__ import annotations
SEEDS=tuple(range(20261011,20261021))
ORIGINAL_A10_SEED=20261011
SOURCE_A10_RUN=38126170978
TRAIN_SCENARIOS=5
HOLDOUT_SCENARIOS=17
MONTHS=25
EXPECTED_MARGIN=0.005       # exact same heuristic as A10
NOISE_STD_FRACTION=0.01     # no new noise distributions
NOISE_CONDITIONS=("noiseless","noisy_1pct")
DECISION_LABELS=("ratio_p","diff_c","ABSTAIN_UNRESOLVED")

def validate():
    if len(SEEDS)!=len(set(SEEDS)) or len(SEEDS)!=10:
        raise ValueError("A10b seeds changed")
    if ORIGINAL_A10_SEED not in SEEDS:
        raise ValueError("Lost A10 reproducibility anchor")
    if any(s<=0 for s in SEEDS):raise ValueError("Invalid RNG seed")
