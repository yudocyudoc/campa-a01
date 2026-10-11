#!/usr/bin/env python3
# CEI A03: original c0.0 SD5-G5 corrected 40-world benchmark.
# Source: https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_G5_Benchmark_Corregido_40_Mundos.ipynb
# Notebook Git blob: 730420a744d91d195ec1eca60ef3c4dd9468e063
# Adaptation: omit only Colab environment bootstrap cell 3.
# Replace only /content/ export directory with CEI_A03_RESULTS_DIR.
# Render display() with a compact non-mutating textual representation.
# Scientific equations, seeds, grids, rules, budgets, gate and ordering unchanged.
import os

def display(obj):
    shape = getattr(obj, "shape", None)
    if shape is not None:
        print("[notebook display]", type(obj).__name__, "shape", shape)
    else:
        print("[notebook display]", type(obj).__name__, str(obj)[:500])



# ---- C0.0 original notebook code cell 4 ----
import sys
import itertools
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import BPTK_Py
from BPTK_Py import Model
from BPTK_Py.sddsl import functions as sd

print("Python:", sys.version.split()[0])
print("NumPy:", np.__version__)
print("pandas:", pd.__version__)
print("BPTK-Py:", getattr(BPTK_Py, "__version__", "versión no expuesta"))


# ---- C0.0 original notebook code cell 6 ----
DEFAULT_PARAMS = {
    "months": 24,
    "base_order_rate": 0.09,
    "market_shock_start": 8.0,
    "market_shock_orders": 25.0,
    "marketing_intensity": 1.0,
    "acquisition_per_marketing_unit": 8.0,
    "nominal_capacity": 115.0,
    "minimum_capacity_fraction": 0.40,
    "cancel_rate": 0.06,
    "base_churn": 2.0,
    "customer_loss_per_cancel": 0.40,
    "price": 100.0,
    "variable_cost_per_order": 50.0,
    "fixed_cost": 4000.0,
    "marketing_cost_per_unit": 800.0,
    "capacity_cost_per_extra_unit": 10.0,
    "collection_delay": 2.0,
}

PRIMITIVES = [
    "accumulation",
    "first_order_relaxation",
    "self_reinforcing",
    "pipeline_delay",
]

TRUE_DERIVED_ID = (
    "ratio::incoming_orders/nominal_capacity"
)

OBSERVED_COLUMNS = [
    "customer_base",
    "customer_acquisition",
    "market_shock",
    "incoming_orders",
    "nominal_capacity",
    "effective_capacity",
    "fulfilled",
    "backlog",
    "cancellations",
    "churn",
    "billed_revenue",
    "receivables",
    "collections",
    "operating_cost",
    "cash",
    "marketing_intensity",
]

VARIABLE_ROLE = {
    "customer_base": "stock",
    "customer_acquisition": "flow",
    "market_shock": "exogenous",
    "incoming_orders": "rate",
    "nominal_capacity": "capacity_rate",
    "effective_capacity": "capacity_rate",
    "fulfilled": "rate",
    "backlog": "stock",
    "cancellations": "flow",
    "churn": "flow",
    "billed_revenue": "money_rate",
    "receivables": "money_stock",
    "collections": "money_rate",
    "operating_cost": "money_rate",
    "cash": "money_stock",
    "marketing_intensity": "control",
}

TARGET = "effective_capacity"

# Variables excluidas de la gramática causal primaria.
# Son target directo o descendientes mecánicos cercanos capaces de
# reintroducir el efecto como proxy.
BLOCKED_DRIVER_VARS = {
    "effective_capacity",
    "fulfilled",
    "backlog",
    "cancellations",
    "churn",
    "billed_revenue",
    "receivables",
    "collections",
    "operating_cost",
}

# Biblioteca estándar congelada.
PROBE_LIBRARY = {
    "demanda_alta_capacidad_holgada": {
        "params": {
            "market_shock_orders": 70.0,
            "nominal_capacity": 220.0,
        },
        "capacity_mode": "constant",
    },
    "buffer_capacidad": {
        "params": {
            "market_shock_orders": 25.0,
            "nominal_capacity": 145.0,
        },
        "capacity_mode": "constant",
    },
    "estres_capacidad_transitorio": {
        "params": {
            "market_shock_orders": 0.0,
            "nominal_capacity": 145.0,
        },
        "capacity_mode": "transient",
        "stress_start": 8.0,
        "stress_end": 14.0,
        "stress_capacity": 80.0,
    },
    "shock_demanda_fuerte": {
        "params": {
            "market_shock_orders": 50.0,
            "nominal_capacity": 115.0,
        },
        "capacity_mode": "constant",
    },
    "marketing_push": {
        "params": {
            "marketing_intensity": 1.5,
            "market_shock_orders": 25.0,
            "nominal_capacity": 115.0,
        },
        "capacity_mode": "constant",
    },
}

# Biblioteca dirigida heredada como pulsos genéricos.
DIRECTED_PROBE_LIBRARY = {
    "pulso_breve_severo_recuperacion_larga": {
        "params": {
            "months": 30,
            "market_shock_orders": 0.0,
            "nominal_capacity": 180.0,
        },
        "capacity_mode": "transient",
        "stress_start": 8.0,
        "stress_end": 10.0,
        "stress_capacity": 60.0,
    },
    "pulso_breve_moderado_recuperacion_larga": {
        "params": {
            "months": 30,
            "market_shock_orders": 0.0,
            "nominal_capacity": 180.0,
        },
        "capacity_mode": "transient",
        "stress_start": 8.0,
        "stress_end": 10.0,
        "stress_capacity": 80.0,
    },
    "pulso_medio_severo_recuperacion_larga": {
        "params": {
            "months": 30,
            "market_shock_orders": 0.0,
            "nominal_capacity": 180.0,
        },
        "capacity_mode": "transient",
        "stress_start": 8.0,
        "stress_end": 12.0,
        "stress_capacity": 65.0,
    },
    "pulso_tardio_breve_recuperacion_larga": {
        "params": {
            "months": 30,
            "market_shock_orders": 0.0,
            "nominal_capacity": 180.0,
        },
        "capacity_mode": "transient",
        "stress_start": 14.0,
        "stress_end": 16.0,
        "stress_capacity": 60.0,
    },
}

ACTIONS = {
    "sin_cambio": {
        "params": {},
        "capacity_mode": "constant",
    },
    "mas_marketing": {
        "params": {
            "marketing_intensity": 1.5,
        },
        "capacity_mode": "constant",
    },
    "mas_capacidad_permanente": {
        "params": {
            "nominal_capacity": 145.0,
        },
        "capacity_mode": "constant",
    },
    "buffer_capacidad_temprano": {
        "params": {},
        "capacity_mode": "transient",
        "stress_start": 8.0,
        "stress_end": 12.0,
        "stress_capacity": 165.0,
    },
    "buffer_capacidad_tardio": {
        "params": {},
        "capacity_mode": "transient",
        "stress_start": 14.0,
        "stress_end": 18.0,
        "stress_capacity": 165.0,
    },
}

WORLD_SEED = 20261006
N_PER_CLASS = 10

WORLD_RANGES = {
    "accumulation": {
        "threshold": (0.15, 0.55),
        "build_rate": (4.8, 7.8),
        "recovery_rate": (1.2, 5.8),
        "degradation": (0.012, 0.032),
    },
    "first_order_relaxation": {
        "threshold": (0.15, 0.55),
        "adjustment_rate": (0.22, 0.78),
        "degradation": (0.22, 0.55),
    },
    "self_reinforcing": {
        "threshold": (0.15, 0.55),
        "drive_rate": (1.8, 4.5),
        "growth_rate": (0.08, 0.28),
        "saturation_level": (1.2, 3.8),
        "degradation": (0.015, 0.040),
    },
    "pipeline_delay": {
        "threshold": (0.15, 0.55),
        "delay_time": (1.2, 3.2),
        "degradation": (0.22, 0.55),
    },
}

rng = np.random.default_rng(WORLD_SEED)

WORLD_CASES = {}
case_counter = 1

for primitive in PRIMITIVES:
    for _ in range(N_PER_CLASS):
        truth = {
            name: float(rng.uniform(low, high))
            for name, (low, high)
            in WORLD_RANGES[primitive].items()
        }

        case_id = f"W{case_counter:03d}"
        WORLD_CASES[case_id] = {
            "primitive": primitive,
            "truth": truth,
        }
        case_counter += 1

print(
    "WORLD_TRUE generados:",
    len(WORLD_CASES),
    "| seed:",
    WORLD_SEED,
)


# ---- C0.0 original notebook code cell 7 ----
def run_model(model, equations, manager_name="m", backend="rust"):
    bptk = BPTK_Py.bptk()
    bptk.register_scenario_manager({manager_name: {"model": model}})
    bptk.register_scenarios(
        scenarios={"base": {}},
        scenario_manager=manager_name,
    )

    try:
        df = bptk.run_scenarios(
            scenario_managers=[manager_name],
            scenarios=["base"],
            equations=equations,
            backend=backend,
        )
        used = backend
    except Exception as exc:
        print("Rust falló; usando Python:", exc)
        bptk = BPTK_Py.bptk()
        bptk.register_scenario_manager({manager_name: {"model": model}})
        bptk.register_scenarios(
            scenarios={"base": {}},
            scenario_manager=manager_name,
        )
        df = bptk.run_scenarios(
            scenario_managers=[manager_name],
            scenarios=["base"],
            equations=equations,
            backend="python",
        )
        used = "python"

    return df, used

WORLD_EQUATIONS = [
    "customer_base", "customer_acquisition", "market_shock",
    "incoming_orders", "nominal_capacity", "effective_capacity",
    "fulfilled", "utilization", "hidden_signal", "hidden_excess",
    "hidden_state", "backlog", "cancellations", "churn",
    "billed_revenue", "receivables", "collections",
    "operating_cost", "cash", "marketing_intensity",
]

