from pathlib import Path
import sys
from collections import Counter

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.red import cargar_datos, verificar_pipeline

TAB = ROOT / "resultados" / "tablas"
FIG = ROOT / "resultados" / "figuras"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

G, nodos, aristas = cargar_datos()

# No continuar si la carga no coincide con el Anexo A.
_, ok = verificar_pipeline(G, nodos, aristas)
if not ok:
    raise RuntimeError("El pipeline no coincide con los valores de referencia.")

info = nodos.set_index("id").to_dict("index")

# ------------------------------------------------------------------
# P1.1 Medidas fundamentales
# ------------------------------------------------------------------
grados = dict(G.degree())
valores_grado = np.array(list(grados.values()), dtype=float)

resumen = {
    "nodos": G.number_of_nodes(),
    "aristas": G.number_of_edges(),
    "densidad": nx.density(G),
    "componentes_conexas": nx.number_connected_components(G),
    "tamano_mayor_componente": len(max(nx.connected_components(G), key=len)),
    "grado_medio": valores_grado.mean(),
    "grado_minimo": valores_grado.min(),
    "grado_maximo": valores_grado.max(),
}

# ------------------------------------------------------------------
# P1.2 Distribución de grado
# ------------------------------------------------------------------
dist = Counter(int(k) for k in valores_grado)
dist_df = pd.DataFrame(
    sorted(dist.items()), columns=["grado", "frecuencia"]
)
dist_df["probabilidad"] = dist_df["frecuencia"] / G.number_of_nodes()
dist_df.to_csv(TAB / "01_distribucion_grado.csv", index=False)

plt.figure(figsize=(8, 5))
plt.hist(valores_grado, bins=np.arange(valores_grado.min(), valores_grado.max() + 2) - 0.5)
plt.xlabel("Grado k")
plt.ylabel("Número de nodos")
plt.title("Distribución de grado — Red UCuenca")
plt.tight_layout()
plt.savefig(FIG / "01_histograma_grado.png", dpi=180)
plt.close()

plt.figure(figsize=(8, 5))
plt.loglog(dist_df["grado"], dist_df["probabilidad"], marker="o", linestyle="none")
plt.xlabel("Grado k (escala log)")
plt.ylabel("P(k) (escala log)")
plt.title("Distribución de grado en escala log-log — Red UCuenca")
plt.tight_layout()
plt.savefig(FIG / "02_grado_loglog.png", dpi=180)
plt.close()

# ------------------------------------------------------------------
# P1.2b Prueba estadística de ley de potencia (¿"red libre de escala"?)
#
# Metodología de Clauset, Shalizi & Newman (2009), "Power-law
# distributions in empirical data": MLE discreta de alpha, selección
# de x_min por mínima distancia KS y prueba de bondad de ajuste por
# bootstrap semi-paramétrico, comparada contra una alternativa
# exponencial (geométrica discreta) vía AIC. Implementada aquí desde
# cero con numpy/scipy (sin el paquete `powerlaw`) para no añadir
# dependencias nuevas al proyecto.
# ------------------------------------------------------------------
from scipy.special import zeta as _zeta


def _powerlaw_alpha_mle(cola, xmin):
    xmin_m = xmin - 0.5
    n = len(cola)
    return 1.0 + n / np.sum(np.log(cola / xmin_m))


def _powerlaw_ks(cola, xmin, alpha):
    xs = np.sort(cola)
    n = len(xs)
    s_emp = (n - np.arange(n)) / n  # P(X >= x_(i)) empírica
    s_fit = _zeta(alpha, xs) / _zeta(alpha, xmin)
    return float(np.max(np.abs(s_emp - s_fit)))


def _mejor_xmin(grados, min_cola=8):
    """Escanea x_min candidatos y devuelve el que minimiza la distancia KS."""
    candidatos = sorted(set(int(k) for k in grados if k >= 1))
    mejor = None
    for xmin in candidatos:
        cola = grados[grados >= xmin]
        if len(cola) < min_cola:
            continue
        alpha = _powerlaw_alpha_mle(cola, xmin)
        if alpha <= 1.0:
            continue
        d = _powerlaw_ks(cola, xmin, alpha)
        if mejor is None or d < mejor[2]:
            mejor = (xmin, alpha, d)
    return mejor  # (xmin, alpha, D_ks) o None


