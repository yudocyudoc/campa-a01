#!/usr/bin/env python3
# CEI-A02: reproduction of the original CEI c0.0 notebook, not a new model.
# Original: https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_SD_Grafo_Colab.ipynb
# Source notebook Git blob: fc66a1c85031c62243d24c03965ec849391bb371
# Source transformations: omit Colab installation, presentation-only plot cells
# (2,9,14,29,33); redirect /content output into CEI_A02_RESULTS_DIR;
# provide display() print shim for the original notebook's tabular views.
# No model parameter, stock/flow equation, scenario, or gate was modified.
import os

def display(value):
    print(value)



# ---- Original c0.0 code cell 3 ----

import sys
import math
import json
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

import BPTK_Py
from BPTK_Py import Model
from BPTK_Py.sddsl import functions as sd

print("Python:", sys.version.split()[0])
print("BPTK-Py:", getattr(BPTK_Py, "__version__", "versión no expuesta"))
print("NetworkX:", nx.__version__)



# ---- Original c0.0 code cell 5 ----

DEFAULT_PARAMS = {
    "months": 24,
    "base_order_rate": 0.09,
    "market_shock_start": 8.0,
    "market_shock_orders": 25.0,
    "marketing_intensity": 1.0,
    "acquisition_per_marketing_unit": 8.0,
    "nominal_capacity": 115.0,
    "capacity_degradation": 0.025,
    "minimum_capacity_fraction": 0.40,
    "maintenance_threshold": 0.85,
    "maintenance_build_rate": 25.0,
    "maintenance_recovery_rate": 3.0,
    "cancel_rate": 0.06,
    "base_churn": 2.0,
    "customer_loss_per_cancel": 0.40,
    "price": 100.0,
    "variable_cost_per_order": 50.0,
    "fixed_cost": 4000.0,
    "marketing_cost_per_unit": 800.0,
    "capacity_cost_per_extra_unit": 10.0,
    "maintenance_cost_per_extra_recovery": 50.0,
    "collection_delay": 2.0,
    "regulatory_index": 1.0,
}

# Una sola ontología estructural para el grafo.
NODE_SPEC = {
    # Campo mercado
    "market_shock":             {"field": "mercado",     "kind": "exogenous", "observable": True},
    "regulatory_index":         {"field": "mercado",     "kind": "exogenous", "observable": True},

    # Campo comercial
    "marketing_intensity":      {"field": "comercial",   "kind": "control",   "observable": True},
    "customer_acquisition":     {"field": "comercial",   "kind": "flow",      "observable": True},
    "customer_base":            {"field": "comercial",   "kind": "stock",     "observable": True},
    "incoming_orders":          {"field": "comercial",   "kind": "converter", "observable": True},
    "churn":                    {"field": "comercial",   "kind": "flow",      "observable": True},

    # Campo operaciones
    "nominal_capacity":         {"field": "operaciones", "kind": "control",   "observable": True},
    "maintenance_recovery_rate":{"field": "operaciones", "kind": "control",   "observable": True},
    "effective_capacity":       {"field": "operaciones", "kind": "converter", "observable": True},
    "fulfilled":                {"field": "operaciones", "kind": "flow",      "observable": True},
    "utilization":              {"field": "operaciones", "kind": "converter", "observable": True},
    "maintenance_build":        {"field": "operaciones", "kind": "flow",      "observable": False},
    "maintenance_recovery":     {"field": "operaciones", "kind": "flow",      "observable": False},
    "maintenance_debt":         {"field": "operaciones", "kind": "stock",     "observable": False},
    "backlog":                  {"field": "operaciones", "kind": "stock",     "observable": True},
    "cancellations":            {"field": "operaciones", "kind": "flow",      "observable": True},
    "complaints":               {"field": "operaciones", "kind": "converter", "observable": True},

    # Campo finanzas
    "billed_revenue":           {"field": "finanzas",    "kind": "flow",      "observable": True},
    "receivables":              {"field": "finanzas",    "kind": "stock",     "observable": True},
    "collections":              {"field": "finanzas",    "kind": "flow",      "observable": True},
    "operating_cost":           {"field": "finanzas",    "kind": "flow",      "observable": True},
    "cash":                     {"field": "finanzas",    "kind": "stock",     "observable": True},
}

