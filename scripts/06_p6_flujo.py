"""
P6 — Flujo máximo, corte mínimo y flujo de costo mínimo — Red UCuenca.

Adaptación metodológica del material del módulo:
- optimization/ford-fulkerson/ford_fulkerson.jl
- optimization/edmonds-karp/edmonds_karp.jl

El código docente usa:
1) una matriz de capacidades C;
2) una matriz de flujo antisimétrica F;
3) capacidad residual r(u,v) = C[u,v] - F[u,v];
4) DFS para Ford-Fulkerson clásico;
5) BFS para Edmonds-Karp;
6) el conjunto alcanzable desde s en la residual para obtener el corte mínimo.

La versión de este script conserva esa estructura, adaptada a Python y al grafo
UCuenca. NetworkX NO se usa para calcular los flujos máximos de P6; solo se usa
para cargar el grafo, identificar puentes y resolver el problema adicional de
flujo de costo mínimo.
"""

from pathlib import Path
from collections import deque
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

SINK = "INTERNET-MPLS"
CAMPUS = [
    "Campus Central",
    "Campus Balzay",
    "Campus Paraiso",
    "Campus Yanuncay",
    "Campus Hospitalidad",
]

# Demanda para P6.5. Se seleccionan Central y Balzay porque son las dos
# infraestructuras grandes con redundancia/WAN explícita en el caso de estudio.
MINCOST_DEMANDS = {
    "Campus Central": 5000,
    "Campus Balzay": 5000,
}

# Costos administrativos por unidad de flujo para P6.5.
# No representan latencia física; penalizan el uso de enlaces de contingencia.
ROLE_COST = {
    "principal": 1,
    "wan": 1,
    "inferido": 1,
    "secundario": 3,
    "respaldo": 6,
}

# ================================================================
# 1. Carga
# ================================================================
G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos = pd.read_csv(DATA / "red_ucuenca_nodes.csv")
aristas = pd.read_csv(DATA / "red_ucuenca_edges.csv")

assert G.number_of_nodes() == 177
assert G.number_of_edges() == 209
assert nx.is_connected(G)
assert SINK in G

meta = nodos.set_index("id")
bridges_original = {tuple(sorted(e)) for e in nx.bridges(G)}

# ================================================================
# 2. Función de capacidad c(u,v)
# ================================================================
def estimar_capacidad(u, v, row):
    """
    Capacidad en Mbps.

    Reglas:
    1) Si capacidad_mbps existe, se conserva sin modificar.
    2) Enlaces WAN/MPLS o inferidos hacia MPLS: 10 Gbps.
    3) Troncales: si al menos un extremo es core/interconexion, 10 Gbps.
    4) Agregacion-agregacion: 10 Gbps.
    5) Agregacion-acceso o acceso-acceso: 1 Gbps.
    6) Fallback: 1 Gbps.

    El atributo rol NO reduce la capacidad nominal por sí solo:
    respaldo/secundario describen función/redundancia, no una velocidad menor.
    """
    if pd.notna(row["capacidad_mbps"]):
        return int(round(float(row["capacidad_mbps"]))), "explicita"

    capa_u = str(meta.loc[u, "capa"])
    capa_v = str(meta.loc[v, "capa"])
    rol = str(row["rol"])
    capas = {capa_u, capa_v}

    if rol in {"wan", "inferido"} or "wan" in capas:
        return 10000, "estimada_10G_WAN_MPLS"

    if "core" in capas or "interconexion" in capas:
        return 10000, "estimada_10G_troncal"

    if capas == {"agregacion"}:
        return 10000, "estimada_10G_agregacion"

    if capas == {"agregacion", "acceso"}:
        return 1000, "estimada_1G_acceso_agregacion"

    if capas == {"acceso"}:
        return 1000, "estimada_1G_acceso"

    return 1000, "estimada_1G_fallback"


cap_rows = []
capacity = {}

