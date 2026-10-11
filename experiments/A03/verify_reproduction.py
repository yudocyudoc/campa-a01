#!/usr/bin/env python3
"""Validate A03 against case-level observations from historical executed G5.

This is a strict numerical/software reproduction check, NOT a causal-validity gate.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE_PATH = HERE / "historical_reference.json"
EXPECTED_COUNTS = {"COMMIT_CORRECT": 15, "COMMIT_WRONG": 25, "ABSTAIN": 0}
EXPECTED_CORRECT_BY_CLASS = {
    "accumulation": 4,
    "first_order_relaxation": 2,
    "self_reinforcing": 4,
    "pipeline_delay": 5,
}
NUMERIC_ANCHORS = {
    "performance.csv": {
        "mean_total_probes": 2.275,
        "mean_informative_probes": 2.175,
        "commit_correct_rate": 0.375,
        "commit_wrong_rate": 0.625,
        "abstention_rate": 0.0,
    },
    "decision_baseline.csv": {
        "constant_policy_match_rate": 0.9,
        "cei_action_match_rate_when_committed": 0.9,
        "cei_minus_constant": 0.0,
    },
}
TOP_FILES = (
    "generalization_summary.csv", "primitive_confusion.csv",
    "protocol_gate.csv", "performance.csv", "decision_baseline.csv",
    "out_of_grid_audit.csv", "feature_leakage_audit.csv",
    "structural_class_audit.csv",
)
CASE_FILES = (
    "multiregime_evidence.csv", "sequential_history.csv",
    "feature_rank.csv", "primitive_summary.csv",
    "decision_table.csv", "oracle_actions.csv",
)


def read_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def verify(directory: Path, reference: dict) -> dict:
    issues = []
    expected = {row["case_id"]: row for row in reference["cases"]}
    rows = read_rows(directory / "generalization_summary.csv")
    actual = {row["case_id"]: row for row in rows if "case_id" in row}
    if len(expected) != 40:
        issues.append("Reference must include exactly 40 cases")
    if len(rows) != 40 or len(actual) != 40 or set(actual) != set(expected):
        issues.append("Case count/identities differ from historical 40-world reference")
    differences = []
    for case, archival in expected.items():
        observed = actual.get(case)
        if observed is None:
            continue
        for field in ("true_primitive", "predicted_primitive", "winner_feature", "primary_outcome"):
            if observed.get(field) != archival[field]:
                differences.append({
                    "case": case, "field": field,
                    "expected": archival[field], "observed": observed.get(field)
                })
    if differences:
        issues.append(f"Historical case outcomes mismatch: {len(differences)} fields")

    counts = dict(Counter(row.get("primary_outcome") for row in rows))
    for name, value in EXPECTED_COUNTS.items():
        if counts.get(name, 0) != value:
            issues.append(f"Outcome {name} count {counts.get(name, 0)} != {value}")

    by_class = Counter(
        row.get("true_primitive") for row in rows
        if row.get("primary_outcome") == "COMMIT_CORRECT"
    )
    for name, value in EXPECTED_CORRECT_BY_CLASS.items():
        if by_class.get(name, 0) != value:
            issues.append(f"Correct per class {name}: {by_class.get(name, 0)} != {value}")

    gates = read_rows(directory / "protocol_gate.csv")
    if len(gates) != 6 or len({g.get("check") for g in gates}) != 6:
        issues.append("Protocol gate must contain six distinct historical checks")
    if any(str(g.get("pass", "")).lower() != "true" for g in gates):
        issues.append("At least one protocol check failed")

    numerical = []
    for name, fields in NUMERIC_ANCHORS.items():
        data = read_rows(directory / name)
        if len(data) != 1:
            issues.append(f"Expected exactly one row in {name}")
            continue
        for metric, expected_value in fields.items():
            try:
                observed_value = float(data[0][metric])
                matches = math.isfinite(observed_value) and math.isclose(
                    observed_value, expected_value, rel_tol=1e-7, abs_tol=1e-7
                )
            except (ValueError, KeyError, TypeError):
                observed_value, matches = None, False
            numerical.append({
                "file": name, "metric": metric,
                "historical_value": expected_value,
                "observed_value": observed_value, "matches": matches
            })
            if not matches:
                issues.append(f"Numerical anchor mismatch {name}/{metric}: {observed_value}")

    missing = [
        str(directory / x) for x in TOP_FILES if not (directory / x).is_file()
    ]
    for case in expected:
        for name in CASE_FILES:
            if not (directory / case / name).is_file():
                missing.append(f"{case}/{name}")
    if missing:
        issues.append(f"Missing expected output files: {len(missing)}")

    available = [directory / x for x in TOP_FILES if (directory / x).is_file()]
    available += [
        directory / c / name for c in expected for name in CASE_FILES
        if (directory / c / name).is_file()
    ]
    hashes = {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in available
    }
    return {
        "experiment": "A03",
        "classification": "HISTORICAL_REPRODUCTION_NOT_CAUSAL_DISCOVERY",
        "status": "REPRODUCED" if not issues else "NOT_REPRODUCED",
        "reference": {
            key: value for key, value in reference.items() if key != "cases"
        },
        "expected_cases": len(expected),
        "observed_cases": len(rows),
        "exact_case_matches": sum(
            all(
                actual.get(case, {}).get(field) == original[field]
                for field in ("true_primitive", "predicted_primitive", "winner_feature", "primary_outcome")
            ) for case, original in expected.items()
        ),
        "outcomes": counts,
        "correct_by_class": dict(by_class),
        "original_protocol_passed": len(gates) == 6 and all(str(g.get("pass", "")).lower() == "true" for g in gates),
        "numerical_comparisons": numerical,
        "case_differences": differences,
        "issues": issues,
        "sha256_by_output": hashes,
        "github_sha": os.environ.get("GITHUB_SHA"),
        "limitations": [
            "The world generators and historical answers are public and used only after the experiment; this is not blind LLM discovery.",
            "Exact case-level comparison measures reproducibility; matching the original 15/25 does not validate those causal conclusions.",
            "A03 does not address the later c0.0 A1/G6 identifiability findings.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/A03"))
    args = parser.parse_args()
    with REFERENCE_PATH.open(encoding="utf-8") as handle:
        reference = json.load(handle)
    args.input.mkdir(parents=True, exist_ok=True)
    result = verify(args.input, reference)
    (args.input / "reproduction.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "status": result["status"],
        "cases": result["observed_cases"],
        "exact_case_matches": result["exact_case_matches"],
        "outcomes": result["outcomes"],
        "errors": result["issues"][:8],
    }, ensure_ascii=False))
    return 0 if result["status"] == "REPRODUCED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
