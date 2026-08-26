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

N_REALIZACIONES = 100
SEED_BASE = 2026

# ---------------------------------------------------------------------------
# 1. Carga
# ---------------------------------------------------------------------------
G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos = pd.read_csv(DATA / "red_ucuenca_nodes.csv")

n = G.number_of_nodes()
m = G.number_of_edges()

assert n == 177
assert m == 209
assert nx.number_connected_components(G) == 1

# ---------------------------------------------------------------------------
# 2. Funciones
# ---------------------------------------------------------------------------
def componente_gigante(H):
    """Devuelve una copia del subgrafo correspondiente a la mayor componente."""
    mayor = max(nx.connected_components(H), key=len)
    return H.subgraph(mayor).copy()


def metricas(H):
    """
    Calcula las métricas pedidas en P2.

    IMPORTANTE:
    Los modelos nulos pueden ser desconectados. Clustering y asortatividad
    se calculan sobre el grafo completo. Distancia media y diámetro se calculan
    sobre la componente gigante. Se reporta además qué fracción del grafo
    pertenece a dicha componente.
    """
    CG = componente_gigante(H)

    return {
        "clustering": nx.average_clustering(H),
        "distancia_media_CG": nx.average_shortest_path_length(CG),
        "diametro_CG": nx.diameter(CG),
        "asortatividad": nx.degree_assortativity_coefficient(H),
        "fraccion_componente_gigante": CG.number_of_nodes() / H.number_of_nodes(),
        "componentes": nx.number_connected_components(H),
    }


def modelo_configuracion_simple(G_original, seed):
    """
    Modelo nulo que conserva EXACTAMENTE la secuencia de grados observada.

    Se parte del grafo real y se aleatorizan las conexiones mediante intercambios
    dobles de aristas (degree-preserving rewiring). Esto mantiene el grafo simple
    y la secuencia de grados, pero destruye en gran medida la organización original.
    """
    H = G_original.copy()

    # 10*E intercambios proporcionan una aleatorización amplia para este tamaño.
    nx.double_edge_swap(
        H,
        nswap=10 * H.number_of_edges(),
        max_tries=200 * H.number_of_edges(),
        seed=seed,
    )

    assert sorted(dict(H.degree()).values()) == sorted(dict(G_original.degree()).values())
    assert H.number_of_edges() == G_original.number_of_edges()
    return H


# ---------------------------------------------------------------------------
# 3. Red real
# ---------------------------------------------------------------------------
real = metricas(G)
pd.DataFrame([{"modelo": "Red UCuenca", **real}]).to_csv(
    TAB / "01_metricas_red_real.csv", index=False
)

# ---------------------------------------------------------------------------
# 4. 100 Erdős–Rényi G(n,m)
# ---------------------------------------------------------------------------
filas = []

for i in range(N_REALIZACIONES):
    H = nx.gnm_random_graph(n, m, seed=SEED_BASE + i)
    filas.append({
        "modelo": "Erdos-Renyi G(n,m)",
        "realizacion": i + 1,
        **metricas(H),
    })

# ---------------------------------------------------------------------------
# 5. 100 modelos de configuración / grado preservado
# ---------------------------------------------------------------------------
for i in range(N_REALIZACIONES):
    H = modelo_configuracion_simple(G, seed=SEED_BASE + 1000 + i)
    filas.append({
        "modelo": "Configuracion (grado preservado)",
        "realizacion": i + 1,
        **metricas(H),
    })

sim = pd.DataFrame(filas)
sim.to_csv(TAB / "02_realizaciones_modelos_nulos.csv", index=False)

metricas_principales = [
    "clustering",
    "distancia_media_CG",
    "diametro_CG",
    "asortatividad",
    "fraccion_componente_gigante",
    "componentes",
]

resumen = (
    sim.groupby("modelo")[metricas_principales]
    .agg(["mean", "std"])
)

# Aplanar nombres de columnas.
resumen.columns = [f"{a}_{b}" for a, b in resumen.columns]
resumen = resumen.reset_index()
resumen.to_csv(TAB / "03_resumen_modelos_nulos.csv", index=False)

# Tabla comparativa más cómoda para el informe.
comparacion = []
for metrica in ["clustering", "distancia_media_CG", "diametro_CG", "asortatividad"]:
    fila = {
        "metrica": metrica,
        "red_real": real[metrica],
    }

    for modelo, prefijo in [
        ("Erdos-Renyi G(n,m)", "ER"),
        ("Configuracion (grado preservado)", "CFG"),
    ]:
        x = sim.loc[sim["modelo"] == modelo, metrica]
        media = x.mean()
        sd = x.std(ddof=1)
        fila[f"{prefijo}_media"] = media
        fila[f"{prefijo}_sd"] = sd
        fila[f"{prefijo}_z"] = (real[metrica] - media) / sd if sd > 0 else np.nan

    comparacion.append(fila)

pd.DataFrame(comparacion).to_csv(
    TAB / "04_comparacion_red_real_vs_nulos.csv", index=False
)

# ---------------------------------------------------------------------------
# 6. Barabási–Albert
# ---------------------------------------------------------------------------
# En el BA estándar el parámetro m_BA debe ser entero.
# m_BA=1 produce 176 enlaces y es el valor estándar más cercano a los 209
# enlaces de la red real. m_BA=2 produciría 350 enlaces, bastante más.
m_BA = 1
G_ba = nx.barabasi_albert_graph(n, m_BA, seed=SEED_BASE)
ba = metricas(G_ba)