for _, row in aristas.iterrows():
    u = row["source"]
    v = row["target"]
    c, fuente = estimar_capacidad(u, v, row)
    key = tuple(sorted((u, v)))
    capacity[key] = c

    cap_rows.append({
        "source": u,
        "target": v,
        "campus_u": meta.loc[u, "campus"],
        "campus_v": meta.loc[v, "campus"],
        "capa_u": meta.loc[u, "capa"],
        "capa_v": meta.loc[v, "capa"],
        "rol": row["rol"],
        "label": row["label"],
        "capacidad_original_mbps": row["capacidad_mbps"],
        "capacidad_modelo_mbps": c,
        "fuente_capacidad": fuente,
        "es_puente_P1": key in bridges_original,
    })

cap_df = pd.DataFrame(cap_rows)
cap_df.to_csv(TAB / "01_capacidades_completas.csv", index=False)

pd.DataFrame([
    {
        "regla": "Capacidad explícita",
        "supuesto": "Se conserva capacidad_mbps",
        "cantidad": int(cap_df["capacidad_original_mbps"].notna().sum()),
    },
    {
        "regla": "WAN/MPLS o rol inferido",
        "supuesto": "10 Gbps",
        "cantidad": int((cap_df["fuente_capacidad"] == "estimada_10G_WAN_MPLS").sum()),
    },
    {
        "regla": "Troncal core/interconexión",
        "supuesto": "10 Gbps",
        "cantidad": int((cap_df["fuente_capacidad"] == "estimada_10G_troncal").sum()),
    },
    {
        "regla": "Agregación-agregación",
        "supuesto": "10 Gbps",
        "cantidad": int((cap_df["fuente_capacidad"] == "estimada_10G_agregacion").sum()),
    },
    {
        "regla": "Acceso-agregación",
        "supuesto": "1 Gbps",
        "cantidad": int((cap_df["fuente_capacidad"] == "estimada_1G_acceso_agregacion").sum()),
    },
    {
        "regla": "Acceso-acceso",
        "supuesto": "1 Gbps",
        "cantidad": int((cap_df["fuente_capacidad"] == "estimada_1G_acceso").sum()),
    },
]).to_csv(TAB / "02_supuestos_capacidad.csv", index=False)

# ================================================================
# 3. Red de flujo por campus
# ================================================================
def construir_red_campus(campus):
    """
    Convierte el grafo físico no dirigido a una red dirigida simétrica.

    Cada enlace físico se modela con capacidad nominal c en ambos sentidos,
    interpretación compatible con enlaces Ethernet full-duplex para este
    experimento s->Internet.

    El super-nodo se conecta a TODOS los equipos de acceso del campus.
    Sus arcos reciben una capacidad suficientemente grande para que nunca
    constituyan el cuello de botella artificial.
    """
    source = f"SUPER_SOURCE::{campus}"
    base_nodes = list(G.nodes())
    names = base_nodes + [source]
    idx = {name: i for i, name in enumerate(names)}
    n = len(names)

    C = np.zeros((n, n), dtype=np.int64)

    for u, v in G.edges():
        c = capacity[tuple(sorted((u, v)))]
        iu, iv = idx[u], idx[v]
        C[iu, iv] = c
        C[iv, iu] = c

    accesos = nodos.loc[
        (nodos["campus"] == campus) & (nodos["capa"] == "acceso"),
        "id"
    ].tolist()

    assert accesos, f"No hay nodos de acceso en {campus}"

    # Mayor que cualquier flujo posible de la red física.
    inf_cap = int(sum(capacity.values()) + 1)

    for a in accesos:
        C[idx[source], idx[a]] = inf_cap

    return C, names, idx, source, accesos, inf_cap


# ================================================================
# 4. Adaptación Ford-Fulkerson / Edmonds-Karp
# ================================================================
def reconstruir(parent, s, t):
    path = [t]
    while path[-1] != s:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def buscar_dfs(C, F, s, t):
    """Camino aumentante DFS, Ford-Fulkerson clásico."""
    n = C.shape[0]
    parent = np.full(n, -1, dtype=int)
    parent[s] = s
    stack = [s]

    while stack:
        u = stack.pop()

        # Orden inverso: al apilar, se exploran antes índices pequeños.
        for v in range(n - 1, -1, -1):
            if parent[v] == -1 and C[u, v] - F[u, v] > 0:
                parent[v] = u
                if v == t:
                    return reconstruir(parent, s, t)
                stack.append(v)

    return []


