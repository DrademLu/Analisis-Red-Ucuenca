"""
P7 — Localización de colectores de telemetría — Red UCuenca

Se resuelven dos problemas clásicos de localización sobre la distancia
topológica (número de saltos):

1) p-mediana:
   minimiza la distancia media de cada equipo a su colector más cercano.

2) p-centro:
   minimiza la peor distancia de cualquier equipo al colector más cercano.

Para p in {1,2,3,5} se calculan:
- una heurística voraz;
- una solución exacta mediante MILP con scipy.optimize.milp / HiGHS.

Todos los nodos se consideran inicialmente candidatos a alojar un colector.
Las restricciones prácticas de elegibilidad (rack, energía, seguridad, etc.)
se discuten como extensión del modelo.
"""

from pathlib import Path
import math
import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TAB = ROOT / "resultados" / "tablas"
FIG = ROOT / "resultados" / "figuras"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

P_VALUES = [1, 2, 3, 5]
MILP_TIME_LIMIT = 120

# ================================================================
# 1. Carga y matriz de distancias
# ================================================================
G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos_df = pd.read_csv(DATA / "red_ucuenca_nodes.csv")

assert G.number_of_nodes() == 177
assert G.number_of_edges() == 209
assert nx.is_connected(G)

NODE_ORDER = list(G.nodes())
N = len(NODE_ORDER)
IDX = {n: i for i, n in enumerate(NODE_ORDER)}
META = nodos_df.set_index("id")

D = np.full((N, N), np.inf, dtype=float)

for i, origen in enumerate(NODE_ORDER):
    dist = nx.single_source_shortest_path_length(G, origen)
    for destino, d in dist.items():
        D[i, IDX[destino]] = float(d)

assert np.isfinite(D).all()
assert np.allclose(D, D.T)

pd.DataFrame(D, index=NODE_ORDER, columns=NODE_ORDER).to_csv(
    TAB / "01_matriz_distancias_saltos.csv"
)

# ================================================================
# 2. Evaluación de una solución
# ================================================================
def evaluar_facilidades(indices):
    nearest = D[:, indices].min(axis=1)
    return {
        "distancia_media": float(nearest.mean()),
        "distancia_maxima": float(nearest.max()),
        "suma_distancias": float(nearest.sum()),
        "distancias": nearest,
    }


# ================================================================
# 3. Heurística voraz p-mediana
# ================================================================
def greedy_pmedian(D, p):
    """
    Empieza sin instalaciones y agrega en cada iteración el candidato
    que produce la menor suma total de distancias al colector más cercano.
    """
    n = D.shape[0]
    chosen = []
    current = np.full(n, np.inf)

    for _ in range(p):
        best_j = None
        best_sum = np.inf

        for j in range(n):
            if j in chosen:
                continue

            candidate = np.minimum(current, D[:, j])
            obj = float(candidate.sum())

            if obj < best_sum - 1e-12:
                best_sum = obj
                best_j = j

        chosen.append(best_j)
        current = np.minimum(current, D[:, best_j])

    return chosen


# ================================================================
# 4. Heurística voraz p-centro
# ================================================================
def greedy_pcenter(D, p):
    """
    En cada iteración agrega el candidato que minimiza la distancia máxima.
    En caso de empate se usa la distancia media como criterio secundario.
    """
    n = D.shape[0]
    chosen = []
    current = np.full(n, np.inf)

    for _ in range(p):
        best_j = None
        best_key = (np.inf, np.inf)

        for j in range(n):
            if j in chosen:
                continue

            candidate = np.minimum(current, D[:, j])
            key = (float(candidate.max()), float(candidate.mean()))

            if key < best_key:
                best_key = key
                best_j = j

        chosen.append(best_j)
        current = np.minimum(current, D[:, best_j])

    return chosen


