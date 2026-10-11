#!/usr/bin/env python3
"""A01: deterministic infrastructure smoke, NOT a causal discovery experiment.

Two hand-authored illustrative response rules are executed under the same
parameters and common initial-stock perturbation. No LLM, secret, or oracle.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

HORIZON_DAYS = 30
DT_DAYS = 1.0
PARAMETERS = {
    "daily_demand_pan_per_day": 8.0,
    "production_capacity_pan_per_day": 12.0,
    "waste_rate_per_day": 0.05,
}
MECHANISMS = ("fixed_production", "demand_responsive_production")
CONDITIONS = {"baseline": 100.0, "initial_stock_plus_10": 110.0}


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def simulate(mechanism: str, initial_stock: float) -> list[dict]:
    if mechanism not in MECHANISMS:
        raise ValueError(f"Unknown mechanism: {mechanism}")
    if initial_stock < 0:
        raise ValueError("Initial stock must be nonnegative")
    stock = float(initial_stock)
    rows = []
    for day in range(HORIZON_DAYS):
        capacity = PARAMETERS["production_capacity_pan_per_day"]
        demand = PARAMETERS["daily_demand_pan_per_day"]
        waste_rate = PARAMETERS["waste_rate_per_day"]
        production = capacity if mechanism == "fixed_production" else min(capacity, demand)
        waste = min(stock / DT_DAYS, stock * waste_rate)
        # Sales are limited by the stock remaining after spoilage in this
        # illustrative one-day step. Production arrives at the end of the day.
        sales = min(demand, max(0.0, stock / DT_DAYS - waste))
        next_stock = stock + DT_DAYS * (production - sales - waste)
        if next_stock < -1e-9:
            raise AssertionError("Illustrative stock balance became negative")
        rows.append({
            "day": day,
            "mechanism": mechanism,
            "initial_stock_pan": float(initial_stock),
            "inventory_before_pan": stock,
            "production_pan_per_day": production,
            "sales_pan_per_day": sales,
            "waste_pan_per_day": waste,
            "inventory_after_pan": next_stock,
        })
        stock = next_stock
    return rows


def run_experiment(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    observations = []
    records = []
    for mechanism in MECHANISMS:
        for condition, initial_stock in CONDITIONS.items():
            trajectory = simulate(mechanism, initial_stock)
            records.extend([{**row, "condition": condition} for row in trajectory])
            observations.append({
                "mechanism": mechanism,
                "condition": condition,
                "initial_stock_pan": initial_stock,
                "final_stock_pan": trajectory[-1]["inventory_after_pan"],
                "trajectory_sha256": stable_hash(trajectory),
            })

    csv_path = output_dir / "trajectories.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    definition = {
        "horizon_days": HORIZON_DAYS,
        "dt_days": DT_DAYS,
        "parameters": PARAMETERS,
        "mechanisms": list(MECHANISMS),
        "conditions": CONDITIONS,
    }
    manifest = {
        "experiment": "A01",
        "status": "TECHNICAL_SMOKE_NOT_CAUSAL_VALIDATION",
        "description": "Two illustrative hand-authored mechanisms; no inference or fitted parameters.",
        "definition": definition,
        "definition_sha256": stable_hash(definition),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "trajectories_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "scenarios": observations,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/A01"))
    args = parser.parse_args()
    result = run_experiment(args.out)
    print(json.dumps({
        "status": result["status"],
        "definition_sha256": result["definition_sha256"],
        "scenarios": len(result["scenarios"]),
        "output": str(args.out),
    }, ensure_ascii=False))
