"""
P5 — Caminos más cortos sobre la red UCuenca.

Se implementan desde cero:
- Dijkstra con cola de prioridad (heapq).
- Floyd–Warshall.

Se verifican ambos algoritmos sobre 20 pares aleatorios para los tres modelos
de peso definidos en el enunciado:
    w_saltos   = 1
    w_latencia = alpha + beta / c(u,v)
    w_carga    = b(u,v) / c(u,v)

Supuestos necesarios porque el dataset no contiene capacidad para 181 enlaces
ni tráfico para 39 enlaces:
- Capacidad explícita: se conserva.
- core–agregación, core–core, agregación–agregación y enlaces que involucren
  WAN/interconexión: 10 Gbps si no existe dato explícito.
- acceso–agregación y acceso–acceso: 1 Gbps si no existe dato explícito.
- Para tráfico faltante se usa la mediana de utilización b/c observada en los
  170 enlaces que sí tienen tráfico, aplicada a la capacidad estimada del enlace.
  Los enlaces de respaldo ya tienen tráfico 0 en el dataset y se conservan.
- alpha = 1 y beta = 1000 Mbps.
  Así, un enlace de 1 Gbps pesa 2.0; uno de 10 Gbps, 1.1; y uno de 20 Gbps, 1.05.
"""

from pathlib import Path
from collections import deque
import heapq
import math
import random
import time

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

SEED = 2026
ALPHA = 1.0
BETA = 1000.0  # Mbps
N_PARES_VERIFICACION = 20
SIZES_BENCHMARK = [25, 50, 75, 100, 125, 150, 177]

# ================================================================
# 1. Carga y construcción del grafo
# ================================================================
G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos = pd.read_csv(DATA / "red_ucuenca_nodes.csv")
aristas = pd.read_csv(DATA / "red_ucuenca_edges.csv")

assert G.number_of_nodes() == 177
assert G.number_of_edges() == 209
assert nx.is_connected(G)

meta = nodos.set_index("id")


def capas_de_arista(u, v):
    return tuple(sorted([str(meta.loc[u, "capa"]), str(meta.loc[v, "capa"])]))


def estimar_capacidad(u, v, capacidad_explicita):
    """
    Modelo de capacidad usado en P5 y reutilizable en P6.

    El informe declara 10 Gbps para troncales. Para enlaces de acceso,
    sin capacidad explícita, se asume 1 Gbps.
    """
    if pd.notna(capacidad_explicita):
        return float(capacidad_explicita), "explicita"

    cu = str(meta.loc[u, "capa"])
    cv = str(meta.loc[v, "capa"])
    capas = {cu, cv}

    if "wan" in capas or "interconexion" in capas:
        return 10000.0, "estimada_10G_WAN_interconexion"

    if "core" in capas:
        return 10000.0, "estimada_10G_troncal_core"

    if capas == {"agregacion"}:
        return 10000.0, "estimada_10G_agregacion"

    if capas == {"agregacion", "acceso"}:
        return 1000.0, "estimada_1G_acceso_agregacion"

    if capas == {"acceso"}:
        return 1000.0, "estimada_1G_acceso"

    # Fallback conservador/documentado.
    return 1000.0, "estimada_1G_fallback"


# Primera pasada: capacidad.
edge_rows = []
for _, r in aristas.iterrows():
    u, v = r["source"], r["target"]
    c_est, fuente_c = estimar_capacidad(u, v, r["capacidad_mbps"])

    edge_rows.append({
        "source": u,
        "target": v,
        "rol": r["rol"],
        "capa_u": meta.loc[u, "capa"],
        "capa_v": meta.loc[v, "capa"],
        "trafico_mbps_original": r["trafico_mbps"],
        "capacidad_mbps_original": r["capacidad_mbps"],
        "capacidad_mbps_modelo": c_est,
        "fuente_capacidad": fuente_c,
    })

modelo_df = pd.DataFrame(edge_rows)

# Mediana de utilización observada, usando la capacidad del modelo.
observadas = modelo_df["trafico_mbps_original"].notna()
util_observada = (
    modelo_df.loc[observadas, "trafico_mbps_original"]
    / modelo_df.loc[observadas, "capacidad_mbps_modelo"]
)
MEDIANA_UTILIZACION = float(util_observada.median())