# ================================================================
# 5. MILP exacto p-mediana
# ================================================================
def solve_pmedian_milp(D, p, time_limit=MILP_TIME_LIMIT):
    """
    Variables:
      x_ij = 1 si el equipo i se asigna al colector j
      y_j  = 1 si se instala un colector en j

    min sum_i sum_j d_ij x_ij

    s.a.
      sum_j x_ij = 1        para todo i
      x_ij <= y_j           para todo i,j
      sum_j y_j = p
      x_ij, y_j binarias
    """
    n = D.shape[0]
    nxv = n * n
    nv = nxv + n

    c = np.concatenate([D.ravel(), np.zeros(n)])

    rows, cols, data = [], [], []
    lb, ub = [], []
    r = 0

    # Cada equipo se asigna exactamente a un colector.
    for i in range(n):
        for j in range(n):
            rows.append(r)
            cols.append(i * n + j)
            data.append(1.0)
        lb.append(1.0)
        ub.append(1.0)
        r += 1

    # Solo puede asignarse a una instalación abierta.
    for i in range(n):
        for j in range(n):
            rows.extend([r, r])
            cols.extend([i * n + j, nxv + j])
            data.extend([1.0, -1.0])
            lb.append(-np.inf)
            ub.append(0.0)
            r += 1

    # Exactamente p colectores.
    for j in range(n):
        rows.append(r)
        cols.append(nxv + j)
        data.append(1.0)

    lb.append(float(p))
    ub.append(float(p))
    r += 1

    A = coo_matrix(
        (data, (rows, cols)),
        shape=(r, nv)
    ).tocsc()

    constraints = LinearConstraint(
        A,
        np.asarray(lb),
        np.asarray(ub)
    )

    integrality = np.ones(nv, dtype=int)
    bounds = Bounds(np.zeros(nv), np.ones(nv))

    t0 = time.perf_counter()
    result = milp(
        c,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={
            "time_limit": time_limit,
            "mip_rel_gap": 0.0,
        },
    )
    elapsed = time.perf_counter() - t0

    if result.x is None:
        raise RuntimeError(
            f"p-mediana p={p}: solver sin solución. {result.message}"
        )

    selected = np.where(result.x[nxv:] > 0.5)[0].tolist()

    return selected, result, elapsed


# ================================================================
# 6. MILP exacto p-centro
# ================================================================
def build_pcenter_constraints(D, p):
    """
    Variables:
      x_ij binarias
      y_j binarias
      z continua = distancia máxima

    min z

    s.a.
      sum_j x_ij = 1
      x_ij <= y_j
      sum_j y_j = p
      sum_j d_ij x_ij <= z  para todo i
    """
    n = D.shape[0]
    nxv = n * n
    yoff = nxv
    zidx = nxv + n
    nv = zidx + 1

    rows, cols, data = [], [], []
    lb, ub = [], []
    r = 0

    for i in range(n):
        for j in range(n):
            rows.append(r)
            cols.append(i * n + j)
            data.append(1.0)
        lb.append(1.0)
        ub.append(1.0)
        r += 1

    for i in range(n):
        for j in range(n):
            rows.extend([r, r])
            cols.extend([i * n + j, yoff + j])
            data.extend([1.0, -1.0])
            lb.append(-np.inf)
            ub.append(0.0)
            r += 1

    for j in range(n):
        rows.append(r)
        cols.append(yoff + j)
        data.append(1.0)

    lb.append(float(p))
    ub.append(float(p))
    r += 1

    # Distancia de cada equipo al colector asignado <= z
    for i in range(n):
        for j in range(n):
            rows.append(r)
            cols.append(i * n + j)
            data.append(float(D[i, j]))

        rows.append(r)
        cols.append(zidx)
        data.append(-1.0)

        lb.append(-np.inf)
        ub.append(0.0)
        r += 1

    A = coo_matrix(
        (data, (rows, cols)),
        shape=(r, nv)
    ).tocsc()

    constraints = LinearConstraint(
        A,
        np.asarray(lb),
        np.asarray(ub)
    )

    integrality = np.concatenate([
        np.ones(nxv + n, dtype=int),
        np.zeros(1, dtype=int),
    ])

    return constraints, integrality, nxv, yoff, zidx, nv


