"""
P10 — Síntesis del diagnóstico y ranking compuesto de criticidad.

Índice propuesto:
    I_i = 0.25 B_i + 0.10 A_i + 0.20 M_i + 0.15 P_i + 0.30 C_i

donde todos los términos, excepto A, se normalizan a [0,1]:

B_i : intermediación normalizada respecto al máximo (P1).
A_i : 1 si es punto de articulación, 0 en otro caso (P1).
M_i : participación normalizada en cortes mínimos de P6.
P_i : daño topológico por eliminación aislada:
      1 - |GCC(G-i)|/(N-1), normalizado respecto al máximo (P8).
C_i : daño secundario de cascada en P9 a tau=0.035:
      (fallos_totales - 1)/(N-1), normalizado respecto al máximo.

Justificación de pesos:
- 25% intermediación: importancia como corredor de tráfico/caminos mínimos.
- 10% articulación: indicador binario de single-point failure; peso menor porque
  parte de su efecto ya queda recogido cuantitativamente por P_i.
- 20% corte mínimo: incorpora capacidad y cuello de botella hacia Internet.
- 15% percolación: cuantifica cuánto se fragmenta la red por la falla aislada.
- 30% cascada: prioriza el daño dinámico secundario, que no aparece en las
  métricas estáticas y representa la consecuencia sistémica más directa.

Se incluye un análisis de sensibilidad con pesos iguales (20% cada componente)
para verificar que el top-10 no dependa por completo de una elección arbitraria.
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


# ================================================================
# Localización de resultados de problemas anteriores DENTRO de esta
# misma carpeta (red_ucuenca_fase5/). Deliberadamente NO se busca en
# ROOT.parent: el directorio del proyecto tiene carpetas hermanas de
# iteraciones previas (red_ucuenca_fase1..fase4) con archivos del
# mismo nombre pero de ejecuciones distintas; buscar fuera de ROOT
# podría hacer que P10 tomara silenciosamente resultados obsoletos de
# otra fase en vez de los que generan los scripts 06 y 09 de esta
# carpeta, rompiendo la reproducibilidad exigida por el enunciado
# (sección 8.1: "un resultado que no se puede regenerar ejecutando el
# repositorio no cuenta como resultado").
# ================================================================
def buscar_archivo(nombre, rutas_preferidas=None):
    """Busca un archivo requerido en rutas conocidas dentro de ROOT
    (esta carpeta de fase) y, como último recurso, en cualquier
    subcarpeta de ROOT. Nunca sale de ROOT."""

    if rutas_preferidas is None:
        rutas_preferidas = []

    for ruta in rutas_preferidas:
        ruta = Path(ruta)
        if ruta.exists():
            print(f"[OK] Encontrado: {ruta}")
            return ruta

    encontrados = list(ROOT.rglob(nombre))

    if not encontrados:
        raise FileNotFoundError(
            f"\nNo se encontró el archivo requerido:\n"
            f"    {nombre}\n\n"
            "Este archivo debe haber sido generado por un script anterior "
            "de esta misma carpeta (scripts/06_p6_flujo.py o "
            "scripts/09_p9_cascadas_sir.py). Ejecute el pipeline en orden "
            "(00 a 11) antes de correr P10.\n"
        )

    archivo = encontrados[0]
    print(f"[OK] Encontrado automáticamente: {archivo}")

    if len(encontrados) > 1:
        print(
            f"[AVISO] Hay {len(encontrados)} copias de {nombre} dentro de "
            f"esta carpeta. Se utilizará:\n    {archivo}"
        )

    return archivo


# ================================================================
# Datos base
# ================================================================
G = nx.Graph(
    nx.read_graphml(DATA / "red_ucuenca.graphml")
)

nodes = pd.read_csv(
    DATA / "red_ucuenca_nodes.csv"
)

meta = nodes.set_index("id")


# ================================================================
# Resultados provenientes de P6
# ================================================================
archivo_cortes = buscar_archivo(
    "05_cortes_minimos_por_campus.csv",
    [
        ROOT / "resultados" / "tablas"
             / "05_cortes_minimos_por_campus.csv",
    ]
)

cuts = pd.read_csv(archivo_cortes)


# ================================================================
# Resultados provenientes de P9
# ================================================================
# Nuestro P9 original genera 02_barrido_tau.csv.
archivo_cascadas = buscar_archivo(
    "02_barrido_tau.csv",
    [
        ROOT / "resultados" / "tablas"
             / "02_barrido_tau.csv",
    ]
)

cascade_scan = pd.read_csv(archivo_cascadas)

N = G.number_of_nodes()
assert N == 177
assert G.number_of_edges() == 209
assert nx.is_connected(G)

# ================================================================
# 1. Métricas provenientes de fases anteriores
# ================================================================

# P1
bet = nx.betweenness_centrality(G, normalized=True)
articulation = set(nx.articulation_points(G))

# P8: daño por eliminación individual.
percolation_damage = {}
isolated_from_gcc = {}

for node in G.nodes():
    H = G.copy()
    H.remove_node(node)

    gcc = max(
        (len(c) for c in nx.connected_components(H)),
        default=0
    )
    isolated = (N - 1) - gcc

    isolated_from_gcc[node] = isolated
    percolation_damage[node] = (
        1.0 - gcc / (N - 1)
    )

# P6: participación en cortes mínimos.
#
# Para cada campus, una arista del corte contribuye c_e / C_cut a cada uno
# de sus dos extremos. Después se suman las contribuciones de los cinco campus.
# Así se distingue una arista que constituye el 100% de un corte de otra que
# apenas representa una pequeña parte de un corte grande.
mincut_raw = {n: 0.0 for n in G.nodes()}
mincut_campuses = {n: set() for n in G.nodes()}
mincut_incident_edges = {n: 0 for n in G.nodes()}

for campus, sub in cuts.groupby("campus"):
    total_capacity = float(sub["capacidad_mbps"].sum())

    for _, r in sub.iterrows():
        contribution = float(r["capacidad_mbps"]) / total_capacity

        for node in [r["desde_S"], r["hacia_T"]]:
            mincut_raw[node] += contribution
            mincut_campuses[node].add(campus)
            mincut_incident_edges[node] += 1

# P9: daño de cascada cerca del margen crítico.
TAU_REF = 0.035
p9_tau = cascade_scan[
    np.isclose(cascade_scan["tau"], TAU_REF)
].set_index("trigger")

assert len(p9_tau) == N

cascade_secondary = {}
cascade_total = {}

for node in G.nodes():
    total_failed = int(p9_tau.loc[node, "fallos_totales"])
    cascade_total[node] = total_failed
    cascade_secondary[node] = max(
        0.0,
        (total_failed - 1) / (N - 1)
    )

# ================================================================
# 2. Normalización
# ================================================================
def normalize_max(values):
    maximum = max(values.values())

    if maximum <= 0:
        return {k: 0.0 for k in values}

    return {
        k: float(v) / maximum
        for k, v in values.items()
    }


B = normalize_max(bet)
M = normalize_max(mincut_raw)
P = normalize_max(percolation_damage)
C = normalize_max(cascade_secondary)

# ================================================================
# 3. Índice compuesto
# ================================================================
WEIGHTS = {
    "betweenness": 0.25,
    "articulation": 0.10,
    "mincut": 0.20,
    "percolation": 0.15,
    "cascade": 0.30,
}

assert math.isclose(sum(WEIGHTS.values()), 1.0)

def hierarchy_function(node):
    capa = str(meta.loc[node, "capa"])

    if node == "INTERNET-MPLS":
        return "Salida institucional / nube MPLS"

    if node.startswith("FORTIGATE"):
        return "Interconexión y seguridad perimetral"

    if node.startswith("PE"):
        return "Router PE / tránsito WAN"

    if node.startswith("ROUTER-CAMPUS"):
        return "Router WAN de campus"

    return {
        "core": "Núcleo (core)",
        "agregacion": "Agregación / distribución",
        "acceso": "Acceso",
        "wan": "WAN / intercampus",
        "interconexion": "Interconexión",
    }.get(capa, capa)


rows = []

for node in G.nodes():
    A = 1.0 if node in articulation else 0.0

    contribution_b = WEIGHTS["betweenness"] * B[node]
    contribution_a = WEIGHTS["articulation"] * A
    contribution_m = WEIGHTS["mincut"] * M[node]
    contribution_p = WEIGHTS["percolation"] * P[node]
    contribution_c = WEIGHTS["cascade"] * C[node]

    score = (
        contribution_b
        + contribution_a
        + contribution_m
        + contribution_p
        + contribution_c
    )

    rows.append({
        "nodo": node,
        "campus": meta.loc[node, "campus"],
        "capa": meta.loc[node, "capa"],
        "funcion_jerarquia": hierarchy_function(node),

        "betweenness": bet[node],
        "B_norm": B[node],
        "punto_articulacion": node in articulation,

        "mincut_score_raw": mincut_raw[node],
        "M_norm": M[node],
        "n_cortes_campus": len(mincut_campuses[node]),
        "campus_cortes": " | ".join(sorted(mincut_campuses[node])),
        "aristas_corte_incidentes": mincut_incident_edges[node],

        "nodos_fuera_GCC_si_falla": isolated_from_gcc[node],
        "percolation_damage": percolation_damage[node],
        "P_norm": P[node],

        "tau_cascada_referencia": TAU_REF,
        "fallos_totales_cascada": cascade_total[node],
        "fallos_secundarios_cascada": cascade_total[node] - 1,
        "cascade_secondary_fraction": cascade_secondary[node],
        "C_norm": C[node],

        "aporte_betweenness": contribution_b,
        "aporte_articulacion": contribution_a,
        "aporte_mincut": contribution_m,
        "aporte_percolacion": contribution_p,
        "aporte_cascada": contribution_c,

        "indice_criticidad": score,
    })

ranking = pd.DataFrame(rows).sort_values(
    ["indice_criticidad", "betweenness"],
    ascending=[False, False]
).reset_index(drop=True)

ranking.insert(0, "ranking", np.arange(1, len(ranking) + 1))
ranking.to_csv(TAB / "01_ranking_criticidad_completo.csv", index=False)

top10 = ranking.head(10).copy()

# ================================================================
# 4. Consecuencia estimada por nodo
# ================================================================
def estimated_consequence(r):
    pieces = []

    if r["nodos_fuera_GCC_si_falla"] > 0:
        pieces.append(
            f"puede dejar {int(r['nodos_fuera_GCC_si_falla'])} nodos "
            "fuera de la componente gigante"
        )

    if r["n_cortes_campus"] > 0:
        campuses = r["campus_cortes"].replace(" | ", ", ")
        pieces.append(
            f"participa en el corte mínimo de {campuses}"
        )

    if r["fallos_secundarios_cascada"] > 0:
        pieces.append(
            f"a τ={TAU_REF:.3f} puede inducir "
            f"{int(r['fallos_secundarios_cascada'])} fallos secundarios"
        )

    if not pieces:
        if r["betweenness"] >= ranking["betweenness"].quantile(0.90):
            pieces.append(
                "concentra rutas mínimas; su pérdida obliga a desviar tráfico "
                "y aumenta la carga de rutas alternativas"
            )
        else:
            pieces.append(
                "impacto principalmente local según las métricas incorporadas"
            )

    return "; ".join(pieces) + "."


top10["consecuencia_estimada"] = top10.apply(
    estimated_consequence,
    axis=1
)

top10.to_csv(TAB / "02_top10_fichas.csv", index=False)

# ================================================================
# 5. Sensibilidad a los pesos
# ================================================================
equal_rows = []

for _, r in ranking.iterrows():
    equal_score = (
        r["B_norm"]
        + (1.0 if r["punto_articulacion"] else 0.0)
        + r["M_norm"]
        + r["P_norm"]
        + r["C_norm"]
    ) / 5.0

    equal_rows.append({
        "nodo": r["nodo"],
        "indice_pesos_iguales": equal_score,
    })

equal_df = pd.DataFrame(equal_rows).sort_values(
    "indice_pesos_iguales",
    ascending=False
).reset_index(drop=True)
equal_df.insert(
    0,
    "ranking_pesos_iguales",
    np.arange(1, len(equal_df) + 1)
)

equal_df.to_csv(
    TAB / "03_sensibilidad_pesos_iguales.csv",
    index=False
)

top10_equal = set(equal_df.head(10)["nodo"])
top10_main = set(top10["nodo"])
overlap = len(top10_equal & top10_main)

pd.DataFrame([{
    "top10_comunes": overlap,
    "porcentaje_solapamiento": 100 * overlap / 10,
    "nodos_comunes": " | ".join(
        sorted(top10_equal & top10_main)
    ),
    "solo_indice_propuesto": " | ".join(
        sorted(top10_main - top10_equal)
    ),
    "solo_pesos_iguales": " | ".join(
        sorted(top10_equal - top10_main)
    ),
}]).to_csv(
    TAB / "04_resumen_sensibilidad.csv",
    index=False
)

# ================================================================
# 6. Evidencia textual resumida
# ================================================================
def evidence_string(r):
    evidence = [
        f"betweenness={r['betweenness']:.3f}"
    ]

    if r["punto_articulacion"]:
        evidence.append("punto de articulación")

    if r["n_cortes_campus"] > 0:
        evidence.append(
            f"corte mínimo ({r['campus_cortes']})"
        )

    if r["nodos_fuera_GCC_si_falla"] > 0:
        evidence.append(
            f"percolación: {int(r['nodos_fuera_GCC_si_falla'])} nodos "
            "fuera de GCC"
        )

    if r["fallos_secundarios_cascada"] > 0:
        evidence.append(
            f"cascada: +{int(r['fallos_secundarios_cascada'])} fallos"
        )

    return "; ".join(evidence)


top10["metricas_que_lo_senalan"] = top10.apply(
    evidence_string,
    axis=1
)

top10[
    [
        "ranking",
        "nodo",
        "campus",
        "funcion_jerarquia",
        "indice_criticidad",
        "metricas_que_lo_senalan",
        "consecuencia_estimada",
    ]
].to_csv(
    TAB / "05_top10_presentacion.csv",
    index=False
)

# ================================================================
# 7. Figuras
# ================================================================
plot_top = top10.sort_values(
    "indice_criticidad",
    ascending=True
)

plt.figure(figsize=(10, 6))
plt.barh(
    plot_top["nodo"],
    plot_top["indice_criticidad"]
)
plt.xlabel("Índice compuesto de criticidad")
plt.ylabel("Nodo")
plt.title("Top-10 de puntos críticos — Red UCuenca")
plt.tight_layout()
plt.savefig(
    FIG / "01_top10_indice_criticidad.png",
    dpi=190
)
plt.close()

# Contribuciones apiladas.
plt.figure(figsize=(11, 6))

left = np.zeros(len(top10))

for col, label in [
    ("aporte_betweenness", "Intermediación"),
    ("aporte_articulacion", "Articulación"),
    ("aporte_mincut", "Corte mínimo"),
    ("aporte_percolacion", "Percolación"),
    ("aporte_cascada", "Cascada"),
]:
    values = top10[col].to_numpy()
    plt.barh(
        top10["nodo"],
        values,
        left=left,
        label=label
    )
    left += values

plt.gca().invert_yaxis()
plt.xlabel("Contribución al índice")
plt.ylabel("Nodo")
plt.title("Composición del índice de criticidad")
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG / "02_componentes_indice_top10.png",
    dpi=190
)
plt.close()

# ================================================================
# 8. Consola
# ================================================================
print("=== TOP-10 P10 ===")
print(
    top10[
        [
            "ranking",
            "nodo",
            "campus",
            "funcion_jerarquia",
            "indice_criticidad",
            "betweenness",
            "punto_articulacion",
            "n_cortes_campus",
            "nodos_fuera_GCC_si_falla",
            "fallos_secundarios_cascada",
        ]
    ].to_string(index=False)
)

print(
    f"\nSensibilidad: {overlap}/10 nodos del top-10 "
    "se mantienen con pesos iguales."
)

print(
    "\nDisparador de cascada más fuerte a tau=0.035:"
)
strongest_cascade = ranking.sort_values(
    "fallos_secundarios_cascada",
    ascending=False
).iloc[0]

print(
    strongest_cascade[
        [
            "nodo",
            "campus",
            "fallos_totales_cascada",
            "indice_criticidad",
            "ranking",
        ]
    ].to_string()
)