def buscar_bfs(C, F, s, t):
    """Camino aumentante BFS, Edmonds-Karp."""
    n = C.shape[0]
    parent = np.full(n, -1, dtype=int)
    parent[s] = s
    q = deque([s])

    while q:
        u = q.popleft()

        for v in range(n):
            if parent[v] == -1 and C[u, v] - F[u, v] > 0:
                parent[v] = u
                if v == t:
                    return reconstruir(parent, s, t)
                q.append(v)

    return []


def max_flow_adaptado(C, s, t, method):
    """
    Adaptación directa de la estructura del código del módulo:
    F antisimétrica y residual C-F.
    """
    n = C.shape[0]
    F = np.zeros((n, n), dtype=np.int64)
    history = []
    total = 0

    search = buscar_dfs if method == "dfs" else buscar_bfs

    while True:
        path = search(C, F, s, t)
        if not path:
            break

        delta = min(
            int(C[path[i], path[i+1]] - F[path[i], path[i+1]])
            for i in range(len(path) - 1)
        )

        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            F[u, v] += delta
            F[v, u] -= delta

        total += delta
        history.append({
            "path": path.copy(),
            "delta": delta,
            "flow_total": total,
            "length": len(path) - 1,
        })

    return int(total), F, history


def corte_minimo(C, F, s):
    """
    S = nodos alcanzables desde s en la red residual.
    Arcos de S a V\\S con capacidad original positiva forman el corte.
    """
    n = C.shape[0]
    visited = np.zeros(n, dtype=bool)
    visited[s] = True
    q = deque([s])

    while q:
        u = q.popleft()
        for v in range(n):
            if not visited[v] and C[u, v] - F[u, v] > 0:
                visited[v] = True
                q.append(v)

    S = set(np.flatnonzero(visited).tolist())
    cut = []
    for u in S:
        for v in range(n):
            if v not in S and C[u, v] > 0:
                cut.append((u, v, int(C[u, v])))

    return S, cut


# ================================================================
# 5. Ejecutar flujo máximo por campus
# ================================================================
summary_rows = []
history_rows = []
cut_rows = []

for campus in CAMPUS:
    C, names, idx, source, accesos, inf_cap = construir_red_campus(campus)
    s, t = idx[source], idx[SINK]

    ff_value, ff_F, ff_hist = max_flow_adaptado(C, s, t, "dfs")
    ek_value, ek_F, ek_hist = max_flow_adaptado(C, s, t, "bfs")

    assert ff_value == ek_value

    # Edmonds-Karp: longitudes no decrecientes.
    ek_lengths = [h["length"] for h in ek_hist]
    assert all(
        ek_lengths[i] <= ek_lengths[i+1]
        for i in range(len(ek_lengths) - 1)
    )

    S, cut = corte_minimo(C, ek_F, s)
    cut_capacity = sum(c for _, _, c in cut)
    assert cut_capacity == ek_value

    # Ignorar arcos artificiales del super-source al interpretar el corte físico.
    physical_cut = [
        (u, v, c)
        for u, v, c in cut
        if names[u] != source and names[v] != source
    ]
    physical_cut_capacity = sum(c for _, _, c in physical_cut)

    # Por diseño el super-source no debe pertenecer al corte mínimo.
    assert physical_cut_capacity == ek_value

    summary_rows.append({
        "campus": campus,
        "n_accesos_fuente": len(accesos),
        "flujo_maximo_mbps": ek_value,
        "FF_iteraciones_DFS": len(ff_hist),
        "EK_iteraciones_BFS": len(ek_hist),
        "FF_longitudes": ", ".join(str(h["length"]) for h in ff_hist),
        "EK_longitudes": ", ".join(str(h["length"]) for h in ek_hist),
        "n_aristas_corte": len(physical_cut),
        "capacidad_corte_mbps": physical_cut_capacity,
    })

    for algorithm, hist in [("Ford-Fulkerson DFS", ff_hist), ("Edmonds-Karp BFS", ek_hist)]:
        for k, h in enumerate(hist, start=1):
            history_rows.append({
                "campus": campus,
                "algoritmo": algorithm,
                "iteracion": k,
                "longitud_camino": h["length"],
                "delta_mbps": h["delta"],
                "flujo_acumulado_mbps": h["flow_total"],
                "camino": " -> ".join(names[i] for i in h["path"]),
            })

    for u, v, c in physical_cut:
        nu, nv = names[u], names[v]
        key = tuple(sorted((nu, nv)))
        erow = cap_df[
            ((cap_df["source"] == nu) & (cap_df["target"] == nv))
            | ((cap_df["source"] == nv) & (cap_df["target"] == nu))
        ].iloc[0]

        cut_rows.append({
            "campus": campus,
            "desde_S": nu,
            "hacia_T": nv,
            "capacidad_mbps": c,
            "rol": erow["rol"],
            "capa_u": erow["capa_u"],
            "capa_v": erow["capa_v"],
            "campus_u": erow["campus_u"],
            "campus_v": erow["campus_v"],
            "label": erow["label"],
            "es_puente_P1": key in bridges_original,
        })

