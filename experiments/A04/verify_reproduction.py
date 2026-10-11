#!/usr/bin/env python3
"""Independent reproduction check for historical C0.0 SD5-A1 diagnostics.

The original A1 audit explicitly emitted NO scientific PASS/FAIL.
Here REPRODUCED means agreement with archived outputs, nothing causal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
HISTORICAL = json.loads((HERE / "historical_reference.json").read_text(encoding="utf-8"))
TOP_OUTPUTS = (
    "smooth_transfer_grid.csv",
    "reinforcing_transfer_grid.csv",
    "reinforcing_nearest_smooth.csv",
    "truth_transfer_overlap.csv",
    "all_probe_class_separability.csv",
    "feature_equivalence_pairs.csv",
    "static_target_dependency.csv",
    "target_proxy_audit.csv",
    "global_vs_class_separation.csv",
    "probe_power.csv",
)
WORLD_IDS = tuple(f"W{i:02d}" for i in range(1, 13))
WORLD_OUTPUT = "all_probe_hypothesis_scores.csv"


def rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def is_true(value: object) -> bool:
    return str(value).strip().lower() == "true"


def audit(directory: Path) -> dict:
    issues = []
    ref = HISTORICAL["summary"]
    sep = rows(directory / "all_probe_class_separability.csv")
    equivalent = rows(directory / "feature_equivalence_pairs.csv")
    direct = rows(directory / "static_target_dependency.csv")
    transfer = rows(directory / "reinforcing_transfer_grid.csv")
    class_sep = rows(directory / "global_vs_class_separation.csv")
    proxy = rows(directory / "target_proxy_audit.csv")

    actual_worlds = {r.get("case_id") for r in sep}
    if len(sep) != 12 or actual_worlds != set(WORLD_IDS):
        issues.append("Expected exactly W01-W12 in the all-probe class audit")
    if len(class_sep) != 12 or {r.get("case_id") for r in class_sep} != set(WORLD_IDS):
        issues.append("Global-vs-class table does not cover exactly 12 worlds")

    n_regimes = 10
    expected_expr = ref["n_expressions"]
    n_world_regime_proxy = 12 * n_regimes * expected_expr
    if len(proxy) != n_world_regime_proxy:
        issues.append(f"Proxy audit row count {len(proxy)} != {n_world_regime_proxy}")

    metrics = {
        "n_worlds": len(actual_worlds),
        "n_expressions": (len({r.get("feature_id") for r in direct})),
        "reinforcing_grid_stable_first_order": sum(
            r.get("regime") == "stable_first_order" for r in transfer),
        "reinforcing_grid_net_reinforcing": sum(
            r.get("regime") == "net_reinforcing" for r in transfer),
        "feature_equivalent_pairs": len(equivalent),
        "direct_target_features": sum(is_true(r.get("uses_target_directly")) for r in direct),
        "all_probe_truth_class_best": sum(is_true(r.get("truth_class_is_best")) for r in sep),
        "n_cases": len(sep),
    }
    for name, expected in ref.items():
        if metrics[name] != expected:
            issues.append(f"{name}: measured {metrics[name]} vs historical {expected}")

    # Important structural fact: the same all-probe comparison is about G4,
    # NOT the later 40-world G5 campaign.
    per_class = {name: sum(r.get("true_primitive") == name for r in sep)
                 for name in ("accumulation", "smooth_delay", "reinforcing", "pipeline_delay")}
    if any(value != 3 for value in per_class.values()):
        issues.append(f"Expected three worlds per G4 family, found: {per_class}")

    exact_direct_ids = sorted(r.get("feature_id") for r in direct if is_true(r.get("uses_target_directly")))
    if exact_direct_ids != sorted(HISTORICAL["direct_target_feature_ids"]):
        issues.append("Direct target-dependent feature identities do not match the archive")

    missing = [str(name) for name in TOP_OUTPUTS if not (directory / name).is_file()]
    for world in WORLD_IDS:
        if not (directory / world / WORLD_OUTPUT).is_file():
            missing.append(f"{world}/{WORLD_OUTPUT}")
    if missing:
        issues.append(f"Missing output files: {', '.join(missing[:10])}")

    files = [directory / name for name in TOP_OUTPUTS if (directory / name).is_file()]
    files += [directory / world / WORLD_OUTPUT for world in WORLD_IDS
              if (directory / world / WORLD_OUTPUT).is_file()]
    return {
        "experiment": "A04",
        "scope": "HISTORICAL_A1_G4_12_WORLDS_NOT_G5_40_WORLDS",
        "reproduction_status": "REPRODUCED" if not issues else "NOT_REPRODUCED",
        "scientific_verdict": "NOT_ISSUED_ORIGINAL_A1_IS_DIAGNOSTIC",
        "reference": {k: v for k, v in HISTORICAL.items() if k != "summary"},
        "historical_metrics": ref,
        "observed_metrics": metrics,
        "observed_worlds_by_class": per_class,
        "direct_target_features": exact_direct_ids,
        "issues": issues,
        "output_sha256": {
            str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        },
        "github_sha": os.getenv("GITHUB_SHA"),
        "limitations": [
            "A1 audits G4's 12 worlds/57 expressions, not G5's 40 worlds or error distribution.",
            "The historical audit did not issue scientific PASS/FAIL and this reproduction adds none.",
            "A matching heuristic feature-equivalence count is not a proof of unique identifiability.",
            "The synthetic worlds are known to the evaluator; this is not blind discovery.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/A04"))
    args = parser.parse_args()
    args.input.mkdir(parents=True, exist_ok=True)
    result = audit(args.input)
    (args.input / "reproduction.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "reproduction_status": result["reproduction_status"],
        "scientific_verdict": result["scientific_verdict"],
        "metrics": result["observed_metrics"],
        "issues": result["issues"],
    }, ensure_ascii=False))
    return 0 if result["reproduction_status"] == "REPRODUCED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