# Aristas de influencia del WORLD.
# sign: +1 amplifica / -1 reduce el destino, manteniendo lo demás constante.
# agent_belief=True indica que esta relación aparece en la representación directiva inicial.
EDGE_SPEC = [
    ("market_shock", "incoming_orders",          +1, "shock de mercado añade pedidos", False),
    ("customer_base", "incoming_orders",         +1, "más clientes generan más pedidos", True),

    ("marketing_intensity", "customer_acquisition", +1, "marketing adquiere clientes", True),
    ("customer_acquisition", "customer_base",    +1, "adquisición alimenta base de clientes", True),
    ("churn", "customer_base",                   -1, "churn reduce base de clientes", False),

    ("incoming_orders", "fulfilled",             +1, "pedidos disponibles pueden cumplirse", True),
    ("backlog", "fulfilled",                     +1, "backlog también demanda capacidad", False),
    ("effective_capacity", "fulfilled",           +1, "capacidad limita cumplimiento", False),
    ("nominal_capacity", "effective_capacity",   +1, "capacidad nominal eleva techo productivo", False),

    ("fulfilled", "utilization",                 +1, "más cumplimiento usa más capacidad", False),
    ("effective_capacity", "utilization",        -1, "más capacidad reduce presión relativa", False),
    ("utilization", "maintenance_build",         +1, "alta utilización acumula deuda de mantenimiento", False),
    ("maintenance_build", "maintenance_debt",    +1, "mantenimiento diferido aumenta deuda", False),
    ("maintenance_recovery_rate", "maintenance_recovery", +1, "esfuerzo de mantenimiento paga deuda", False),
    ("maintenance_recovery", "maintenance_debt", -1, "recuperación reduce deuda", False),
    ("maintenance_debt", "effective_capacity",   -1, "deuda degrada capacidad efectiva", False),

    ("incoming_orders", "backlog",               +1, "pedidos no cumplidos alimentan backlog", False),
    ("fulfilled", "backlog",                     -1, "cumplimiento drena backlog", False),
    ("backlog", "cancellations",                 +1, "espera acumulada produce cancelaciones", False),
    ("cancellations", "backlog",                 -1, "cancelaciones drenan backlog", False),
    ("cancellations", "churn",                   +1, "cancelaciones pierden clientes", False),

    ("backlog", "complaints",                    +1, "backlog aumenta quejas", False),
    ("maintenance_debt", "complaints",           +1, "degradación operativa aumenta quejas", False),

    ("fulfilled", "billed_revenue",              +1, "pedidos cumplidos se facturan", True),
    ("billed_revenue", "receivables",            +1, "facturación crea cuentas por cobrar", True),
    ("receivables", "collections",               +1, "cartera genera cobros con retardo", True),
    ("collections", "cash",                      +1, "cobros elevan caja", True),

    ("fulfilled", "operating_cost",              +1, "producir tiene costo variable", True),
    ("marketing_intensity", "operating_cost",    +1, "marketing tiene costo", False),
    ("nominal_capacity", "operating_cost",       +1, "capacidad adicional tiene costo", False),
    ("maintenance_recovery_rate", "operating_cost", +1, "mantenimiento adicional tiene costo", False),
    ("operating_cost", "cash",                   -1, "costos reducen caja", True),
]

# Creencia directiva adicional, plausible pero incorrecta:
# "más marketing aumenta caja" como vínculo directo.
AGENT_FALSE_EDGES = [
    ("marketing_intensity", "cash", +1, "más marketing → más ventas → más caja")
]

len(NODE_SPEC), len(EDGE_SPEC)



# ---- Original c0.0 code cell 6 ----