summary_df = pd.DataFrame(summary_rows)
history_df = pd.DataFrame(history_rows)
cuts_df = pd.DataFrame(cut_rows)

summary_df.to_csv(TAB / "03_resumen_flujo_por_campus.csv", index=False)
history_df.to_csv(TAB / "04_iteraciones_caminos_aumentantes.csv", index=False)
cuts_df.to_csv(TAB / "05_cortes_minimos_por_campus.csv", index=False)

# Resumen interpretación del corte.
cut_interp = (
    cuts_df.groupby("campus")
    .agg(
        aristas_corte=("capacidad_mbps", "size"),
        puentes_P1=("es_puente_P1", "sum"),
        capacidad_total=("capacidad_mbps", "sum"),
    )
    .reset_index()
)
cut_interp["fraccion_corte_que_es_puente"] = (
    cut_interp["puentes_P1"] / cut_interp["aristas_corte"]
)
cut_interp.to_csv(TAB / "06_comparacion_corte_vs_puentes.csv", index=False)

# ================================================================
# 6. Verificación manual de un corte mínimo
# ================================================================
# Elegimos Campus Central por ser la red de mayor tamaño.
manual_campus = "Campus Central"
manual_cut = cuts_df[cuts_df["campus"] == manual_campus].copy()
manual_cut["expresion"] = manual_cut.apply(
    lambda r: f"{r['desde_S']} -> {r['hacia_T']}: {int(r['capacidad_mbps'])} Mbps",
    axis=1
)
manual_cut.to_csv(TAB / "07_verificacion_manual_corte_central.csv", index=False)

manual_sum = int(manual_cut["capacidad_mbps"].sum())
expected = int(
    summary_df.loc[
        summary_df["campus"] == manual_campus, "flujo_maximo_mbps"
    ].iloc[0]
)
assert manual_sum == expected

# ================================================================
# 7. Flujo de costo mínimo desde dos campus
# ================================================================
def construir_min_cost_graph(demands):
    """
    Multi-source min-cost flow.

    Cada campus tiene su propio super-source con demanda negativa.
    INTERNET-MPLS recibe la demanda total positiva.

    Los enlaces físicos se representan en ambos sentidos.
    """
    D = nx.DiGraph()

    for n in G.nodes():
        D.add_node(n, demand=0)

    D.nodes[SINK]["demand"] = int(sum(demands.values()))

    for campus, demand in demands.items():
        s = f"MINCOST::{campus}"
        D.add_node(s, demand=-int(demand))

        accesos = nodos.loc[
            (nodos["campus"] == campus) & (nodos["capa"] == "acceso"),
            "id"
        ].tolist()

        inf_cap = int(sum(capacity.values()) + 1)
        for a in accesos:
            D.add_edge(s, a, capacity=inf_cap, weight=0, physical=False)

    for _, row in aristas.iterrows():
        u, v = row["source"], row["target"]
        c = capacity[tuple(sorted((u, v)))]
        role = str(row["rol"])
        cost = int(ROLE_COST.get(role, 1))

        D.add_edge(
            u, v,
            capacity=c,
            weight=cost,
            physical=True,
            role=role,
        )
        D.add_edge(
            v, u,
            capacity=c,
            weight=cost,
            physical=True,
            role=role,
        )

    return D


