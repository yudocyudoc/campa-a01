#!/usr/bin/env python3
"""Compare A02 results with the original archived CEI C0.0-A notebook.

Checks are intentionally separate from the source runner. Positive results
establish software/numerical reproduction only, not causal identification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path

SOURCE = {
    "repository": "yudocyudoc/c0.0",
    "commit": "d90ff87ba47572edd7d2084ecdc62dfba54cd14d",
    "notebook": "CEI_C0_0_SD_Grafo_Colab.ipynb",
    "git_blob_sha": "fc66a1c85031c62243d24c03965ec849391bb371",
}
CHECKS = (
    "A_backlog_final_mayor_que_inicial",
    "A_maintenance_debt_final_positiva",
    "A_effective_capacity_final_menor_nominal",
    "A_cash_final_menor_inicial",
    "E_marketing_empeora_caja_vs_baseline",
    "E_marketing_empeora_backlog_vs_baseline",
    "E_capacidad_reduce_backlog_vs_baseline",
    "E_capacidad_mejora_caja_vs_baseline",
    "B_detecta_variable_desconectada",
    "B_detecta_feedback_loops",
    "B_detecta_cross_field_edges",
    "C_detecta_relaciones_omitidas",
    "C_detecta_creencia_falsa",
    "D_hay_ruta_maintenance_a_cash",
)
# Literal values displayed in original notebook cell 28 (six decimal places).
EXPECTED = {
    "baseline": {"cash_final": -1087.722016, "backlog_final": 363.215796, "maintenance_debt_final": 15.0},
    "mas_marketing": {"cash_final": -10183.728616, "backlog_final": 423.142561},
    "mas_capacidad": {"cash_final": 7676.077354, "backlog_final": 0.0, "effective_capacity_final": 140.028955},
    "mas_mantenimiento": {"cash_final": 1026.314163, "backlog_final": 191.215245},
    "capacidad_mas_mantenimiento": {"cash_final": 4076.077354, "backlog_final": 0.0},
}
EXPECTED_OUTPUTS = (
    "baseline.csv",
    "scenario_summary.csv",
    "cei_representation_gaps.csv",
    "gate_c00.csv",
    "graph_nodes.csv",
    "graph_edges.csv",
    "world_true.graphml",
    "agent_representation.graphml",
)


def validate(directory: Path) -> dict:
    issues = []
    missing = [name for name in EXPECTED_OUTPUTS if not (directory / name).is_file()]
    if missing:
        issues.append("Missing outputs: " + ", ".join(missing))

    observed_checks = {}
    if (directory / "gate_c00.csv").is_file():
        with (directory / "gate_c00.csv").open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        observed_checks = {row["check"]: str(row["pass"]).strip().lower() == "true" for row in rows}
        if len(rows) != len(CHECKS) or set(observed_checks) != set(CHECKS):
            issues.append("Gate names/count diverge from archived source (14 checks)")
        for check in CHECKS:
            if not observed_checks.get(check, False):
                issues.append(f"Original gate did not pass: {check}")

    comparisons = []
    if (directory / "scenario_summary.csv").is_file():
        with (directory / "scenario_summary.csv").open(encoding="utf-8-sig", newline="") as file:
            scenarios = {row["scenario"]: row for row in csv.DictReader(file)}
        if set(scenarios) != set(EXPECTED):
            issues.append(f"Scenario identities diverge: {sorted(scenarios)}")
        for scenario, metric_expectations in EXPECTED.items():
            for metric, expected in metric_expectations.items():
                row = scenarios.get(scenario, {})
                try:
                    actual = float(row[metric])
                    matches = math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-3)
                except (ValueError, TypeError, KeyError):
                    actual, matches = None, False
                comparisons.append({
                    "scenario": scenario, "metric": metric,
                    "source_reference": expected, "observed": actual,
                    "matches": matches,
                })
                if not matches:
                    issues.append(f"Numeric mismatch: {scenario}/{metric}: {actual} != {expected}")

    output_hashes = {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in EXPECTED_OUTPUTS if (directory / name).is_file()
    }
    return {
        "experiment": "A02",
        "type": "REPRODUCTION_OF_ORIGINAL_C00_A_NOT_NEW_CAUSAL_INFERENCE",
        "source": SOURCE,
        "status": "REPRODUCED" if not issues else "NOT_REPRODUCED",
        "original_gate_count": len(CHECKS),
        "observed_pass_count": sum(observed_checks.get(check, False) for check in CHECKS),
        "numerical_anchor_count": len(comparisons),
        "numerical_matches": sum(x["matches"] for x in comparisons),
        "numerical_comparisons": comparisons,
        "issues": issues,
        "outputs_sha256": output_hashes,
        "github_sha": os.environ.get("GITHUB_SHA"),
        "limitations": [
            "Synthetic original world and original model equations are public; this is not a blind mechanism discovery test.",
            "Archived rounded display values have 0.001 absolute / 1e-6 relative tolerance.",
            "A passing reproduction says nothing about generalization to c0.0 G5 or later adversarial G6.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/A02"))
    args = parser.parse_args()
    args.input.mkdir(parents=True, exist_ok=True)
    record = validate(args.input)
    (args.input / "reproduction.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8"
    )
    print(json.dumps({
        "status": record["status"],
        "checks": record["observed_pass_count"],
        "anchors": f'{record["numerical_matches"]}/{record["numerical_anchor_count"]}',
        "issues": record["issues"],
    }, ensure_ascii=False))
    return 0 if record["status"] == "REPRODUCED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
