"""Diagnóstico: efecto de la normalización de la betweenness en el modelo de cascada.

NO modifica el pipeline ni escribe en resultados/. Solo compara, para los mismos
disparadores y los mismos valores de tau, el modelo actual (betweenness
normalizada, recalculada sobre la topología superviviente) contra el modelo de
Motter-Lai estándar (betweenness sin normalizar).

El problema: la betweenness normalizada divide por (n-1)(n-2)/2. Al ir
eliminando nodos, H encoge y ese denominador se reduce, por lo que las cargas
recalculadas se reescalan hacia arriba mientras las capacidades siguen fijadas
a la escala de los 177 nodos originales.

Colócalo en la RAÍZ del proyecto (junto a run_all.py) y ejecuta:

    python diagnostico_cascada.py

Tarda un par de minutos. Si lo guardas dentro de scripts/, run_all.py lo
ignorará porque su nombre no empieza con un prefijo numérico.
"""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# Funciona tanto si el archivo está en la raíz como dentro de scripts/.
_AQUI = Path(__file__).resolve().parent
ROOT = _AQUI if (_AQUI / "data").is_dir() else _AQUI.parent
DATA = ROOT / "data"

G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
META = pd.read_csv(DATA / "red_ucuenca_nodes.csv").set_index("id")
NODES = list(G)
N = len(NODES)

# Las dos escalas de carga inicial.
INIT_NORM = nx.betweenness_centrality(G, normalized=True)
INIT_RAW = nx.betweenness_centrality(G, normalized=False)

TAUS = [0.0, 0.035]


def cascade(trigger, tau, normalizada):
    """Cascada de Motter-Lai. normalizada=True reproduce el código actual."""
    init = INIT_NORM if normalizada else INIT_RAW
    cap = {n: (1 + tau) * init[n] for n in NODES}
    H = G.copy()
    failed = {trigger}
    gens = [[trigger]]
    H.remove_node(trigger)

    while H.number_of_nodes():
        load = nx.betweenness_centrality(H, normalized=normalizada)
        over = [n for n in H if load[n] > cap[n] + 1e-12]
        if not over:
            break
        H.remove_nodes_from(over)
        failed.update(over)
        gens.append(over)
    return failed, gens


def worker(args):
    trigger, tau, normalizada = args
    fallos, gens = cascade(trigger, tau, normalizada)
    return {
        "modelo": "normalizada (actual)" if normalizada else "sin normalizar (Motter-Lai)",
        "tau": tau,
        "trigger": trigger,
        "campus": META.loc[trigger, "campus"],
        "capa": META.loc[trigger, "capa"],
        "betweenness": INIT_NORM[trigger],
        "fallos_totales": len(fallos),
        "fraccion": len(fallos) / N,
        "generaciones": len(gens),
    }


def main():
    tareas = [
        (n, tau, norm)
        for norm in (True, False)
        for tau in TAUS
        for n in NODES
    ]
    print(f"Red: {N} nodos, {G.number_of_edges()} aristas")
    print(f"Ejecutando {len(tareas)} cascadas ({len(TAUS)} taus x 2 modelos)...")

    filas = []
    with ProcessPoolExecutor(max_workers=min(5, os.cpu_count() or 1)) as ex:
        for i, salida in enumerate(ex.map(worker, tareas, chunksize=4), 1):
            filas.append(salida)
            if i % 100 == 0:
                print(f"  {i}/{len(tareas)}", flush=True)

    df = pd.DataFrame(filas)

    for tau in TAUS:
        print("\n" + "=" * 78)
        print(f"TAU = {tau}")
        print("=" * 78)

        for modelo in df["modelo"].unique():
            sub = df[(df.tau == tau) & (df.modelo == modelo)]
            top = sub.sort_values(
                ["fallos_totales", "trigger"], ascending=[False, True]
            ).head(8)
            print(f"\n--- {modelo} ---")
            print(
                top[["trigger", "campus", "capa", "betweenness",
                     "fallos_totales", "fraccion"]]
                .to_string(index=False, float_format=lambda v: f"{v:.4f}")
            )

            # ¿El daño de la cascada se alinea con la importancia estructural?
            if sub["fallos_totales"].std() > 0:
                rho = sub["betweenness"].corr(sub["fallos_totales"], method="spearman")
                print(f"    correlación de Spearman betweenness vs daño: {rho:+.3f}")
            n_super = int((sub.fraccion > 0.2).sum())
            print(f"    disparadores que superan el 20% de la red: {n_super}")

        # Coincidencia entre los dos top-10.
        a = set(df[(df.tau == tau) & (df.modelo.str.startswith("normalizada"))]
                .nlargest(10, "fallos_totales")["trigger"])
        b = set(df[(df.tau == tau) & (df.modelo.str.startswith("sin"))]
                .nlargest(10, "fallos_totales")["trigger"])
        print(f"\n  Nodos comunes entre ambos top-10: {len(a & b)}/10")
        if a - b:
            print(f"  Solo con el modelo actual : {sorted(a - b)}")
        if b - a:
            print(f"  Solo sin normalizar       : {sorted(b - a)}")

    salida = ROOT / "diagnostico_cascada.csv"
    df.to_csv(salida, index=False)
    print(f"\nDetalle completo guardado en: {salida}")
    print("\nLECTURA: si la correlación de Spearman es cercana a cero o negativa")
    print("en el modelo actual y claramente positiva sin normalizar, la cascada")
    print("actual está midiendo capacidad de fragmentación, no redistribución.")


if __name__ == "__main__":
    main()  