def solve_pcenter_milp(D, p, time_limit=MILP_TIME_LIMIT):
    """
    Dos fases:
    1) minimiza exactamente el radio z;
    2) fijado el radio óptimo, minimiza la suma de distancias.

    La segunda fase solo rompe empates entre soluciones igualmente óptimas
    para p-centro y produce una ubicación más representativa.
    """
    n = D.shape[0]
    constraints, integrality, nxv, yoff, zidx, nv = (
        build_pcenter_constraints(D, p)
    )

    # -------- Fase 1: radio mínimo --------
    c1 = np.zeros(nv)
    c1[zidx] = 1.0

    lower = np.zeros(nv)
    upper = np.ones(nv)
    upper[zidx] = np.inf

    t0 = time.perf_counter()
    r1 = milp(
        c1,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={
            "time_limit": time_limit,
            "mip_rel_gap": 0.0,
        },
    )

    if r1.x is None:
        raise RuntimeError(
            f"p-centro fase 1 p={p}: solver sin solución. {r1.message}"
        )

    radius = float(r1.fun)

    # -------- Fase 2: mejor media manteniendo z óptimo --------
    c2 = np.zeros(nv)
    c2[:nxv] = D.ravel()

    lower2 = np.zeros(nv)
    upper2 = np.ones(nv)
    lower2[zidx] = radius
    upper2[zidx] = radius

    r2 = milp(
        c2,
        integrality=integrality,
        bounds=Bounds(lower2, upper2),
        constraints=constraints,
        options={
            "time_limit": time_limit,
            "mip_rel_gap": 0.0,
        },
    )
    elapsed = time.perf_counter() - t0

    if r2.x is None:
        raise RuntimeError(
            f"p-centro fase 2 p={p}: solver sin solución. {r2.message}"
        )

    selected = np.where(
        r2.x[yoff:yoff + n] > 0.5
    )[0].tolist()

    return selected, radius, r1, r2, elapsed


# ================================================================
# 7. Ejecutar p = 1,2,3,5
# ================================================================
rows = []
facility_rows = []

