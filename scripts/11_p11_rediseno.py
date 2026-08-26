"""
P11 — Rediseño acotado de la red UCuenca.

Objetivo:
Seleccionar como máximo cinco enlaces nuevos a partir del diagnóstico P10 y
compararlos contra dos alternativas ingenuas.

Propuesta diagnóstica (5 cambios):
1) CP-EADMINA1-D6 -- ROUTER-CAMPUS-PARAISO, 10 Gbps
2) CP-ODONTOLOGIA-D4 -- ROUTER-CAMPUS-PARAISO, 10 Gbps
3) DT-0A-C12 -- PE2-BALZAY, 20 Gbps
4) AGRPRI-1A-D10 -- INTERNET-MPLS, 10 Gbps
5) HOS-0A-D05 -- PE2-CENTRAL, 10 Gbps

Interpretación:
- Paraíso: dos uplinks alternativos desde agregación al router WAN secundario.
- Balzay: simetrizar el dual-homing de core hacia PE2.
- Yanuncay: segundo acceso MPLS que evita depender del router único.
- Hospitalidad: segundo camino WAN aguas arriba.

Dos líneas base de comparación:
A) "grado ingenuo": conectar el nodo de mayor grado con cinco nodos de alto
   grado con los que no tenía enlace.
B) "intermediación ingenua": hacer lo mismo usando el ranking de betweenness.

La percolación dirigida utilizada en P11 es la estrategia más severa de P8:
intermediación recalculada tras cada eliminación.

El modelo de capacidades reutiliza los supuestos de P6:
- capacidad explícita si existe;
- WAN/core/interconexión/agregación troncal: 10 Gbps;
- acceso-agregación / acceso-acceso: 1 Gbps;
- DT-0A-C12--PE2-BALZAY se fija en 20 Gbps para replicar el enlace existente
  DT-0A-C13--PE2-BALZAY ("2x10 Gbps").
"""

from pathlib import Path
import math

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TAB = ROOT / "resultados" / "tablas"
FIG = ROOT / "resultados" / "figuras"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

G0 = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodes_df = pd.read_csv(DATA / "red_ucuenca_nodes.csv")
edges_df = pd.read_csv(DATA / "red_ucuenca_edges.csv")

META = nodes_df.set_index("id")
N = G0.number_of_nodes()

assert N == 177
assert G0.number_of_edges() == 209
assert nx.is_connected(G0)

CAMPUS_FLOW = [
    "Campus Central",
    "Campus Balzay",
    "Campus Paraiso",
    "Campus Yanuncay",
    "Campus Hospitalidad",
]

# ================================================================
# 1. Diseños
# ================================================================
PROPOSAL = [
    ("CP-EADMINA1-D6", "ROUTER-CAMPUS-PARAISO", 10000),
    ("CP-ODONTOLOGIA-D4", "ROUTER-CAMPUS-PARAISO", 10000),
    ("DT-0A-C12", "PE2-BALZAY", 20000),
    ("AGRPRI-1A-D10", "INTERNET-MPLS", 10000),
    ("HOS-0A-D05", "PE2-CENTRAL", 10000),
]

def first_missing_pairs(order, k=5):
    result = []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            u, v = order[i], order[j]
            if not G0.has_edge(u, v):
                result.append((u, v, 10000))
                if len(result) == k:
                    return result
    return result


degree_order = [
    n for n, d in sorted(
        G0.degree(),
        key=lambda x: (-x[1], str(x[0]))
    )
]

bet = nx.betweenness_centrality(G0, normalized=True)
bet_order = [
    n for n, b in sorted(
        bet.items(),
        key=lambda x: (-x[1], str(x[0]))
    )
]

ALT_DEGREE = first_missing_pairs(degree_order, 5)
ALT_BETWEENNESS = first_missing_pairs(bet_order, 5)

DESIGNS = {
    "Base": [],
    "Propuesta diagnostica": PROPOSAL,
    "Alternativa grado ingenuo": ALT_DEGREE,
    "Alternativa intermediacion ingenua": ALT_BETWEENNESS,
}

