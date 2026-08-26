# Fuentes y adaptaciones — P6

## Material del módulo

La implementación de flujo máximo de este trabajo adapta la estructura de los
archivos públicos del repositorio del módulo:

- `optimization/ford-fulkerson/ford_fulkerson.jl`
- `optimization/edmonds-karp/edmonds_karp.jl`

Repositorio:
https://github.com/fabianastudillo/ComplexNetworks

Elementos adaptados:
- matriz de capacidades C;
- matriz de flujo antisimétrica F;
- residual r(u,v)=C[u,v]-F[u,v];
- búsqueda DFS para Ford-Fulkerson;
- búsqueda BFS para Edmonds-Karp;
- registro de camino, cuello de botella y flujo acumulado;
- determinación del corte mínimo mediante alcanzabilidad en la red residual.

La adaptación se realizó en Python y se aplicó a la red UCuenca. Los resultados
numéricos fueron recalculados desde los CSV/GraphML suministrados.

## Flujo de costo mínimo

El problema de costo mínimo se resolvió con `networkx.network_simplex`.
Esta parte no sustituye las implementaciones propias de Ford-Fulkerson y
Edmonds-Karp requeridas por P6.