def build_world(params=None):
    p = DEFAULT_PARAMS.copy()
    if params:
        p.update(params)

    model = Model(
        starttime=0.0,
        stoptime=float(p["months"]),
        dt=1.0,
        name="cei_c00_world"
    )

    # -----------------
    # Stocks
    # -----------------
    customer_base = model.stock("customer_base")
    backlog = model.stock("backlog")
    maintenance_debt = model.stock("maintenance_debt")
    receivables = model.stock("receivables")
    cash = model.stock("cash")

    customer_base.initial_value = 1000.0
    backlog.initial_value = 0.0
    maintenance_debt.initial_value = 0.0
    receivables.initial_value = 0.0
    cash.initial_value = 20000.0

    # -----------------
    # Constants / controls
    # -----------------
    def constant(name, value):
        c = model.constant(name)
        c.equation = float(value)
        return c

    base_order_rate = constant("base_order_rate", p["base_order_rate"])
    market_shock_start = constant("market_shock_start", p["market_shock_start"])
    market_shock_orders = constant("market_shock_orders", p["market_shock_orders"])

    marketing_intensity = constant("marketing_intensity", p["marketing_intensity"])
    acquisition_per_marketing_unit = constant(
        "acquisition_per_marketing_unit", p["acquisition_per_marketing_unit"]
    )

    nominal_capacity = constant("nominal_capacity", p["nominal_capacity"])
    capacity_degradation = constant("capacity_degradation", p["capacity_degradation"])
    minimum_capacity_fraction = constant(
        "minimum_capacity_fraction", p["minimum_capacity_fraction"]
    )
    maintenance_threshold = constant("maintenance_threshold", p["maintenance_threshold"])
    maintenance_build_rate = constant("maintenance_build_rate", p["maintenance_build_rate"])
    maintenance_recovery_rate = constant(
        "maintenance_recovery_rate", p["maintenance_recovery_rate"]
    )

    cancel_rate = constant("cancel_rate", p["cancel_rate"])
    base_churn = constant("base_churn", p["base_churn"])
    customer_loss_per_cancel = constant(
        "customer_loss_per_cancel", p["customer_loss_per_cancel"]
    )

    price = constant("price", p["price"])
    variable_cost_per_order = constant(
        "variable_cost_per_order", p["variable_cost_per_order"]
    )
    fixed_cost = constant("fixed_cost", p["fixed_cost"])
    marketing_cost_per_unit = constant(
        "marketing_cost_per_unit", p["marketing_cost_per_unit"]
    )
    capacity_cost_per_extra_unit = constant(
        "capacity_cost_per_extra_unit", p["capacity_cost_per_extra_unit"]
    )
    maintenance_cost_per_extra_recovery = constant(
        "maintenance_cost_per_extra_recovery", p["maintenance_cost_per_extra_recovery"]
    )
    collection_delay = constant("collection_delay", p["collection_delay"])

    regulatory_index = constant("regulatory_index", p["regulatory_index"])

    # -----------------
    # Converters / flows
    # -----------------
    market_shock = model.converter("market_shock")
    market_shock.equation = sd.If(
        sd.time() >= market_shock_start,
        market_shock_orders,
        0.0
    )

    customer_acquisition = model.flow("customer_acquisition")
    customer_acquisition.equation = (
        acquisition_per_marketing_unit * marketing_intensity
    )

    incoming_orders = model.converter("incoming_orders")
    incoming_orders.equation = (
        customer_base * base_order_rate + market_shock
    )

    effective_capacity = model.converter("effective_capacity")
    raw_capacity_fraction = 1.0 - maintenance_debt * capacity_degradation
    effective_capacity.equation = sd.If(
        raw_capacity_fraction > minimum_capacity_fraction,
        nominal_capacity * raw_capacity_fraction,
        nominal_capacity * minimum_capacity_fraction
    )

    fulfilled = model.flow("fulfilled")
    total_demand_to_serve = backlog + incoming_orders
    fulfilled.equation = sd.If(
        total_demand_to_serve < effective_capacity,
        total_demand_to_serve,
        effective_capacity
    )

    utilization = model.converter("utilization")
    utilization.equation = fulfilled / effective_capacity

    maintenance_build = model.flow("maintenance_build")
    maintenance_build.equation = sd.If(
        utilization > maintenance_threshold,
        (utilization - maintenance_threshold) * maintenance_build_rate,
        0.0
    )

    maintenance_recovery = model.flow("maintenance_recovery")
    maintenance_recovery.equation = sd.If(
        maintenance_debt > maintenance_recovery_rate,
        maintenance_recovery_rate,
        maintenance_debt
    )

    cancellations = model.flow("cancellations")
    cancellations.equation = backlog * cancel_rate

    churn = model.flow("churn")
    churn.equation = base_churn + cancellations * customer_loss_per_cancel

    complaints = model.converter("complaints")
    complaints.equation = backlog / 20.0 + maintenance_debt / 10.0

    billed_revenue = model.flow("billed_revenue")
    billed_revenue.equation = fulfilled * price

    collections = model.flow("collections")
    collections.equation = receivables / collection_delay

    extra_capacity_cost = model.converter("extra_capacity_cost")
    extra_capacity_cost.equation = sd.If(
        nominal_capacity > DEFAULT_PARAMS["nominal_capacity"],
        (nominal_capacity - DEFAULT_PARAMS["nominal_capacity"]) * capacity_cost_per_extra_unit,
        0.0
    )

    extra_maintenance_cost = model.converter("extra_maintenance_cost")
    extra_maintenance_cost.equation = sd.If(
        maintenance_recovery_rate > DEFAULT_PARAMS["maintenance_recovery_rate"],
        (maintenance_recovery_rate - DEFAULT_PARAMS["maintenance_recovery_rate"])
        * maintenance_cost_per_extra_recovery,
        0.0
    )

    operating_cost = model.flow("operating_cost")
    operating_cost.equation = (
        fixed_cost
        + fulfilled * variable_cost_per_order
        + marketing_intensity * marketing_cost_per_unit
        + extra_capacity_cost
        + extra_maintenance_cost
    )

    # -----------------
    # Stock equations
    # -----------------
    customer_base.equation = customer_acquisition - churn
    backlog.equation = incoming_orders - fulfilled - cancellations
    maintenance_debt.equation = maintenance_build - maintenance_recovery
    receivables.equation = billed_revenue - collections
    cash.equation = collections - operating_cost

    return model



