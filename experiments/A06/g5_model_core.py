#!/usr/bin/env python3
# A06 scientific model core copied from C0.0 G5 corrected benchmark, NOT the 40-world run.
# Source notebook commit d90ff87ba47572edd7d2084ecdc62dfba54cd14d
# Source Git blob 730420a744d91d195ec1eca60ef3c4dd9468e063
# Original scientific cells: 4, 6, 7, 9, 10, 12. Equations and world cases unchanged.
# The runtime experiment is in experiment.py; model_core is imported without running G5.
def display(obj):
    print("[notebook display]", type(obj).__name__, getattr(obj,"shape",""))


# ---- Original G5 cell 4 ----
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

# ---- Original G5 cell 6 ----
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

# ---- Original G5 cell 7 ----
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

# ---- Original G5 cell 9 ----
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


# ---- Original G5 cell 10 ----
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


# ---- Original G5 cell 12 ----
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
