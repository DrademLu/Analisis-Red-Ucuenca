# Procedencia de las métricas — P10

P10 no introduce un algoritmo externo nuevo; sintetiza resultados de fases previas.

- **P1:** intermediación y condición de punto de articulación. Se recalculan desde
  `red_ucuenca.graphml` para mantener reproducibilidad.
- **P6:** se reutiliza `05_cortes_minimos_por_campus.csv`.
- **P8:** el daño por percolación de un nodo se recalcula directamente eliminando
  cada nodo de forma aislada y midiendo el tamaño de la componente gigante.
- **P9:** se reutiliza `02_barrido_tau.csv` y se toma `tau=0.035`, cercano al
  margen crítico encontrado en P9.

El índice compuesto y sus ponderaciones son una decisión metodológica propia del
proyecto y quedan documentados en el código y en `resumen_P10.md`.