for p in P_VALUES:
    # ----- p-mediana greedy -----
    sel = greedy_pmedian(D, p)
    ev = evaluar_facilidades(sel)

    rows.append({
        "problema": "p-mediana",
        "metodo": "voraz",
        "p": p,
        "distancia_media": ev["distancia_media"],
        "distancia_maxima": ev["distancia_maxima"],
        "suma_distancias": ev["suma_distancias"],
        "tiempo_solver_s": np.nan,
        "estado_solver": "heuristica",
        "instalaciones": " | ".join(NODE_ORDER[j] for j in sel),
    })

    for j in sel:
        facility_rows.append({
            "problema": "p-mediana",
            "metodo": "voraz",
            "p": p,
            "nodo": NODE_ORDER[j],
            "campus": META.loc[NODE_ORDER[j], "campus"],
            "capa": META.loc[NODE_ORDER[j], "capa"],
        })

    # ----- p-mediana MILP -----
    sel, res, elapsed = solve_pmedian_milp(D, p)
    ev = evaluar_facilidades(sel)

    rows.append({
        "problema": "p-mediana",
        "metodo": "MILP exacto",
        "p": p,
        "distancia_media": ev["distancia_media"],
        "distancia_maxima": ev["distancia_maxima"],
        "suma_distancias": ev["suma_distancias"],
        "tiempo_solver_s": elapsed,
        "estado_solver": res.message,
        "instalaciones": " | ".join(NODE_ORDER[j] for j in sel),
    })

    for j in sel:
        facility_rows.append({
            "problema": "p-mediana",
            "metodo": "MILP exacto",
            "p": p,
            "nodo": NODE_ORDER[j],
            "campus": META.loc[NODE_ORDER[j], "campus"],
            "capa": META.loc[NODE_ORDER[j], "capa"],
        })

    # ----- p-centro greedy -----
    sel = greedy_pcenter(D, p)
    ev = evaluar_facilidades(sel)

    rows.append({
        "problema": "p-centro",
        "metodo": "voraz",
        "p": p,
        "distancia_media": ev["distancia_media"],
        "distancia_maxima": ev["distancia_maxima"],
        "suma_distancias": ev["suma_distancias"],
        "tiempo_solver_s": np.nan,
        "estado_solver": "heuristica",
        "instalaciones": " | ".join(NODE_ORDER[j] for j in sel),
    })

    for j in sel:
        facility_rows.append({
            "problema": "p-centro",
            "metodo": "voraz",
            "p": p,
            "nodo": NODE_ORDER[j],
            "campus": META.loc[NODE_ORDER[j], "campus"],
            "capa": META.loc[NODE_ORDER[j], "capa"],
        })

    # ----- p-centro MILP -----
    sel, radius, r1, r2, elapsed = solve_pcenter_milp(D, p)
    ev = evaluar_facilidades(sel)

    assert math.isclose(
        ev["distancia_maxima"],
        radius,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )

    rows.append({
        "problema": "p-centro",
        "metodo": "MILP exacto",
        "p": p,
        "distancia_media": ev["distancia_media"],
        "distancia_maxima": ev["distancia_maxima"],
        "suma_distancias": ev["suma_distancias"],
        "tiempo_solver_s": elapsed,
        "estado_solver": f"fase1: {r1.message}; fase2: {r2.message}",
        "instalaciones": " | ".join(NODE_ORDER[j] for j in sel),
    })

    for j in sel:
        facility_rows.append({
            "problema": "p-centro",
            "metodo": "MILP exacto",
            "p": p,
            "nodo": NODE_ORDER[j],
            "campus": META.loc[NODE_ORDER[j], "campus"],
            "capa": META.loc[NODE_ORDER[j], "capa"],
        })

results_df = pd.DataFrame(rows)
facilities_df = pd.DataFrame(facility_rows)

results_df.to_csv(
    TAB / "02_resultados_localizacion.csv",
    index=False
)
facilities_df.to_csv(
    TAB / "03_ubicaciones_colectores.csv",
    index=False
)

# ================================================================
# 8. Comparación con centralidades de P1
# ================================================================
bet = nx.betweenness_centrality(G, normalized=True)
close = nx.closeness_centrality(G)

bet_sorted = sorted(
    bet.items(),
    key=lambda x: x[1],
    reverse=True
)
close_sorted = sorted(
    close.items(),
    key=lambda x: x[1],
    reverse=True
)

rank_bet = {
    node: rank
    for rank, (node, _) in enumerate(bet_sorted, start=1)
}
rank_close = {
    node: rank
    for rank, (node, _) in enumerate(close_sorted, start=1)
}

top10_bet = {node for node, _ in bet_sorted[:10]}
top10_close = {node for node, _ in close_sorted[:10]}

comparison_rows = []

exact_facilities = facilities_df[
    facilities_df["metodo"] == "MILP exacto"
].copy()

for _, r in exact_facilities.iterrows():
    node = r["nodo"]

    comparison_rows.append({
        "problema": r["problema"],
        "p": r["p"],
        "nodo": node,
        "campus": r["campus"],
        "capa": r["capa"],
        "betweenness": bet[node],
        "ranking_betweenness_P1": rank_bet[node],
        "en_top10_betweenness": node in top10_bet,
        "closeness": close[node],
        "ranking_closeness_P1": rank_close[node],
        "en_top10_closeness": node in top10_close,
    })