# ---- Original c0.0 code cell 8 ----

EQUATIONS = [
    "customer_base",
    "customer_acquisition",
    "market_shock",
    "incoming_orders",
    "effective_capacity",
    "fulfilled",
    "utilization",
    "maintenance_build",
    "maintenance_recovery",
    "maintenance_debt",
    "backlog",
    "cancellations",
    "churn",
    "complaints",
    "billed_revenue",
    "receivables",
    "collections",
    "operating_cost",
    "cash",
    "marketing_intensity",
    "nominal_capacity",
    "maintenance_recovery_rate",
    "regulatory_index",
]

def simulate(overrides=None, backend="rust"):
    model = build_world(overrides)
    bptk = BPTK_Py.bptk()
    bptk.register_scenario_manager({"c00": {"model": model}})
    bptk.register_scenarios(scenarios={"base": {}}, scenario_manager="c00")

    try:
        df = bptk.run_scenarios(
            scenario_managers=["c00"],
            scenarios=["base"],
            equations=EQUATIONS,
            backend=backend,
        )
        engine = backend
    except Exception as exc:
        if backend != "rust":
            raise
        print("Rust no pudo ejecutar este modelo; reintentando con backend Python.")
        print("Motivo:", exc)
        model = build_world(overrides)
        bptk = BPTK_Py.bptk()
        bptk.register_scenario_manager({"c00": {"model": model}})
        bptk.register_scenarios(scenarios={"base": {}}, scenario_manager="c00")
        df = bptk.run_scenarios(
            scenario_managers=["c00"],
            scenarios=["base"],
            equations=EQUATIONS,
            backend="python",
        )
        engine = "python"

    return df, engine

