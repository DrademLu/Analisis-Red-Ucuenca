# Fuentes y adaptaciones — P4

Este trabajo reutiliza/adapta material del repositorio oficial del módulo:

1. **Louvain y visualización**
   - Archivo: `intro/codes/gen_visualizacion-louvain.jl`
   - Repositorio: https://github.com/fabianastudillo/ComplexNetworks
   - Uso: metodología de detección de comunidades Louvain, modularidad y visualización.
   - Adaptación: la ejecución se realizó en Python/NetworkX para controlar semillas,
     calcular NMI/ARI y automatizar las tablas del proyecto UCuenca.

2. **K-means desde cero**
   - Archivo: `algoritmos/kmeans/ejemplo1.jl`
   - Repositorio: https://github.com/fabianastudillo/ComplexNetworks
   - Uso: estructura del algoritmo (distancia euclídea cuadrática, K-means++,
     asignación, actualización, WCSS y convergencia).
   - Adaptación: traducción conceptual a Python y aplicación sobre un embedding
     espectral de los nodos de la red UCuenca.

Todos los resultados numéricos de este directorio fueron recalculados sobre
`red_ucuenca.graphml`; no se reutilizaron resultados numéricos externos.