Dcost = construir_min_cost_graph(MINCOST_DEMANDS)
mincost_value, mincost_flow = nx.network_simplex(Dcost)

mincost_rows = []
role_flow = {}

for u, nbrs in mincost_flow.items():
    for v, f in nbrs.items():
        if f <= 0:
            continue

        attrs = Dcost[u][v]
        if not attrs.get("physical", False):
            continue

        role = attrs["role"]
        role_flow[role] = role_flow.get(role, 0) + f

        mincost_rows.append({
            "desde": u,
            "hacia": v,
            "flujo_mbps": int(f),
            "costo_unitario": int(attrs["weight"]),
            "costo_total_arco": int(f * attrs["weight"]),
            "rol": role,
            "capacidad_mbps": int(attrs["capacity"]),
        })

mincost_df = pd.DataFrame(mincost_rows)
mincost_df.to_csv(TAB / "08_flujo_costo_minimo_aristas.csv", index=False)

mincost_summary = pd.DataFrame([{
    "demanda_central_mbps": MINCOST_DEMANDS["Campus Central"],
    "demanda_balzay_mbps": MINCOST_DEMANDS["Campus Balzay"],
    "demanda_total_mbps": sum(MINCOST_DEMANDS.values()),
    "costo_total": int(mincost_value),
    "costo_medio_por_mbps": mincost_value / sum(MINCOST_DEMANDS.values()),
    "flujo_por_roles": "; ".join(f"{k}:{v}" for k, v in sorted(role_flow.items())),
}])
mincost_summary.to_csv(TAB / "09_resumen_flujo_costo_minimo.csv", index=False)


# Descomposición del flujo min-cost en caminos fuente -> INTERNET-MPLS.
# Esto es solo una descomposición de una solución de flujo; cuando varios flujos
# se mezclan en un nodo pueden existir otras descomposiciones equivalentes.
residual_flow = {
    u: {v: int(f) for v, f in nbrs.items() if f > 0}
    for u, nbrs in mincost_flow.items()
}

path_rows = []

for campus in MINCOST_DEMANDS:
    source = f"MINCOST::{campus}"
    remaining = MINCOST_DEMANDS[campus]
    path_id = 0

    while remaining > 0:
        # DFS sobre arcos con flujo positivo.
        parent = {source: None}
        stack = [source]

        while stack and SINK not in parent:
            u = stack.pop()
            for v, f in residual_flow.get(u, {}).items():
                if f > 0 and v not in parent:
                    parent[v] = u
                    stack.append(v)

        if SINK not in parent:
            raise RuntimeError(
                f"No se pudo descomponer todo el flujo de {campus}; "
                f"restante={remaining}"
            )

        path = [SINK]
        while path[-1] != source:
            path.append(parent[path[-1]])
        path.reverse()

        delta = min(
            residual_flow[path[i]][path[i+1]]
            for i in range(len(path)-1)
        )
        delta = min(delta, remaining)

        unit_cost = 0
        roles = []
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            residual_flow[u][v] -= delta
            attrs = Dcost[u][v]
            unit_cost += int(attrs["weight"])
            if attrs.get("physical", False):
                roles.append(str(attrs["role"]))

        remaining -= delta
        path_id += 1

        path_rows.append({
            "campus_origen": campus,
            "camino_id": path_id,
            "flujo_mbps": delta,
            "costo_unitario_camino": unit_cost,
            "costo_total_camino": delta * unit_cost,
            "saltos_fisicos": sum(
                1 for i in range(len(path)-1)
                if Dcost[path[i]][path[i+1]].get("physical", False)
            ),
            "roles": " -> ".join(roles),
            "camino": " -> ".join(path),
        })

mincost_paths_df = pd.DataFrame(path_rows)
mincost_paths_df.to_csv(
    TAB / "10_mincost_descomposicion_caminos.csv",
    index=False
)

