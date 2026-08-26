from pathlib import Path
from collections import Counter, deque

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

CORE_CENTRAL = "DATCC-2A-C3"
CORE_CENTRAL_ALTERNATIVO = "DATCC-2A-C2"
MPLS = "INTERNET-MPLS"

G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos = pd.read_csv(DATA / "red_ucuenca_nodes.csv")
meta = nodos.set_index("id")

# ================================================================
# 1. BFS DESDE CERO
# ================================================================
def bfs_desde_cero(G, origen):
    """
    BFS implementado sin usar funciones BFS de NetworkX.

    Estructuras:
      - deque: cola FIFO de nodos pendientes.
      - set: nodos visitados.
      - dict parent: padre de cada nodo en el árbol BFS.
      - dict distance: distancia mínima en número de aristas desde el origen.
      - list order: orden de extracción de la cola.

    Complejidad:
      Tiempo: O(V + E)
      Memoria: O(V)
    """
    visitados = {origen}
    cola = deque([origen])
    padre = {origen: None}
    distancia = {origen: 0}
    orden = []

    while cola:
        u = cola.popleft()
        orden.append(u)

        for v in G.neighbors(u):
            if v not in visitados:
                visitados.add(v)
                padre[v] = u
                distancia[v] = distancia[u] + 1
                cola.append(v)

    return orden, padre, distancia


# ================================================================
# 2. DFS DESDE CERO + CICLOS FUNDAMENTALES
# ================================================================
def dfs_ciclos_desde_cero(G, origen=None):
    """
    DFS iterativo sin usar funciones DFS/cycle_basis de NetworkX.

    Cada frame de la pila guarda:
      (nodo_actual, iterador_de_vecinos)

    Un ciclo fundamental se detecta cuando aparece una arista (u,v)
    hacia un ancestro v distinto del padre de u.

    Estructuras:
      - list: pila LIFO explícita.
      - set: visitados.
      - dict parent y depth.
      - list cycles: ciclos fundamentales encontrados.

    Complejidad:
      Recorrido DFS: O(V + E)
      Memoria: O(V)
      La reconstrucción explícita de los ciclos añade un costo proporcional
      a la suma de las longitudes de los ciclos reportados.
    """
    visitados = set()
    padre = {}
    profundidad = {}
    orden = []
    ciclos = []

    inicios = []
    if origen is not None:
        inicios.append(origen)
    inicios.extend(n for n in G.nodes() if n != origen)

    for raiz in inicios:
        if raiz in visitados:
            continue

        visitados.add(raiz)
        padre[raiz] = None
        profundidad[raiz] = 0
        orden.append(raiz)

        pila = [(raiz, iter(G.neighbors(raiz)))]

        while pila:
            u, vecinos = pila[-1]

            try:
                v = next(vecinos)
            except StopIteration:
                pila.pop()
                continue

            if v not in visitados:
                visitados.add(v)
                padre[v] = u
                profundidad[v] = profundidad[u] + 1
                orden.append(v)
                pila.append((v, iter(G.neighbors(v))))

            elif v != padre[u] and profundidad[v] < profundidad[u]:
                # En un DFS de un grafo no dirigido, esta arista apunta
                # a un ancestro. Se reconstruye el camino u -> ... -> v.
                ciclo = [u]
                x = u

                while x != v:
                    x = padre[x]
                    ciclo.append(x)

                ciclos.append(ciclo)

    return orden, padre, profundidad, ciclos


def perfil_profundidad(distancia):
    conteo = Counter(distancia.values())
    return pd.DataFrame(
        [{"distancia": d, "nodos": conteo[d]} for d in sorted(conteo)]
    )


# ================================================================
# 3. BFS DESDE LOS DOS CORES DE CAMPUS CENTRAL
# ================================================================
resultados_bfs = {}

for origen in [CORE_CENTRAL, CORE_CENTRAL_ALTERNATIVO, MPLS]:
    orden, padre, distancia = bfs_desde_cero(G, origen)
    resultados_bfs[origen] = {
        "orden": orden,
        "padre": padre,
        "distancia": distancia,
    }

    # Verificación contra NetworkX (SOLO verificación).
    dist_nx = dict(nx.single_source_shortest_path_length(G, origen))
    assert distancia == dist_nx, f"BFS incorrecto para {origen}"

    perfil_profundidad(distancia).to_csv(
        TAB / f"perfil_BFS_{origen}.csv", index=False
    )

# ================================================================
# 4. PERFIL DEL CORE CENTRAL E INTERPRETACIÓN POR CAPA
# ================================================================
dist_core = resultados_bfs[CORE_CENTRAL]["distancia"]

filas_core = []
for n, d in dist_core.items():
    filas_core.append({
        "nodo": n,
        "distancia": d,
        "campus": meta.loc[n, "campus"],
        "capa": meta.loc[n, "capa"],
    })

df_core = pd.DataFrame(filas_core)
df_core.to_csv(TAB / "01_distancias_desde_core_central.csv", index=False)

tabla_capa_total = pd.crosstab(df_core["distancia"], df_core["capa"])
tabla_capa_total.to_csv(TAB / "02_perfil_core_por_capa_toda_red.csv")

df_campus_central = df_core[df_core["campus"] == "Campus Central"].copy()
tabla_capa_central = pd.crosstab(
    df_campus_central["distancia"], df_campus_central["capa"]
)
tabla_capa_central.to_csv(TAB / "03_perfil_core_por_capa_campus_central.csv")

# ================================================================
# 5. BFS DESDE MPLS Y DISTANCIA POR CAMPUS
# ================================================================
dist_mpls = resultados_bfs[MPLS]["distancia"]