baseline, engine = simulate()
print("Backend usado:", engine)
baseline.tail()



# ---- Original c0.0 code cell 11 ----

pre = baseline.loc[baseline.index < DEFAULT_PARAMS["market_shock_start"]]
post = baseline.loc[baseline.index >= DEFAULT_PARAMS["market_shock_start"]]

gate_a = {
    "backlog_final_mayor_que_inicial": float(baseline["backlog"].iloc[-1]) > float(baseline["backlog"].iloc[0]),
    "maintenance_debt_final_positiva": float(baseline["maintenance_debt"].iloc[-1]) > 0,
    "effective_capacity_final_menor_nominal": float(baseline["effective_capacity"].iloc[-1]) < DEFAULT_PARAMS["nominal_capacity"],
    "cash_final_menor_inicial": float(baseline["cash"].iloc[-1]) < float(baseline["cash"].iloc[0]),
}
pd.Series(gate_a, name="C0.0-A")



# ---- Original c0.0 code cell 13 ----

def build_true_graph():
    G = nx.DiGraph()

    for node, attrs in NODE_SPEC.items():
        G.add_node(node, **attrs)

    for source, target, sign, mechanism, agent_belief in EDGE_SPEC:
        G.add_edge(
            source,
            target,
            sign=sign,
            mechanism=mechanism,
            agent_belief=agent_belief,
        )
    return G

G_TRUE = build_true_graph()

print("Nodos:", G_TRUE.number_of_nodes())
print("Aristas:", G_TRUE.number_of_edges())
print("Componentes débilmente conectados:", nx.number_weakly_connected_components(G_TRUE))



# ---- Original c0.0 code cell 16 ----

FOCAL_TARGET = "cash"

# 4.1 Componentes y nodos que no tienen ruta al objetivo.
components = list(nx.weakly_connected_components(G_TRUE))
disconnected_from_target = sorted(
    n for n in G_TRUE.nodes
    if n != FOCAL_TARGET and not nx.has_path(G_TRUE, n, FOCAL_TARGET)
)

print("Componentes:")
for i, component in enumerate(components, 1):
    print(i, sorted(component))

print("\nSin ruta hacia cash:")
print(disconnected_from_target)



# ---- Original c0.0 code cell 17 ----

# 4.2 Relaciones que cruzan campos.
cross_field_edges = []
for u, v, data in G_TRUE.edges(data=True):
    fu = G_TRUE.nodes[u]["field"]
    fv = G_TRUE.nodes[v]["field"]
    if fu != fv:
        cross_field_edges.append({
            "source": u,
            "source_field": fu,
            "target": v,
            "target_field": fv,
            "sign": data["sign"],
            "mechanism": data["mechanism"],
        })

pd.DataFrame(cross_field_edges)



# ---- Original c0.0 code cell 18 ----

# 4.3 Feedback loops: componentes fuertemente conectados de tamaño > 1.
feedback_components = [
    sorted(component)
    for component in nx.strongly_connected_components(G_TRUE)
    if len(component) > 1
]

print("Loops / componentes de feedback:")
for loop in feedback_components:
    print(" -", " → ".join(loop))



# ---- Original c0.0 code cell 19 ----

# 4.4 Subgrafo causal que sí puede alcanzar el objetivo focal.
ancestors = nx.ancestors(G_TRUE, FOCAL_TARGET)
target_subgraph = G_TRUE.subgraph(ancestors | {FOCAL_TARGET}).copy()

# Puentes estructurales aproximados:
# articulation points sobre la proyección no dirigida del subgrafo que llega a cash.
undirected_target = target_subgraph.to_undirected()
articulation = sorted(nx.articulation_points(undirected_target))

# Centralidad de intermediación.
betweenness = nx.betweenness_centrality(target_subgraph)
betweenness_rank = (
    pd.Series(betweenness, name="betweenness")
      .sort_values(ascending=False)
      .to_frame()
)