# ================================================================
# 2. Capacidad base de P6
# ================================================================
def capacity_from_row(u, v, row):
    if pd.notna(row["capacidad_mbps"]):
        return float(row["capacidad_mbps"])

    cu = str(META.loc[u, "capa"])
    cv = str(META.loc[v, "capa"])
    rol = str(row["rol"])
    capas = {cu, cv}

    if rol in {"wan", "inferido"} or "wan" in capas:
        return 10000.0
    if "core" in capas or "interconexion" in capas:
        return 10000.0
    if capas == {"agregacion"}:
        return 10000.0
    if capas == {"agregacion", "acceso"}:
        return 1000.0
    if capas == {"acceso"}:
        return 1000.0

    return 1000.0


BASE_CAPACITY = {}

for _, row in edges_df.iterrows():
    u, v = row["source"], row["target"]
    BASE_CAPACITY[tuple(sorted((u, v)))] = capacity_from_row(
        u, v, row
    )

# ================================================================
# 3. Construcción de grafo modificado
# ================================================================
def build_design(interventions):
    G = G0.copy()
    new_capacity = {}

    for u, v, cap in interventions:
        if G.has_edge(u, v):
            raise ValueError(
                f"La intervención {u}--{v} ya existe en el grafo."
            )

        G.add_edge(
            u, v,
            nueva_intervencion=True,
            capacidad_mbps=cap
        )
        new_capacity[tuple(sorted((u, v)))] = float(cap)

    return G, new_capacity


# ================================================================
# 4. Métricas estructurales
# ================================================================
def global_efficiency(G):
    return nx.global_efficiency(G)


def adaptive_betweenness_percolation(G):
    """
    Ataque dirigido adaptativo: se recalcula la intermediación después de
    cada eliminación.

    S(f) = |GCC| / N_original.
    """
    H = G.copy()
    f_values = []
    S_values = []
    order = []

    for k in range(N + 1):
        if H.number_of_nodes() == 0:
            gcc = 0
        else:
            gcc = max(
                len(c) for c in nx.connected_components(H)
            )

        f_values.append(k / N)
        S_values.append(gcc / N)

        if k == N:
            break

        if H.number_of_nodes() == 1:
            chosen = next(iter(H.nodes()))
        else:
            b = nx.betweenness_centrality(
                H,
                normalized=True
            )
            chosen = min(
                H.nodes(),
                key=lambda n: (-b[n], str(n))
            )

        order.append(chosen)
        H.remove_node(chosen)

    f_values = np.asarray(f_values)
    S_values = np.asarray(S_values)

    auc = float(np.trapz(S_values, f_values))

    idx = np.flatnonzero(S_values <= 0.5)
    f50 = (
        float(f_values[idx[0]])
        if len(idx)
        else 1.0
    )

    # Valor más próximo a 5% y 10%.
    i5 = int(np.argmin(np.abs(f_values - 0.05)))
    i10 = int(np.argmin(np.abs(f_values - 0.10)))

    return {
        "f": f_values,
        "S": S_values,
        "orden": order,
        "AUC": auc,
        "f50": f50,
        "S_5pct": float(S_values[i5]),
        "S_10pct": float(S_values[i10]),
    }


# ================================================================
# 5. Flujo máximo por campus
# ================================================================
def max_flow_by_campus(G, new_capacity):
    DG = nx.DiGraph()

    for u, v in G.edges():
        key = tuple(sorted((u, v)))
        cap = new_capacity.get(
            key,
            BASE_CAPACITY.get(key, 10000.0)
        )

        # Enlace físico full-duplex modelado simétricamente.
        DG.add_edge(u, v, capacity=cap)
        DG.add_edge(v, u, capacity=cap)

    inf_cap = (
        sum(
            data["capacity"]
            for _, _, data in DG.edges(data=True)
        )
        + 1
    )

    values = {}

    for campus in CAMPUS_FLOW:
        H = DG.copy()
        source = f"SUPER::{campus}"
        H.add_node(source)

        access_nodes = nodes_df.loc[
            (nodes_df["campus"] == campus)
            & (nodes_df["capa"] == "acceso"),
            "id"
        ].tolist()

        for node in access_nodes:
            H.add_edge(
                source,
                node,
                capacity=inf_cap
            )

        flow_value, _ = nx.maximum_flow(
            H,
            source,
            "INTERNET-MPLS",
            flow_func=nx.algorithms.flow.edmonds_karp
        )

        values[campus] = float(flow_value)

    return values