filas_mpls = []
for n, d in dist_mpls.items():
    filas_mpls.append({
        "nodo": n,
        "distancia": d,
        "campus": meta.loc[n, "campus"],
        "capa": meta.loc[n, "capa"],
    })

df_mpls = pd.DataFrame(filas_mpls)
df_mpls.to_csv(TAB / "04_distancias_desde_MPLS.csv", index=False)

campus_stats = (
    df_mpls.groupby("campus")["distancia"]
    .agg(["count", "mean", "median", "min", "max"])
    .sort_values("mean", ascending=False)
)
campus_stats.to_csv(TAB / "05_distancia_MPLS_por_campus.csv")

# Distribución distancia x campus
tabla_mpls_campus = pd.crosstab(df_mpls["campus"], df_mpls["distancia"])
tabla_mpls_campus.to_csv(TAB / "06_perfil_MPLS_por_campus.csv")

# ================================================================
# 6. DFS Y CICLOS
# ================================================================
orden_dfs, padre_dfs, profundidad_dfs, ciclos = dfs_ciclos_desde_cero(
    G, CORE_CENTRAL
)

# Verificación estructural:
# para un grafo conexo, el número de ciclos fundamentales es E - V + 1.
rango_ciclotomatico = G.number_of_edges() - G.number_of_nodes() + 1
assert len(ciclos) == rango_ciclotomatico

# NetworkX se usa únicamente como comprobación externa.
assert len(nx.cycle_basis(G)) == len(ciclos)

filas_ciclos = []
for i, ciclo in enumerate(ciclos, start=1):
    campuses = sorted({meta.loc[n, "campus"] for n in ciclo})
    capas = sorted({meta.loc[n, "capa"] for n in ciclo})

    if len(campuses) == 1:
        zona = campuses[0]
    else:
        zona = "Intercampus / WAN"

    filas_ciclos.append({
        "ciclo_fundamental": i,
        "longitud": len(ciclo),
        "zona": zona,
        "campuses": " | ".join(campuses),
        "capas": " | ".join(capas),
        "recorrido": " -> ".join(ciclo + [ciclo[0]]),
    })

df_ciclos = pd.DataFrame(filas_ciclos)
df_ciclos.to_csv(TAB / "07_ciclos_fundamentales_DFS.csv", index=False)

resumen_ciclos = (
    df_ciclos.groupby("zona")
    .agg(ciclos_fundamentales=("ciclo_fundamental", "count"),
         longitud_media=("longitud", "mean"),
         longitud_maxima=("longitud", "max"))
    .sort_values("ciclos_fundamentales", ascending=False)
)
resumen_ciclos.to_csv(TAB / "08_resumen_ciclos_por_zona.csv")

# ================================================================
# 7. FIGURAS
# ================================================================
perfil_core = perfil_profundidad(dist_core)
perfil_mpls = perfil_profundidad(dist_mpls)

max_d = max(perfil_core["distancia"].max(), perfil_mpls["distancia"].max())
x = np.arange(max_d + 1)

core_map = dict(zip(perfil_core["distancia"], perfil_core["nodos"]))
mpls_map = dict(zip(perfil_mpls["distancia"], perfil_mpls["nodos"]))

width = 0.38
plt.figure(figsize=(9, 5))
plt.bar(x - width/2, [core_map.get(i, 0) for i in x], width=width, label=CORE_CENTRAL)
plt.bar(x + width/2, [mpls_map.get(i, 0) for i in x], width=width, label=MPLS)
plt.xlabel("Distancia BFS (saltos)")
plt.ylabel("Número de nodos")
plt.title("Perfil de profundidad BFS: core Campus Central vs MPLS")
plt.xticks(x)
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "01_perfiles_BFS_core_vs_MPLS.png", dpi=180)
plt.close()

# Distancia media desde MPLS por campus/sede
plot_stats = campus_stats.drop(index="Nube MPLS", errors="ignore").sort_values("mean")
plt.figure(figsize=(10, 5))
plt.barh(plot_stats.index, plot_stats["mean"])
plt.xlabel("Distancia media desde INTERNET-MPLS (saltos)")
plt.ylabel("Campus / sede")
plt.title("Distancia media a la nube MPLS")
plt.tight_layout()
plt.savefig(FIG / "02_distancia_media_MPLS_por_campus.png", dpi=180)
plt.close()

# Ciclos fundamentales por zona
plt.figure(figsize=(8, 5))
plt.bar(resumen_ciclos.index, resumen_ciclos["ciclos_fundamentales"])
plt.ylabel("Ciclos fundamentales de la base DFS")
plt.xlabel("Zona")
plt.title("Ubicación de ciclos fundamentales detectados por DFS")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.savefig(FIG / "03_ciclos_por_zona.png", dpi=180)
plt.close()

# ================================================================
# 8. CONSOLA
# ================================================================
print("=== BFS DESDE CORE CENTRAL ===")
print(f"Core usado en el análisis principal: {CORE_CENTRAL}")
print("Perfil:", dict(sorted(Counter(dist_core.values()).items())))

print("\nPerfil por capa, restringido a Campus Central:")
print(tabla_capa_central)

print("\n=== BFS DESDE MPLS ===")
print("Perfil:", dict(sorted(Counter(dist_mpls.values()).items())))
print("\nDistancia por campus:")
print(campus_stats)

print("\n=== DFS / CICLOS ===")
print(f"Ciclos fundamentales detectados: {len(ciclos)}")
print(f"Rango ciclotomático E-V+1: {rango_ciclotomatico}")
print(resumen_ciclos)

print("\nVerificación BFS con NetworkX: OK")
print("Verificación cantidad de ciclos con cycle_basis: OK")
print(f"\nResultados guardados en {ROOT / 'resultados'}")
