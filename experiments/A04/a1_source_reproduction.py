#!/usr/bin/env python3
# A04: verbatim scientific computations from original C0.0 SD5-A1 audit.
# Source: https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_A1_Auditoria_Identificabilidad_Leakage.ipynb
# Source Git blob SHA: 458e12ed39404a3c13b4cd2c3105be78c0b2ee7b
# Mechanical adaptations only:
#   - omit Colab package auto-install/restart (original notebook cell 3)
#   - redirect /content/ output to CEI_A04_RESULTS_DIR
#   - display() shim for non-interactive logs (non-mutating)
# No change to model equations, calibration, audits, thresholds or case ordering.
import os

def display(obj):
    shape = getattr(obj, "shape", None)
    if shape is None:
        print("[notebook display]", type(obj).__name__, str(obj)[:250])
    else:
        print("[notebook display]", type(obj).__name__, "shape", shape)



# ---- Original C0.0 SD5-A1 code cell 4 ----
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


# ---- Original C0.0 SD5-A1 code cell 6 ----
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

WORLD_CASES = {
    "W01": {"primitive": "accumulation", "truth": {
        "threshold": 0.18, "build_rate": 5.8,
        "recovery_rate": 2.2, "degradation": 0.021,
    }},
    "W02": {"primitive": "accumulation", "truth": {
        "threshold": 0.36, "build_rate": 6.6,
        "recovery_rate": 4.2, "degradation": 0.024,
    }},
    "W03": {"primitive": "accumulation", "truth": {
        "threshold": 0.44, "build_rate": 7.1,
        "recovery_rate": 2.8, "degradation": 0.027,
    }},
    "W04": {"primitive": "smooth_delay", "truth": {
        "threshold": 0.18, "adjustment_rate": 0.38,
        "degradation": 0.34,
    }},
    "W05": {"primitive": "smooth_delay", "truth": {
        "threshold": 0.36, "adjustment_rate": 0.62,
        "degradation": 0.41,
    }},
    "W06": {"primitive": "smooth_delay", "truth": {
        "threshold": 0.44, "adjustment_rate": 0.68,
        "degradation": 0.46,
    }},
    "W07": {"primitive": "reinforcing", "truth": {
        "threshold": 0.18, "drive_rate": 3.1,
        "feedback_gain": 0.08, "leak_rate": 0.19,
        "degradation": 0.021,
    }},
    "W08": {"primitive": "reinforcing", "truth": {
        "threshold": 0.36, "drive_rate": 3.9,
        "feedback_gain": 0.12, "leak_rate": 0.23,
        "degradation": 0.024,
    }},
    "W09": {"primitive": "reinforcing", "truth": {
        "threshold": 0.44, "drive_rate": 4.4,
        "feedback_gain": 0.14, "leak_rate": 0.27,
        "degradation": 0.027,
    }},
    "W10": {"primitive": "pipeline_delay", "truth": {
        "threshold": 0.18, "delay_time": 1.6,
        "degradation": 0.34,
    }},
    "W11": {"primitive": "pipeline_delay", "truth": {
        "threshold": 0.36, "delay_time": 2.4,
        "degradation": 0.41,
    }},
    "W12": {"primitive": "pipeline_delay", "truth": {
        "threshold": 0.44, "delay_time": 2.7,
        "degradation": 0.46,
    }},
}

TRUE_DERIVED_ID = "ratio::fulfilled/effective_capacity"

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

PRIMITIVES = [
    "accumulation",
    "smooth_delay",
    "reinforcing",
    "pipeline_delay",
]

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