# ================================================================
# 6. Evaluación completa
# ================================================================
metric_rows = []
flow_rows = []
percolation_curves = {}

for design_name, interventions in DESIGNS.items():
    print(f"Evaluando: {design_name}")

    G, new_capacity = build_design(interventions)

    bridges = list(nx.bridges(G))
    articulations = list(nx.articulation_points(G))
    distance = nx.average_shortest_path_length(G)
    efficiency = global_efficiency(G)

    perc = adaptive_betweenness_percolation(G)
    flows = max_flow_by_campus(G, new_capacity)

    percolation_curves[design_name] = perc

    metric_rows.append({
        "diseno": design_name,
        "puentes": len(bridges),
        "puntos_articulacion": len(articulations),
        "distancia_media": distance,
        "eficiencia_global": efficiency,
        "AUC_percolacion_adaptativa": perc["AUC"],
        "f50_percolacion_adaptativa": perc["f50"],
        "S_5pct": perc["S_5pct"],
        "S_10pct": perc["S_10pct"],
    })

    for campus, flow in flows.items():
        flow_rows.append({
            "diseno": design_name,
            "campus": campus,
            "flujo_maximo_mbps": flow,
        })

metrics_df = pd.DataFrame(metric_rows)
flows_df = pd.DataFrame(flow_rows)

metrics_df.to_csv(
    TAB / "01_metricas_todos_disenos.csv",
    index=False
)
flows_df.to_csv(
    TAB / "02_flujo_maximo_todos_disenos.csv",
    index=False
)

# ================================================================
# 7. Tabla antes / después / variación
# ================================================================
base = metrics_df[
    metrics_df["diseno"] == "Base"
].iloc[0]

proposal = metrics_df[
    metrics_df["diseno"] == "Propuesta diagnostica"
].iloc[0]

before_after_rows = []

for metric, label in [
    ("puentes", "Número de puentes"),
    ("puntos_articulacion", "Puntos de articulación"),
    ("distancia_media", "Distancia media [saltos]"),
    ("eficiencia_global", "Eficiencia global"),
    ("AUC_percolacion_adaptativa", "AUC S(f), ataque adaptativo"),
    ("f50_percolacion_adaptativa", "f50, ataque adaptativo"),
    ("S_5pct", "S(f) con 5% de nodos eliminados"),
]:
    before = float(base[metric])
    after = float(proposal[metric])
    delta = after - before

    pct = (
        100 * delta / before
        if before != 0
        else np.nan
    )

    before_after_rows.append({
        "metrica": label,
        "antes": before,
        "despues": after,
        "variacion_absoluta": delta,
        "variacion_porcentual": pct,
    })

before_after_df = pd.DataFrame(before_after_rows)
before_after_df.to_csv(
    TAB / "03_antes_despues_variacion.csv",
    index=False
)

# Flujos antes/después.
base_flows = flows_df[
    flows_df["diseno"] == "Base"
].set_index("campus")["flujo_maximo_mbps"]

proposal_flows = flows_df[
    flows_df["diseno"] == "Propuesta diagnostica"
].set_index("campus")["flujo_maximo_mbps"]

flow_change_rows = []