print("Nodos puente aproximados hacia cash:")
print(articulation)

betweenness_rank.head(12)



# ---- Original c0.0 code cell 20 ----

# 4.5 Rutas de propagación útiles para explicar mecanismos.
def show_paths(source, target=FOCAL_TARGET, cutoff=10, max_paths=12):
    if source not in G_TRUE or target not in G_TRUE:
        return []
    if not nx.has_path(G_TRUE, source, target):
        return []

    paths = list(nx.all_simple_paths(G_TRUE, source=source, target=target, cutoff=cutoff))
    paths = sorted(paths, key=len)[:max_paths]
    return paths

for source in ["market_shock", "marketing_intensity", "maintenance_debt", "backlog"]:
    print(f"\n{source} → {FOCAL_TARGET}")
    paths = show_paths(source)
    if not paths:
        print("  sin ruta")
    for path in paths:
        print("  ", " → ".join(path))



# ---- Original c0.0 code cell 22 ----

def build_agent_graph():
    G = nx.DiGraph()

    for node, attrs in NODE_SPEC.items():
        G.add_node(node, **attrs)

    for source, target, sign, mechanism, agent_belief in EDGE_SPEC:
        if agent_belief:
            G.add_edge(source, target, sign=sign, mechanism=mechanism, belief_type="declared")

    for source, target, sign, mechanism in AGENT_FALSE_EDGES:
        G.add_edge(source, target, sign=sign, mechanism=mechanism, belief_type="false_summary")

    return G

G_AGENT = build_agent_graph()

true_edges = set(G_TRUE.edges())
agent_edges = set(G_AGENT.edges())

missing_in_agent = sorted(true_edges - agent_edges)
false_in_agent = sorted(agent_edges - true_edges)

print("Relaciones reales ausentes de la representación:", len(missing_in_agent))
print("Relaciones de la representación que no existen en WORLD:", false_in_agent)



# ---- Original c0.0 code cell 24 ----

edge_bet = nx.edge_betweenness_centrality(target_subgraph)

rows = []
for u, v in missing_in_agent:
    if u not in target_subgraph or v not in target_subgraph:
        continue

    reaches_target = nx.has_path(G_TRUE, v, FOCAL_TARGET)
    path_len = nx.shortest_path_length(G_TRUE, v, FOCAL_TARGET) if reaches_target else np.inf

    # Alcance simple: más alto cuanto más cerca está del objetivo,
    # pero siempre > 0 si existe ruta.
    reach_score = 0.0 if not reaches_target else 1.0 / (1.0 + path_len)
    centrality = edge_bet.get((u, v), 0.0)

    rows.append({
        "source": u,
        "target": v,
        "source_field": G_TRUE.nodes[u]["field"],
        "target_field": G_TRUE.nodes[v]["field"],
        "mechanism": G_TRUE.edges[u, v]["mechanism"],
        "edge_betweenness": centrality,
        "distance_from_target": None if not reaches_target else path_len,
        "reach_score": reach_score,
        "representation_gap": 1.0,
        "priority_proxy": centrality * reach_score,
    })

cei_gap_table = (
    pd.DataFrame(rows)
      .sort_values(["priority_proxy", "edge_betweenness"], ascending=False)
      .reset_index(drop=True)
)

cei_gap_table.head(15)



# ---- Original c0.0 code cell 27 ----

SCENARIOS = {
    "baseline": {},
    "mas_marketing": {
        "marketing_intensity": 1.5,
    },
    "mas_capacidad": {
        "nominal_capacity": 145.0,
    },
    "mas_mantenimiento": {
        "maintenance_recovery_rate": 6.0,
    },
    "capacidad_mas_mantenimiento": {
        "nominal_capacity": 145.0,
        "maintenance_recovery_rate": 6.0,
    },
}

scenario_frames = {}
scenario_engines = {}