centrality_comparison = pd.DataFrame(comparison_rows)
centrality_comparison.to_csv(
    TAB / "04_comparacion_con_centralidades_P1.csv",
    index=False
)

# Top-10 P1 para referencia
top10_rows = []
for k in range(10):
    bn, bv = bet_sorted[k]
    cn, cv = close_sorted[k]

    top10_rows.append({
        "ranking": k + 1,
        "betweenness_nodo": bn,
        "betweenness_valor": bv,
        "closeness_nodo": cn,
        "closeness_valor": cv,
    })

pd.DataFrame(top10_rows).to_csv(
    TAB / "05_top10_P1_referencia.csv",
    index=False
)

# ================================================================
# 9. Comparación greedy vs exacto
# ================================================================
comparison_method_rows = []

for problem in ["p-mediana", "p-centro"]:
    for p in P_VALUES:
        sub = results_df[
            (results_df["problema"] == problem)
            & (results_df["p"] == p)
        ]

        greedy = sub[sub["metodo"] == "voraz"].iloc[0]
        exact = sub[sub["metodo"] == "MILP exacto"].iloc[0]

        if problem == "p-mediana":
            gobj = greedy["distancia_media"]
            eobj = exact["distancia_media"]
        else:
            gobj = greedy["distancia_maxima"]
            eobj = exact["distancia_maxima"]

        gap_pct = 0.0
        if eobj > 0:
            gap_pct = 100.0 * (gobj - eobj) / eobj

        comparison_method_rows.append({
            "problema": problem,
            "p": p,
            "objetivo_voraz": gobj,
            "objetivo_exacto": eobj,
            "gap_voraz_porcentaje": gap_pct,
            "instalaciones_voraz": greedy["instalaciones"],
            "instalaciones_exactas": exact["instalaciones"],
        })

pd.DataFrame(comparison_method_rows).to_csv(
    TAB / "06_voraz_vs_exacto.csv",
    index=False
)

# ================================================================
# 10. Figuras
# ================================================================
pm = results_df[results_df["problema"] == "p-mediana"]

plt.figure(figsize=(8, 5))
for method in ["voraz", "MILP exacto"]:
    sub = pm[pm["metodo"] == method]
    plt.plot(
        sub["p"],
        sub["distancia_media"],
        marker="o",
        label=method,
    )

plt.xlabel("Número de colectores p")
plt.ylabel("Distancia media al colector más cercano (saltos)")
plt.title("p-mediana: heurística voraz vs solución exacta")
plt.xticks(P_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG / "01_pmediana_objetivo_vs_p.png",
    dpi=180
)
plt.close()

pc = results_df[results_df["problema"] == "p-centro"]

plt.figure(figsize=(8, 5))
for method in ["voraz", "MILP exacto"]:
    sub = pc[pc["metodo"] == method]
    plt.plot(
        sub["p"],
        sub["distancia_maxima"],
        marker="o",
        label=method,
    )

plt.xlabel("Número de colectores p")
plt.ylabel("Distancia máxima al colector más cercano (saltos)")
plt.title("p-centro: heurística voraz vs solución exacta")
plt.xticks(P_VALUES)
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG / "02_pcentro_objetivo_vs_p.png",
    dpi=180
)
plt.close()

# ================================================================
# 11. Consola
# ================================================================
print("=== RESULTADOS P7 ===")
print(
    results_df[
        [
            "problema",
            "metodo",
            "p",
            "distancia_media",
            "distancia_maxima",
            "instalaciones",
        ]
    ].to_string(index=False)
)

print("\n=== COMPARACIÓN CON CENTRALIDADES P1 (SOLUCIONES EXACTAS) ===")
print(
    centrality_comparison[
        [
            "problema",
            "p",
            "nodo",
            "campus",
            "capa",
            "ranking_betweenness_P1",
            "ranking_closeness_P1",
        ]
    ].to_string(index=False)
)

print(f"\nResultados guardados en {ROOT / 'resultados'}")