for campus in CAMPUS_FLOW:
    before = float(base_flows[campus])
    after = float(proposal_flows[campus])

    flow_change_rows.append({
        "campus": campus,
        "antes_mbps": before,
        "despues_mbps": after,
        "variacion_mbps": after - before,
        "variacion_pct": (
            100 * (after - before) / before
            if before > 0
            else np.nan
        )
    })

pd.DataFrame(flow_change_rows).to_csv(
    TAB / "04_flujo_antes_despues.csv",
    index=False
)

# ================================================================
# 8. Qué puentes y articulaciones desaparecen
# ================================================================
G_proposal, _ = build_design(PROPOSAL)

bridges_before = {
    tuple(sorted(e))
    for e in nx.bridges(G0)
}
bridges_after = {
    tuple(sorted(e))
    for e in nx.bridges(G_proposal)
}

art_before = set(nx.articulation_points(G0))
art_after = set(nx.articulation_points(G_proposal))

pd.DataFrame(
    sorted(bridges_before - bridges_after),
    columns=["u", "v"]
).to_csv(
    TAB / "05_puentes_eliminados_por_propuesta.csv",
    index=False
)

pd.DataFrame({
    "punto_articulacion_eliminado": sorted(
        art_before - art_after
    )
}).to_csv(
    TAB / "06_articulaciones_eliminadas.csv",
    index=False
)

# ================================================================
# 9. Tabla de intervenciones
# ================================================================
INTERVENTION_DESCRIPTION = [
    {
        "id": "I1",
        "u": "CP-EADMINA1-D6",
        "v": "ROUTER-CAMPUS-PARAISO",
        "capacidad_Gbps": 10,
        "problema": (
            "Crea una salida alternativa para una de las ramas más grandes "
            "de Paraíso y contribuye a eliminar la dependencia del enlace "
            "CPAR-C10--ROUTER-CAMPUS-HUAYNA-CAPAC."
        ),
        "factibilidad": (
            "Media-alta: conexión dentro de Paraíso hacia un router WAN ya "
            "existente; requiere fibra/ducto y puertos 10G."
        ),
    },
    {
        "id": "I2",
        "u": "CP-ODONTOLOGIA-D4",
        "v": "ROUTER-CAMPUS-PARAISO",
        "capacidad_Gbps": 10,
        "problema": (
            "Da un segundo bypass del core CPAR-C10 para otra rama importante "
            "y evita concentrar toda la mejora en un único edificio."
        ),
        "factibilidad": (
            "Media-alta: enlace intra-campus; condicionado por distancia real, "
            "ductería y disponibilidad de SFP+/puertos."
        ),
    },
    {
        "id": "I3",
        "u": "DT-0A-C12",
        "v": "PE2-BALZAY",
        "capacidad_Gbps": 20,
        "problema": (
            "Simetriza la salida de los dos cores de Balzay hacia PE2. "
            "Actualmente el enlace 2x10G directo está representado solo desde "
            "DT-0A-C13."
        ),
        "factibilidad": (
            "Alta si ambos equipos están en la misma infraestructura de "
            "data center/campus y existen dos puertos 10G disponibles."
        ),
    },
    {
        "id": "I4",
        "u": "AGRPRI-1A-D10",
        "v": "INTERNET-MPLS",
        "capacidad_Gbps": 10,
        "problema": (
            "Introduce un segundo uplink MPLS para Yanuncay y elimina al "
            "ROUTER-CAMPUS-YANUNCAY como punto de articulación."
        ),
        "factibilidad": (
            "Media: debe interpretarse como un segundo circuito hacia la nube "
            "MPLS/proveedor, no como un cable literal a Internet. Requiere "
            "diversidad de ruta para aportar redundancia real."
        ),
    },
    {
        "id": "I5",
        "u": "HOS-0A-D05",
        "v": "PE2-CENTRAL",
        "capacidad_Gbps": 10,
        "problema": (
            "Agrega un segundo camino WAN para Hospitalidad y elimina como "
            "puente el uplink HOS-0A-D05--INTERNET-MPLS."
        ),
        "factibilidad": (
            "Media: probable circuito metropolitano/MPLS adicional; debe "
            "evitar compartir la misma fibra/ducto del enlace actual."
        ),
    },
]