def _muestra_powerlaw_discreta(n, xmin, alpha, rng):
    r = rng.uniform(size=n)
    xmin_m = xmin - 0.5
    return np.floor(xmin_m * (1 - r) ** (-1.0 / (alpha - 1.0)) + 0.5)


def _bootstrap_gof(grados, xmin_obs, alpha_obs, d_obs, rng, n_rep=1000, min_cola=8):
    """p-valor semi-paramétrico: fracción de réplicas con ajuste tan malo
    o peor que el observado, generando la cola con el modelo de potencia
    ajustado y el cuerpo con remuestreo de los datos reales por debajo de x_min."""
    n = len(grados)
    debajo = grados[grados < xmin_obs]
    p_cola = (n - len(debajo)) / n
    peores_o_iguales = 0
    validos = 0
    for _ in range(n_rep):
        usar_cola = rng.uniform(size=n) < p_cola
        n_sim_cola = int(usar_cola.sum())
        sim_cola = _muestra_powerlaw_discreta(n_sim_cola, xmin_obs, alpha_obs, rng)
        sim_debajo = (
            rng.choice(debajo, size=n - n_sim_cola, replace=True)
            if (n - n_sim_cola) > 0 and len(debajo) > 0
            else np.array([])
        )
        muestra = np.concatenate([sim_cola, sim_debajo])
        resultado = _mejor_xmin(muestra, min_cola=min_cola)
        if resultado is None:
            continue
        validos += 1
        _, _, d_sim = resultado
        if d_sim >= d_obs:
            peores_o_iguales += 1
    return peores_o_iguales / validos if validos else float("nan")


rng_pl = np.random.default_rng(2026)
ajuste = _mejor_xmin(valores_grado, min_cola=8)

if ajuste is None:
    # Cola insuficiente para cualquier x_min con al menos 8 nodos: no hay
    # base estadística siquiera para intentar el ajuste.
    powerlaw_df = pd.DataFrame([{
        "xmin_optimo": np.nan, "alpha_MLE": np.nan, "n_nodos_en_cola": 0,
        "grado_maximo": int(valores_grado.max()), "decadas_de_grado": np.nan,
        "D_ks_observado": np.nan, "p_valor_bootstrap_gof": np.nan,
        "logL_powerlaw": np.nan, "logL_exponencial": np.nan,
        "AIC_powerlaw": np.nan, "AIC_exponencial": np.nan,
        "modelo_preferido_por_AIC": "ninguno (cola insuficiente)",
        "conclusion": "Sin datos suficientes en la cola para ajustar una ley de potencia con mínimo de 8 nodos.",
    }])