# Segunda pasada: tráfico y pesos.
modelo_df["trafico_mbps_modelo"] = modelo_df["trafico_mbps_original"]
modelo_df["trafico_imputado"] = modelo_df["trafico_mbps_original"].isna()

modelo_df.loc[
    modelo_df["trafico_imputado"], "trafico_mbps_modelo"
] = (
    MEDIANA_UTILIZACION
    * modelo_df.loc[
        modelo_df["trafico_imputado"], "capacidad_mbps_modelo"
    ]
)

modelo_df["w_saltos"] = 1.0
modelo_df["w_latencia"] = (
    ALPHA + BETA / modelo_df["capacidad_mbps_modelo"]
)
modelo_df["w_carga"] = (
    modelo_df["trafico_mbps_modelo"]
    / modelo_df["capacidad_mbps_modelo"]
)

# Ningún peso puede ser negativo.
assert (modelo_df[["w_saltos", "w_latencia", "w_carga"]] >= 0).all().all()

# Añadir atributos al grafo.
for _, r in modelo_df.iterrows():
    u, v = r["source"], r["target"]
    for col in [
        "capacidad_mbps_modelo",
        "trafico_mbps_modelo",
        "w_saltos",
        "w_latencia",
        "w_carga",
    ]:
        G[u][v][col] = float(r[col])

modelo_df.to_csv(TAB / "01_modelo_pesos_y_capacidades.csv", index=False)

pd.DataFrame([{
    "alpha": ALPHA,
    "beta_Mbps": BETA,
    "mediana_utilizacion_observada": MEDIANA_UTILIZACION,
    "enlaces_trafico_imputado": int(modelo_df["trafico_imputado"].sum()),
    "enlaces_capacidad_explicita": int(
        modelo_df["capacidad_mbps_original"].notna().sum()
    ),
    "enlaces_capacidad_estimada": int(
        modelo_df["capacidad_mbps_original"].isna().sum()
    ),
}]).to_csv(TAB / "02_supuestos_modelo_pesos.csv", index=False)

# ================================================================
# 2. Dijkstra desde cero con cola de prioridad
# ================================================================
def dijkstra_heap(G, origen, atributo_peso, destino=None):
    """
    Dijkstra con heap binario.

    Complejidad teórica con lista de adyacencia + heap:
        O((V + E) log V)
    Memoria:
        O(V + E) por el grafo + O(V) para distancias/padres/heap.
    """
    dist = {n: math.inf for n in G.nodes()}
    padre = {origen: None}
    dist[origen] = 0.0

    heap = [(0.0, origen)]
    visitado = set()

    while heap:
        du, u = heapq.heappop(heap)

        if u in visitado:
            continue

        visitado.add(u)

        if destino is not None and u == destino:
            break

        for v, attrs in G[u].items():
            w = float(attrs[atributo_peso])
            alt = du + w

            if alt < dist[v]:
                dist[v] = alt
                padre[v] = u
                heapq.heappush(heap, (alt, v))

    return dist, padre


def reconstruir_ruta(padre, origen, destino):
    if destino not in padre and destino != origen:
        return None

    ruta = [destino]
    x = destino

    while x != origen:
        x = padre.get(x)
        if x is None:
            return None
        ruta.append(x)

    ruta.reverse()
    return ruta


# ================================================================
# 3. Floyd–Warshall desde cero
# ================================================================
def floyd_warshall(G, atributo_peso, node_order=None):
    """
    Floyd–Warshall clásico.

    Complejidad:
        Tiempo O(V^3)
        Memoria O(V^2)
    """
    if node_order is None:
        node_order = list(G.nodes())

    n = len(node_order)
    idx = {node: i for i, node in enumerate(node_order)}

    D = [[math.inf] * n for _ in range(n)]

    for i in range(n):
        D[i][i] = 0.0

    for u, v, attrs in G.edges(data=True):
        i = idx[u]
        j = idx[v]
        w = float(attrs[atributo_peso])
        if w < D[i][j]:
            D[i][j] = w
            D[j][i] = w

    for k in range(n):
        Dk = D[k]
        for i in range(n):
            Dik = D[i][k]
            if math.isinf(Dik):
                continue

            Di = D[i]
            for j in range(n):
                alt = Dik + Dk[j]
                if alt < Di[j]:
                    Di[j] = alt

    return np.asarray(D, dtype=float), idx