for name, overrides in SCENARIOS.items():
    frame, used_engine = simulate(overrides)
    scenario_frames[name] = frame
    scenario_engines[name] = used_engine

scenario_engines



# ---- Original c0.0 code cell 28 ----

summary_rows = []

for name, df in scenario_frames.items():
    summary_rows.append({
        "scenario": name,
        "cash_final": float(df["cash"].iloc[-1]),
        "backlog_final": float(df["backlog"].iloc[-1]),
        "complaints_final": float(df["complaints"].iloc[-1]),
        "maintenance_debt_final": float(df["maintenance_debt"].iloc[-1]),
        "effective_capacity_final": float(df["effective_capacity"].iloc[-1]),
        "customer_base_final": float(df["customer_base"].iloc[-1]),
        "fulfilled_final": float(df["fulfilled"].iloc[-1]),
    })

scenario_summary = pd.DataFrame(summary_rows).set_index("scenario")
scenario_summary



# ---- Original c0.0 code cell 31 ----

baseline_final = scenario_summary.loc["baseline"]
marketing_final = scenario_summary.loc["mas_marketing"]
capacity_final = scenario_summary.loc["mas_capacidad"]

gate_b = {
    "marketing_empeora_caja_vs_baseline":
        marketing_final["cash_final"] < baseline_final["cash_final"],

    "marketing_empeora_backlog_vs_baseline":
        marketing_final["backlog_final"] > baseline_final["backlog_final"],

    "capacidad_reduce_backlog_vs_baseline":
        capacity_final["backlog_final"] < baseline_final["backlog_final"],

    "capacidad_mejora_caja_vs_baseline":
        capacity_final["cash_final"] > baseline_final["cash_final"],
}

pd.Series(gate_b, name="C0.0-B")



# ---- Original c0.0 code cell 35 ----

checks = {}

checks.update({f"A_{k}": v for k, v in gate_a.items()})
checks.update({f"E_{k}": v for k, v in gate_b.items()})

checks["B_detecta_variable_desconectada"] = "regulatory_index" in disconnected_from_target
checks["B_detecta_feedback_loops"] = len(feedback_components) >= 1
checks["B_detecta_cross_field_edges"] = len(cross_field_edges) >= 1
checks["C_detecta_relaciones_omitidas"] = len(missing_in_agent) >= 1
checks["C_detecta_creencia_falsa"] = ("marketing_intensity", "cash") in false_in_agent
checks["D_hay_ruta_maintenance_a_cash"] = nx.has_path(G_TRUE, "maintenance_debt", "cash")

gate_df = pd.DataFrame({
    "check": list(checks.keys()),
    "pass": list(checks.values()),
})

display(gate_df)
print("\nC0.0:", "PASS" if gate_df["pass"].all() else "REVISAR")



# ---- Original c0.0 code cell 37 ----

from pathlib import Path

EXPORT_DIR = Path(os.environ.get("CEI_A02_RESULTS_DIR", "results/A02"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

baseline.to_csv(EXPORT_DIR / "baseline.csv")

scenario_summary.to_csv(EXPORT_DIR / "scenario_summary.csv")
cei_gap_table.to_csv(EXPORT_DIR / "cei_representation_gaps.csv", index=False)
gate_df.to_csv(EXPORT_DIR / "gate_c00.csv", index=False)

pd.DataFrame([
    {"node": n, **attrs}
    for n, attrs in G_TRUE.nodes(data=True)
]).to_csv(EXPORT_DIR / "graph_nodes.csv", index=False)

pd.DataFrame([
    {"source": u, "target": v, **attrs}
    for u, v, attrs in G_TRUE.edges(data=True)
]).to_csv(EXPORT_DIR / "graph_edges.csv", index=False)

nx.write_graphml(G_TRUE, EXPORT_DIR / "world_true.graphml")
nx.write_graphml(G_AGENT, EXPORT_DIR / "agent_representation.graphml")

print("Exportado a:", EXPORT_DIR)
for path in sorted(EXPORT_DIR.iterdir()):
    print(" -", path.name)