else:
    xmin_opt, alpha_opt, d_ks_opt = ajuste
    cola_opt = valores_grado[valores_grado >= xmin_opt]
    n_cola = len(cola_opt)

    p_valor_gof = _bootstrap_gof(valores_grado, xmin_opt, alpha_opt, d_ks_opt, rng_pl, n_rep=1000)

    # Alternativa: geométrica discreta (equivalente discreto de la exponencial)
    lam = np.log(1.0 + n_cola / np.sum(cola_opt - xmin_opt))
    loglik_pl = -alpha_opt * np.sum(np.log(cola_opt)) - n_cola * np.log(_zeta(alpha_opt, xmin_opt))
    loglik_exp = n_cola * np.log(1.0 - np.exp(-lam)) - lam * np.sum(cola_opt - xmin_opt)
    aic_pl = 2 * 1 - 2 * loglik_pl
    aic_exp = 2 * 1 - 2 * loglik_exp
    decadas = np.log10(valores_grado.max() / xmin_opt) if xmin_opt > 0 else np.nan

    rechazar_powerlaw = (
        (not np.isnan(p_valor_gof) and p_valor_gof < 0.1)
        or aic_exp < aic_pl
        or decadas < 1.0
        or n_cola < 20
    )
    conclusion_libre_escala = (
        "NO se sostiene estadísticamente la afirmación de 'red libre de escala': "
        f"el ajuste cubre menos de una década de grados ({decadas:.2f}) y/o el "
        "modelo de potencia no supera la prueba de bondad de ajuste o pierde "
        "frente a la alternativa exponencial."
        if rechazar_powerlaw else
        "La hipótesis de ley de potencia no se rechaza con la evidencia disponible "
        "(p-valor de bondad de ajuste >= 0.1 y AIC favorable), aunque el tamaño "
        "de la red limita la certeza de la conclusión."
    )

    powerlaw_df = pd.DataFrame([{
        "xmin_optimo": xmin_opt,
        "alpha_MLE": alpha_opt,
        "n_nodos_en_cola": n_cola,
        "grado_maximo": int(valores_grado.max()),
        "decadas_de_grado": decadas,
        "D_ks_observado": d_ks_opt,
        "p_valor_bootstrap_gof": p_valor_gof,
        "logL_powerlaw": loglik_pl,
        "logL_exponencial": loglik_exp,
        "AIC_powerlaw": aic_pl,
        "AIC_exponencial": aic_exp,
        "modelo_preferido_por_AIC": "powerlaw" if aic_pl < aic_exp else "exponencial",
        "conclusion": conclusion_libre_escala,
    }])

    # Log-log con el ajuste superpuesto (reemplaza la figura anterior).
    plt.figure(figsize=(8, 5))
    plt.loglog(
        dist_df["grado"], dist_df["probabilidad"],
        marker="o", linestyle="none", label="P(k) empírico",
    )
    xs_fit = np.arange(xmin_opt, int(valores_grado.max()) + 1)
    pmf_fit = (xs_fit.astype(float) ** (-alpha_opt)) / _zeta(alpha_opt, xmin_opt)
    fila_xmin = dist_df.loc[dist_df["grado"] == xmin_opt, "probabilidad"]
    escala = float(fila_xmin.iloc[0]) / pmf_fit[0] if len(fila_xmin) else 1.0
    plt.loglog(
        xs_fit, pmf_fit * escala, linestyle="--", color="firebrick",
        label=f"Ajuste ley de potencia (α={alpha_opt:.2f}, x_min={xmin_opt})",
    )
    plt.xlabel("Grado k (escala log)")
    plt.ylabel("P(k) (escala log)")
    plt.title("Distribución de grado y ajuste de ley de potencia — Red UCuenca")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "02_grado_loglog.png", dpi=180)
    plt.close()

powerlaw_df.to_csv(TAB / "11_prueba_ley_potencia.csv", index=False)

# ------------------------------------------------------------------
# P1.3 Centralidades
# ------------------------------------------------------------------
centralidades = {
    "grado": nx.degree_centrality(G),
    "intermediacion": nx.betweenness_centrality(G, normalized=True),
    "cercania": nx.closeness_centrality(G),
    "vector_propio": nx.eigenvector_centrality(G, max_iter=5000, tol=1e-10),
}

filas_todos = []
for nodo in G.nodes():
    filas_todos.append({
        "nodo": nodo,
        "campus": info[nodo]["campus"],
        "capa": info[nodo]["capa"],
        "grado_absoluto": grados[nodo],
        "centralidad_grado": centralidades["grado"][nodo],
        "intermediacion": centralidades["intermediacion"][nodo],
        "cercania": centralidades["cercania"][nodo],
        "vector_propio": centralidades["vector_propio"][nodo],
    })
pd.DataFrame(filas_todos).to_csv(TAB / "02_centralidades_todos.csv", index=False)

# Top-10 de las cuatro medidas en una sola tabla comparativa.
ordenes = {}
for nombre, valores in centralidades.items():
    ordenes[nombre] = sorted(valores.items(), key=lambda x: x[1], reverse=True)[:10]

top10 = []
for i in range(10):
    fila = {"ranking": i + 1}
    for nombre in ["grado", "intermediacion", "cercania", "vector_propio"]:
        nodo, valor = ordenes[nombre][i]
        fila[f"{nombre}_nodo"] = nodo
        fila[f"{nombre}_valor"] = valor
        fila[f"{nombre}_campus"] = info[nodo]["campus"]
        fila[f"{nombre}_capa"] = info[nodo]["capa"]
    top10.append(fila)
pd.DataFrame(top10).to_csv(TAB / "03_top10_centralidades.csv", index=False)

# ------------------------------------------------------------------
# P1.4 Clustering, diámetro, distancia y asortatividad
# ------------------------------------------------------------------
resumen.update({
    "clustering_medio": nx.average_clustering(G),
    "diametro": nx.diameter(G),
    "distancia_media": nx.average_shortest_path_length(G),
    "asortatividad_grado": nx.degree_assortativity_coefficient(G),
})