# ================================================================
# 4. Verificación Dijkstra vs Floyd para 20 pares
# ================================================================
NODE_ORDER = list(G.nodes())
rng = random.Random(SEED)

pares = []
while len(pares) < N_PARES_VERIFICACION:
    u, v = rng.sample(NODE_ORDER, 2)
    if (u, v) not in pares and (v, u) not in pares:
        pares.append((u, v))

MODELOS = {
    "saltos": "w_saltos",
    "latencia": "w_latencia",
    "carga": "w_carga",
}

# Floyd completo para los tres modelos; se reutiliza después.
matrices = {}
indices = {}
verification_rows = []

for nombre_modelo, attr in MODELOS.items():
    D, idx = floyd_warshall(G, attr, NODE_ORDER)
    matrices[nombre_modelo] = D
    indices[nombre_modelo] = idx

    for numero, (u, v) in enumerate(pares, start=1):
        dist_dij, _ = dijkstra_heap(G, u, attr, destino=v)
        d_dij = dist_dij[v]
        d_fw = D[idx[u], idx[v]]

        coincide = math.isclose(d_dij, d_fw, rel_tol=1e-10, abs_tol=1e-10)
        assert coincide

        verification_rows.append({
            "modelo": nombre_modelo,
            "par": numero,
            "origen": u,
            "destino": v,
            "distancia_dijkstra": d_dij,
            "distancia_floyd": d_fw,
            "coincide": coincide,
        })

pd.DataFrame(verification_rows).to_csv(
    TAB / "03_verificacion_20_pares.csv", index=False
)

# ================================================================
# 5. Benchmark sobre subredes crecientes
# ================================================================
def bfs_order(G, origen):
    visitados = {origen}
    q = deque([origen])
    orden = []

    while q:
        u = q.popleft()
        orden.append(u)

        for v in G.neighbors(u):
            if v not in visitados:
                visitados.add(v)
                q.append(v)

    return orden


def medir(func, repeticiones=3):
    tiempos = []
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        func()
        tiempos.append(time.perf_counter() - t0)
    return float(np.median(tiempos))


orden_bfs = bfs_order(G, "DATCC-2A-C3")
benchmark_rows = []