# Flujo máximo puro combinado para los mismos dos campus.
def construir_red_multicampus(campuses):
    source = "SUPER_SOURCE::DOS_CAMPUS"
    names = list(G.nodes()) + [source]
    idx = {name: i for i, name in enumerate(names)}
    n = len(names)
    C = np.zeros((n, n), dtype=np.int64)

    for u, v in G.edges():
        c = capacity[tuple(sorted((u, v)))]
        C[idx[u], idx[v]] = c
        C[idx[v], idx[u]] = c

    inf_cap = int(sum(capacity.values()) + 1)

    for campus in campuses:
        accesos = nodos.loc[
            (nodos["campus"] == campus) & (nodos["capa"] == "acceso"),
            "id"
        ].tolist()
        for a in accesos:
            C[idx[source], idx[a]] = inf_cap

    return C, names, idx, source


C2, names2, idx2, source2 = construir_red_multicampus(list(MINCOST_DEMANDS))
max2, F2, hist2 = max_flow_adaptado(C2, idx2[source2], idx2[SINK], "bfs")

pd.DataFrame([{
    "campuses": " + ".join(MINCOST_DEMANDS.keys()),
    "flujo_maximo_puro_mbps": max2,
    "iteraciones_EK": len(hist2),
    "demanda_mincost_mbps": sum(MINCOST_DEMANDS.values()),
    "porcentaje_capacidad_usada_por_demanda": 100 * sum(MINCOST_DEMANDS.values()) / max2,
    "costo_minimo_total": int(mincost_value),
}]).to_csv(TAB / "11_comparacion_maxflow_mincost.csv", index=False)

# ================================================================
# 8. Figuras
# ================================================================
plt.figure(figsize=(9, 5))
x = np.arange(len(summary_df))
w = 0.35
plt.bar(x - w/2, summary_df["FF_iteraciones_DFS"], width=w, label="Ford-Fulkerson (DFS)")
plt.bar(x + w/2, summary_df["EK_iteraciones_BFS"], width=w, label="Edmonds-Karp (BFS)")
plt.xticks(x, summary_df["campus"], rotation=25, ha="right")
plt.ylabel("Número de iteraciones")
plt.title("Iteraciones de flujo máximo por campus")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "01_iteraciones_FF_EK_por_campus.png", dpi=180)
plt.close()

plt.figure(figsize=(9, 5))
plt.bar(summary_df["campus"], summary_df["flujo_maximo_mbps"] / 1000)
plt.ylabel("Flujo máximo (Gbps)")
plt.title("Flujo máximo hacia INTERNET-MPLS por campus")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(FIG / "02_flujo_maximo_por_campus.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
role_series = mincost_df.groupby("rol")["flujo_mbps"].sum().sort_values()
plt.barh(role_series.index, role_series.values / 1000)
plt.xlabel("Flujo agregado por arcos usados (Gbps)")
plt.ylabel("Rol del enlace")
plt.title("Flujo de costo mínimo según rol")
plt.tight_layout()
plt.savefig(FIG / "03_mincost_flujo_por_rol.png", dpi=180)
plt.close()

# ================================================================
# 9. Consola
# ================================================================
print("=== CAPACIDADES ===")
print(cap_df["fuente_capacidad"].value_counts().to_string())

print("\n=== FLUJO MÁXIMO POR CAMPUS ===")
print(summary_df.to_string(index=False))

print("\n=== CORTES MÍNIMOS ===")
for campus in CAMPUS:
    sub = cuts_df[cuts_df["campus"] == campus]
    print(f"\n{campus}:")
    for _, r in sub.iterrows():
        print(
            f"  {r['desde_S']} -> {r['hacia_T']} "
            f"{int(r['capacidad_mbps'])} Mbps "
            f"rol={r['rol']} puente_P1={r['es_puente_P1']}"
        )

print("\n=== VERIFICACIÓN MANUAL: CAMPUS CENTRAL ===")
for text in manual_cut["expresion"]:
    print(" +", text)
print(f" = {manual_sum} Mbps = flujo máximo")

print("\n=== FLUJO DE COSTO MÍNIMO ===")
print(mincost_summary.to_string(index=False))
print(f"Flujo máximo puro combinado Central+Balzay: {max2} Mbps")
print(f"Demanda fija min-cost: {sum(MINCOST_DEMANDS.values())} Mbps")
print(f"Costo mínimo total: {mincost_value}")

print(f"\nResultados guardados en {ROOT / 'resultados'}")