# ------------------------------------------------------------------
# P1.5 Puntos de articulación y puentes
# ------------------------------------------------------------------
articulaciones = list(nx.articulation_points(G))
puentes = list(nx.bridges(G))

resumen["puntos_articulacion"] = len(articulaciones)
resumen["puentes"] = len(puentes)

art_df = pd.DataFrame([
    {
        "nodo": n,
        "campus": info[n]["campus"],
        "capa": info[n]["capa"],
        "grado": grados[n],
        "intermediacion": centralidades["intermediacion"][n],
    }
    for n in articulaciones
]).sort_values("intermediacion", ascending=False)
art_df.to_csv(TAB / "04_puntos_articulacion.csv", index=False)

conteo_art = (
    art_df.groupby(["campus", "capa"])
    .size()
    .reset_index(name="cantidad")
    .sort_values("cantidad", ascending=False)
)
conteo_art.to_csv(TAB / "05_articulaciones_por_campus_capa.csv", index=False)

bridge_rows = []
for u, v in puentes:
    iu, iv = info[u], info[v]
    mismo_campus = iu["campus"] == iv["campus"]
    bridge_rows.append({
        "u": u,
        "v": v,
        "campus_u": iu["campus"],
        "campus_v": iv["campus"],
        "capa_u": iu["capa"],
        "capa_v": iv["capa"],
        "campus_resumen": iu["campus"] if mismo_campus
                          else f'{iu["campus"]} <-> {iv["campus"]}',
        "capas": " <-> ".join(sorted([iu["capa"], iv["capa"]])),
    })
puentes_df = pd.DataFrame(bridge_rows)
puentes_df.to_csv(TAB / "06_puentes.csv", index=False)

(
    puentes_df["campus_resumen"]
    .value_counts()
    .rename_axis("campus")
    .reset_index(name="cantidad")
    .to_csv(TAB / "07_puentes_por_campus.csv", index=False)
)

(
    puentes_df["capas"]
    .value_counts()
    .rename_axis("par_de_capas")
    .reset_index(name="cantidad")
    .to_csv(TAB / "08_puentes_por_capas.csv", index=False)
)

# ------------------------------------------------------------------
# P1.6 Contraste core-agregación
# ------------------------------------------------------------------
contraste = []
for campus in ["Campus Balzay", "Campus Paraiso", "Campus Central"]:
    ids = nodos[
        (nodos["campus"] == campus)
        & (nodos["capa"].isin(["core", "agregacion"]))
    ]["id"].tolist()

    H = G.subgraph(ids).copy()

    n_core = sum(info[n]["capa"] == "core" for n in H)
    n_agg = sum(info[n]["capa"] == "agregacion" for n in H)
    core_agg = sum(
        {info[u]["capa"], info[v]["capa"]} == {"core", "agregacion"}
        for u, v in H.edges()
    )

    contraste.append({
        "campus": campus,
        "n_core": n_core,
        "n_agregacion": n_agg,
        "enlaces_core_agregacion": core_agg,
        "ciclos_subgrafo_core_agregacion": len(nx.cycle_basis(H)),
        "puentes_subgrafo_core_agregacion": len(list(nx.bridges(H))),
    })

pd.DataFrame(contraste).to_csv(
    TAB / "09_contraste_core_agregacion.csv", index=False
)

# Guardar resumen global
pd.DataFrame(
    [{"metrica": k, "valor": v} for k, v in resumen.items()]
).to_csv(TAB / "10_resumen_metricas_P1.csv", index=False)

print("\n=== RESUMEN P1 ===")
for k, v in resumen.items():
    if isinstance(v, float):
        print(f"{k:30s}: {v:.6f}")
    else:
        print(f"{k:30s}: {v}")

print("\nTop-10 por intermediación:")
for i, (nodo, valor) in enumerate(ordenes["intermediacion"], 1):
    print(f"{i:2d}. {nodo:30s} {valor:.6f}  {info[nodo]['campus']} / {info[nodo]['capa']}")

print("\n=== ¿RED LIBRE DE ESCALA? (prueba estadística) ===")
for _, fila in powerlaw_df.iterrows():
    for col, val in fila.items():
        if col == "conclusion":
            continue
        print(f"{col:30s}: {val}")
    print(f"\n{fila['conclusion']}\n")

print(f"\nResultados guardados en: {ROOT / 'resultados'}")