# Biblioteca temporal dirigida.
# No reemplaza los probes de G2: sólo se habilita tras UNRESOLVED.
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
        "params": {"marketing_intensity": 1.5},
        "capacity_mode": "constant",
    },
    "mas_capacidad_permanente": {
        "params": {"nominal_capacity": 145.0},
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


# ---- Original C0.0 SD5-A1 code cell 7 ----
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
        name=f"cei_sd5g4_world_{true_primitive}",
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
    hidden_signal.equation = (utilization - 0.80) / 0.20

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

    elif true_primitive == "smooth_delay":
        hidden_in = model.flow("hidden_in")
        hidden_out = model.flow("hidden_out")

        hidden_in.equation = hidden_excess * float(truth["adjustment_rate"])
        hidden_out.equation = hidden_state * float(truth["adjustment_rate"])
        hidden_state.equation = hidden_in - hidden_out
        primitive_impact.equation = hidden_state * float(truth["degradation"])

    elif true_primitive == "reinforcing":
        hidden_in = model.flow("hidden_in")
        hidden_out = model.flow("hidden_out")

        hidden_in.equation = (
            hidden_excess * float(truth["drive_rate"])
            + hidden_state * float(truth["feedback_gain"])
        )
        hidden_out.equation = hidden_state * float(truth["leak_rate"])
        hidden_state.equation = hidden_in - hidden_out
        primitive_impact.equation = hidden_state * float(truth["degradation"])

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


# ---- Original C0.0 SD5-A1 code cell 8 ----
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

RAW_ELIGIBLE = [
    v for v in OBSERVED_COLUMNS
    if v != TARGET
    and VARIABLE_ROLE[v] != "control"
]

RATE_VARS = [
    "incoming_orders",
    "nominal_capacity",
    "effective_capacity",
    "fulfilled",
]

DIFF_VARS = [
    "incoming_orders",
    "nominal_capacity",
    "fulfilled",
]

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

for x in RAW_ELIGIBLE:
    EXPRESSIONS.append({"kind": "raw", "x": x})

for x in RATE_VARS:
    for y in RATE_VARS:
        if x == y:
            continue
        if x == TARGET:
            continue
        EXPRESSIONS.append({"kind": "ratio", "x": x, "y": y})

for x, y in itertools.permutations(DIFF_VARS, 2):
    EXPRESSIONS.append({"kind": "diff", "x": x, "y": y})

for x in RAW_ELIGIBLE:
    EXPRESSIONS.append({"kind": "lag1", "x": x})
    EXPRESSIONS.append({"kind": "delta1", "x": x})

EXPRESSIONS = list({
    expression_id(e): e
    for e in EXPRESSIONS
}.values())

print("Expresiones gramaticales:", len(EXPRESSIONS))
print(
    "Relación oracle en la gramática?:",
    TRUE_DERIVED_ID in {expression_id(e) for e in EXPRESSIONS},
)


# ---- Original C0.0 SD5-A1 code cell 9 ----
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
        "threshold": [0.10, 0.25, 0.50],
        "build_rate": [5.0, 7.5],
        "recovery_rate": [1.5, 3.5, 5.5],
        "degradation": [0.015, 0.030],
    },
    "smooth_delay": {
        "threshold": [0.10, 0.25, 0.50],
        "adjustment_rate": [0.25, 0.50, 0.75],
        "degradation": [0.25, 0.50],
    },
    "reinforcing": {
        "threshold": [0.10, 0.25, 0.50],
        "drive_rate": [2.5, 5.0],
        "feedback_gain": [0.05, 0.15],
        "leak_rate": [0.10, 0.30],
        "degradation": [0.015, 0.030],
    },
    "pipeline_delay": {
        "threshold": [0.10, 0.25, 0.50],
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

# --- Auditoría SD5-G4: 12 WORLD_TRUE fuera del grid exacto ---

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

OUT_OF_GRID_AUDIT = pd.DataFrame(OUT_OF_GRID_ROWS)

CLASS_COUNTS = (
    pd.Series(
        [spec["primitive"] for spec in WORLD_CASES.values()]
    )
    .value_counts()
    .sort_index()
)

display(OUT_OF_GRID_AUDIT)
print("\nCasos por clase:")
display(CLASS_COUNTS)

assert len(WORLD_CASES) == 12, "G4 requiere exactamente 12 mundos."
assert bool((CLASS_COUNTS == 3).all()), (
    "G4 requiere exactamente 3 mundos por primitive."
)
assert not OUT_OF_GRID_AUDIT["exact_match_in_grid"].any(), (
    "G4 inválido: al menos un parámetro WORLD aparece exactamente en el grid."
)

print("AUDITORÍA G4: PASS — 12 mundos, 3 por clase, todos out-of-grid.")



# ---- Original C0.0 SD5-A1 code cell 10 ----
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
        "feedback_gain": 0.10,
        "leak_rate": 0.30,
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

    elif primitive == "smooth_delay":
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

    elif primitive == "reinforcing":
        drive_rate = constant("drive_rate", r["drive_rate"])
        feedback_gain = constant(
            "feedback_gain",
            r["feedback_gain"],
        )
        leak_rate = constant("leak_rate", r["leak_rate"])

        primitive_in = model.flow("primitive_in")
        primitive_out = model.flow("primitive_out")

        primitive_in.equation = (
            stress_excess * drive_rate
            + latent_state * feedback_gain
        )
        primitive_out.equation = latent_state * leak_rate
        latent_state.equation = primitive_in - primitive_out
        impact.equation = latent_state * degradation

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


# ---- Original C0.0 SD5-A1 code cell 12 ----
MIN_PROBES_BEFORE_ACCEPT = 2
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

    def adjudicate(evidence_df, n_probes):
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
                ["mean_multiregime", "worst_regime"]
            )
            .reset_index(drop=True)
        )

        winner = repairs.iloc[0]["hypothesis_id"]
        winner_score = float(
            repairs.iloc[0]["mean_multiregime"]
        )
        winner_worst = float(
            repairs.iloc[0]["worst_regime"]
        )

        second_score = (
            float(repairs.iloc[1]["mean_multiregime"])
            if len(repairs) > 1
            else np.nan
        )

        separation = (
            (second_score - winner_score) / second_score
            if second_score > 0
            else np.nan
        )

        agent_score = float(
            agent_row["mean_multiregime"]
        )
        agent_worst = float(
            agent_row["worst_regime"]
        )

        advantage = (
            (agent_score - winner_score) / agent_score
            if agent_score > 0
            else -np.inf
        )

        if invariant_break <= 0.10:
            verdict = "RETAIN_AGENT"
        elif (
            n_probes >= MIN_PROBES_BEFORE_ACCEPT
            and advantage >= MIN_ADVANTAGE
            and (
                winner_worst
                <= agent_worst * MAX_WORST_RELATIVE
            )
            and (
                np.isnan(separation)
                or separation >= MIN_REPAIR_SEPARATION
            )
        ):
            verdict = "REPAIR_ACCEPTED"
        else:
            verdict = "UNRESOLVED"

        return {
            "winner": winner,
            "winner_score": winner_score,
            "winner_worst": winner_worst,
            "second_score": second_score,
            "separation": separation,
            "agent_score": agent_score,
            "agent_worst": agent_worst,
            "advantage": advantage,
            "verdict": verdict,
        }

    def best_current_hypothesis_by_primitive(evidence_df):
        repairs = evidence_df[
            evidence_df["hypothesis_id"] != "__agent_original__"
        ].copy()

        return (
            repairs
            .sort_values(
                ["mean_multiregime", "worst_regime"]
            )
            .groupby("primitive", as_index=False)
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
        start = float(cfg.get("stress_start", 8.0))
        end = float(cfg.get("stress_end", 10.0))
        recovery_end = min(
            end + 8.0,
            float(min(a.index.max(), b.index.max())),
        )

        mask = (
            (a.index >= start)
            & (a.index <= recovery_end)
        )

        xa = a.loc[mask, "effective_capacity"].astype(float)
        xb = b.loc[mask, "effective_capacity"].astype(float)

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

        da = xa.diff().fillna(0.0).to_numpy()
        db = xb.diff().fillna(0.0).to_numpy()

        slope_scale = max(
            float(np.max(np.abs(da))) if len(da) else 0.0,
            float(np.max(np.abs(db))) if len(db) else 0.0,
            1.0,
        )

        slope_rmse = float(
            np.sqrt(np.mean((da - db) ** 2))
        ) / slope_scale

        # Peso igual a nivel y forma temporal.
        return 0.5 * level_rmse + 0.5 * slope_rmse

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

        rivals = primitive_best.iloc[:2].copy()
        h1 = rivals.iloc[0]["hypothesis_id"]
        h2 = rivals.iloc[1]["hypothesis_id"]

        rows = []

        for probe_name in remaining_directed_probes:
            cfg = DIRECTED_PROBE_LIBRARY[probe_name]

            pred1 = probe_prediction_cache[
                (probe_name, h1)
            ]
            pred2 = probe_prediction_cache[
                (probe_name, h2)
            ]

            d = temporal_signature_distance(
                pred1,
                pred2,
                cfg,
            )

            rows.append({
                "probe": probe_name,
                "rival_1": h1,
                "rival_1_primitive": rivals.iloc[0]["primitive"],
                "rival_2": h2,
                "rival_2_primitive": rivals.iloc[1]["primitive"],
                "temporal_signature_distance": d,
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

        current_evidence = accumulated_evidence(
            selected_probes,
            probe_observations,
        )

        current_result = adjudicate(
            current_evidence,
            len(selected_probes),
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
            "active_after": len(active_repairs),
            "winner": current_result["winner"],
            "winner_primitive": win_meta["primitive"],
            "winner_feature": win_meta["feature_id"],
            "winner_score": current_result["winner_score"],
            "second_score": current_result["second_score"],
            "agent_score": current_result["agent_score"],
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
            "| verdict", current_result["verdict"],
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

            current_evidence = accumulated_evidence(
                selected_probes,
                probe_observations,
            )

            current_result = adjudicate(
                current_evidence,
                len(selected_probes),
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
        "probe_prediction_cache":
            probe_prediction_cache,
        "agent_probe_prediction_cache":
            agent_probe_prediction_cache,
        "best_generated":
            best_generated,
        "hypothesis_meta":
            hypothesis_meta,
        "feature_meta":
            feature_meta,
        "all_probe_library":
            ALL_PROBE_LIBRARY,
    }


# ---- Original C0.0 SD5-A1 code cell 13 ----
GENERALIZATION_RESULTS = {}

for case_id, spec in WORLD_CASES.items():
    GENERALIZATION_RESULTS[case_id] = run_sd5g_case(
        case_id,
        spec["primitive"],
        spec["truth"],
    )


# ---- Original C0.0 SD5-A1 code cell 15 ----
smooth_rows = []

for a in PRIMITIVE_GRIDS["smooth_delay"]["adjustment_rate"]:
    for ds in PRIMITIVE_GRIDS["smooth_delay"]["degradation"]:
        smooth_rows.append({
            "adjustment_rate": float(a),
            "degradation": float(ds),
            "pole_rate": float(a),
            "numerator_gain": float(a * ds),
            "dc_gain": float(ds),
        })

SMOOTH_TRANSFER = pd.DataFrame(smooth_rows)

reinforcing_rows = []

for drive in PRIMITIVE_GRIDS["reinforcing"]["drive_rate"]:
    for feedback in PRIMITIVE_GRIDS["reinforcing"]["feedback_gain"]:
        for leak in PRIMITIVE_GRIDS["reinforcing"]["leak_rate"]:
            for deg in PRIMITIVE_GRIDS["reinforcing"]["degradation"]:
                net_damping = float(leak - feedback)

                if net_damping > 0:
                    regime = "stable_first_order"
                    dc_gain = float(
                        drive * deg / net_damping
                    )
                elif abs(net_damping) < 1e-12:
                    regime = "integrator"
                    dc_gain = np.inf
                else:
                    regime = "net_reinforcing"
                    dc_gain = np.nan

                reinforcing_rows.append({
                    "drive_rate": float(drive),
                    "feedback_gain": float(feedback),
                    "leak_rate": float(leak),
                    "degradation": float(deg),
                    "net_damping": net_damping,
                    "regime": regime,
                    "pole_rate": (
                        net_damping
                        if net_damping > 0
                        else np.nan
                    ),
                    "numerator_gain":
                        float(drive * deg),
                    "dc_gain": dc_gain,
                })

REINFORCING_TRANSFER = pd.DataFrame(
    reinforcing_rows
)

print("Regímenes dentro del grid reinforcing:")
display(
    REINFORCING_TRANSFER["regime"]
    .value_counts()
    .rename_axis("regime")
    .reset_index(name="n")
)

stable_r = REINFORCING_TRANSFER[
    REINFORCING_TRANSFER["regime"]
    == "stable_first_order"
].copy()

nearest_rows = []

for ri, r in stable_r.iterrows():
    best = None

    for si, s in SMOOTH_TRANSFER.iterrows():
        # Distancia adimensional simple en tasa y ganancia DC.
        rate_scale = max(
            abs(r["pole_rate"]),
            abs(s["pole_rate"]),
            1e-9,
        )
        gain_scale = max(
            abs(r["dc_gain"]),
            abs(s["dc_gain"]),
            1e-9,
        )

        rate_gap = abs(
            r["pole_rate"] - s["pole_rate"]
        ) / rate_scale

        gain_gap = abs(
            r["dc_gain"] - s["dc_gain"]
        ) / gain_scale

        distance = float(
            np.sqrt(
                rate_gap**2
                + gain_gap**2
            )
        )

        row = {
            **r.to_dict(),
            "smooth_adjustment_rate":
                s["adjustment_rate"],
            "smooth_degradation":
                s["degradation"],
            "relative_rate_gap":
                rate_gap,
            "relative_dc_gain_gap":
                gain_gap,
            "transfer_distance":
                distance,
        }

        if best is None or (
            row["transfer_distance"]
            < best["transfer_distance"]
        ):
            best = row

    nearest_rows.append(best)

REINFORCING_NEAREST_SMOOTH = (
    pd.DataFrame(nearest_rows)
    .sort_values("transfer_distance")
    .reset_index(drop=True)
)

print("\nReinforcing estable → smooth más cercano:")
display(
    REINFORCING_NEAREST_SMOOTH.head(12)
)

# Comparación de las verdades G4 con la clase rival.
truth_transfer_rows = []

for case_id, spec in WORLD_CASES.items():
    p = spec["primitive"]
    t = spec["truth"]

    if p == "smooth_delay":
        pole = float(t["adjustment_rate"])
        dc = float(t["degradation"])
        rival = stable_r.copy()

        rival["distance"] = np.sqrt(
            (
                (rival["pole_rate"] - pole)
                / np.maximum(
                    np.maximum(
                        rival["pole_rate"].abs(),
                        abs(pole),
                    ),
                    1e-9,
                )
            ) ** 2
            +
            (
                (rival["dc_gain"] - dc)
                / np.maximum(
                    np.maximum(
                        rival["dc_gain"].abs(),
                        abs(dc),
                    ),
                    1e-9,
                )
            ) ** 2
        )

        b = rival.sort_values(
            "distance"
        ).iloc[0]

        truth_transfer_rows.append({
            "case_id": case_id,
            "true_primitive": p,
            "truth_pole_rate": pole,
            "truth_dc_gain": dc,
            "nearest_rival": "reinforcing",
            "nearest_rival_pole":
                b["pole_rate"],
            "nearest_rival_dc_gain":
                b["dc_gain"],
            "transfer_distance":
                b["distance"],
        })

    elif p == "reinforcing":
        damping = float(
            t["leak_rate"]
            - t["feedback_gain"]
        )

        if damping <= 0:
            continue

        pole = damping
        dc = float(
            t["drive_rate"]
            * t["degradation"]
            / damping
        )

        rival = SMOOTH_TRANSFER.copy()

        rival["distance"] = np.sqrt(
            (
                (rival["pole_rate"] - pole)
                / np.maximum(
                    np.maximum(
                        rival["pole_rate"].abs(),
                        abs(pole),
                    ),
                    1e-9,
                )
            ) ** 2
            +
            (
                (rival["dc_gain"] - dc)
                / np.maximum(
                    np.maximum(
                        rival["dc_gain"].abs(),
                        abs(dc),
                    ),
                    1e-9,
                )
            ) ** 2
        )

        b = rival.sort_values(
            "distance"
        ).iloc[0]

        truth_transfer_rows.append({
            "case_id": case_id,
            "true_primitive": p,
            "truth_pole_rate": pole,
            "truth_dc_gain": dc,
            "nearest_rival": "smooth_delay",
            "nearest_rival_pole":
                b["pole_rate"],
            "nearest_rival_dc_gain":
                b["dc_gain"],
            "transfer_distance":
                b["distance"],
        })

TRUTH_TRANSFER_OVERLAP = pd.DataFrame(
    truth_transfer_rows
)

print("\nVerdades smooth/reinforcing → clase rival más cercana:")
display(TRUTH_TRANSFER_OVERLAP)


# ---- Original C0.0 SD5-A1 code cell 17 ----
ALL_WORLD_OBSERVATIONS = {}

for case_id, spec in WORLD_CASES.items():
    case_obs = {}

    base_df, _ = simulate_world_case(
        spec["primitive"],
        world_truth=spec["truth"],
    )
    case_obs["__base__"] = (
        base_df[OBSERVED_COLUMNS].copy()
    )

    for probe_name, cfg in {
        **PROBE_LIBRARY,
        **DIRECTED_PROBE_LIBRARY,
    }.items():
        df, _ = simulate_world_case(
            spec["primitive"],
            world_truth=spec["truth"],
            params=cfg.get("params"),
            capacity_mode=cfg.get(
                "capacity_mode", "constant"
            ),
            stress_start=cfg.get(
                "stress_start", 8.0
            ),
            stress_end=cfg.get(
                "stress_end", 14.0
            ),
            stress_capacity=cfg.get(
                "stress_capacity", 80.0
            ),
        )

        case_obs[probe_name] = (
            df[OBSERVED_COLUMNS].copy()
        )

    ALL_WORLD_OBSERVATIONS[case_id] = case_obs

print(
    "WORLD × regímenes:",
    len(ALL_WORLD_OBSERVATIONS),
    "×",
    len(next(iter(
        ALL_WORLD_OBSERVATIONS.values()
    ))),
)


# ---- Original C0.0 SD5-A1 code cell 19 ----
ALL_PROBE_SEPARABILITY_ROWS = []
ALL_PROBE_HYPOTHESIS_SCORES = {}

for case_id, result in GENERALIZATION_RESULTS.items():
    obs = ALL_WORLD_OBSERVATIONS[case_id]
    cache = result["probe_prediction_cache"]
    plausible = result["version_space"]
    meta = result["hypothesis_meta"]
    best_generated = result["best_generated"]

    hypothesis_rows = []

    for h_id in plausible:
        scores = []

        # Base completo.
        base_pred = best_generated[h_id][
            "pred_base"
        ]
        base_score, _ = score_against(
            obs["__base__"],
            base_pred,
        )
        scores.append(base_score)

        # Todos los probes ya preregistrados.
        for probe_name in {
            **PROBE_LIBRARY,
            **DIRECTED_PROBE_LIBRARY,
        }:
            key = (probe_name, h_id)

            if key not in cache:
                continue

            s, _ = score_against(
                obs[probe_name],
                cache[key],
            )
            scores.append(s)

        hypothesis_rows.append({
            "hypothesis_id": h_id,
            "primitive":
                meta[h_id]["primitive"],
            "feature_id":
                meta[h_id]["feature_id"],
            "mean_all_regimes":
                float(np.mean(scores)),
            "worst_all_regimes":
                float(np.max(scores)),
            "n_regimes":
                len(scores),
        })

    hdf = (
        pd.DataFrame(hypothesis_rows)
        .sort_values(
            [
                "mean_all_regimes",
                "worst_all_regimes",
            ]
        )
        .reset_index(drop=True)
    )

    ALL_PROBE_HYPOTHESIS_SCORES[
        case_id
    ] = hdf

    by_primitive = (
        hdf
        .sort_values(
            [
                "mean_all_regimes",
                "worst_all_regimes",
            ]
        )
        .groupby(
            "primitive",
            as_index=False,
        )
        .first()
        .sort_values("mean_all_regimes")
        .reset_index(drop=True)
    )

    true_p = result["true_primitive"]

    true_row = by_primitive[
        by_primitive["primitive"] == true_p
    ]

    rival_rows = by_primitive[
        by_primitive["primitive"] != true_p
    ]

    if len(true_row) == 0:
        true_score = np.nan
        true_h = None
    else:
        true_score = float(
            true_row.iloc[0][
                "mean_all_regimes"
            ]
        )
        true_h = true_row.iloc[0][
            "hypothesis_id"
        ]

    if len(rival_rows) == 0:
        rival_score = np.nan
        rival_p = None
        rival_h = None
    else:
        b = rival_rows.iloc[0]
        rival_score = float(
            b["mean_all_regimes"]
        )
        rival_p = b["primitive"]
        rival_h = b["hypothesis_id"]

    class_gap = (
        (rival_score - true_score)
        / rival_score
        if (
            np.isfinite(true_score)
            and np.isfinite(rival_score)
            and rival_score > 0
        )
        else np.nan
    )

    ALL_PROBE_SEPARABILITY_ROWS.append({
        "case_id": case_id,
        "true_primitive": true_p,
        "true_best_hypothesis": true_h,
        "true_score": true_score,
        "best_rival_primitive": rival_p,
        "best_rival_hypothesis": rival_h,
        "best_rival_score": rival_score,
        "class_gap_true_vs_best_rival":
            class_gap,
        "truth_class_is_best":
            (
                bool(
                    true_score
                    <= by_primitive[
                        "mean_all_regimes"
                    ].min()
                    + 1e-12
                )
                if np.isfinite(true_score)
                else False
            ),
    })

ALL_PROBE_SEPARABILITY = pd.DataFrame(
    ALL_PROBE_SEPARABILITY_ROWS
)

display(ALL_PROBE_SEPARABILITY)

print("\nResumen por clase:")
display(
    ALL_PROBE_SEPARABILITY
    .groupby("true_primitive")
    .agg(
        n=("case_id", "size"),
        truth_class_best=(
            "truth_class_is_best",
            "sum",
        ),
        median_class_gap=(
            "class_gap_true_vs_best_rival",
            "median",
        ),
        min_class_gap=(
            "class_gap_true_vs_best_rival",
            "min",
        ),
    )
)


# ---- Original C0.0 SD5-A1 code cell 21 ----
def affine_equivalence(a, b):
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)

    valid = (
        np.isfinite(x)
        & np.isfinite(y)
    )
    x = x[valid]
    y = y[valid]

    if len(x) < 5:
        return None

    sx = float(np.std(x))
    sy = float(np.std(y))

    if sx < 1e-12 or sy < 1e-12:
        return None

    corr = float(np.corrcoef(x, y)[0, 1])

    X = np.column_stack([
        np.ones(len(x)),
        x,
    ])

    beta, *_ = np.linalg.lstsq(
        X,
        y,
        rcond=None,
    )
    pred = X @ beta

    rmse = float(
        np.sqrt(
            np.mean((y - pred) ** 2)
        )
    )

    norm = max(
        float(np.std(y)),
        1e-12,
    )

    return {
        "corr": corr,
        "affine_rmse_norm":
            rmse / norm,
        "intercept": float(beta[0]),
        "slope": float(beta[1]),
    }

FEATURE_EQUIVALENCE_ROWS = []

for case_id, regimes in (
    ALL_WORLD_OBSERVATIONS.items()
):
    pieces = []

    for regime_name, df in regimes.items():
        part = pd.DataFrame(
            index=np.arange(len(df))
        )

        for e in EXPRESSIONS:
            fid = expression_id(e)
            part[fid] = (
                eval_expression_df(e, df)
                .reset_index(drop=True)
            )

        part["__regime__"] = regime_name
        pieces.append(part)

    feature_df = pd.concat(
        pieces,
        ignore_index=True,
    )

    ids = [
        c for c in feature_df.columns
        if c != "__regime__"
    ]

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a_id = ids[i]
            b_id = ids[j]

            eq = affine_equivalence(
                feature_df[a_id],
                feature_df[b_id],
            )

            if eq is None:
                continue

            if (
                abs(eq["corr"]) >= 0.9999
                and eq["affine_rmse_norm"]
                <= 0.01
            ):
                FEATURE_EQUIVALENCE_ROWS.append({
                    "case_id": case_id,
                    "feature_a": a_id,
                    "feature_b": b_id,
                    **eq,
                })

FEATURE_EQUIVALENCE = pd.DataFrame(
    FEATURE_EQUIVALENCE_ROWS
)

print(
    "Pares de features casi equivalentes:",
    len(FEATURE_EQUIVALENCE),
)

if len(FEATURE_EQUIVALENCE):
    display(
        FEATURE_EQUIVALENCE
        .sort_values(
            [
                "affine_rmse_norm",
                "case_id",
            ]
        )
        .head(60)
    )

# Inspección específica de W02.
W02_EQUIVALENCE = (
    FEATURE_EQUIVALENCE[
        (FEATURE_EQUIVALENCE["case_id"] == "W02")
        & (
            (
                FEATURE_EQUIVALENCE["feature_a"]
                == "ratio::fulfilled/nominal_capacity"
            )
            |
            (
                FEATURE_EQUIVALENCE["feature_b"]
                == "ratio::fulfilled/nominal_capacity"
            )
        )
    ]
    if len(FEATURE_EQUIVALENCE)
    else pd.DataFrame()
)

print("\nEquivalencias alrededor del winner de W02:")
display(W02_EQUIVALENCE)


# ---- Original C0.0 SD5-A1 code cell 23 ----
def expression_uses_target(e):
    return (
        e.get("x") == TARGET
        or e.get("y") == TARGET
    )

STATIC_TARGET_DEPENDENCY = pd.DataFrame([
    {
        "feature_id": expression_id(e),
        "kind": e["kind"],
        "uses_target_directly":
            expression_uses_target(e),
        "uses_fulfilled":
            (
                e.get("x") == "fulfilled"
                or e.get("y") == "fulfilled"
            ),
    }
    for e in EXPRESSIONS
])

print("Dependencia estática del target:")
display(
    STATIC_TARGET_DEPENDENCY[
        STATIC_TARGET_DEPENDENCY[
            "uses_target_directly"
        ]
    ]
)

PROXY_ROWS = []

for case_id, regimes in (
    ALL_WORLD_OBSERVATIONS.items()
):
    for regime_name, df in regimes.items():
        saturation = (
            (
                df["fulfilled"]
                - df["effective_capacity"]
            ).abs()
            <= 1e-9
        )

        sat_fraction = float(
            saturation.mean()
        )

        target_ratio = (
            df["effective_capacity"]
            / df["nominal_capacity"]
        )

        for e in EXPRESSIONS:
            fid = expression_id(e)
            feature = eval_expression_df(
                e,
                df,
            )

            eq_all = affine_equivalence(
                feature,
                target_ratio,
            )

            if saturation.sum() >= 5:
                eq_sat = affine_equivalence(
                    feature[saturation],
                    target_ratio[saturation],
                )

                sat_feature = (
                    feature[saturation]
                    .astype(float)
                )
                sat_target = (
                    target_ratio[saturation]
                    .astype(float)
                )

                valid_identity = (
                    sat_feature.notna()
                    & sat_target.notna()
                )

                if valid_identity.sum() >= 1:
                    direct_identity_rmse = float(
                        np.sqrt(
                            np.mean(
                                (
                                    sat_feature[
                                        valid_identity
                                    ].to_numpy()
                                    -
                                    sat_target[
                                        valid_identity
                                    ].to_numpy()
                                ) ** 2
                            )
                        )
                    )
                else:
                    direct_identity_rmse = np.nan
            else:
                eq_sat = None
                direct_identity_rmse = np.nan

            PROXY_ROWS.append({
                "case_id": case_id,
                "regime": regime_name,
                "feature_id": fid,
                "uses_target_directly":
                    expression_uses_target(e),
                "uses_fulfilled":
                    (
                        e.get("x")
                        == "fulfilled"
                        or e.get("y")
                        == "fulfilled"
                    ),
                "saturation_fraction":
                    sat_fraction,
                "corr_target_ratio_all":
                    (
                        eq_all["corr"]
                        if eq_all else np.nan
                    ),
                "affine_rmse_target_all":
                    (
                        eq_all[
                            "affine_rmse_norm"
                        ]
                        if eq_all else np.nan
                    ),
                "corr_target_ratio_saturated":
                    (
                        eq_sat["corr"]
                        if eq_sat else np.nan
                    ),
                "affine_rmse_target_saturated":
                    (
                        eq_sat[
                            "affine_rmse_norm"
                        ]
                        if eq_sat else np.nan
                    ),
                "direct_identity_rmse_saturated":
                    direct_identity_rmse,
            })

TARGET_PROXY_AUDIT = pd.DataFrame(
    PROXY_ROWS
)

W02_PROXY = TARGET_PROXY_AUDIT[
    (TARGET_PROXY_AUDIT["case_id"] == "W02")
    & (
        TARGET_PROXY_AUDIT["feature_id"]
        == "ratio::fulfilled/nominal_capacity"
    )
].copy()

print("\nW02 — fulfilled/nominal_capacity:")
display(W02_PROXY)

print("\nTop proxies sin target explícito, alta saturación:")
proxy_summary = (
    TARGET_PROXY_AUDIT[
        ~TARGET_PROXY_AUDIT[
            "uses_target_directly"
        ]
    ]
    .groupby("feature_id")
    .agg(
        mean_saturation=(
            "saturation_fraction",
            "mean",
        ),
        median_abs_corr_target=(
            "corr_target_ratio_all",
            lambda x: float(
                np.nanmedian(np.abs(x))
            ),
        ),
        median_affine_rmse=(
            "affine_rmse_target_all",
            "median",
        ),
        median_sat_abs_corr=(
            "corr_target_ratio_saturated",
            lambda x: float(
                np.nanmedian(np.abs(x))
            ),
        ),
        median_sat_affine_rmse=(
            "affine_rmse_target_saturated",
            "median",
        ),
        median_direct_identity_rmse_sat=(
            "direct_identity_rmse_saturated",
            "median",
        ),
    )
    .sort_values(
        [
            "median_sat_affine_rmse",
            "median_affine_rmse",
        ]
    )
)

display(proxy_summary.head(25))


# ---- Original C0.0 SD5-A1 code cell 25 ----
CLASS_SEPARATION_ROWS = []

for case_id, result in (
    GENERALIZATION_RESULTS.items()
):
    evidence = (
        result["multiregime"]
        [
            result["multiregime"][
                "hypothesis_id"
            ]
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

    winner = evidence.iloc[0]
    global_second = (
        evidence.iloc[1]
        if len(evidence) > 1
        else None
    )

    other_class = evidence[
        evidence["primitive"]
        != winner["primitive"]
    ]

    class_second = (
        other_class.iloc[0]
        if len(other_class)
        else None
    )

    winner_score = float(
        winner["mean_multiregime"]
    )

    global_second_score = (
        float(
            global_second[
                "mean_multiregime"
            ]
        )
        if global_second is not None
        else np.nan
    )

    class_second_score = (
        float(
            class_second[
                "mean_multiregime"
            ]
        )
        if class_second is not None
        else np.nan
    )

    sep_global = (
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

    sep_class = (
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

    CLASS_SEPARATION_ROWS.append({
        "case_id": case_id,
        "true_primitive":
            result["true_primitive"],
        "winner_hypothesis":
            winner["hypothesis_id"],
        "winner_primitive":
            winner["primitive"],
        "winner_feature":
            winner["feature_id"],
        "winner_score":
            winner_score,
        "global_second_hypothesis":
            (
                global_second[
                    "hypothesis_id"
                ]
                if global_second is not None
                else None
            ),
        "global_second_primitive":
            (
                global_second["primitive"]
                if global_second is not None
                else None
            ),
        "separation_global":
            sep_global,
        "best_other_class_hypothesis":
            (
                class_second[
                    "hypothesis_id"
                ]
                if class_second is not None
                else None
            ),
        "best_other_class_primitive":
            (
                class_second["primitive"]
                if class_second is not None
                else None
            ),
        "separation_class":
            sep_class,
        "winner_class_correct":
            (
                winner["primitive"]
                == result["true_primitive"]
            ),
        "winner_feature_true":
            (
                winner["feature_id"]
                == TRUE_DERIVED_ID
            ),
    })

CLASS_SEPARATION = pd.DataFrame(
    CLASS_SEPARATION_ROWS
)

display(CLASS_SEPARATION)

print("\nW02 y W04:")
display(
    CLASS_SEPARATION[
        CLASS_SEPARATION["case_id"]
        .isin(["W02", "W04"])
    ]
)


# ---- Original C0.0 SD5-A1 code cell 27 ----
PROBE_POWER_ROWS = []

for case_id, result in (
    GENERALIZATION_RESULTS.items()
):
    hdf = ALL_PROBE_HYPOTHESIS_SCORES[
        case_id
    ]

    # Mejor hipótesis por primitive usando todos los regímenes.
    leaders = (
        hdf
        .sort_values(
            [
                "mean_all_regimes",
                "worst_all_regimes",
            ]
        )
        .groupby(
            "primitive",
            as_index=False,
        )
        .first()
    )

    leader_ids = leaders[
        "hypothesis_id"
    ].tolist()

    for regime_name, obs in (
        ALL_WORLD_OBSERVATIONS[
            case_id
        ].items()
    ):
        scores = []

        for h_id in leader_ids:
            if regime_name == "__base__":
                pred = result[
                    "best_generated"
                ][h_id]["pred_base"]
            else:
                key = (regime_name, h_id)
                if key not in result[
                    "probe_prediction_cache"
                ]:
                    continue
                pred = result[
                    "probe_prediction_cache"
                ][key]

            s, _ = score_against(
                obs,
                pred,
            )
            scores.append(s)

        PROBE_POWER_ROWS.append({
            "case_id": case_id,
            "regime": regime_name,
            "n_class_leaders": len(scores),
            "score_range": (
                float(max(scores) - min(scores))
                if scores else np.nan
            ),
            "score_std": (
                float(np.std(scores))
                if scores else np.nan
            ),
        })

PROBE_POWER = pd.DataFrame(
    PROBE_POWER_ROWS
)

print("W02 / W04 — poder por régimen:")
display(
    PROBE_POWER[
        PROBE_POWER["case_id"]
        .isin(["W02", "W04"])
    ]
    .sort_values(
        ["case_id", "score_range"]
    )
)


# ---- Original C0.0 SD5-A1 code cell 29 ----
AUDIT_SUMMARY = {
    "n_worlds": len(WORLD_CASES),
    "n_expressions": len(EXPRESSIONS),
    "reinforcing_grid_stable_first_order": int(
        (
            REINFORCING_TRANSFER["regime"]
            == "stable_first_order"
        ).sum()
    ),
    "reinforcing_grid_net_reinforcing": int(
        (
            REINFORCING_TRANSFER["regime"]
            == "net_reinforcing"
        ).sum()
    ),
    "feature_equivalent_pairs": int(
        len(FEATURE_EQUIVALENCE)
    ),
    "direct_target_features": int(
        STATIC_TARGET_DEPENDENCY[
            "uses_target_directly"
        ].sum()
    ),
    "all_probe_truth_class_best": int(
        ALL_PROBE_SEPARABILITY[
            "truth_class_is_best"
        ].sum()
    ),
    "n_cases": int(
        len(ALL_PROBE_SEPARABILITY)
    ),
}

print("RESUMEN A1")
for k, v in AUDIT_SUMMARY.items():
    print(f"{k}: {v}")

print("\nNo hay veredicto PASS/FAIL en A1.")


# ---- Original C0.0 SD5-A1 code cell 31 ----
from pathlib import Path

EXPORT_DIR = Path(
    os.environ.get("CEI_A04_RESULTS_DIR", "results/A04")
)
EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SMOOTH_TRANSFER.to_csv(
    EXPORT_DIR / "smooth_transfer_grid.csv",
    index=False,
)
REINFORCING_TRANSFER.to_csv(
    EXPORT_DIR / "reinforcing_transfer_grid.csv",
    index=False,
)
REINFORCING_NEAREST_SMOOTH.to_csv(
    EXPORT_DIR
    / "reinforcing_nearest_smooth.csv",
    index=False,
)
TRUTH_TRANSFER_OVERLAP.to_csv(
    EXPORT_DIR
    / "truth_transfer_overlap.csv",
    index=False,
)
ALL_PROBE_SEPARABILITY.to_csv(
    EXPORT_DIR
    / "all_probe_class_separability.csv",
    index=False,
)
FEATURE_EQUIVALENCE.to_csv(
    EXPORT_DIR
    / "feature_equivalence_pairs.csv",
    index=False,
)
STATIC_TARGET_DEPENDENCY.to_csv(
    EXPORT_DIR
    / "static_target_dependency.csv",
    index=False,
)
TARGET_PROXY_AUDIT.to_csv(
    EXPORT_DIR
    / "target_proxy_audit.csv",
    index=False,
)
CLASS_SEPARATION.to_csv(
    EXPORT_DIR
    / "global_vs_class_separation.csv",
    index=False,
)
PROBE_POWER.to_csv(
    EXPORT_DIR
    / "probe_power.csv",
    index=False,
)

for case_id, hdf in (
    ALL_PROBE_HYPOTHESIS_SCORES.items()
):
    case_dir = EXPORT_DIR / case_id
    case_dir.mkdir(exist_ok=True)

    hdf.to_csv(
        case_dir
        / "all_probe_hypothesis_scores.csv",
        index=False,
    )

print("Exportado a:", EXPORT_DIR)
for p in sorted(EXPORT_DIR.iterdir()):
    print(" -", p.name)
