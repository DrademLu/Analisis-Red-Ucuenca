# Red UCuenca — Análisis de Redes Complejas

Análisis de extremo a extremo de la red de datos de la Universidad de Cuenca
(177 nodos, 209 enlaces, topología jerárquica de tres capas sobre un núcleo
MPLS) usando teoría de grafos: caracterización estructural, comunidades,
caminos/flujo, localización de instalaciones, percolación, cascadas y
epidemiología SIR, ranking de criticidad y una propuesta de rediseño de red.

El informe completo está en [`informe_final.md`](informe_final.md). Este
repositorio contiene el código que genera **todas** las tablas y figuras
citadas en ese informe — ningún resultado se calculó ni editó a mano.

## Estructura del repositorio

```
data/           Datos de entrada (grafo GraphML + nodos/aristas en CSV)
src/            Módulo compartido (carga y verificación de datos)
scripts/        12 scripts numerados por fase (00 a 11), ejecutables en orden
resultados/
  tablas/       CSV generados por los scripts (uno por script/figura)
  figuras/      PNG generados por los scripts
docs/           Resúmenes por fase, procedencia de métricas y fuentes citadas
informe_final.md   Informe final del proyecto
run_all.py      Ejecuta scripts/00 a scripts/11 en orden con un solo comando
requirements.txt
```

## Instalación

Requiere Python ≥ 3.11.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Reproducir todos los resultados

Los scripts deben ejecutarse **en orden numérico** desde la raíz del
repositorio: los scripts posteriores leen resultados que generan los
anteriores (por ejemplo, `10_p10_ranking_criticos.py` reutiliza tablas
producidas por `06_p6_flujo.py` y `09_p9_cascadas_sir.py`, buscándolas en
`resultados/tablas/`). No hay pasos manuales entre scripts.

Opción 1 — todo el pipeline con un solo comando:

```bash
python run_all.py
```

Opción 2 — script por script:

```bash
python scripts/00_verificar_datos.py        # valida los datos contra el Anexo A
python scripts/01_p1_caracterizacion.py     # P1: caracterización estructural
python scripts/02_p2_modelos_nulos.py       # P2: contraste con modelos nulos
python scripts/03_p3_bfs_dfs.py             # P3: recorridos BFS/DFS, ciclos
python scripts/04_p4_comunidades.py         # P4: comunidades (Louvain, k-means)
python scripts/05_p5_caminos.py             # P5: caminos mínimos (Dijkstra/Floyd-Warshall)
python scripts/06_p6_flujo.py               # P6: flujo máximo/corte mínimo, flujo de costo mínimo
python scripts/07_p7_localizacion.py        # P7: localización de instalaciones (p-mediana/p-centro)
python scripts/08_p8_percolacion.py         # P8: percolación de nodos y enlaces
python scripts/09_p9_cascadas_sir.py        # P9: cascadas por sobrecarga y SIR
python scripts/10_p10_ranking_criticos.py   # P10: índice compuesto de criticidad
python scripts/11_p11_rediseno.py           # P11: propuesta de rediseño (5 enlaces)
```

Cada script escribe sus tablas en `resultados/tablas/` y sus figuras en
`resultados/figuras/`, usando rutas relativas a la raíz del repositorio (no
hay rutas absolutas ni credenciales). Los CSV y PNG versionados en
`resultados/` son exactamente los que produce este pipeline; no deben
editarse a mano — cualquier discrepancia se corrige regenerándolos con los
scripts, nunca editando el CSV o el informe directamente.

Los algoritmos que el enunciado exige implementar "desde cero" (BFS, DFS,
Dijkstra, Floyd-Warshall, Ford-Fulkerson, Edmonds-Karp, k-means) están
implementados sin usar las funciones equivalentes de NetworkX/SciPy, y se
verifican contra ellas donde corresponde.

## Datos

`data/red_ucuenca.graphml`, `data/red_ucuenca_nodes.csv` y
`data/red_ucuenca_edges.csv` fueron reconstruidos a partir de 34 diagramas
técnicos de red suministrados por la universidad. `scripts/00_verificar_datos.py`
valida su carga contra los valores de referencia del Anexo A antes de correr
el resto del pipeline.

## Documentación adicional

- `docs/resumen_P4.md` … `docs/resumen_P11.md`: notas de diseño y decisiones
  metodológicas por fase.
- `docs/PROCEDENCIA_METRICAS.md`: de qué script/tabla sale cada métrica citada
  en el informe.
- `docs/FUENTES_Y_ADAPTACIONES_P4.md`, `docs/FUENTES_Y_ADAPTACIONES_P6.md`,
  `docs/REFERENCIAS_P9.md`: fuentes bibliográficas y adaptaciones de algoritmos
  de referencia usadas en esas fases.

## Integrantes

Luis Antonio Andrade Matute 

Claudia Estefanía Padilla Guamán

Maestría en Ciencias de la Ingeniería Eléctrica — Módulo 1217, Redes
Complejas, IV Cohorte. Docente: Dr. Fabián Astudillo-Salinas.