ba_row = {
    "modelo": "Barabasi-Albert",
    "n": G_ba.number_of_nodes(),
    "aristas": G_ba.number_of_edges(),
    "m_BA": m_BA,
    **ba,
}
pd.DataFrame([ba_row]).to_csv(TAB / "05_barabasi_albert.csv", index=False)

# Distribución de grado BA vs real, para apoyar la discusión.
def dist_grado(H, nombre):
    vals = pd.Series(dict(H.degree()).values())
    frec = vals.value_counts().sort_index()
    return pd.DataFrame({
        "modelo": nombre,
        "grado": frec.index.astype(int),
        "frecuencia": frec.values.astype(int),
        "probabilidad": frec.values / H.number_of_nodes(),
    })

pd.concat([
    dist_grado(G, "Red UCuenca"),
    dist_grado(G_ba, "Barabasi-Albert"),
], ignore_index=True).to_csv(TAB / "06_distribucion_grado_real_vs_BA.csv", index=False)

# ---------------------------------------------------------------------------
# 7. Visualizaciones propias
# ---------------------------------------------------------------------------
# Layout reproducible.
pos = nx.spring_layout(G, seed=SEED_BASE, k=0.42, iterations=300)

meta = nodos.set_index("id")
campus = [meta.loc[node, "campus"] for node in G.nodes()]
campus_unicos = sorted(set(campus))
campus_a_num = {c: i for i, c in enumerate(campus_unicos)}
valores_campus = [campus_a_num[c] for c in campus]

# 7.1 Color por campus.
plt.figure(figsize=(13, 10))
nx.draw_networkx_edges(G, pos, alpha=0.24, width=0.7)
nx.draw_networkx_nodes(
    G,
    pos,
    node_size=34,
    node_color=valores_campus,
    cmap=plt.get_cmap("tab10", len(campus_unicos)),
)
# Leyenda simple por campus.
handles = []
for i, c in enumerate(campus_unicos):
    handles.append(
        plt.Line2D(
            [0], [0],
            marker="o",
            linestyle="",
            label=c,
            markerfacecolor=plt.get_cmap("tab10", len(campus_unicos))(i),
            markersize=7,
        )
    )
plt.legend(handles=handles, loc="best", fontsize=8, frameon=True)
plt.title("Red UCuenca — nodos coloreados por campus")
plt.axis("off")
plt.tight_layout()
plt.savefig(FIG / "01_red_por_campus.png", dpi=200)
plt.close()

# 7.2 Tamaño según intermediación.
bet = nx.betweenness_centrality(G, normalized=True)
bet_vals = np.array([bet[node] for node in G.nodes()])
# Escalamiento para visualización; todos los nodos conservan un tamaño mínimo.
sizes = 25 + 1900 * (bet_vals / bet_vals.max())

plt.figure(figsize=(13, 10))
nx.draw_networkx_edges(G, pos, alpha=0.22, width=0.7)
nodes_artist = nx.draw_networkx_nodes(
    G,
    pos,
    node_size=sizes,
    node_color=bet_vals,
    cmap="viridis",
)
plt.colorbar(nodes_artist, label="Centralidad de intermediación")
plt.title("Red UCuenca — tamaño de nodo proporcional a intermediación")
plt.axis("off")
plt.tight_layout()
plt.savefig(FIG / "02_red_por_intermediacion.png", dpi=200)
plt.close()

# 7.3 Comparación visual de las distribuciones de métricas de los modelos nulos.
for metrica, etiqueta in [
    ("clustering", "Clustering medio"),
    ("distancia_media_CG", "Distancia media en la componente gigante"),
    ("diametro_CG", "Diámetro de la componente gigante"),
    ("asortatividad", "Asortatividad por grado"),
]:
    er = sim.loc[sim["modelo"] == "Erdos-Renyi G(n,m)", metrica].values
    cfg = sim.loc[sim["modelo"] == "Configuracion (grado preservado)", metrica].values

    plt.figure(figsize=(8, 5))
    plt.boxplot([er, cfg])
    plt.xticks([1, 2], ["Erdős–Rényi", "Configuración"])
    plt.axhline(real[metrica], linestyle="--", label="Red UCuenca")
    plt.ylabel(etiqueta)
    plt.title(f"Red real frente a modelos nulos — {etiqueta}")
    plt.legend()
    plt.tight_layout()
    nombre = metrica.replace("_CG", "")
    plt.savefig(FIG / f"03_boxplot_{nombre}.png", dpi=180)
    plt.close()

# ---------------------------------------------------------------------------
# 8. Salida por consola
# ---------------------------------------------------------------------------
print("=== RED REAL ===")
for k, v in real.items():
    print(f"{k:32s}: {v:.6f}" if isinstance(v, float) else f"{k:32s}: {v}")

print("\n=== MODELOS NULOS: media ± desviación estándar ===")
for modelo in sim["modelo"].unique():
    print(f"\n{modelo}")
    sub = sim[sim["modelo"] == modelo]
    for c in metricas_principales:
        print(f"{c:32s}: {sub[c].mean():.6f} ± {sub[c].std(ddof=1):.6f}")

print("\n=== BARABÁSI–ALBERT ===")
print(f"n={G_ba.number_of_nodes()}, E={G_ba.number_of_edges()}, m_BA={m_BA}")
for k, v in ba.items():
    print(f"{k:32s}: {v:.6f}" if isinstance(v, float) else f"{k:32s}: {v}")

print(f"\nResultados guardados en: {ROOT / 'resultados'}")