for n_sub in SIZES_BENCHMARK:
    seleccion = orden_bfs[:n_sub]
    H = G.subgraph(seleccion).copy()
    assert nx.is_connected(H)

    # Un origen fijo dentro de la subred.
    origen = seleccion[0]

    # Pares aleatorios para el tiempo de consulta puntual.
    rng_sub = random.Random(SEED + n_sub)
    pares_sub = [
        tuple(rng_sub.sample(seleccion, 2))
        for _ in range(min(30, max(10, n_sub // 3)))
    ]

    t_dij_fuente = medir(
        lambda: dijkstra_heap(H, origen, "w_saltos"),
        repeticiones=5
    )

    def consultas_pares():
        for u, v in pares_sub:
            dijkstra_heap(H, u, "w_saltos", destino=v)

    t_pares_total = medir(consultas_pares, repeticiones=3)
    t_dij_par = t_pares_total / len(pares_sub)

    t_floyd = medir(
        lambda: floyd_warshall(H, "w_saltos", list(H.nodes())),
        repeticiones=3 if n_sub <= 100 else 1
    )

    # All-pairs mediante Dijkstra: una ejecución por cada fuente.
    def all_pairs_dijkstra():
        for u in H.nodes():
            dijkstra_heap(H, u, "w_saltos")

    t_all_dij = medir(
        all_pairs_dijkstra,
        repeticiones=3 if n_sub <= 75 else 1
    )

    break_even_pairs = (
        math.ceil(t_floyd / t_dij_par) if t_dij_par > 0 else math.inf
    )
    break_even_sources = (
        math.ceil(t_floyd / t_dij_fuente) if t_dij_fuente > 0 else math.inf
    )

    benchmark_rows.append({
        "V": H.number_of_nodes(),
        "E": H.number_of_edges(),
        "t_dijkstra_1_fuente_s": t_dij_fuente,
        "t_dijkstra_1_par_s": t_dij_par,
        "t_floyd_all_pairs_s": t_floyd,
        "t_dijkstra_all_sources_s": t_all_dij,
        "break_even_pares_aprox": break_even_pairs,
        "break_even_fuentes_aprox": break_even_sources,
    })

bench_df = pd.DataFrame(benchmark_rows)
bench_df.to_csv(TAB / "04_benchmark_dijkstra_floyd.csv", index=False)

# ================================================================
# 6. Guardar matrices completas
# ================================================================
for nombre, D in matrices.items():
    pd.DataFrame(
        D,
        index=NODE_ORDER,
        columns=NODE_ORDER
    ).to_csv(TAB / f"05_matriz_distancias_{nombre}.csv")

# ================================================================
# 7. Cercanía ponderada y top-10
# ================================================================
def closeness_desde_matriz(D, node_order):
    n = len(node_order)
    values = {}

    for i, node in enumerate(node_order):
        suma = float(D[i].sum())
        values[node] = (n - 1) / suma if suma > 0 else 0.0

    return values


tops = {}
for nombre, D in matrices.items():
    c = closeness_desde_matriz(D, NODE_ORDER)
    tops[nombre] = sorted(
        c.items(), key=lambda x: x[1], reverse=True
    )[:10]

top_rows = []
for rank in range(10):
    row = {"ranking": rank + 1}

    for nombre in ["saltos", "latencia", "carga"]:
        node, value = tops[nombre][rank]
        row[f"{nombre}_nodo"] = node
        row[f"{nombre}_valor"] = value
        row[f"{nombre}_campus"] = meta.loc[node, "campus"]
        row[f"{nombre}_capa"] = meta.loc[node, "capa"]

    top_rows.append(row)

top_df = pd.DataFrame(top_rows)
top_df.to_csv(TAB / "06_top10_cercania_tres_pesos.csv", index=False)

# Solapamientos entre rankings.
sets_top = {k: {x[0] for x in v} for k, v in tops.items()}
overlap_rows = []
for a, b in [("saltos", "latencia"), ("saltos", "carga"), ("latencia", "carga")]:
    overlap_rows.append({
        "modelo_A": a,
        "modelo_B": b,
        "interseccion_top10": len(sets_top[a] & sets_top[b]),
        "nodos_comunes": " | ".join(sorted(sets_top[a] & sets_top[b])),
    })
pd.DataFrame(overlap_rows).to_csv(
    TAB / "07_solapamiento_top10_cercania.csv", index=False
)

# ================================================================
# 8. Par de equipos de acceso más distante y ruta
# ================================================================
access_nodes = nodos.loc[nodos["capa"] == "acceso", "id"].tolist()
index_global = {n: i for i, n in enumerate(NODE_ORDER)}

farthest_rows = []
route_rows = []

for nombre, attr in MODELOS.items():
    D = matrices[nombre]

    max_d = -1.0
    pair = None

    for i in range(len(access_nodes)):
        u = access_nodes[i]
        iu = index_global[u]

        for j in range(i + 1, len(access_nodes)):
            v = access_nodes[j]
            iv = index_global[v]
            d = D[iu, iv]

            if d > max_d:
                max_d = float(d)
                pair = (u, v)

    u, v = pair

    dist, padre = dijkstra_heap(G, u, attr, destino=v)
    ruta = reconstruir_ruta(padre, u, v)
    assert ruta is not None
    assert math.isclose(dist[v], max_d, rel_tol=1e-10, abs_tol=1e-10)

    farthest_rows.append({
        "modelo": nombre,
        "origen": u,
        "campus_origen": meta.loc[u, "campus"],
        "destino": v,
        "campus_destino": meta.loc[v, "campus"],
        "distancia_minima": max_d,
        "saltos_ruta": len(ruta) - 1,
        "ruta": " -> ".join(ruta),
    })

    acumulado = 0.0
    for paso in range(len(ruta) - 1):
        a, b = ruta[paso], ruta[paso + 1]
        attrs = G[a][b]
        w = float(attrs[attr])
        acumulado += w

        route_rows.append({
            "modelo": nombre,
            "paso": paso + 1,
            "desde": a,
            "hacia": b,
            "campus_desde": meta.loc[a, "campus"],
            "campus_hacia": meta.loc[b, "campus"],
            "capacidad_mbps": attrs["capacidad_mbps_modelo"],
            "trafico_mbps": attrs["trafico_mbps_modelo"],
            "peso_arista": w,
            "peso_acumulado": acumulado,
        })

farthest_df = pd.DataFrame(farthest_rows)
farthest_df.to_csv(TAB / "08_pares_acceso_mas_distantes.csv", index=False)

pd.DataFrame(route_rows).to_csv(
    TAB / "09_rutas_acceso_mas_distantes_paso_a_paso.csv",
    index=False
)

# ================================================================
# 9. Figuras
# ================================================================
# Benchmark log-log para apreciar tendencias.
plt.figure(figsize=(8, 5))
plt.plot(
    bench_df["V"],
    bench_df["t_dijkstra_1_fuente_s"],
    marker="o",
    label="Dijkstra: 1 fuente"
)
plt.plot(
    bench_df["V"],
    bench_df["t_floyd_all_pairs_s"],
    marker="o",
    label="Floyd-Warshall: todos los pares"
)
plt.yscale("log")
plt.xlabel("Número de nodos V")
plt.ylabel("Tiempo mediano (s, escala log)")
plt.title("Tiempo empírico: Dijkstra vs Floyd-Warshall")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "01_benchmark_dijkstra_floyd.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(
    bench_df["V"],
    bench_df["t_dijkstra_all_sources_s"],
    marker="o",
    label="Dijkstra desde todas las fuentes"
)
plt.plot(
    bench_df["V"],
    bench_df["t_floyd_all_pairs_s"],
    marker="o",
    label="Floyd-Warshall"
)
plt.xlabel("Número de nodos V")
plt.ylabel("Tiempo mediano (s)")
plt.title("Cálculo all-pairs sobre subredes crecientes")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "02_all_pairs_dijkstra_vs_floyd.png", dpi=180)
plt.close()

# Ranking top-10: valores normalizados dentro de cada modelo para comparabilidad visual.
plot_rows = []
for nombre in ["saltos", "latencia", "carga"]:
    vals = np.array([v for _, v in tops[nombre]], dtype=float)
    norm = vals / vals.max()

    for rank, ((node, value), nv) in enumerate(zip(tops[nombre], norm), 1):
        plot_rows.append({
            "modelo": nombre,
            "ranking": rank,
            "nodo": node,
            "valor": value,
            "valor_normalizado": nv,
        })

plot_df = pd.DataFrame(plot_rows)
plt.figure(figsize=(9, 5))
for nombre in ["saltos", "latencia", "carga"]:
    sub = plot_df[plot_df["modelo"] == nombre]
    plt.plot(
        sub["ranking"],
        sub["valor_normalizado"],
        marker="o",
        label=nombre
    )

plt.xlabel("Posición en el ranking")
plt.ylabel("Cercanía normalizada respecto al máximo")
plt.title("Top-10 de cercanía bajo los tres modelos")
plt.xticks(range(1, 11))
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "03_top10_cercania_tres_modelos.png", dpi=180)
plt.close()

# ================================================================
# 10. Consola
# ================================================================
print("=== SUPUESTOS ===")
print(f"alpha={ALPHA}, beta={BETA} Mbps")
print(f"Mediana de utilización observada = {MEDIANA_UTILIZACION:.6f}")
print(f"Tráfico imputado en {int(modelo_df['trafico_imputado'].sum())} enlaces")
print("Todos los pesos son no negativos: OK")

print("\n=== VERIFICACIÓN DIJKSTRA VS FLOYD ===")
ver_df = pd.DataFrame(verification_rows)
print(
    ver_df.groupby("modelo")["coincide"]
    .agg(["count", "sum"])
    .to_string()
)

print("\n=== BENCHMARK ===")
print(bench_df.to_string(index=False))

print("\n=== TOP-10 CERCANÍA ===")
print(top_df.to_string(index=False))

print("\n=== PARES DE ACCESO MÁS DISTANTES ===")
print(farthest_df.to_string(index=False))

print(f"\nResultados guardados en {ROOT / 'resultados'}")
