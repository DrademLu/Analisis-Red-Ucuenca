# P6 — Flujo máximo, corte mínimo y flujo de costo mínimo

## 1. Modelo de capacidad

El conjunto de datos contiene `capacidad_mbps` explícita únicamente en **28 de las 209 aristas**, por lo que fue necesario completar la función `c(u,v)` para los 181 enlaces restantes.

Se utilizaron los siguientes supuestos:

| Tipo de enlace | Capacidad adoptada |
|---|---:|
| Capacidad explícita en el dataset | Se conserva |
| WAN/MPLS o enlace inferido hacia la WAN | 10 Gbps |
| Troncal con core o interconexión | 10 Gbps |
| Agregación–agregación | 10 Gbps |
| Acceso–agregación | 1 Gbps |
| Acceso–acceso | 1 Gbps |

El criterio principal es que el informe técnico declara **10 Gbps para los enlaces troncales**. Para las conexiones de acceso, donde no existe una velocidad nominal documentada en el dataset, se utilizó **1 Gbps** como hipótesis de trabajo.

El atributo `rol` se emplea para interpretar la función de la arista, pero no para reducir automáticamente su capacidad. Un enlace de `respaldo` o `secundario` puede tener la misma velocidad nominal que el enlace principal; el rol describe su función dentro de la redundancia y no necesariamente una menor capacidad.

Además, como el grafo original es no dirigido, cada enlace físico se representó mediante capacidad `c(u,v)` en ambos sentidos. Para este experimento se interpreta como un enlace Ethernet full-duplex con la misma capacidad nominal en cada dirección.

Todos estos supuestos se almacenan en `01_capacidades_completas.csv`, de modo que el modelo pueda modificarse posteriormente sin alterar los algoritmos.

## 2. Fuente y sumidero

Para cada campus se creó un **super-nodo fuente** conectado a todos los nodos cuya capa es `acceso` dentro de dicho campus. Las conexiones artificiales del super-nodo poseen una capacidad suficientemente grande para que no se conviertan en el cuello de botella.

El sumidero es:

`INTERNET-MPLS`

De esta forma, el problema representa la capacidad máxima con la que el conjunto de equipos de acceso de un campus podría enviar tráfico hacia la salida institucional.

## 3. Ford–Fulkerson y Edmonds–Karp

Las implementaciones se adaptaron del material del módulo:

- `optimization/ford-fulkerson/ford_fulkerson.jl`
- `optimization/edmonds-karp/edmonds_karp.jl`

Se conservó la idea del código docente de utilizar una matriz de capacidades `C`, una matriz de flujo antisimétrica `F` y la capacidad residual `C-F`.

Para **Ford–Fulkerson** se utiliza DFS para escoger cualquier camino aumentante. Para **Edmonds–Karp** se utiliza BFS, por lo que cada camino aumentante tiene longitud mínima en número de arcos.

Los resultados fueron:

| Campus | Nodos de acceso | Flujo máximo (Gbps) | Iteraciones FF | Iteraciones EK | Aristas del corte |
|---|---:|---:|---:|---:|---:|
| Campus Central | 56 | 44.0 | 44 | 44 | 7 |
| Campus Balzay | 24 | 23.0 | 23 | 23 | 23 |
| Campus Paraiso | 35 | 10.0 | 10 | 10 | 1 |
| Campus Yanuncay | 11 | 10.0 | 10 | 10 | 1 |
| Campus Hospitalidad | 4 | 4.0 | 4 | 4 | 4 |

Ambos algoritmos alcanzaron **exactamente el mismo flujo máximo para los cinco campus**, como exige el teorema de flujo máximo–corte mínimo.

En esta red el número total de iteraciones de FF y EK resultó igual para cada campus. Esto no significa que ambos algoritmos sean equivalentes: las secuencias de caminos son distintas. En Campus Central, por ejemplo, DFS utiliza caminos de longitudes que suben y bajan durante la ejecución, mientras que las longitudes de Edmonds–Karp son **no decrecientes**, tal como establece la propiedad característica del algoritmo.

Las secuencias completas de caminos, longitudes, cuellos de botella y flujo acumulado se encuentran en `04_iteraciones_caminos_aumentantes.csv`.

## 4. Corte mínimo e interpretación

La relación entre los cortes mínimos y los puentes encontrados en P1 es:

| Campus | Aristas del corte | También son puentes P1 | Porcentaje | Capacidad del corte (Gbps) |
|---|---:|---:|---:|---:|
| Campus Balzay | 23 | 23 | 100.0% | 23.0 |
| Campus Central | 7 | 2 | 28.6% | 44.0 |
| Campus Hospitalidad | 4 | 4 | 100.0% | 4.0 |
| Campus Paraiso | 1 | 1 | 100.0% | 10.0 |
| Campus Yanuncay | 1 | 1 | 100.0% | 10.0 |

### Campus Paraíso

El corte mínimo contiene una sola arista:

`CPAR-C10 → ROUTER-CAMPUS-HUAYNA-CAPAC`

con **10 Gbps**.

Esta arista también fue identificada como **puente en P1**. Por tanto, el resultado de flujo confirma que la conexión entre el núcleo de Paraíso y su router WAN constituye un cuello de botella estructural: no existe otro camino topológico representado en el grafo para evitarla.

### Campus Yanuncay

El corte está formado únicamente por:

`AGRPRI-1A-D10 → ROUTER-CAMPUS-YANUNCAY`

con **10 Gbps**.

También es un puente. De nuevo, el corte mínimo coincide con un punto único de conectividad hacia la WAN.

### Campus Hospitalidad

El flujo máximo es **4 Gbps**, pero el corte no aparece en el enlace WAN inferido de 10 Gbps. El cuello de botella está antes: los cuatro equipos de acceso disponen de enlaces individuales de 1 Gbps hacia `HOS-0A-D05`.

Por tanto, aunque la salida WAN modelada admite 10 Gbps, el conjunto de accesos únicamente puede inyectar 4 Gbps bajo los supuestos adoptados.

### Campus Balzay

El flujo máximo es **23 Gbps** y el corte contiene 23 enlaces de acceso de 1 Gbps. Todos son puentes del grafo.

Esto es un resultado interesante: la redundancia presente en las capas superiores de Balzay evita que un único enlace de core/WAN domine el corte, pero **no elimina el single-homing de muchos equipos de acceso**. La limitación aparece en el borde de la red y no en el backbone.

### Campus Central

Campus Central alcanza **44 Gbps**. Su corte mínimo contiene siete enlaces y solamente dos de ellos son puentes de P1. Aparecen varios enlaces de alta capacidad del core/WAN, junto con enlaces menores.

La ausencia de un único puente dominante es consistente con una mayor cantidad de caminos alternativos en la zona de core e interconexión. En este caso la capacidad máxima queda determinada por la **suma de varias fronteras de capacidad**, no por una sola arista crítica.

Debe notarse además que, al trabajar sobre el grafo institucional completo, algunos caminos de Central pueden atravesar elementos de otras sedes. Por ello el corte es un corte de la **red completa para el tráfico originado en Central**, no exclusivamente una frontera física encerrada dentro del campus.

## 5. Verificación manual del corte mínimo

Se verificó manualmente el corte obtenido para Campus Central.

Las capacidades de las siete aristas son:

`1000 + 1000 + 1000 + 1000 + 10000 + 10000 + 20000` Mbps

por lo que:

`1000 + 1000 + 1000 + 1000 + 10000 + 10000 + 20000 = 44000 Mbps = 44.0 Gbps`

El resultado coincide exactamente con el flujo máximo calculado para Campus Central:

**flujo máximo = capacidad del corte mínimo = 44.0 Gbps**.

Esto constituye una verificación directa del teorema max-flow/min-cut para uno de los casos solicitados.

## 6. Flujo de costo mínimo

Como extensión se formuló un problema con dos fuentes:

- Campus Central: **5 Gbps**
- Campus Balzay: **5 Gbps**
- demanda total hacia `INTERNET-MPLS`: **10 Gbps**

Se asignó un costo administrativo por unidad de flujo según el rol de cada enlace:

| Rol | Costo unitario |
|---|---:|
| `principal` | 1 |
| `wan` | 1 |
| `inferido` | 1 |
| `secundario` | 3 |
| `respaldo` | 6 |

La intención es representar que, para una demanda conocida, se prefiere utilizar enlaces normales y reservar los enlaces de contingencia cuando no sean necesarios.

El costo mínimo obtenido fue:

- **Demanda:** 10 Gbps
- **Costo total:** 41000
- **Costo medio:** 4.10 unidades por Mbps

Una descomposición posible del flujo óptimo es:

