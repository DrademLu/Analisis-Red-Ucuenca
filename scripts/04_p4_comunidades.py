"""
P4 — Comunidades y modularidad sobre la red UCuenca.

Fuentes del repositorio del módulo reutilizadas/adaptadas:
1) Louvain / visualización:
   https://github.com/fabianastudillo/ComplexNetworks/blob/main/intro/codes/gen_visualizacion-louvain.jl
   Se reutiliza la idea de detectar comunidades con Louvain, calcular modularidad
   y visualizar los nodos por comunidad. La implementación concreta aquí usa
   NetworkX para poder repetir Louvain con semillas controladas.

2) K-means desde cero:
   https://github.com/fabianastudillo/ComplexNetworks/blob/main/algoritmos/kmeans/ejemplo1.jl
   Se adapta a Python la estructura del algoritmo del ejemplo del módulo:
   distancia euclídea al cuadrado, inicialización k-means++, asignación,
   actualización de centroides, WCSS y criterio de convergencia.

No se reutilizan resultados del repositorio; todo se calcula sobre red_ucuenca.
"""

from pathlib import Path
from itertools import combinations

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import (
    adjusted_rand_score,
    normalized_mutual_info_score,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TAB = ROOT / "resultados" / "tablas"
FIG = ROOT / "resultados" / "figuras"

TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

SEEDS = [11, 22, 33, 44, 55]
RESOLUCIONES = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
SEED_LAYOUT = 2026

# ---------------------------------------------------------------------
# 1. Carga
# ---------------------------------------------------------------------
G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
nodos_df = pd.read_csv(DATA / "red_ucuenca_nodes.csv")

assert G.number_of_nodes() == 177
assert G.number_of_edges() == 209
assert nx.is_connected(G)

node_order = list(G.nodes())
meta = nodos_df.set_index("id").loc[node_order].copy()
campus_labels = meta["campus"].astype(str).tolist()
campus_unicos = sorted(meta["campus"].unique())

# ---------------------------------------------------------------------
# 2. Utilidades de partición
# ---------------------------------------------------------------------
def comunidades_a_labels(comunidades, node_order):
    """Convierte una lista de sets de nodos a un vector de etiquetas enteras."""
    mapa = {}
    for cid, comunidad in enumerate(comunidades):
        for n in comunidad:
            mapa[n] = cid
    return np.array([mapa[n] for n in node_order], dtype=int), mapa


def labels_a_comunidades(labels, node_order):
    """Convierte vector de etiquetas a lista de sets."""
    grupos = {}
    for n, lab in zip(node_order, labels):
        grupos.setdefault(int(lab), set()).add(n)
    return list(grupos.values())


def matriz_confusion_particion(labels_comunidad, campus_labels):
    """Matriz comunidad x campus."""
    df = pd.DataFrame({
        "comunidad": labels_comunidad,
        "campus": campus_labels,
    })
    tabla = pd.crosstab(df["comunidad"], df["campus"])
    return tabla


# ---------------------------------------------------------------------
# 3. Louvain con cinco semillas
# ---------------------------------------------------------------------
runs = []
particiones_louvain = {}

for seed in SEEDS:
    comunidades = nx.community.louvain_communities(
        G, seed=seed, resolution=1.0
    )
    labels, _ = comunidades_a_labels(comunidades, node_order)
    Q = nx.community.modularity(G, comunidades, resolution=1.0)

    nmi_campus = normalized_mutual_info_score(campus_labels, labels)
    ari_campus = adjusted_rand_score(campus_labels, labels)

    runs.append({
        "seed": seed,
        "n_comunidades": len(comunidades),
        "modularidad_Q": Q,
        "NMI_vs_campus": nmi_campus,
        "ARI_vs_campus": ari_campus,
    })
    particiones_louvain[seed] = labels

runs_df = pd.DataFrame(runs).sort_values("seed")
runs_df.to_csv(TAB / "01_louvain_cinco_semillas.csv", index=False)

# Estabilidad entre ejecuciones: NMI y ARI por pares de semillas.
estabilidad = []
for s1, s2 in combinations(SEEDS, 2):
    l1 = particiones_louvain[s1]
    l2 = particiones_louvain[s2]
    estabilidad.append({
        "seed_1": s1,
        "seed_2": s2,
        "NMI_entre_particiones": normalized_mutual_info_score(l1, l2),
        "ARI_entre_particiones": adjusted_rand_score(l1, l2),
    })

est_df = pd.DataFrame(estabilidad)
est_df.to_csv(TAB / "02_estabilidad_louvain.csv", index=False)

# Elegimos como partición principal la de mayor modularidad.
best_row = runs_df.sort_values(
    ["modularidad_Q", "seed"], ascending=[False, True]
).iloc[0]
BEST_SEED = int(best_row["seed"])
louvain_labels = particiones_louvain[BEST_SEED]
louvain_comunidades = labels_a_comunidades(louvain_labels, node_order)
K_LOUVAIN = len(louvain_comunidades)

# ---------------------------------------------------------------------
# 4. Comparación Louvain vs campus
# ---------------------------------------------------------------------
conf = matriz_confusion_particion(louvain_labels, campus_labels)
conf.to_csv(TAB / "03_matriz_confusion_louvain_vs_campus.csv")

asignaciones = meta.reset_index()[["id", "label", "campus", "capa"]].copy()
asignaciones["comunidad_louvain"] = louvain_labels

# Campus dominante por comunidad y discrepancias.
dominante = {}
pureza = {}
for cid in sorted(set(louvain_labels)):
    sub = asignaciones[asignaciones["comunidad_louvain"] == cid]
    counts = sub["campus"].value_counts()
    dominante[cid] = counts.index[0]
    pureza[cid] = counts.iloc[0] / len(sub)

asignaciones["campus_dominante_comunidad"] = asignaciones[
    "comunidad_louvain"
].map(dominante)
asignaciones["coincide_campus_dominante"] = (
    asignaciones["campus"] == asignaciones["campus_dominante_comunidad"]
)

asignaciones.to_csv(TAB / "04_asignaciones_louvain.csv", index=False)

discrepancias = asignaciones[
    ~asignaciones["coincide_campus_dominante"]
].copy()
discrepancias.to_csv(TAB / "05_nodos_discrepantes_campus_louvain.csv", index=False)

resumen_comunidades = []
for cid in sorted(set(louvain_labels)):
    sub = asignaciones[asignaciones["comunidad_louvain"] == cid]
    counts = sub["campus"].value_counts()
    resumen_comunidades.append({
        "comunidad": cid,
        "tamano": len(sub),
        "campus_dominante": counts.index[0],
        "pureza_campus": counts.iloc[0] / len(sub),
        "n_campus_presentes": sub["campus"].nunique(),
        "composicion": "; ".join(f"{c}:{n}" for c, n in counts.items()),
    })

res_com_df = pd.DataFrame(resumen_comunidades)
res_com_df.to_csv(TAB / "06_resumen_comunidades_louvain.csv", index=False)

# ---------------------------------------------------------------------
# 5. Embedding espectral
# ---------------------------------------------------------------------
# Laplaciano normalizado L = I - D^{-1/2} A D^{-1/2}
# Se toman los K primeros autovectores no triviales.
A = nx.to_numpy_array(G, nodelist=node_order, dtype=float)
deg = A.sum(axis=1)
D_inv_sqrt = np.diag(np.where(deg > 0, 1.0 / np.sqrt(deg), 0.0))
Lnorm = np.eye(len(node_order)) - D_inv_sqrt @ A @ D_inv_sqrt

eigvals, eigvecs = np.linalg.eigh(Lnorm)
idx = np.argsort(eigvals)
eigvals = eigvals[idx]
eigvecs = eigvecs[:, idx]

# Primer autovector corresponde aproximadamente al autovalor 0 y se descarta.
dim_embedding = min(K_LOUVAIN, len(node_order) - 1)
X = eigvecs[:, 1:1 + dim_embedding].copy()

# Normalización por fila típica en clustering espectral.
norms = np.linalg.norm(X, axis=1, keepdims=True)
X = np.divide(X, norms, out=np.zeros_like(X), where=norms != 0)

pd.DataFrame(
    X,
    index=node_order,
    columns=[f"z{i+1}" for i in range(X.shape[1])]
).to_csv(TAB / "07_embedding_espectral.csv")

# ---------------------------------------------------------------------
# 6. K-means desde cero, adaptado del ejemplo Julia del módulo
# ---------------------------------------------------------------------
def dist2(x, mu):
    """Distancia euclídea al cuadrado."""
    d = x - mu
    return float(d @ d)


def init_plusplus(X, K, rng):
    """Inicialización K-means++."""
    n = X.shape[0]
    centers = [X[rng.integers(0, n)].copy()]

    for _ in range(1, K):
        D = np.array([
            min(dist2(X[i], c) for c in centers)
            for i in range(n)
        ], dtype=float)

        total = D.sum()
        if total <= 0:
            j = int(rng.integers(0, n))
        else:
            probs = D / total
            j = int(rng.choice(n, p=probs))

        centers.append(X[j].copy())

    return np.vstack(centers)


def assign_clusters(X, centers):
    """Asigna cada punto al centroide euclídeo más cercano."""
    labels = np.empty(X.shape[0], dtype=int)
    for i in range(X.shape[0]):
        dists = [dist2(X[i], c) for c in centers]
        labels[i] = int(np.argmin(dists))
    return labels


def update_centroids(X, labels, K, rng):
    """Actualiza centroides; reinicializa clusters vacíos."""
    centers = np.empty((K, X.shape[1]), dtype=float)

    for k in range(K):
        mask = labels == k
        if not np.any(mask):
            centers[k] = X[rng.integers(0, X.shape[0])]
        else:
            centers[k] = X[mask].mean(axis=0)

    return centers


def wcss(X, centers, labels):
    return sum(dist2(X[i], centers[labels[i]]) for i in range(X.shape[0]))


def my_kmeans(X, K, max_iter=300, tol=1e-6, seed=42):
    """
    Adaptación a Python de algoritmos/kmeans/ejemplo1.jl.
    Usa K-means++, asignación euclídea, actualización por media y WCSS.
    """
    rng = np.random.default_rng(seed)
    centers = init_plusplus(X, K, rng)
    history = []

    for it in range(1, max_iter + 1):
        old = centers.copy()
        labels = assign_clusters(X, centers)
        centers = update_centroids(X, labels, K, rng)
        J = wcss(X, centers, labels)
        history.append(J)

        movement = np.linalg.norm(centers - old, axis=1)
        if np.all(movement < tol):
            return {
                "labels": labels,
                "centroids": centers,
                "wcss_history": history,
                "iterations": it,
            }

    return {
        "labels": labels,
        "centroids": centers,
        "wcss_history": history,
        "iterations": max_iter,
    }


# Para reducir dependencia de una inicialización concreta, ejecutamos varias
# semillas y conservamos la solución con menor WCSS.
kmeans_runs = []
best_km = None

for seed in SEEDS:
    result = my_kmeans(X, K_LOUVAIN, seed=seed)
    labels = result["labels"]
    communities = labels_a_comunidades(labels, node_order)
    Q = nx.community.modularity(G, communities)

    row = {
        "seed": seed,
        "K": K_LOUVAIN,
        "iteraciones": result["iterations"],
        "WCSS": result["wcss_history"][-1],
        "modularidad_Q": Q,
        "NMI_vs_Louvain": normalized_mutual_info_score(
            louvain_labels, labels
        ),
        "ARI_vs_Louvain": adjusted_rand_score(
            louvain_labels, labels
        ),
        "NMI_vs_campus": normalized_mutual_info_score(
            campus_labels, labels
        ),
        "ARI_vs_campus": adjusted_rand_score(
            campus_labels, labels
        ),
    }
    kmeans_runs.append(row)

    if best_km is None or row["WCSS"] < best_km["row"]["WCSS"]:
        best_km = {"row": row, "result": result}

km_df = pd.DataFrame(kmeans_runs)
km_df.to_csv(TAB / "08_kmeans_cinco_semillas.csv", index=False)

kmeans_labels = best_km["result"]["labels"]
km_asig = asignaciones[
    ["id", "label", "campus", "capa", "comunidad_louvain"]
].copy()
km_asig["cluster_kmeans"] = kmeans_labels
km_asig.to_csv(TAB / "09_asignaciones_louvain_kmeans.csv", index=False)

# ---------------------------------------------------------------------
# 7. Limitación de resolución de la modularidad
# ---------------------------------------------------------------------
resolution_rows = []
resolution_partitions = {}

# Misma semilla para aislar principalmente el efecto de gamma.
for gamma in RESOLUCIONES:
    comunidades = nx.community.louvain_communities(
        G, seed=BEST_SEED, resolution=gamma
    )
    labels, _ = comunidades_a_labels(comunidades, node_order)

    resolution_rows.append({
        "resolution_gamma": gamma,
        "n_comunidades": len(comunidades),
        "Q_con_gamma": nx.community.modularity(
            G, comunidades, resolution=gamma
        ),
        "Q_estandar_gamma1": nx.community.modularity(
            G, comunidades, resolution=1.0
        ),
        "NMI_vs_particion_gamma1": normalized_mutual_info_score(
            louvain_labels, labels
        ),
        "ARI_vs_particion_gamma1": adjusted_rand_score(
            louvain_labels, labels
        ),
    })
    resolution_partitions[gamma] = labels

res_gamma_df = pd.DataFrame(resolution_rows)
res_gamma_df.to_csv(TAB / "10_sensibilidad_resolucion_louvain.csv", index=False)

# Evidencia de qué comunidades gamma=1 se subdividen a gamma=1.5 y 2.0.
evidencia_split = []
for gamma in [1.25, 1.5, 2.0]:
    labels_g = resolution_partitions[gamma]
    for cid in sorted(set(louvain_labels)):
        mask = louvain_labels == cid
        sublabels = labels_g[mask]
        counts = pd.Series(sublabels).value_counts()
        evidencia_split.append({
            "comunidad_gamma1": cid,
            "tamano_gamma1": int(mask.sum()),
            "gamma_comparado": gamma,
            "n_subcomunidades": int(len(counts)),
            "tamano_mayor_subgrupo": int(counts.iloc[0]),
            "fraccion_mayor_subgrupo": float(counts.iloc[0] / mask.sum()),
        })

split_df = pd.DataFrame(evidencia_split)
split_df.to_csv(TAB / "11_evidencia_limitacion_resolucion.csv", index=False)


# ---------------------------------------------------------------------
# 7.1 Modularidad de particiones naturales para comparación
# ---------------------------------------------------------------------
campus_communities = [
    set(group["id"])
    for _, group in nodos_df.groupby("campus")
]
Q_campus = nx.community.modularity(G, campus_communities)

campus_capa_communities = [
    set(group["id"])
    for _, group in nodos_df.groupby(["campus", "capa"])
]
Q_campus_capa = nx.community.modularity(G, campus_capa_communities)

pd.DataFrame([
    {
        "particion": "Louvain principal",
        "n_grupos": K_LOUVAIN,
        "Q": float(best_row["modularidad_Q"]),
    },
    {
        "particion": "Campus",
        "n_grupos": len(campus_communities),
        "Q": Q_campus,
    },
    {
        "particion": "Campus + capa",
        "n_grupos": len(campus_capa_communities),
        "Q": Q_campus_capa,
    },
]).to_csv(
    TAB / "12_modularidad_particiones_naturales.csv",
    index=False
)

# ---------------------------------------------------------------------
# 8. Visualizaciones
# ---------------------------------------------------------------------
pos = nx.spring_layout(G, seed=SEED_LAYOUT, k=0.45, iterations=300)

# Red Louvain
plt.figure(figsize=(13, 10))
nx.draw_networkx_edges(G, pos, alpha=0.20, width=0.7)
nx.draw_networkx_nodes(
    G, pos,
    node_size=45,
    node_color=louvain_labels,
    cmap="tab20"
)
plt.title(
    f"Louvain — seed={BEST_SEED}, K={K_LOUVAIN}, "
    f"Q={best_row['modularidad_Q']:.3f}"
)
plt.axis("off")
plt.tight_layout()
plt.savefig(FIG / "01_red_louvain.png", dpi=190)
plt.close()

# Red K-means espectral
plt.figure(figsize=(13, 10))
nx.draw_networkx_edges(G, pos, alpha=0.20, width=0.7)
nx.draw_networkx_nodes(
    G, pos,
    node_size=45,
    node_color=kmeans_labels,
    cmap="tab20"
)
plt.title(
    f"K-means sobre embedding espectral — K={K_LOUVAIN}"
)
plt.axis("off")
plt.tight_layout()
plt.savefig(FIG / "02_red_kmeans_espectral.png", dpi=190)
plt.close()

# Matriz de confusión
plt.figure(figsize=(12, 6))
mat = conf.to_numpy()
plt.imshow(mat, aspect="auto")
plt.colorbar(label="Número de nodos")
plt.xticks(
    range(len(conf.columns)),
    conf.columns,
    rotation=35,
    ha="right",
    fontsize=8
)
plt.yticks(range(len(conf.index)), [f"C{c}" for c in conf.index])
plt.xlabel("Campus")
plt.ylabel("Comunidad Louvain")
plt.title("Matriz comunidad × campus")
plt.tight_layout()
plt.savefig(FIG / "03_matriz_confusion_louvain_campus.png", dpi=190)
plt.close()

# Estabilidad de Louvain por semilla
plt.figure(figsize=(8, 5))
plt.plot(
    runs_df["seed"].astype(str),
    runs_df["modularidad_Q"],
    marker="o"
)
plt.xlabel("Semilla")
plt.ylabel("Modularidad Q")
plt.title("Estabilidad de Louvain: modularidad por semilla")
plt.tight_layout()
plt.savefig(FIG / "04_estabilidad_louvain_Q.png", dpi=180)
plt.close()

# Sensibilidad a gamma
plt.figure(figsize=(8, 5))
plt.plot(
    res_gamma_df["resolution_gamma"],
    res_gamma_df["n_comunidades"],
    marker="o"
)
plt.xlabel("Parámetro de resolución γ")
plt.ylabel("Número de comunidades")
plt.title("Sensibilidad de Louvain al parámetro de resolución")
plt.tight_layout()
plt.savefig(FIG / "05_resolucion_num_comunidades.png", dpi=180)
plt.close()

# ---------------------------------------------------------------------
# 9. Consola
# ---------------------------------------------------------------------
print("=== LOUVAIN: CINCO SEMILLAS ===")
print(runs_df.to_string(index=False))

print("\n=== ESTABILIDAD ENTRE PARTICIONES LOUVAIN ===")
print(est_df.describe().loc[["mean", "min", "max"],
                            ["NMI_entre_particiones",
                             "ARI_entre_particiones"]])

print("\n=== PARTICIÓN PRINCIPAL ===")
print(f"Best seed: {BEST_SEED}")
print(f"Comunidades: {K_LOUVAIN}")
print(f"Q: {best_row['modularidad_Q']:.6f}")
print(f"NMI vs campus: {best_row['NMI_vs_campus']:.6f}")
print(f"ARI vs campus: {best_row['ARI_vs_campus']:.6f}")
print(f"Nodos fuera del campus dominante de su comunidad: {len(discrepancias)}")

print("\nResumen de comunidades:")
print(res_com_df.to_string(index=False))

print("\n=== K-MEANS ESPECTRAL ===")
print(km_df.to_string(index=False))
print("\nMejor K-means por WCSS:")
print(best_km["row"])

print("\n=== RESOLUCIÓN DE MODULARIDAD ===")
print(res_gamma_df.to_string(index=False))

print("\nComunidades gamma=1 que más se subdividen al aumentar gamma:")
print(
    split_df.sort_values(
        ["gamma_comparado", "n_subcomunidades", "tamano_gamma1"],
        ascending=[True, False, False]
    ).head(15).to_string(index=False)
)

print(f"\nResultados guardados en {ROOT / 'resultados'}")