pd.DataFrame(INTERVENTION_DESCRIPTION).to_csv(
    TAB / "07_intervenciones_propuestas.csv",
    index=False
)

# Alternativas exactas.
alt_rows = []
for design_name in [
    "Alternativa grado ingenuo",
    "Alternativa intermediacion ingenua",
]:
    for i, (u, v, cap) in enumerate(
        DESIGNS[design_name],
        start=1
    ):
        alt_rows.append({
            "diseno": design_name,
            "enlace": i,
            "u": u,
            "v": v,
            "capacidad_mbps": cap,
        })

pd.DataFrame(alt_rows).to_csv(
    TAB / "08_enlaces_alternativas.csv",
    index=False
)

# ================================================================
# 10. Curvas de percolación
# ================================================================
curve_rows = []

for design_name, perc in percolation_curves.items():
    for f, S in zip(perc["f"], perc["S"]):
        curve_rows.append({
            "diseno": design_name,
            "f": f,
            "S": S,
        })

pd.DataFrame(curve_rows).to_csv(
    TAB / "09_curvas_percolacion_adaptativa.csv",
    index=False
)

# ================================================================
# 11. Figuras
# ================================================================
plt.figure(figsize=(9, 6))

for design_name, perc in percolation_curves.items():
    plt.plot(
        perc["f"],
        perc["S"],
        label=design_name
    )

plt.xlim(0, 0.20)
plt.xlabel("Fracción de nodos eliminados f")
plt.ylabel("S(f) = |GCC| / N original")
plt.title("Ataque adaptativo por intermediación — comparación de diseños")
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG / "01_percolacion_dirigida_comparacion.png",
    dpi=190
)
plt.close()

# Flujos.
pivot_flow = flows_df.pivot(
    index="campus",
    columns="diseno",
    values="flujo_maximo_mbps"
) / 1000.0

ax = pivot_flow.plot.bar(
    figsize=(10, 6)
)
ax.set_ylabel("Flujo máximo [Gbps]")
ax.set_xlabel("Campus")
ax.set_title("Flujo máximo por campus — diseños comparados")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(
    FIG / "02_flujo_maximo_comparacion.png",
    dpi=190
)
plt.close()

# Antes/después de métricas con mejora relativa orientada.
relative = pd.DataFrame({
    "Métrica": [
        "Puentes",
        "Articulaciones",
        "Distancia media",
        "Eficiencia",
        "AUC ataque adaptativo",
    ],
    "Antes": [
        base["puentes"],
        base["puntos_articulacion"],
        base["distancia_media"],
        base["eficiencia_global"],
        base["AUC_percolacion_adaptativa"],
    ],
    "Después": [
        proposal["puentes"],
        proposal["puntos_articulacion"],
        proposal["distancia_media"],
        proposal["eficiencia_global"],
        proposal["AUC_percolacion_adaptativa"],
    ],
})

relative.to_csv(
    TAB / "10_metricas_clave_figura.csv",
    index=False
)

# ================================================================
# 12. Consola
# ================================================================
print("\n=== PROPUESTA P11 ===")
for item in INTERVENTION_DESCRIPTION:
    print(
        f"{item['id']}: {item['u']} -- {item['v']} "
        f"({item['capacidad_Gbps']} Gbps)"
    )

print("\n=== ANTES / DESPUÉS ===")
print(before_after_df.to_string(index=False))

print("\n=== FLUJO MÁXIMO ===")
print(pd.DataFrame(flow_change_rows).to_string(index=False))

print("\n=== COMPARACIÓN DE DISEÑOS ===")
print(metrics_df.to_string(index=False))

print("\nPuentes que dejan de ser puentes:")
for e in sorted(bridges_before - bridges_after):
    print(" ", e)

print("\nPuntos que dejan de ser articulación:")
for n in sorted(art_before - art_after):
    print(" ", n)