| Origen | Flujo (Mbps) | Saltos físicos | Costo unitario | Camino |
|---|---:|---:|---:|---|
| Campus Central | 1000 | 4 | 4 | `MINCOST::Campus Central -> PSIC-1A-A53 -> CC-PSICOLOGIA-D125 -> DATCC-2A-C3 -> PE2-CENTRAL -> INTERNET-MPLS` |
| Campus Central | 1000 | 4 | 4 | `MINCOST::Campus Central -> FILOB-1B-A58 -> CC-FILOSOFIA-B-D111 -> DATCC-2A-C3 -> PE2-CENTRAL -> INTERNET-MPLS` |
| Campus Central | 1000 | 4 | 4 | `MINCOST::Campus Central -> ECOK1-1A-A101 -> CC-ECONOMIA-D51 -> DATCC-2A-C3 -> PE2-CENTRAL -> INTERNET-MPLS` |
| Campus Central | 1000 | 2 | 2 | `MINCOST::Campus Central -> CCJ-1A-A11 -> CCJ-CJURIDICO-D4 -> INTERNET-MPLS` |
| Campus Central | 1000 | 2 | 2 | `MINCOST::Campus Central -> CCJ-1A-A10 -> CCJ-CJURIDICO-D4 -> INTERNET-MPLS` |
| Campus Balzay | 1000 | 5 | 5 | `MINCOST::Campus Balzay -> CTBLOQ2-0A-A102 -> BAL-CENTEC-D2 -> DT-0A-C12 -> FORTIGATE-1800F-BALZAY -> PE1-BALZAY -> INTERNET-MPLS` |
| Campus Balzay | 1000 | 5 | 5 | `MINCOST::Campus Balzay -> CTBLOQ1-0A-A101 -> BAL-CENTEC-D2 -> DT-0A-C12 -> FORTIGATE-1800F-BALZAY -> PE1-BALZAY -> INTERNET-MPLS` |
| Campus Balzay | 1000 | 5 | 5 | `MINCOST::Campus Balzay -> AUL2-0A-A118 -> BAL-AUL2-D1 -> DT-0A-C12 -> FORTIGATE-1800F-BALZAY -> PE1-BALZAY -> INTERNET-MPLS` |
| Campus Balzay | 1000 | 5 | 5 | `MINCOST::Campus Balzay -> AUL2-01A-A24-SUB -> BAL-AUL2-D1 -> DT-0A-C12 -> FORTIGATE-1800F-BALZAY -> PE1-BALZAY -> INTERNET-MPLS` |
| Campus Balzay | 1000 | 5 | 5 | `MINCOST::Campus Balzay -> AUL2-01A-A124-SUBLAB2 -> BAL-AUL2-D1 -> DT-0A-C12 -> FORTIGATE-1800F-BALZAY -> PE1-BALZAY -> INTERNET-MPLS` |

En esta solución no fue necesario utilizar enlaces de `respaldo` ni `secundario`: la capacidad disponible en enlaces principales/WAN fue suficiente para satisfacer la demanda de 10 Gbps.

## 7. Comparación con flujo máximo puro

Si se combinan los equipos de acceso de Central y Balzay en un único problema de **flujo máximo**, la red admite aproximadamente:

**62.0 Gbps**.

El problema de costo mínimo, en cambio, transporta únicamente los **10 Gbps solicitados**, equivalentes a aproximadamente **16.1%** de ese máximo combinado.

Los objetivos son distintos:

- **Flujo máximo:** intenta enviar la mayor cantidad posible, independientemente del costo de las rutas.
- **Flujo de costo mínimo:** recibe una demanda fija y decide por dónde transportarla para minimizar un criterio adicional.

Por ello no debe esperarse que ambos produzcan los mismos caminos. El flujo máximo es apropiado para estudiar **capacidad y cuellos de botella**, mientras que el flujo de costo mínimo es más apropiado cuando la demanda ya es conocida y existen preferencias operativas entre rutas.

## 8. Conclusión

Los resultados muestran dos tipos distintos de limitación en la red. En Paraíso y Yanuncay el corte mínimo coincide directamente con un único puente hacia la WAN, evidenciando una dependencia estructural clara. En Balzay y Hospitalidad, en cambio, el cuello de botella se encuentra principalmente en los enlaces individuales de acceso. Campus Central presenta un corte distribuido entre varias aristas, reflejando una estructura con más caminos alternativos.

Por tanto, **un puente y una arista de corte mínimo no representan exactamente el mismo concepto**. Un puente mide vulnerabilidad topológica: su eliminación desconecta el grafo. El corte mínimo incorpora además las capacidades, de modo que puede estar compuesto por varias aristas no puente cuya capacidad total limita el flujo.

Esta distinción será especialmente útil en P10, donde ambos tipos de evidencia podrán combinarse para construir el ranking de puntos críticos.