def build_world(
    true_primitive,
    world_truth,
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    p = DEFAULT_PARAMS.copy()
    if params:
        p.update(params)

    truth = dict(world_truth)

    model = Model(
        starttime=0.0,
        stoptime=float(p["months"]),
        dt=1.0,
        name=f"cei_sd5g5_world_{true_primitive}",
    )

    customer_base = model.stock("customer_base")
    backlog = model.stock("backlog")
    hidden_state = model.stock("hidden_state")
    receivables = model.stock("receivables")
    cash = model.stock("cash")

    customer_base.initial_value = 1000.0
    backlog.initial_value = 0.0
    hidden_state.initial_value = 0.0
    receivables.initial_value = 0.0
    cash.initial_value = 20000.0

    def constant(name, value):
        c = model.constant(name)
        c.equation = float(value)
        return c

    base_order_rate = constant("base_order_rate", p["base_order_rate"])
    market_shock_start = constant("market_shock_start", p["market_shock_start"])
    market_shock_orders = constant("market_shock_orders", p["market_shock_orders"])
    marketing_intensity = constant("marketing_intensity", p["marketing_intensity"])
    acquisition_per_marketing_unit = constant(
        "acquisition_per_marketing_unit",
        p["acquisition_per_marketing_unit"],
    )
    base_nominal_capacity = constant(
        "base_nominal_capacity",
        p["nominal_capacity"],
    )

    stress_start_c = constant("stress_start", stress_start)
    stress_end_c = constant("stress_end", stress_end)
    stress_capacity_c = constant("stress_capacity", stress_capacity)

    cancel_rate = constant("cancel_rate", p["cancel_rate"])
    base_churn = constant("base_churn", p["base_churn"])
    customer_loss_per_cancel = constant(
        "customer_loss_per_cancel",
        p["customer_loss_per_cancel"],
    )
    price = constant("price", p["price"])
    variable_cost_per_order = constant(
        "variable_cost_per_order",
        p["variable_cost_per_order"],
    )
    fixed_cost = constant("fixed_cost", p["fixed_cost"])
    marketing_cost_per_unit = constant(
        "marketing_cost_per_unit",
        p["marketing_cost_per_unit"],
    )
    capacity_cost_per_extra_unit = constant(
        "capacity_cost_per_extra_unit",
        p["capacity_cost_per_extra_unit"],
    )
    collection_delay = constant("collection_delay", p["collection_delay"])
    minimum_fraction = constant(
        "minimum_capacity_fraction",
        p["minimum_capacity_fraction"],
    )

    nominal_capacity = model.converter("nominal_capacity")
    if capacity_mode == "transient":
        nominal_capacity.equation = sd.If(
            sd.time() >= stress_start_c,
            sd.If(
                sd.time() < stress_end_c,
                stress_capacity_c,
                base_nominal_capacity,
            ),
            base_nominal_capacity,
        )
    else:
        nominal_capacity.equation = base_nominal_capacity

    market_shock = model.converter("market_shock")
    market_shock.equation = sd.If(
        sd.time() >= market_shock_start,
        market_shock_orders,
        0.0,
    )

    customer_acquisition = model.flow("customer_acquisition")
    customer_acquisition.equation = (
        acquisition_per_marketing_unit * marketing_intensity
    )

    incoming_orders = model.converter("incoming_orders")
    incoming_orders.equation = customer_base * base_order_rate + market_shock

    effective_capacity = model.converter("effective_capacity")

    fulfilled = model.flow("fulfilled")
    total_demand_to_serve = backlog + incoming_orders
    fulfilled.equation = sd.If(
        total_demand_to_serve < effective_capacity,
        total_demand_to_serve,
        effective_capacity,
    )

    utilization = model.converter("utilization")
    utilization.equation = fulfilled / effective_capacity

    hidden_signal = model.converter("hidden_signal")

    # Driver verdadero target-free:
    # presión de demanda relativa a capacidad nominal.
    demand_pressure = incoming_orders / nominal_capacity

    hidden_signal.equation = (
        demand_pressure - 0.75
    ) / 0.25

    hidden_excess = model.converter("hidden_excess")
    hidden_excess.equation = sd.If(
        hidden_signal > float(truth["threshold"]),
        hidden_signal - float(truth["threshold"]),
        0.0,
    )

    primitive_impact = model.converter("primitive_impact")

    if true_primitive == "accumulation":
        hidden_in = model.flow("hidden_in")
        hidden_out = model.flow("hidden_out")

        hidden_in.equation = hidden_excess * float(truth["build_rate"])
        hidden_out.equation = sd.If(
            hidden_state > float(truth["recovery_rate"]),
            float(truth["recovery_rate"]),
            hidden_state,
        )
        hidden_state.equation = hidden_in - hidden_out
        primitive_impact.equation = hidden_state * float(truth["degradation"])

    elif true_primitive == "first_order_relaxation":
        hidden_in = model.flow("hidden_in")
        hidden_out = model.flow("hidden_out")

        hidden_in.equation = hidden_excess * float(truth["adjustment_rate"])
        hidden_out.equation = hidden_state * float(truth["adjustment_rate"])
        hidden_state.equation = hidden_in - hidden_out
        primitive_impact.equation = hidden_state * float(truth["degradation"])

    elif true_primitive == "self_reinforcing":
        drive_rate = float(truth["drive_rate"])
        growth_rate = float(truth["growth_rate"])
        saturation_level = float(
            truth["saturation_level"]
        )

        # Feedback positivo genuino y no lineal.
        # En L=0 no crece sin estímulo; una vez activado,
        # el estado se auto-refuerza hasta saturar.
        hidden_state.equation = (
            hidden_excess * drive_rate
            + growth_rate
            * hidden_state
            * (
                1.0
                - hidden_state
                / saturation_level
            )
        )

        primitive_impact.equation = (
            hidden_state
            * float(truth["degradation"])
        )

    elif true_primitive == "pipeline_delay":
        hidden_state.equation = 0.0
        delayed_excess = sd.delay(
            model,
            hidden_excess,
            float(truth["delay_time"]),
            0.0,
        )
        primitive_impact.equation = delayed_excess * float(truth["degradation"])

    else:
        raise ValueError(f"WORLD primitive desconocida: {true_primitive}")

    raw_fraction = 1.0 - primitive_impact
    effective_capacity.equation = sd.If(
        raw_fraction > minimum_fraction,
        nominal_capacity * raw_fraction,
        nominal_capacity * minimum_fraction,
    )

    cancellations = model.flow("cancellations")
    cancellations.equation = backlog * cancel_rate

    churn = model.flow("churn")
    churn.equation = base_churn + cancellations * customer_loss_per_cancel

    billed_revenue = model.flow("billed_revenue")
    billed_revenue.equation = fulfilled * price

    collections = model.flow("collections")
    collections.equation = receivables / collection_delay

    extra_capacity_cost = model.converter("extra_capacity_cost")
    extra_capacity_cost.equation = sd.If(
        nominal_capacity > DEFAULT_PARAMS["nominal_capacity"],
        (nominal_capacity - DEFAULT_PARAMS["nominal_capacity"])
        * capacity_cost_per_extra_unit,
        0.0,
    )

    operating_cost = model.flow("operating_cost")
    operating_cost.equation = (
        fixed_cost
        + fulfilled * variable_cost_per_order
        + marketing_intensity * marketing_cost_per_unit
        + extra_capacity_cost
    )

    customer_base.equation = customer_acquisition - churn
    backlog.equation = incoming_orders - fulfilled - cancellations
    receivables.equation = billed_revenue - collections
    cash.equation = collections - operating_cost

    return model

def simulate_world_case(
    true_primitive,
    world_truth,
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    return run_model(
        build_world(
            true_primitive=true_primitive,
            world_truth=world_truth,
            params=params,
            capacity_mode=capacity_mode,
            stress_start=stress_start,
            stress_end=stress_end,
            stress_capacity=stress_capacity,
        ),
        WORLD_EQUATIONS,
        manager_name=f"world_{true_primitive}",
    )


# ---- C0.0 original notebook code cell 9 ----
def build_agent_model(
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    p = DEFAULT_PARAMS.copy()
    if params:
        p.update(params)

    model = Model(
        starttime=0.0,
        stoptime=float(p["months"]),
        dt=1.0,
        name="cei_sd5g_agent",
    )

    customer_base = model.stock("customer_base")
    backlog = model.stock("backlog")
    receivables = model.stock("receivables")
    cash = model.stock("cash")

    customer_base.initial_value = 1000.0
    backlog.initial_value = 0.0
    receivables.initial_value = 0.0
    cash.initial_value = 20000.0

    def constant(name, value):
        c = model.constant(name)
        c.equation = float(value)
        return c

    base_order_rate = constant("base_order_rate", p["base_order_rate"])
    market_shock_start = constant("market_shock_start", p["market_shock_start"])
    market_shock_orders = constant("market_shock_orders", p["market_shock_orders"])
    marketing_intensity = constant("marketing_intensity", p["marketing_intensity"])
    acquisition_per_marketing_unit = constant(
        "acquisition_per_marketing_unit",
        p["acquisition_per_marketing_unit"],
    )
    base_nominal_capacity = constant(
        "base_nominal_capacity",
        p["nominal_capacity"],
    )
    stress_start_c = constant("stress_start", stress_start)
    stress_end_c = constant("stress_end", stress_end)
    stress_capacity_c = constant("stress_capacity", stress_capacity)

    cancel_rate = constant("cancel_rate", p["cancel_rate"])
    base_churn = constant("base_churn", p["base_churn"])
    customer_loss_per_cancel = constant(
        "customer_loss_per_cancel",
        p["customer_loss_per_cancel"],
    )
    price = constant("price", p["price"])
    variable_cost_per_order = constant(
        "variable_cost_per_order",
        p["variable_cost_per_order"],
    )
    fixed_cost = constant("fixed_cost", p["fixed_cost"])
    marketing_cost_per_unit = constant(
        "marketing_cost_per_unit",
        p["marketing_cost_per_unit"],
    )
    capacity_cost_per_extra_unit = constant(
        "capacity_cost_per_extra_unit",
        p["capacity_cost_per_extra_unit"],
    )
    collection_delay = constant("collection_delay", p["collection_delay"])

    nominal_capacity = model.converter("nominal_capacity")
    if capacity_mode == "transient":
        nominal_capacity.equation = sd.If(
            sd.time() >= stress_start_c,
            sd.If(
                sd.time() < stress_end_c,
                stress_capacity_c,
                base_nominal_capacity,
            ),
            base_nominal_capacity,
        )
    else:
        nominal_capacity.equation = base_nominal_capacity

    market_shock = model.converter("market_shock")
    market_shock.equation = sd.If(
        sd.time() >= market_shock_start,
        market_shock_orders,
        0.0,
    )

    customer_acquisition = model.flow("customer_acquisition")
    customer_acquisition.equation = (
        acquisition_per_marketing_unit * marketing_intensity
    )

    incoming_orders = model.converter("incoming_orders")
    incoming_orders.equation = customer_base * base_order_rate + market_shock

    effective_capacity = model.converter("effective_capacity")
    effective_capacity.equation = nominal_capacity

    fulfilled = model.flow("fulfilled")
    total_demand_to_serve = backlog + incoming_orders
    fulfilled.equation = sd.If(
        total_demand_to_serve < effective_capacity,
        total_demand_to_serve,
        effective_capacity,
    )

    cancellations = model.flow("cancellations")
    cancellations.equation = backlog * cancel_rate

    churn = model.flow("churn")
    churn.equation = base_churn + cancellations * customer_loss_per_cancel

    billed_revenue = model.flow("billed_revenue")
    billed_revenue.equation = fulfilled * price

    collections = model.flow("collections")
    collections.equation = receivables / collection_delay

    extra_capacity_cost = model.converter("extra_capacity_cost")
    extra_capacity_cost.equation = sd.If(
        nominal_capacity > DEFAULT_PARAMS["nominal_capacity"],
        (nominal_capacity - DEFAULT_PARAMS["nominal_capacity"])
        * capacity_cost_per_extra_unit,
        0.0,
    )

    operating_cost = model.flow("operating_cost")
    operating_cost.equation = (
        fixed_cost
        + fulfilled * variable_cost_per_order
        + marketing_intensity * marketing_cost_per_unit
        + extra_capacity_cost
    )

    customer_base.equation = customer_acquisition - churn
    backlog.equation = incoming_orders - fulfilled - cancellations
    receivables.equation = billed_revenue - collections
    cash.equation = collections - operating_cost

    return model

def simulate_agent(
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    return run_model(
        build_agent_model(
            params=params,
            capacity_mode=capacity_mode,
            stress_start=stress_start,
            stress_end=stress_end,
            stress_capacity=stress_capacity,
        ),
        OBSERVED_COLUMNS,
        manager_name="agent",
    )

PRIMARY_VARS = [
    "market_shock",
    "incoming_orders",
    "nominal_capacity",
    "customer_acquisition",
]

RATIO_PAIRS = [
    # Todas son razones entre tasas de órdenes/capacidad.
    # Ningún denominador es cero en el régimen base.
    ("incoming_orders", "nominal_capacity"),
    ("market_shock", "nominal_capacity"),
    ("market_shock", "incoming_orders"),
]

# Un solo sentido por par: no A-B y B-A simultáneamente.
DIFF_PAIRS = [
    # Sólo diferencias con unidades compatibles.
    ("incoming_orders", "nominal_capacity"),
    ("market_shock", "nominal_capacity"),
    ("incoming_orders", "market_shock"),
]

LAG_DELTA_VARS = PRIMARY_VARS.copy()

def expression_id(e):
    k = e["kind"]
    if k == "raw":
        return f"raw::{e['x']}"
    if k == "ratio":
        return f"ratio::{e['x']}/{e['y']}"
    if k == "diff":
        return f"diff::{e['x']}-{e['y']}"
    if k == "lag1":
        return f"lag1::{e['x']}"
    if k == "delta1":
        return f"delta1::{e['x']}"
    raise ValueError(k)

EXPRESSIONS = []

for x in PRIMARY_VARS:
    EXPRESSIONS.append({
        "kind": "raw",
        "x": x,
    })

for x, y in RATIO_PAIRS:
    EXPRESSIONS.append({
        "kind": "ratio",
        "x": x,
        "y": y,
    })

for x, y in DIFF_PAIRS:
    EXPRESSIONS.append({
        "kind": "diff",
        "x": x,
        "y": y,
    })

for x in LAG_DELTA_VARS:
    EXPRESSIONS.append({
        "kind": "lag1",
        "x": x,
    })
    EXPRESSIONS.append({
        "kind": "delta1",
        "x": x,
    })

EXPRESSIONS = list({
    expression_id(e): e
    for e in EXPRESSIONS
}.values())

def expression_variables(e):
    return {
        v
        for v in [
            e.get("x"),
            e.get("y"),
        ]
        if v is not None
    }

LEAKAGE_AUDIT = pd.DataFrame([
    {
        "feature_id": expression_id(e),
        "variables": ", ".join(
            sorted(expression_variables(e))
        ),
        "blocked_intersection": ", ".join(
            sorted(
                expression_variables(e)
                & BLOCKED_DRIVER_VARS
            )
        ),
        "is_primary_safe":
            len(
                expression_variables(e)
                & BLOCKED_DRIVER_VARS
            ) == 0,
    }
    for e in EXPRESSIONS
])

assert bool(
    LEAKAGE_AUDIT[
        "is_primary_safe"
    ].all()
), "La gramática primaria contiene leakage bloqueado."

assert (
    TRUE_DERIVED_ID
    in {expression_id(e) for e in EXPRESSIONS}
)

print(
    "Expresiones canonicalizadas:",
    len(EXPRESSIONS),
)
print(
    "Relación oracle target-free en gramática?:",
    TRUE_DERIVED_ID
    in {expression_id(e) for e in EXPRESSIONS},
)
display(LEAKAGE_AUDIT)



# ---- C0.0 original notebook code cell 10 ----
def eval_expression_df(e, df):
    kind = e["kind"]

    if kind == "raw":
        return df[e["x"]].astype(float)

    if kind == "ratio":
        den = df[e["y"]].astype(float).replace(0.0, np.nan)
        return (
            df[e["x"]].astype(float) / den
        ).replace([np.inf, -np.inf], np.nan)

    if kind == "diff":
        return df[e["x"]].astype(float) - df[e["y"]].astype(float)

    if kind == "lag1":
        s = df[e["x"]].astype(float)
        return s.shift(1).fillna(float(s.iloc[0]))

    if kind == "delta1":
        s = df[e["x"]].astype(float)
        return (s - s.shift(1)).fillna(0.0)

    raise ValueError(kind)

def safe_corr(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 3 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])

def variable_scale(series):
    s = series.astype(float)
    span = float(s.max() - s.min())
    return max(span, float(s.abs().mean()) * 0.10, 1.0)

SCORE_VARS = [
    "effective_capacity",
    "fulfilled",
    "backlog",
    "cash",
    "customer_base",
]

def score_against(obs_df, pred_df, mask=None, scales=None):
    if mask is None:
        mask = pd.Series(True, index=obs_df.index)

    if scales is None:
        scales = {
            v: variable_scale(obs_df[v])
            for v in SCORE_VARS
        }

    parts = {}
    for v in SCORE_VARS:
        obs = obs_df.loc[mask, v].astype(float).to_numpy()
        est = pred_df.loc[mask, v].astype(float).to_numpy()
        rmse = float(np.sqrt(np.mean((obs - est) ** 2)))
        parts[v] = rmse / scales[v]

    return float(np.mean(list(parts.values()))), parts

def parameter_combinations(space):
    keys = list(space.keys())
    for vals in itertools.product(*(space[k] for k in keys)):
        yield dict(zip(keys, vals))

PRIMITIVE_GRIDS = {
    "accumulation": {
        "threshold": [0.10, 0.30, 0.50],
        "build_rate": [5.0, 7.5],
        "recovery_rate": [1.5, 3.5, 5.5],
        "degradation": [0.015, 0.030],
    },
    "first_order_relaxation": {
        "threshold": [0.10, 0.30, 0.50],
        "adjustment_rate": [0.25, 0.50, 0.75],
        "degradation": [0.25, 0.50],
    },
    "self_reinforcing": {
        "threshold": [0.10, 0.30, 0.50],
        "drive_rate": [2.0, 4.0],
        "growth_rate": [0.10, 0.25],
        "saturation_level": [1.5, 3.5],
        "degradation": [0.020, 0.040],
    },
    "pipeline_delay": {
        "threshold": [0.10, 0.30, 0.50],
        "delay_time": [1.0, 2.0, 3.0],
        "degradation": [0.25, 0.50],
    },
}

CLOCK_GRID = {
    "threshold": [0.0],
    "build_rate": [1.5, 3.5, 5.5],
    "recovery_rate": [0.0, 1.5, 3.5],
    "degradation": [0.015, 0.035],
}

def hypothesis_id(primitive, feature_id):
    return f"{primitive}::{feature_id}"

# Auditoría de parametrización y muestreo.
OUT_OF_GRID_ROWS = []

for case_id, spec in WORLD_CASES.items():
    primitive = spec["primitive"]
    truth = spec["truth"]
    grid = PRIMITIVE_GRIDS[primitive]

    for parameter, value in truth.items():
        candidate_values = grid[parameter]

        exact_match = any(
            abs(float(value) - float(v)) < 1e-12
            for v in candidate_values
        )

        OUT_OF_GRID_ROWS.append({
            "case_id": case_id,
            "primitive": primitive,
            "parameter": parameter,
            "world_value": value,
            "candidate_grid": str(candidate_values),
            "exact_match_in_grid": exact_match,
        })

OUT_OF_GRID_AUDIT = pd.DataFrame(
    OUT_OF_GRID_ROWS
)

CLASS_COUNTS = (
    pd.Series([
        spec["primitive"]
        for spec in WORLD_CASES.values()
    ])
    .value_counts()
    .sort_index()
)

assert len(WORLD_CASES) == 40
assert bool((CLASS_COUNTS == 10).all())
assert not OUT_OF_GRID_AUDIT[
    "exact_match_in_grid"
].any()

# La clase self_reinforcing es genuinamente no lineal:
# no existe feedback negativo disfrazado de relajación.
STRUCTURAL_CLASS_AUDIT = pd.DataFrame([
    {
        "primitive": "first_order_relaxation",
        "linear_first_order": True,
        "positive_self_feedback": False,
        "nonlinear_saturation": False,
    },
    {
        "primitive": "self_reinforcing",
        "linear_first_order": False,
        "positive_self_feedback": True,
        "nonlinear_saturation": True,
    },
])

print("Casos por clase:")
display(CLASS_COUNTS)

print("Auditoría out-of-grid:")
display(OUT_OF_GRID_AUDIT.head(20))

print("Auditoría estructural:")
display(STRUCTURAL_CLASS_AUDIT)



# ---- C0.0 original notebook code cell 12 ----
def build_repair_model(
    primitive,
    feature_id,
    feature_meta,
    repair=None,
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    p = DEFAULT_PARAMS.copy()
    if params:
        p.update(params)

    r = {
        "threshold": 0.25,
        "build_rate": 5.0,
        "recovery_rate": 3.5,
        "adjustment_rate": 0.50,
        "drive_rate": 2.5,
        "growth_rate": 0.15,
        "saturation_level": 2.5,
        "delay_time": 2.0,
        "degradation": 0.03,
        "minimum_fraction": 0.40,
        "baseline": 0.0,
        "excursion": 1.0,
        "orientation": 1.0,
        "initial_raw": 0.0,
    }
    if repair:
        r.update(repair)

    model = Model(
        starttime=0.0,
        stoptime=float(p["months"]),
        dt=1.0,
        name="cei_sd5g_repair",
    )

    customer_base = model.stock("customer_base")
    backlog = model.stock("backlog")
    receivables = model.stock("receivables")
    cash = model.stock("cash")
    latent_state = model.stock("latent_state")

    customer_base.initial_value = 1000.0
    backlog.initial_value = 0.0
    receivables.initial_value = 0.0
    cash.initial_value = 20000.0
    latent_state.initial_value = 0.0

    def constant(name, value):
        c = model.constant(name)
        c.equation = float(value)
        return c

    base_order_rate = constant("base_order_rate", p["base_order_rate"])
    market_shock_start = constant("market_shock_start", p["market_shock_start"])
    market_shock_orders = constant("market_shock_orders", p["market_shock_orders"])
    marketing_intensity = constant("marketing_intensity", p["marketing_intensity"])
    acquisition_per_marketing_unit = constant(
        "acquisition_per_marketing_unit",
        p["acquisition_per_marketing_unit"],
    )
    base_nominal_capacity = constant(
        "base_nominal_capacity",
        p["nominal_capacity"],
    )

    stress_start_c = constant("stress_start", stress_start)
    stress_end_c = constant("stress_end", stress_end)
    stress_capacity_c = constant("stress_capacity", stress_capacity)

    cancel_rate = constant("cancel_rate", p["cancel_rate"])
    base_churn = constant("base_churn", p["base_churn"])
    customer_loss_per_cancel = constant(
        "customer_loss_per_cancel",
        p["customer_loss_per_cancel"],
    )
    price = constant("price", p["price"])
    variable_cost_per_order = constant(
        "variable_cost_per_order",
        p["variable_cost_per_order"],
    )
    fixed_cost = constant("fixed_cost", p["fixed_cost"])
    marketing_cost_per_unit = constant(
        "marketing_cost_per_unit",
        p["marketing_cost_per_unit"],
    )
    capacity_cost_per_extra_unit = constant(
        "capacity_cost_per_extra_unit",
        p["capacity_cost_per_extra_unit"],
    )
    collection_delay = constant("collection_delay", p["collection_delay"])

    threshold = constant("repair_threshold", r["threshold"])
    degradation = constant("repair_degradation", r["degradation"])
    minimum_fraction = constant(
        "repair_minimum_fraction",
        r["minimum_fraction"],
    )
    feature_baseline = constant("feature_baseline", r["baseline"])
    feature_excursion = constant(
        "feature_excursion",
        max(float(r["excursion"]), 1e-6),
    )
    feature_orientation = constant(
        "feature_orientation",
        r["orientation"],
    )

    nominal_capacity = model.converter("nominal_capacity")
    if capacity_mode == "transient":
        nominal_capacity.equation = sd.If(
            sd.time() >= stress_start_c,
            sd.If(
                sd.time() < stress_end_c,
                stress_capacity_c,
                base_nominal_capacity,
            ),
            base_nominal_capacity,
        )
    else:
        nominal_capacity.equation = base_nominal_capacity

    market_shock = model.converter("market_shock")
    market_shock.equation = sd.If(
        sd.time() >= market_shock_start,
        market_shock_orders,
        0.0,
    )

    customer_acquisition = model.flow("customer_acquisition")
    customer_acquisition.equation = (
        acquisition_per_marketing_unit * marketing_intensity
    )

    incoming_orders = model.converter("incoming_orders")
    incoming_orders.equation = customer_base * base_order_rate + market_shock

    effective_capacity = model.converter("effective_capacity")

    fulfilled = model.flow("fulfilled")
    total_demand_to_serve = backlog + incoming_orders
    fulfilled.equation = sd.If(
        total_demand_to_serve < effective_capacity,
        total_demand_to_serve,
        effective_capacity,
    )

    cancellations = model.flow("cancellations")
    cancellations.equation = backlog * cancel_rate

    churn = model.flow("churn")
    churn.equation = base_churn + cancellations * customer_loss_per_cancel

    billed_revenue = model.flow("billed_revenue")
    billed_revenue.equation = fulfilled * price

    collections = model.flow("collections")
    collections.equation = receivables / collection_delay

    extra_capacity_cost = model.converter("extra_capacity_cost")
    extra_capacity_cost.equation = sd.If(
        nominal_capacity > DEFAULT_PARAMS["nominal_capacity"],
        (nominal_capacity - DEFAULT_PARAMS["nominal_capacity"])
        * capacity_cost_per_extra_unit,
        0.0,
    )

    operating_cost = model.flow("operating_cost")
    operating_cost.equation = (
        fixed_cost
        + fulfilled * variable_cost_per_order
        + marketing_intensity * marketing_cost_per_unit
        + extra_capacity_cost
    )

    element_map = {
        "customer_base": customer_base,
        "customer_acquisition": customer_acquisition,
        "market_shock": market_shock,
        "incoming_orders": incoming_orders,
        "nominal_capacity": nominal_capacity,
        "effective_capacity": effective_capacity,
        "fulfilled": fulfilled,
        "backlog": backlog,
        "cancellations": cancellations,
        "churn": churn,
        "billed_revenue": billed_revenue,
        "receivables": receivables,
        "collections": collections,
        "operating_cost": operating_cost,
        "cash": cash,
        "marketing_intensity": marketing_intensity,
    }

    derived_signal = model.converter("derived_signal")

    if feature_id == "__clock__":
        derived_signal.equation = sd.If(
            sd.time() >= market_shock_start,
            1.0,
            0.0,
        )
    else:
        meta = feature_meta[feature_id]
        raw_driver = model.converter("raw_driver")

        if meta["kind"] == "raw":
            raw_driver.equation = element_map[meta["x"]]

        elif meta["kind"] == "ratio":
            raw_driver.equation = (
                element_map[meta["x"]] / element_map[meta["y"]]
            )

        elif meta["kind"] == "diff":
            raw_driver.equation = (
                element_map[meta["x"]] - element_map[meta["y"]]
            )

        elif meta["kind"] == "lag1":
            raw_driver.equation = sd.delay(
                model,
                element_map[meta["x"]],
                1.0,
                float(r["initial_raw"]),
            )

        elif meta["kind"] == "delta1":
            delayed = sd.delay(
                model,
                element_map[meta["x"]],
                1.0,
                float(r["initial_raw"]),
            )
            raw_driver.equation = element_map[meta["x"]] - delayed

        else:
            raise ValueError(meta["kind"])

        derived_signal.equation = (
            feature_orientation
            * (raw_driver - feature_baseline)
            / feature_excursion
        )

    stress_excess = model.converter("stress_excess")
    stress_excess.equation = sd.If(
        derived_signal > threshold,
        derived_signal - threshold,
        0.0,
    )

    impact = model.converter("primitive_impact")

    if primitive == "accumulation":
        build_rate = constant("build_rate", r["build_rate"])
        recovery_rate = constant("recovery_rate", r["recovery_rate"])

        primitive_in = model.flow("primitive_in")
        primitive_out = model.flow("primitive_out")

        primitive_in.equation = stress_excess * build_rate
        primitive_out.equation = sd.If(
            latent_state > recovery_rate,
            recovery_rate,
            latent_state,
        )
        latent_state.equation = primitive_in - primitive_out
        impact.equation = latent_state * degradation

    elif primitive == "first_order_relaxation":
        adjustment_rate = constant(
            "adjustment_rate",
            r["adjustment_rate"],
        )

        primitive_in = model.flow("primitive_in")
        primitive_out = model.flow("primitive_out")

        primitive_in.equation = stress_excess * adjustment_rate
        primitive_out.equation = latent_state * adjustment_rate
        latent_state.equation = primitive_in - primitive_out
        impact.equation = latent_state * degradation

    elif primitive == "self_reinforcing":
        drive_rate = constant(
            "drive_rate",
            r["drive_rate"],
        )
        growth_rate = constant(
            "growth_rate",
            r["growth_rate"],
        )
        saturation_level = constant(
            "saturation_level",
            r["saturation_level"],
        )

        latent_state.equation = (
            stress_excess * drive_rate
            + growth_rate
            * latent_state
            * (
                1.0
                - latent_state
                / saturation_level
            )
        )

        impact.equation = (
            latent_state * degradation
        )

    elif primitive == "pipeline_delay":
        delay_time = float(r["delay_time"])
        latent_state.equation = 0.0

        delayed_excess = sd.delay(
            model,
            stress_excess,
            delay_time,
            0.0,
        )
        impact.equation = delayed_excess * degradation

    else:
        raise ValueError(f"Primitiva desconocida: {primitive}")

    raw_fraction = 1.0 - impact
    effective_capacity.equation = sd.If(
        raw_fraction > minimum_fraction,
        nominal_capacity * raw_fraction,
        nominal_capacity * minimum_fraction,
    )

    customer_base.equation = customer_acquisition - churn
    backlog.equation = incoming_orders - fulfilled - cancellations
    receivables.equation = billed_revenue - collections
    cash.equation = collections - operating_cost

    return model

def simulate_repair(
    primitive,
    feature_id,
    feature_meta,
    repair=None,
    params=None,
    capacity_mode="constant",
    stress_start=8.0,
    stress_end=14.0,
    stress_capacity=80.0,
):
    return run_model(
        build_repair_model(
            primitive=primitive,
            feature_id=feature_id,
            feature_meta=feature_meta,
            repair=repair,
            params=params,
            capacity_mode=capacity_mode,
            stress_start=stress_start,
            stress_end=stress_end,
            stress_capacity=stress_capacity,
        ),
        OBSERVED_COLUMNS,
        manager_name="repair",
    )


# ---- C0.0 original notebook code cell 14 ----
MIN_PROBES_BEFORE_ACCEPT = 2
MIN_INFORMATIVE_PROBES_BEFORE_ACCEPT = 2
MIN_CLASS_DISAGREEMENT = 0.02
MAX_STANDARD_PROBES = 3
TOTAL_PROBE_BUDGET = 5
MAX_PROBES = MAX_STANDARD_PROBES
MAX_DIRECTED_PROBES = TOTAL_PROBE_BUDGET - MAX_STANDARD_PROBES
MIN_ADVANTAGE = 0.15
MAX_WORST_RELATIVE = 1.10
MIN_REPAIR_SEPARATION = 0.10
COMMITTEE_N = 10
DIAG_VARS = ["effective_capacity", "backlog", "cash"]

def run_sd5g_case(case_id, true_primitive, world_truth):
    print("\n" + "=" * 80)
    print(case_id, "| WORLD oculto =", true_primitive)
    print("=" * 80)

    WORLD_BASE, world_engine = simulate_world_case(
        true_primitive,
        world_truth=world_truth,
    )
    CEI_BASE = WORLD_BASE[OBSERVED_COLUMNS].copy()

    AGENT_BASE, agent_engine = simulate_agent()

    capacity_ratio_obs = (
        CEI_BASE["effective_capacity"]
        / CEI_BASE["nominal_capacity"]
    )
    capacity_ratio_agent = (
        AGENT_BASE["effective_capacity"]
        / AGENT_BASE["nominal_capacity"]
    )

    post = CEI_BASE.index >= DEFAULT_PARAMS["market_shock_start"]
    invariant_break = float(
        np.max(
            np.abs(
                capacity_ratio_obs[post]
                - capacity_ratio_agent[post]
            )
        )
    )

    shock_t = DEFAULT_PARAMS["market_shock_start"]
    pre_mask = CEI_BASE.index < shock_t
    proposal_mask = CEI_BASE.index <= 15.0

    capacity_gap = (
        (
            CEI_BASE["nominal_capacity"]
            - CEI_BASE["effective_capacity"]
        )
        / CEI_BASE["nominal_capacity"].clip(lower=1e-6)
    )

    def feature_geometry(raw, orientation):
        pre = raw[pre_mask].dropna().astype(float)
        baseline = float(np.median(pre)) if len(pre) else 0.0

        proposal = raw[proposal_mask].dropna().astype(float)
        oriented = orientation * (proposal - baseline)

        positive = oriented[oriented > 0.0]
        excursion = (
            float(positive.max())
            if len(positive)
            else 0.0
        )

        if excursion < 1e-8:
            excursion = (
                float(np.max(np.abs(proposal - baseline)))
                if len(proposal)
                else 0.0
            )

        return baseline, max(excursion, 1e-6)

    feature_rows = []
    feature_meta = {}

    for e in EXPRESSIONS:
        fid = expression_id(e)
        raw = eval_expression_df(e, CEI_BASE)

        valid = (
            proposal_mask
            & raw.notna()
            & capacity_gap.notna()
        )

        if (
            valid.sum() < 5
            or float(raw[valid].std()) < 1e-10
        ):
            continue

        corr_signed = safe_corr(
            raw[valid],
            capacity_gap[valid],
        )
        orientation = 1.0 if corr_signed >= 0 else -1.0

        baseline, excursion = feature_geometry(
            raw,
            orientation,
        )

        z = orientation * (raw - baseline) / excursion
        corr = abs(
            safe_corr(
                z[valid],
                capacity_gap[valid],
            )
        )

        early = (
            (CEI_BASE.index >= shock_t)
            & (CEI_BASE.index <= shock_t + 2)
        )

        pre_mean = (
            float(z[pre_mask].mean())
            if pre_mask.any()
            else 0.0
        )
        post_mean = float(z[early].mean())
        onset_shift = abs(post_mean - pre_mean)

        complexity = {
            "raw": 1,
            "lag1": 2,
            "delta1": 2,
            "diff": 2,
            "ratio": 2,
        }[e["kind"]]

        proposal_score = (
            corr
            + 0.15 * min(onset_shift, 2.0)
            - 0.01 * (complexity - 1)
        )

        meta = {
            **e,
            "feature_id": fid,
            "baseline": baseline,
            "excursion": excursion,
            "orientation": orientation,
            "initial_raw": float(raw.dropna().iloc[0]),
            "corr_with_gap": corr,
            "onset_shift": onset_shift,
            "proposal_score": proposal_score,
        }

        feature_meta[fid] = meta
        feature_rows.append(meta)

    feature_rank = (
        pd.DataFrame(feature_rows)
        .sort_values("proposal_score", ascending=False)
        .reset_index(drop=True)
    )

    generated_features = feature_rank["feature_id"].tolist()

    cal_mask = (
        (CEI_BASE.index >= shock_t)
        & (CEI_BASE.index <= 15.0)
    )
    hold_mask = CEI_BASE.index >= 16.0

    base_scales = {
        v: variable_scale(CEI_BASE[v])
        for v in SCORE_VARS
    }

    agent_cal, _ = score_against(
        CEI_BASE,
        AGENT_BASE,
        cal_mask,
        base_scales,
    )
    agent_hold, _ = score_against(
        CEI_BASE,
        AGENT_BASE,
        hold_mask,
        base_scales,
    )

    search_rows = []
    best_generated = {}
    hypothesis_meta = {}

    for primitive in PRIMITIVES:
        grid = PRIMITIVE_GRIDS[primitive]

        for feature_id in generated_features:
            m = feature_meta[feature_id]
            h_id = hypothesis_id(primitive, feature_id)

            feature_params = {
                "baseline": m["baseline"],
                "excursion": m["excursion"],
                "orientation": m["orientation"],
                "initial_raw": m["initial_raw"],
            }

            best = None

            for p in parameter_combinations(grid):
                repair = {**p, **feature_params}

                pred, _ = simulate_repair(
                    primitive,
                    feature_id,
                    feature_meta,
                    repair=repair,
                )

                cal_score, _ = score_against(
                    CEI_BASE,
                    pred,
                    cal_mask,
                    base_scales,
                )

                search_rows.append({
                    "hypothesis_id": h_id,
                    "primitive": primitive,
                    "feature_id": feature_id,
                    **p,
                    "cal_score": cal_score,
                })

                if (
                    best is None
                    or cal_score < best["cal_score"]
                ):
                    best = {
                        "hypothesis_id": h_id,
                        "primitive": primitive,
                        "feature_id": feature_id,
                        "repair": repair.copy(),
                        "cal_score": cal_score,
                        "pred_base": pred,
                    }

            hold_score, hold_parts = score_against(
                CEI_BASE,
                best["pred_base"],
                hold_mask,
                base_scales,
            )

            best["hold_score"] = hold_score
            best["hold_parts"] = hold_parts
            best_generated[h_id] = best
            hypothesis_meta[h_id] = {
                "primitive": primitive,
                "feature_id": feature_id,
            }

    clock_h_id = hypothesis_id(
        "accumulation",
        "__clock__",
    )
    clock_feature_params = {
        "baseline": 0.0,
        "excursion": 1.0,
        "orientation": 1.0,
        "initial_raw": 0.0,
    }

    clock_best = None

    for p in parameter_combinations(CLOCK_GRID):
        repair = {**p, **clock_feature_params}

        pred, _ = simulate_repair(
            "accumulation",
            "__clock__",
            feature_meta,
            repair=repair,
        )

        cal_score, _ = score_against(
            CEI_BASE,
            pred,
            cal_mask,
            base_scales,
        )

        search_rows.append({
            "hypothesis_id": clock_h_id,
            "primitive": "accumulation",
            "feature_id": "__clock__",
            **p,
            "cal_score": cal_score,
        })

        if (
            clock_best is None
            or cal_score < clock_best["cal_score"]
        ):
            clock_best = {
                "hypothesis_id": clock_h_id,
                "primitive": "accumulation",
                "feature_id": "__clock__",
                "repair": repair.copy(),
                "cal_score": cal_score,
                "pred_base": pred,
            }

    clock_hold, clock_parts = score_against(
        CEI_BASE,
        clock_best["pred_base"],
        hold_mask,
        base_scales,
    )
    clock_best["hold_score"] = clock_hold
    clock_best["hold_parts"] = clock_parts

    best_generated[clock_h_id] = clock_best
    hypothesis_meta[clock_h_id] = {
        "primitive": "accumulation",
        "feature_id": "__clock__",
    }

    structural_search = pd.DataFrame(search_rows)

    generated_summary = pd.DataFrame(
        [{
            "hypothesis_id": "__agent_original__",
            "primitive": "__agent__",
            "feature_id": "__agent_original__",
            "cal_score": agent_cal,
            "hold_score": agent_hold,
        }]
        + [
            {
                "hypothesis_id": h,
                "primitive": b["primitive"],
                "feature_id": b["feature_id"],
                "cal_score": b["cal_score"],
                "hold_score": b["hold_score"],
            }
            for h, b in best_generated.items()
        ]
    ).sort_values("hold_score").reset_index(drop=True)

    plausible_repairs = (
        generated_summary[
            (
                generated_summary["hypothesis_id"]
                != "__agent_original__"
            )
            & (
                generated_summary["hold_score"]
                < agent_hold
            )
        ]
        .sort_values("hold_score")
        ["hypothesis_id"]
        .tolist()
    )

    true_hypothesis_id = hypothesis_id(
        true_primitive,
        TRUE_DERIVED_ID,
    )

    def simulate_probe_for_hypothesis(h_id, cfg):
        b = best_generated[h_id]
        return simulate_repair(
            b["primitive"],
            b["feature_id"],
            feature_meta,
            repair=b["repair"],
            params=cfg.get("params"),
            capacity_mode=cfg.get("capacity_mode", "constant"),
            stress_start=cfg.get("stress_start", 8.0),
            stress_end=cfg.get("stress_end", 14.0),
            stress_capacity=cfg.get("stress_capacity", 80.0),
        )[0]

    def pairwise_prediction_distance(a, b):
        vals = []
        for v in DIAG_VARS:
            scale = max(
                variable_scale(a[v]),
                variable_scale(b[v]),
                1.0,
            )
            x = a[v].astype(float).to_numpy()
            y = b[v].astype(float).to_numpy()
            vals.append(
                float(np.sqrt(np.mean((x - y) ** 2)))
                / scale
            )
        return float(np.mean(vals))

    ALL_PROBE_LIBRARY = {
        **PROBE_LIBRARY,
        **DIRECTED_PROBE_LIBRARY,
    }

    probe_prediction_cache = {}

    for probe_name, cfg in ALL_PROBE_LIBRARY.items():
        for h_id in plausible_repairs:
            probe_prediction_cache[
                (probe_name, h_id)
            ] = simulate_probe_for_hypothesis(
                h_id,
                cfg,
            )

    agent_probe_prediction_cache = {}

    for probe_name, cfg in ALL_PROBE_LIBRARY.items():
        pred, _ = simulate_agent(
            params=cfg.get("params"),
            capacity_mode=cfg.get("capacity_mode", "constant"),
            stress_start=cfg.get("stress_start", 8.0),
            stress_end=cfg.get("stress_end", 14.0),
            stress_capacity=cfg.get("stress_capacity", 80.0),
        )
        agent_probe_prediction_cache[probe_name] = pred

    def hypothesis_distance(a_id, b_id, probe_names):
        ds = [
            pairwise_prediction_distance(
                probe_prediction_cache[(p, a_id)],
                probe_prediction_cache[(p, b_id)],
            )
            for p in probe_names
        ]
        return float(np.mean(ds)) if ds else 0.0

    def build_diverse_committee(
        active_repairs,
        remaining_probes,
        evidence_df=None,
    ):
        if not active_repairs:
            return []

        n = min(COMMITTEE_N, len(active_repairs))

        if evidence_df is None:
            first = min(
                active_repairs,
                key=lambda h: best_generated[h]["hold_score"],
            )
            score_map = {}
        else:
            score_map = dict(
                zip(
                    evidence_df["hypothesis_id"],
                    evidence_df["mean_multiregime"],
                )
            )
            first = min(
                active_repairs,
                key=lambda h: score_map.get(h, np.inf),
            )

        committee = [first]

        while len(committee) < n:
            remaining = [
                h for h in active_repairs
                if h not in committee
            ]

            if not remaining:
                break

            scored = []

            for cand in remaining:
                min_dist = min(
                    hypothesis_distance(
                        cand,
                        chosen,
                        remaining_probes,
                    )
                    for chosen in committee
                )

                quality = (
                    best_generated[cand]["hold_score"]
                    if evidence_df is None
                    else score_map.get(cand, np.inf)
                )

                scored.append(
                    (min_dist, -quality, cand)
                )

            scored.sort(reverse=True)
            committee.append(scored[0][2])

        return committee

    def design_next_probe(
        active_repairs,
        remaining_probes,
        evidence_df=None,
    ):
        committee = build_diverse_committee(
            active_repairs,
            remaining_probes,
            evidence_df=evidence_df,
        )

        rows = []

        for probe_name in remaining_probes:
            distances = [
                pairwise_prediction_distance(
                    probe_prediction_cache[(probe_name, a)],
                    probe_prediction_cache[(probe_name, b)],
                )
                for a, b in itertools.combinations(
                    committee,
                    2,
                )
            ]

            rows.append({
                "probe": probe_name,
                "mean_pairwise_disagreement": (
                    float(np.mean(distances))
                    if distances
                    else 0.0
                ),
                "max_pairwise_disagreement": (
                    float(np.max(distances))
                    if distances
                    else 0.0
                ),
                "committee_size": len(committee),
            })

        design = (
            pd.DataFrame(rows)
            .sort_values(
                [
                    "mean_pairwise_disagreement",
                    "max_pairwise_disagreement",
                ],
                ascending=False,
            )
            .reset_index(drop=True)
        )

        return committee, design

    def accumulated_evidence(
        selected_probes,
        observations,
    ):
        rows = []
        candidates = [
            "__agent_original__"
        ] + plausible_repairs

        for h_id in candidates:
            row = {
                "hypothesis_id": h_id,
                "primitive": (
                    "__agent__"
                    if h_id == "__agent_original__"
                    else hypothesis_meta[h_id]["primitive"]
                ),
                "feature_id": (
                    "__agent_original__"
                    if h_id == "__agent_original__"
                    else hypothesis_meta[h_id]["feature_id"]
                ),
                "base_holdout": (
                    agent_hold
                    if h_id == "__agent_original__"
                    else best_generated[h_id]["hold_score"]
                ),
            }

            for probe_name in selected_probes:
                obs = observations[probe_name]

                pred = (
                    agent_probe_prediction_cache[probe_name]
                    if h_id == "__agent_original__"
                    else probe_prediction_cache[
                        (probe_name, h_id)
                    ]
                )

                s, _ = score_against(obs, pred)
                row[f"probe::{probe_name}"] = s

            score_cols = ["base_holdout"] + [
                f"probe::{p}"
                for p in selected_probes
            ]

            row["mean_multiregime"] = float(
                np.mean([row[c] for c in score_cols])
            )
            row["worst_regime"] = float(
                np.max([row[c] for c in score_cols])
            )

            rows.append(row)

        return (
            pd.DataFrame(rows)
            .sort_values(
                ["mean_multiregime", "worst_regime"]
            )
            .reset_index(drop=True)
        )

    def adjudicate(
        evidence_df,
        n_probes,
        n_informative_probes,
    ):
        agent_row = evidence_df[
            evidence_df["hypothesis_id"]
            == "__agent_original__"
        ].iloc[0]

        repairs = (
            evidence_df[
                evidence_df["hypothesis_id"]
                != "__agent_original__"
            ]
            .sort_values(
                [
                    "mean_multiregime",
                    "worst_regime",
                ]
            )
            .reset_index(drop=True)
        )

        winner_row = repairs.iloc[0]
        winner = winner_row["hypothesis_id"]
        winner_primitive_local = (
            winner_row["primitive"]
        )
        winner_score = float(
            winner_row["mean_multiregime"]
        )
        winner_worst = float(
            winner_row["worst_regime"]
        )

        global_second_score = (
            float(
                repairs.iloc[1][
                    "mean_multiregime"
                ]
            )
            if len(repairs) > 1
            else np.nan
        )

        other_class = repairs[
            repairs["primitive"]
            != winner_primitive_local
        ].reset_index(drop=True)

        if len(other_class):
            class_second = other_class.iloc[0]
            class_second_score = float(
                class_second[
                    "mean_multiregime"
                ]
            )
            class_second_id = (
                class_second["hypothesis_id"]
            )
            class_second_primitive = (
                class_second["primitive"]
            )
        else:
            class_second_score = np.nan
            class_second_id = None
            class_second_primitive = None

        global_separation = (
            (
                global_second_score
                - winner_score
            )
            / global_second_score
            if (
                np.isfinite(
                    global_second_score
                )
                and global_second_score > 0
            )
            else np.nan
        )

        class_separation = (
            (
                class_second_score
                - winner_score
            )
            / class_second_score
            if (
                np.isfinite(
                    class_second_score
                )
                and class_second_score > 0
            )
            else np.nan
        )

        agent_score = float(
            agent_row["mean_multiregime"]
        )
        agent_worst = float(
            agent_row["worst_regime"]
        )

        advantage = (
            (agent_score - winner_score)
            / agent_score
            if agent_score > 0
            else -np.inf
        )

        if invariant_break <= 0.10:
            verdict = "RETAIN_AGENT"
        elif (
            n_probes >= MIN_PROBES_BEFORE_ACCEPT
            and (
                n_informative_probes
                >= MIN_INFORMATIVE_PROBES_BEFORE_ACCEPT
            )
            and advantage >= MIN_ADVANTAGE
            and (
                winner_worst
                <= agent_worst
                * MAX_WORST_RELATIVE
            )
            and (
                np.isnan(class_separation)
                or class_separation
                >= MIN_REPAIR_SEPARATION
            )
        ):
            verdict = "REPAIR_ACCEPTED"
        else:
            verdict = "UNRESOLVED"

        return {
            "winner": winner,
            "winner_score": winner_score,
            "winner_worst": winner_worst,
            "global_second_score":
                global_second_score,
            "class_second_score":
                class_second_score,
            "class_second_id":
                class_second_id,
            "class_second_primitive":
                class_second_primitive,
            "global_separation":
                global_separation,
            "class_separation":
                class_separation,
            "separation":
                class_separation,
            "agent_score": agent_score,
            "agent_worst": agent_worst,
            "advantage": advantage,
            "n_informative_probes":
                n_informative_probes,
            "verdict": verdict,
        }

    def class_leader_disagreement(
        probe_name,
        evidence_df=None,
    ):
        # Un probe cuenta como informativo sólo si separa
        # a las DOS primitives líderes actuales.
        if evidence_df is None:
            rows = []

            for h_id in plausible_repairs:
                rows.append({
                    "hypothesis_id": h_id,
                    "primitive":
                        hypothesis_meta[
                            h_id
                        ]["primitive"],
                    "score":
                        best_generated[
                            h_id
                        ]["hold_score"],
                })

            edf = pd.DataFrame(rows)
        else:
            edf = (
                evidence_df[
                    evidence_df[
                        "hypothesis_id"
                    ]
                    != "__agent_original__"
                ][
                    [
                        "hypothesis_id",
                        "primitive",
                        "mean_multiregime",
                    ]
                ]
                .rename(
                    columns={
                        "mean_multiregime":
                            "score"
                    }
                )
            )

        leaders = (
            edf
            .sort_values("score")
            .groupby(
                "primitive",
                as_index=False,
            )
            .first()
            .sort_values("score")
            .reset_index(drop=True)
        )

        if len(leaders) < 2:
            return 0.0

        h1 = leaders.iloc[0][
            "hypothesis_id"
        ]
        h2 = leaders.iloc[1][
            "hypothesis_id"
        ]

        key1 = (probe_name, h1)
        key2 = (probe_name, h2)

        if (
            key1 not in probe_prediction_cache
            or key2
            not in probe_prediction_cache
        ):
            return 0.0

        return pairwise_prediction_distance(
            probe_prediction_cache[key1],
            probe_prediction_cache[key2],
        )


    def best_current_hypothesis_by_primitive(evidence_df):
        repairs = evidence_df[
            evidence_df["hypothesis_id"]
            != "__agent_original__"
        ].copy()

        return (
            repairs
            .sort_values(
                ["mean_multiregime", "worst_regime"]
            )
            .groupby(
                "primitive",
                as_index=False,
            )
            .first()
            .sort_values(
                ["mean_multiregime", "worst_regime"]
            )
            .reset_index(drop=True)
        )

    def temporal_signature_distance(
        a,
        b,
        cfg,
    ):
        start = float(
            cfg.get("stress_start", 8.0)
        )
        end = float(
            cfg.get("stress_end", 10.0)
        )
        recovery_end = min(
            end + 8.0,
            float(
                min(
                    a.index.max(),
                    b.index.max(),
                )
            ),
        )

        mask = (
            (a.index >= start)
            & (a.index <= recovery_end)
        )

        xa = a.loc[
            mask,
            "effective_capacity",
        ].astype(float)

        xb = b.loc[
            mask,
            "effective_capacity",
        ].astype(float)

        scale = max(
            variable_scale(xa),
            variable_scale(xb),
            1.0,
        )

        level_rmse = float(
            np.sqrt(
                np.mean(
                    (
                        xa.to_numpy()
                        - xb.to_numpy()
                    ) ** 2
                )
            )
        ) / scale

        da = (
            xa.diff()
            .fillna(0.0)
            .to_numpy()
        )
        db = (
            xb.diff()
            .fillna(0.0)
            .to_numpy()
        )

        slope_scale = max(
            (
                float(
                    np.max(
                        np.abs(da)
                    )
                )
                if len(da)
                else 0.0
            ),
            (
                float(
                    np.max(
                        np.abs(db)
                    )
                )
                if len(db)
                else 0.0
            ),
            1.0,
        )

        slope_rmse = float(
            np.sqrt(
                np.mean(
                    (da - db) ** 2
                )
            )
        ) / slope_scale

        return (
            0.5 * level_rmse
            + 0.5 * slope_rmse
        )

    def design_directed_probe(
        evidence_df,
        remaining_directed_probes,
    ):
        primitive_best = (
            best_current_hypothesis_by_primitive(
                evidence_df
            )
        )

        if len(primitive_best) < 2:
            return None, primitive_best

        rivals = (
            primitive_best
            .iloc[:2]
            .copy()
        )

        h1 = rivals.iloc[0][
            "hypothesis_id"
        ]
        h2 = rivals.iloc[1][
            "hypothesis_id"
        ]

        rows = []

        for probe_name in (
            remaining_directed_probes
        ):
            cfg = (
                DIRECTED_PROBE_LIBRARY[
                    probe_name
                ]
            )

            pred1 = (
                probe_prediction_cache[
                    (probe_name, h1)
                ]
            )
            pred2 = (
                probe_prediction_cache[
                    (probe_name, h2)
                ]
            )

            d = temporal_signature_distance(
                pred1,
                pred2,
                cfg,
            )

            rows.append({
                "probe": probe_name,
                "rival_1": h1,
                "rival_1_primitive":
                    rivals.iloc[0][
                        "primitive"
                    ],
                "rival_2": h2,
                "rival_2_primitive":
                    rivals.iloc[1][
                        "primitive"
                    ],
                "temporal_signature_distance":
                    d,
            })

        design = (
            pd.DataFrame(rows)
            .sort_values(
                "temporal_signature_distance",
                ascending=False,
            )
            .reset_index(drop=True)
        )

        return design, primitive_best


    selected_probes = []
    informative_probes = []
    probe_observations = {}
    sequential_log = []
    design_history = {}
    committee_history = {}
    directed_design_history = {}
    directed_rival_history = {}

    active_repairs = plausible_repairs.copy()
    current_evidence = None
    current_result = None

    for step in range(1, MAX_PROBES + 1):
        remaining_probes = [
            p for p in PROBE_LIBRARY
            if p not in selected_probes
        ]

        if (
            not remaining_probes
            or len(active_repairs) < 2
        ):
            break

        committee, design = design_next_probe(
            active_repairs,
            remaining_probes,
            evidence_df=current_evidence,
        )

        committee_history[step] = committee.copy()
        design_history[step] = design.copy()

        next_probe = design.iloc[0]["probe"]
        next_disagreement = float(
            design.iloc[0]["mean_pairwise_disagreement"]
        )

        class_disagreement = (
            class_leader_disagreement(
                next_probe,
                current_evidence,
            )
        )

        probe_is_informative = (
            class_disagreement
            >= MIN_CLASS_DISAGREEMENT
        )

        cfg = PROBE_LIBRARY[next_probe]

        world_df, _ = simulate_world_case(
            true_primitive,
            world_truth=world_truth,
            params=cfg.get("params"),
            capacity_mode=cfg.get(
                "capacity_mode",
                "constant",
            ),
            stress_start=cfg.get("stress_start", 8.0),
            stress_end=cfg.get("stress_end", 14.0),
            stress_capacity=cfg.get(
                "stress_capacity",
                80.0,
            ),
        )

        probe_observations[next_probe] = (
            world_df[OBSERVED_COLUMNS].copy()
        )
        selected_probes.append(next_probe)

        if probe_is_informative:
            informative_probes.append(
                next_probe
            )

        current_evidence = accumulated_evidence(
            selected_probes,
            probe_observations,
        )

        current_result = adjudicate(
            current_evidence,
            len(selected_probes),
            len(informative_probes),
        )

        agent_score_now = current_result["agent_score"]

        active_repairs = (
            current_evidence[
                (
                    current_evidence["hypothesis_id"]
                    != "__agent_original__"
                )
                & (
                    current_evidence["mean_multiregime"]
                    < agent_score_now
                )
            ]
            ["hypothesis_id"]
            .tolist()
        )

        win_meta = hypothesis_meta[
            current_result["winner"]
        ]

        sequential_log.append({
            "stage": "standard",
            "step": step,
            "probe": next_probe,
            "probe_disagreement": next_disagreement,
            "class_disagreement":
                class_disagreement,
            "probe_is_informative":
                probe_is_informative,
            "active_after": len(active_repairs),
            "winner": current_result["winner"],
            "winner_primitive": win_meta["primitive"],
            "winner_feature": win_meta["feature_id"],
            "winner_score":
                current_result["winner_score"],
            "global_second_score":
                current_result[
                    "global_second_score"
                ],
            "class_second_score":
                current_result[
                    "class_second_score"
                ],
            "agent_score":
                current_result["agent_score"],
            "winner_worst": current_result["winner_worst"],
            "agent_worst": current_result["agent_worst"],
            "separation": current_result["separation"],
            "repair_advantage": current_result["advantage"],
            "verdict": current_result["verdict"],
        })

        print(
            case_id,
            "| step", step,
            "| probe", next_probe,
            "| active", len(active_repairs),
            "| winner", current_result["winner"],
            "| sep", round(
                current_result["separation"],
                4,
            ),
            "| informative",
            probe_is_informative,
            "| class_sep",
            round(
                current_result[
                    "class_separation"
                ],
                4,
            ),
            "| verdict",
            current_result["verdict"],
        )

        if current_result["verdict"] in {
            "REPAIR_ACCEPTED",
            "RETAIN_AGENT",
        }:
            break

    standard_verdict = (
        None
        if current_result is None
        else current_result["verdict"]
    )
    standard_selected_probes = selected_probes.copy()

    # Segunda etapa: sólo se activa tras abstención estándar.
    if (
        current_result is not None
        and current_result["verdict"] == "UNRESOLVED"
    ):
        for directed_step in range(
            1,
            MAX_DIRECTED_PROBES + 1,
        ):
            remaining_directed = [
                p for p in DIRECTED_PROBE_LIBRARY
                if p not in selected_probes
            ]

            if not remaining_directed:
                break

            directed_design, primitive_best = (
                design_directed_probe(
                    current_evidence,
                    remaining_directed,
                )
            )

            if directed_design is None or directed_design.empty:
                break

            directed_design_history[
                directed_step
            ] = directed_design.copy()

            directed_rival_history[
                directed_step
            ] = primitive_best.copy()

            next_probe = directed_design.iloc[0]["probe"]
            directed_distance = float(
                directed_design.iloc[0][
                    "temporal_signature_distance"
                ]
            )

            class_disagreement = (
                class_leader_disagreement(
                    next_probe,
                    current_evidence,
                )
            )

            probe_is_informative = (
                class_disagreement
                >= MIN_CLASS_DISAGREEMENT
            )

            rival_1_primitive = (
                directed_design.iloc[0][
                    "rival_1_primitive"
                ]
            )
            rival_2_primitive = (
                directed_design.iloc[0][
                    "rival_2_primitive"
                ]
            )

            cfg = DIRECTED_PROBE_LIBRARY[next_probe]

            # Sólo ahora se consulta WORLD.
            world_df, _ = simulate_world_case(
                true_primitive,
                world_truth=world_truth,
                params=cfg.get("params"),
                capacity_mode=cfg.get(
                    "capacity_mode",
                    "constant",
                ),
                stress_start=cfg.get(
                    "stress_start",
                    8.0,
                ),
                stress_end=cfg.get(
                    "stress_end",
                    10.0,
                ),
                stress_capacity=cfg.get(
                    "stress_capacity",
                    80.0,
                ),
            )

            probe_observations[next_probe] = (
                world_df[OBSERVED_COLUMNS].copy()
            )
            selected_probes.append(next_probe)

            if probe_is_informative:
                informative_probes.append(
                    next_probe
                )

            current_evidence = accumulated_evidence(
                selected_probes,
                probe_observations,
            )

            current_result = adjudicate(
                current_evidence,
                len(selected_probes),
                len(informative_probes),
            )

            agent_score_now = (
                current_result["agent_score"]
            )

            active_repairs = (
                current_evidence[
                    (
                        current_evidence[
                            "hypothesis_id"
                        ]
                        != "__agent_original__"
                    )
                    & (
                        current_evidence[
                            "mean_multiregime"
                        ]
                        < agent_score_now
                    )
                ]
                ["hypothesis_id"]
                .tolist()
            )

            win_meta = hypothesis_meta[
                current_result["winner"]
            ]

            sequential_log.append({
                "stage": "directed",
                "step": (
                    MAX_PROBES
                    + directed_step
                ),
                "probe": next_probe,
                "probe_disagreement":
                    directed_distance,
                "class_disagreement":
                    class_disagreement,
                "probe_is_informative":
                    probe_is_informative,
                "active_after":
                    len(active_repairs),
                "winner":
                    current_result["winner"],
                "winner_primitive":
                    win_meta["primitive"],
                "winner_feature":
                    win_meta["feature_id"],
                "separation":
                    current_result["separation"],
                "repair_advantage":
                    current_result["advantage"],
                "verdict":
                    current_result["verdict"],
                "rival_1_primitive":
                    rival_1_primitive,
                "rival_2_primitive":
                    rival_2_primitive,
            })

            print(
                case_id,
                "| DIRECTED", directed_step,
                "| rivals",
                rival_1_primitive,
                "vs",
                rival_2_primitive,
                "| probe", next_probe,
                "| signature",
                round(directed_distance, 4),
                "| winner",
                current_result["winner"],
                "| sep",
                round(
                    current_result["separation"],
                    4,
                ),
                "| verdict",
                current_result["verdict"],
            )

            if current_result["verdict"] in {
                "REPAIR_ACCEPTED",
                "RETAIN_AGENT",
            }:
                break

    if current_evidence is None:
        raise RuntimeError(
            f"{case_id}: no se ejecutó ningún probe"
        )

    structural_winner = current_result["winner"]
    winner_primitive = hypothesis_meta[
        structural_winner
    ]["primitive"]
    winner_feature = hypothesis_meta[
        structural_winner
    ]["feature_id"]
    verdict = current_result["verdict"]

    winner = best_generated[structural_winner]

    decision_rows = []

    def simulation_kwargs(cfg):
        return {
            "params": cfg.get("params"),
            "capacity_mode": cfg.get(
                "capacity_mode", "constant"
            ),
            "stress_start": cfg.get(
                "stress_start", 8.0
            ),
            "stress_end": cfg.get(
                "stress_end", 14.0
            ),
            "stress_capacity": cfg.get(
                "stress_capacity", 80.0
            ),
        }

    decision_rows = []

    for action, cfg in ACTIONS.items():
        pred, _ = simulate_repair(
            winner_primitive,
            winner_feature,
            feature_meta,
            repair=winner["repair"],
            **simulation_kwargs(cfg),
        )

        decision_rows.append({
            "action": action,
            "cash_final": float(
                pred["cash"].iloc[-1]
            ),
            "backlog_final": float(
                pred["backlog"].iloc[-1]
            ),
        })

    decision_table = (
        pd.DataFrame(decision_rows)
        .set_index("action")
    )

    decision_table["policy_score"] = (
        decision_table["cash_final"]
        - 20.0 * decision_table["backlog_final"]
    )

    exploratory_action = (
        decision_table["policy_score"].idxmax()
    )

    proposed_action = (
        exploratory_action
        if verdict == "REPAIR_ACCEPTED"
        else None
    )

    oracle_rows = []

    for action, cfg in ACTIONS.items():
        df, _ = simulate_world_case(
            true_primitive,
            world_truth=world_truth,
            **simulation_kwargs(cfg),
        )

        oracle_rows.append({
            "action": action,
            "cash_final": float(
                df["cash"].iloc[-1]
            ),
            "backlog_final": float(
                df["backlog"].iloc[-1]
            ),
            "effective_capacity_final": float(
                df["effective_capacity"].iloc[-1]
            ),
        })

    oracle_actions = (
        pd.DataFrame(oracle_rows)
        .set_index("action")
    )

    oracle_actions["policy_score"] = (
        oracle_actions["cash_final"]
        - 20.0 * oracle_actions["backlog_final"]
    )

    oracle_best_action = (
        oracle_actions["policy_score"].idxmax()
    )

    action_matches_oracle = (
        proposed_action is not None
        and proposed_action == oracle_best_action
    )

    def classify_final_at_threshold(sep_threshold):
        if invariant_break <= 0.10:
            return "COMMIT_WRONG"

        separation_ok = (
            np.isnan(current_result["separation"])
            or current_result["separation"]
            >= sep_threshold
        )

        accept = (
            len(selected_probes)
            >= MIN_PROBES_BEFORE_ACCEPT
            and (
                len(informative_probes)
                >= MIN_INFORMATIVE_PROBES_BEFORE_ACCEPT
            )
            and current_result["advantage"]
            >= MIN_ADVANTAGE
            and (
                current_result["winner_worst"]
                <= current_result["agent_worst"]
                * MAX_WORST_RELATIVE
            )
            and separation_ok
        )

        if not accept:
            return "ABSTAIN"

        correct = (
            winner_primitive == true_primitive
            and winner_feature == TRUE_DERIVED_ID
        )

        return (
            "COMMIT_CORRECT"
            if correct
            else "COMMIT_WRONG"
        )

    outcome_005 = classify_final_at_threshold(0.05)
    outcome_010 = classify_final_at_threshold(0.10)
    outcome_015 = classify_final_at_threshold(0.15)

    gate = {
        "utilization_no_fue_observable":
            "utilization" not in CEI_BASE.columns,

        "invariancia_agente_falsada":
            invariant_break > 0.10,

        "relacion_verdadera_construida":
            TRUE_DERIVED_ID
            in {expression_id(e) for e in EXPRESSIONS},

        "cuatro_primitivas_compitieron":
            set(PRIMITIVES).issubset(
                set(
                    generated_summary[
                        "primitive"
                    ].unique()
                )
            ),

        "hipotesis_verdadera_es_plausible":
            true_hypothesis_id
            in plausible_repairs,

        "presupuesto_total_respetado":
            len(selected_probes)
            <= TOTAL_PROBE_BUDGET,

        "probes_estandar_max_3":
            len(standard_selected_probes)
            <= MAX_STANDARD_PROBES,

        "probes_dirigidos_max_2":
            len([
                p for p in selected_probes
                if p in DIRECTED_PROBE_LIBRARY
            ])
            <= MAX_DIRECTED_PROBES,
    }

    gate_df = pd.DataFrame({
        "check": list(gate.keys()),
        "pass": list(gate.values()),
    })

    case_pass = bool(gate_df["pass"].all())

    primitive_summary = (
        current_evidence[
            current_evidence["hypothesis_id"]
            != "__agent_original__"
        ]
        .sort_values(
            ["mean_multiregime", "worst_regime"]
        )
        .groupby(
            "primitive",
            as_index=False,
        )
        .first()[
            [
                "primitive",
                "hypothesis_id",
                "feature_id",
                "mean_multiregime",
                "worst_regime",
            ]
        ]
        .sort_values("mean_multiregime")
    )

    final_repairs = (
        current_evidence[
            current_evidence["hypothesis_id"]
            != "__agent_original__"
        ]
        .sort_values(
            ["mean_multiregime", "worst_regime"]
        )
        .reset_index(drop=True)
    )

    final_top2 = final_repairs.head(2).copy()

    second_hypothesis = (
        final_top2.iloc[1]["hypothesis_id"]
        if len(final_top2) > 1
        else None
    )
    second_primitive = (
        final_top2.iloc[1]["primitive"]
        if len(final_top2) > 1
        else None
    )
    second_feature = (
        final_top2.iloc[1]["feature_id"]
        if len(final_top2) > 1
        else None
    )

    print(
        case_id,
        "| TRUE", true_primitive,
        "| PRED", winner_primitive,
        "| FEATURE", winner_feature,
        "| OUTCOME", outcome_010,
    )

    return {
        "case_id": case_id,
        "true_primitive": true_primitive,
        "winner": structural_winner,
        "winner_primitive": winner_primitive,
        "winner_feature": winner_feature,
        "verdict": verdict,
        "case_pass": case_pass,
        "outcome_005": outcome_005,
        "outcome_010": outcome_010,
        "outcome_015": outcome_015,
        "second_hypothesis": second_hypothesis,
        "second_primitive": second_primitive,
        "second_feature": second_feature,
        "final_top2": final_top2,
        "oracle_best_action": oracle_best_action,
        "action_matches_oracle": action_matches_oracle,
        "selected_probes": selected_probes,
        "informative_probes":
            informative_probes,
        "n_informative_probes":
            len(informative_probes),
        "global_separation":
            current_result[
                "global_separation"
            ],
        "class_separation":
            current_result[
                "class_separation"
            ],
        "class_second_id":
            current_result[
                "class_second_id"
            ],
        "class_second_primitive":
            current_result[
                "class_second_primitive"
            ],
        "standard_selected_probes":
            standard_selected_probes,
        "standard_verdict":
            standard_verdict,
        "directed_probes": [
            p for p in selected_probes
            if p in DIRECTED_PROBE_LIBRARY
        ],
        "directed_design_history":
            directed_design_history,
        "directed_rival_history":
            directed_rival_history,
        "invariant_break": invariant_break,
        "agent_hold": agent_hold,
        "repair_advantage": current_result["advantage"],
        "separation": current_result["separation"],
        "proposed_action": proposed_action,
        "feature_rank": feature_rank,
        "structural_search": structural_search,
        "generated_summary": generated_summary,
        "version_space": plausible_repairs,
        "multiregime": current_evidence,
        "primitive_summary": primitive_summary,
        "sequential_history": pd.DataFrame(
            sequential_log
        ),
        "committee_history": committee_history,
        "design_history": design_history,
        "decision_table": decision_table,
        "oracle_actions": oracle_actions,
        "gate": gate_df,
        "base_observations": CEI_BASE,
        "probe_observations": probe_observations,
    }


# ---- C0.0 original notebook code cell 16 ----
GENERALIZATION_RESULTS = {}

for case_id, spec in WORLD_CASES.items():
    GENERALIZATION_RESULTS[
        case_id
    ] = run_sd5g_case(
        case_id,
        spec["primitive"],
        spec["truth"],
    )


# ---- C0.0 original notebook code cell 18 ----
summary_rows = []

for case_id, result in (
    GENERALIZATION_RESULTS.items()
):
    summary_rows.append({
        "case_id": case_id,
        "true_primitive":
            result["true_primitive"],
        "predicted_primitive":
            result["winner_primitive"],
        "winner_feature":
            result["winner_feature"],
        "primary_outcome":
            result["outcome_010"],
        "n_total_probes":
            len(result["selected_probes"]),
        "n_informative_probes":
            result["n_informative_probes"],
        "probes":
            " -> ".join(
                result["selected_probes"]
            ),
        "informative_probes":
            " -> ".join(
                result["informative_probes"]
            ),
        "repair_advantage":
            result["repair_advantage"],
        "global_separation":
            result["global_separation"],
        "class_separation":
            result["class_separation"],
        "class_second_primitive":
            result[
                "class_second_primitive"
            ],
        "proposed_action":
            result["proposed_action"],
        "oracle_best_action":
            result["oracle_best_action"],
        "action_matches_oracle":
            result["action_matches_oracle"],
    })

GENERALIZATION_SUMMARY = pd.DataFrame(
    summary_rows
)

display(GENERALIZATION_SUMMARY)

CONFUSION_COMMITTED = pd.crosstab(
    GENERALIZATION_SUMMARY[
        "true_primitive"
    ],
    GENERALIZATION_SUMMARY[
        "predicted_primitive"
    ],
    rownames=["true"],
    colnames=["winner"],
)

print("\nTrue × winner:")
display(CONFUSION_COMMITTED)


# ---- C0.0 original notebook code cell 20 ----
PROTOCOL_CHECKS = {
    "cuarenta_casos":
        len(GENERALIZATION_RESULTS)
        == 40,

    "diez_por_clase":
        bool((CLASS_COUNTS == 10).all()),

    "worlds_out_of_grid":
        bool(
            not OUT_OF_GRID_AUDIT[
                "exact_match_in_grid"
            ].any()
        ),

    "gramatica_sin_leakage_bloqueado":
        bool(
            LEAKAGE_AUDIT[
                "is_primary_safe"
            ].all()
        ),

    "oracle_feature_target_free":
        TRUE_DERIVED_ID
        == "ratio::incoming_orders/nominal_capacity",

    "presupuesto_total_max_5":
        bool(
            (
                GENERALIZATION_SUMMARY[
                    "n_total_probes"
                ]
                <= TOTAL_PROBE_BUDGET
            ).all()
        ),
}

PROTOCOL_GATE = pd.DataFrame({
    "check": list(
        PROTOCOL_CHECKS.keys()
    ),
    "pass": list(
        PROTOCOL_CHECKS.values()
    ),
})

print("GATE DE INTEGRIDAD")
display(PROTOCOL_GATE)

def wilson_interval(
    success,
    total,
    z=1.959963984540054,
):
    if total == 0:
        return (np.nan, np.nan)

    p = success / total
    z2 = z * z
    denom = 1.0 + z2 / total

    center = (
        p
        + z2 / (2.0 * total)
    ) / denom

    half = (
        z
        * np.sqrt(
            p * (1.0 - p) / total
            + z2 / (4.0 * total * total)
        )
        / denom
    )

    return (
        center - half,
        center + half,
    )

counts = (
    GENERALIZATION_SUMMARY[
        "primary_outcome"
    ]
    .value_counts()
    .reindex(
        [
            "COMMIT_CORRECT",
            "COMMIT_WRONG",
            "ABSTAIN",
        ],
        fill_value=0,
    )
)

n = len(GENERALIZATION_SUMMARY)
n_correct = int(
    counts["COMMIT_CORRECT"]
)
n_wrong = int(
    counts["COMMIT_WRONG"]
)
n_abstain = int(
    counts["ABSTAIN"]
)
n_committed = n_correct + n_wrong

correct_ci = wilson_interval(
    n_correct,
    n,
)
wrong_ci = wilson_interval(
    n_wrong,
    n,
)

PERFORMANCE = pd.DataFrame([{
    "n": n,
    "commit_correct": n_correct,
    "commit_wrong": n_wrong,
    "abstain": n_abstain,
    "commit_correct_rate":
        n_correct / n,
    "commit_correct_wilson_lo":
        correct_ci[0],
    "commit_correct_wilson_hi":
        correct_ci[1],
    "commit_wrong_rate":
        n_wrong / n,
    "commit_wrong_wilson_lo":
        wrong_ci[0],
    "commit_wrong_wilson_hi":
        wrong_ci[1],
    "abstention_rate":
        n_abstain / n,
    "accuracy_when_committed":
        (
            n_correct / n_committed
            if n_committed
            else np.nan
        ),
    "mean_total_probes":
        GENERALIZATION_SUMMARY[
            "n_total_probes"
        ].mean(),
    "mean_informative_probes":
        GENERALIZATION_SUMMARY[
            "n_informative_probes"
        ].mean(),
}])

print("\nDESEMPEÑO ESTRUCTURAL")
display(PERFORMANCE)

print("\nPOR CLASE")
display(
    GENERALIZATION_SUMMARY
    .groupby(
        [
            "true_primitive",
            "primary_outcome",
        ]
    )
    .size()
    .unstack(fill_value=0)
)

print(
    "\nGLOBAL VS CLASS SEPARATION"
)
display(
    GENERALIZATION_SUMMARY[
        [
            "case_id",
            "true_primitive",
            "predicted_primitive",
            "global_separation",
            "class_separation",
            "primary_outcome",
        ]
    ]
)

# Línea base decisional: mejor política constante ex post
# se reporta sólo como referencia, no como evidencia estructural.
policy_counts = (
    GENERALIZATION_SUMMARY[
        "oracle_best_action"
    ]
    .value_counts()
)

CONSTANT_POLICY = (
    policy_counts.index[0]
)
CONSTANT_POLICY_RATE = (
    policy_counts.iloc[0] / n
)

committed_mask = (
    GENERALIZATION_SUMMARY[
        "primary_outcome"
    ]
    != "ABSTAIN"
)

cei_action_rate = (
    GENERALIZATION_SUMMARY.loc[
        committed_mask,
        "action_matches_oracle",
    ].mean()
    if committed_mask.any()
    else np.nan
)

DECISION_BASELINE = pd.DataFrame([{
    "best_constant_policy":
        CONSTANT_POLICY,
    "constant_policy_match_rate":
        CONSTANT_POLICY_RATE,
    "cei_action_match_rate_when_committed":
        cei_action_rate,
    "cei_minus_constant":
        cei_action_rate
        - CONSTANT_POLICY_RATE,
}])

print(
    "\nDECISIÓN VS POLÍTICA CONSTANTE"
)
display(DECISION_BASELINE)

# Casos problemáticos visibles en notebook ejecutado.
problem = GENERALIZATION_SUMMARY[
    GENERALIZATION_SUMMARY[
        "primary_outcome"
    ]
    != "COMMIT_CORRECT"
]

if len(problem):
    print("\nCASOS NO COMMIT_CORRECT")
    display(problem)

    for case_id in problem[
        "case_id"
    ].tolist():
        print("\n", "=" * 72)
        print(case_id)
        print("=" * 72)

        ev = (
            GENERALIZATION_RESULTS[
                case_id
            ]["multiregime"]
        )

        display(
            ev[
                ev["hypothesis_id"]
                != "__agent_original__"
            ]
            .sort_values(
                [
                    "mean_multiregime",
                    "worst_regime",
                ]
            )
            .head(8)
        )
else:
    print(
        "\nNo hubo errores ni abstenciones."
    )


# ---- C0.0 original notebook code cell 23 ----
from pathlib import Path

EXPORT_DIR = Path(
    os.environ.get("CEI_A03_RESULTS_DIR", "results/A03")
)
EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

GENERALIZATION_SUMMARY.to_csv(
    EXPORT_DIR
    / "generalization_summary.csv",
    index=False,
)
CONFUSION_COMMITTED.to_csv(
    EXPORT_DIR
    / "primitive_confusion.csv"
)
PROTOCOL_GATE.to_csv(
    EXPORT_DIR
    / "protocol_gate.csv",
    index=False,
)
PERFORMANCE.to_csv(
    EXPORT_DIR
    / "performance.csv",
    index=False,
)
DECISION_BASELINE.to_csv(
    EXPORT_DIR
    / "decision_baseline.csv",
    index=False,
)
OUT_OF_GRID_AUDIT.to_csv(
    EXPORT_DIR
    / "out_of_grid_audit.csv",
    index=False,
)
LEAKAGE_AUDIT.to_csv(
    EXPORT_DIR
    / "feature_leakage_audit.csv",
    index=False,
)
STRUCTURAL_CLASS_AUDIT.to_csv(
    EXPORT_DIR
    / "structural_class_audit.csv",
    index=False,
)

for case_id, result in (
    GENERALIZATION_RESULTS.items()
):
    case_dir = EXPORT_DIR / case_id
    case_dir.mkdir(exist_ok=True)

    result["multiregime"].to_csv(
        case_dir
        / "multiregime_evidence.csv",
        index=False,
    )
    result[
        "sequential_history"
    ].to_csv(
        case_dir
        / "sequential_history.csv",
        index=False,
    )
    result["feature_rank"].to_csv(
        case_dir
        / "feature_rank.csv",
        index=False,
    )
    result[
        "primitive_summary"
    ].to_csv(
        case_dir
        / "primitive_summary.csv",
        index=False,
    )
    result["decision_table"].to_csv(
        case_dir
        / "decision_table.csv"
    )
    result["oracle_actions"].to_csv(
        case_dir
        / "oracle_actions.csv"
    )

print("Exportado a:", EXPORT_DIR)
