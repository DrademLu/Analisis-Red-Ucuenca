# P5 — Caminos más cortos

## 1. Modelos de peso

Se analizaron los tres modelos definidos en el enunciado:

- **Saltos:** `w(u,v) = 1`.
- **Latencia/capacidad:** `w(u,v) = α + β/c(u,v)`.
- **Carga:** `w(u,v) = b(u,v)/c(u,v)`.

Para el modelo de latencia se adoptó **α = 1.0** y **β = 1000 Mbps**. De esta manera, el peso de un enlace de 1 Gbps es 2.0, el de uno de 10 Gbps es 1.1 y el de uno de 20 Gbps es 1.05. La constante α evita que agregar muchos enlaces de alta capacidad resulte artificialmente gratuito y mantiene un costo básico por salto.

El conjunto de datos únicamente proporciona capacidad explícita para 28 enlaces. Para completar `c(u,v)` se adoptaron los siguientes supuestos:

- se conserva toda capacidad explícita;
- enlaces troncales asociados a core, WAN o interconexión: **10 Gbps**, salvo dato explícito;
- enlaces agregación–agregación: **10 Gbps**;
- enlaces acceso–agregación y acceso–acceso: **1 Gbps**.

El tráfico está disponible en 170 de los 209 enlaces. Para los **39 enlaces sin medición**, se aplicó la mediana de utilización observada en los enlaces medidos, que fue aproximadamente **1.648%** de la capacidad. Esta imputación no pretende reconstruir el tráfico real; únicamente permite definir una matriz completa para el modelo de carga y debe considerarse una limitación del análisis.

Todos los pesos resultantes son no negativos, por lo que Dijkstra es válido.

## 2. Dijkstra y Floyd–Warshall

Se implementaron ambos algoritmos desde cero.

### Dijkstra

Dijkstra utiliza una **cola de prioridad implementada con `heapq`**. Para cada nodo se mantiene su distancia provisional y su predecesor. Cuando se encuentra una ruta de menor costo hacia un vecino, la distancia se actualiza y el nodo se introduce nuevamente en la cola.

Su complejidad con listas de adyacencia y heap binario es:

`O((V + E) log V)`.

### Floyd–Warshall

Floyd–Warshall mantiene una matriz `V × V` y prueba sucesivamente cada nodo como posible intermediario entre cada par.

Su complejidad temporal es:

`O(V³)`

y su memoria:

`O(V²)`.

## 3. Verificación

Se seleccionaron aleatoriamente **20 pares de nodos** y se comparó la distancia obtenida con Dijkstra y Floyd–Warshall.

La comprobación se realizó no solamente para un modelo, sino para los **tres pesos**, dando un total de 60 comparaciones:

- saltos: **20/20 coincidencias**;
- latencia: **20/20 coincidencias**;
- carga: **20/20 coincidencias**.

Por tanto, ambas implementaciones producen los mismos costos mínimos dentro de la tolerancia numérica utilizada.

## 4. Comparación empírica de tiempos

Las subredes de tamaño creciente se construyeron siguiendo un orden BFS desde el core del Campus Central, de modo que cada subgrafo permaneciera conectado.

Los tiempos obtenidos en esta ejecución fueron:

| V | E | Dijkstra 1 fuente (ms) | Floyd todos los pares (ms) | Dijkstra todas las fuentes (ms) | Pares aprox. para amortizar Floyd |
|---:|---:|---:|---:|---:|---:|
| 25 | 39 | 0.038 | 0.544 | 0.879 | 32 |
| 50 | 64 | 0.072 | 2.935 | 3.668 | 63 |
| 75 | 93 | 0.093 | 7.965 | 7.270 | 114 |
| 100 | 132 | 0.136 | 15.205 | 13.201 | 208 |
| 125 | 157 | 0.163 | 25.753 | 20.555 | 314 |
| 150 | 182 | 0.197 | 35.422 | 29.438 | 282 |
| 177 | 209 | 0.224 | 54.571 | 40.367 | 381 |

Los tiempos absolutos dependen del equipo y del sistema operativo, por lo que lo importante es la tendencia.

Para una **consulta individual** Dijkstra es claramente más conveniente. En la red completa de 177 nodos, una ejecución desde una fuente tomó aproximadamente **0.224 ms**, mientras que Floyd–Warshall necesitó alrededor de **54.571 ms** para construir toda la matriz.

Si cada consulta correspondiera a un par independiente, Floyd comenzaría a amortizar su preprocesamiento después de aproximadamente **381 pares** en esta ejecución. Sin embargo, una sola ejecución de Dijkstra desde una fuente ya responde simultáneamente la distancia hacia todos los destinos de esa fuente.

También se comparó el cálculo completo de todos los pares. En estas implementaciones, Floyd fue competitivo en las subredes pequeñas de 25 y 50 nodos, pero a partir de aproximadamente **75 nodos** ejecutar Dijkstra desde todas las fuentes resultó más rápido. Esto es coherente con que UCuenca sea una red muy dispersa (`E` cercano a `V`): Dijkstra aprovecha la estructura escasa, mientras Floyd realiza trabajo cúbico independientemente de cuántas aristas existan.

## 5. Ranking por cercanía según el peso

A partir de las tres matrices completas se calculó una cercanía ponderada como `(n-1) / Σ d(i,j)`.

| Rank | Saltos | Cercanía | Latencia | Cercanía | Carga | Cercanía |
|---:|---|---:|---|---:|---|---:|
| 1 | `INTERNET-MPLS` | 0.2759 | `INTERNET-MPLS` | 0.2111 | `INTERNET-MPLS` | 13.5781 |
| 2 | `DATCC-2A-C3` | 0.2683 | `PE2-CENTRAL` | 0.2054 | `CC-AETUC-D30` | 13.4716 |
| 3 | `PE2-CENTRAL` | 0.2667 | `DATCC-2A-C3` | 0.1994 | `CC-ARQUITECTURA-D107` | 13.4716 |
| 4 | `FORTIGATE-1800F-CENTRAL` | 0.2596 | `PE1-CENTRAL` | 0.1985 | `CC-BIBLIOTECA-D112` | 13.4716 |
| 5 | `PE1-CENTRAL` | 0.2562 | `PE1-BALZAY` | 0.1949 | `CC-PROMAS-D31` | 13.4716 |
| 6 | `PE1-BALZAY` | 0.2511 | `FORTIGATE-1800F-CENTRAL` | 0.1931 | `CC-QUIMICA-D109` | 13.4716 |
| 7 | `DATCC-2A-C2` | 0.2475 | `ROUTER-CAMPUS-HUAYNA-CAPAC` | 0.1890 | `DATCC-2A-C3` | 13.4716 |
| 8 | `ROUTER-CAMPUS-HUAYNA-CAPAC` | 0.2421 | `DATCC-2A-C2` | 0.1864 | `QUI-0A-A78` | 13.4716 |
| 9 | `FORTIGATE-1800F-BALZAY` | 0.2408 | `PE2-BALZAY` | 0.1860 | `PE2-CENTRAL` | 13.4039 |
| 10 | `PE2-BALZAY` | 0.2385 | `ROUTER-CAMPUS-PARAISO` | 0.1844 | `FORTIGATE-1800F-CENTRAL` | 13.3144 |

El ranking **sí cambia según el peso**.

Los modelos de saltos y latencia son muy similares: comparten **9 de los 10 primeros nodos**. Esto ocurre porque el término `α = 1` mantiene una penalización por salto y la mayoría de los enlaces troncales poseen capacidades comparables.

En cambio, el modelo de carga comparte solamente **4 nodos** con cada uno de los otros rankings. Aparecen varios equipos de agregación e incluso un nodo de acceso entre los primeros puestos. Esto se debe a que `b/c` mide únicamente utilización: un enlace prácticamente o totalmente inactivo tiene un costo cercano a cero, independientemente del número de saltos.

Este resultado es importante porque demuestra que “central” depende de la pregunta. El ranking por saltos identifica buena posición topológica; el de latencia favorece además enlaces de mayor capacidad; y el de carga privilegia caminos actualmente poco utilizados.

## 6. Equipos de acceso más distantes

### Modelo de saltos

**Par más distante:** `ENF-2B-A122` (Campus Paraiso) → `POST-2A-A66` (Campus Central)

- Distancia mínima: **11.00000**
- Saltos de la ruta elegida: **11**

| Paso | Desde | Hacia | Capacidad (Mbps) | Tráfico modelado (Mbps) | Peso | Acumulado |
|---:|---|---|---:|---:|---:|---:|
| 1 | `ENF-2B-A122` | `ENF-2B-A22` | 1000 | 51.99 | 1.00000 | 1.00000 |
| 2 | `ENF-2B-A22` | `CP-ENFERMERIA-D1` | 1000 | 48.66 | 1.00000 | 2.00000 |
| 3 | `CP-ENFERMERIA-D1` | `CPAR-C10` | 10000 | 147.90 | 1.00000 | 3.00000 |
| 4 | `CPAR-C10` | `ROUTER-CAMPUS-HUAYNA-CAPAC` | 10000 | 317.83 | 1.00000 | 4.00000 |
| 5 | `ROUTER-CAMPUS-HUAYNA-CAPAC` | `INTERNET-MPLS` | 10000 | 164.80 | 1.00000 | 5.00000 |
| 6 | `INTERNET-MPLS` | `PE2-CENTRAL` | 10000 | 164.80 | 1.00000 | 6.00000 |
| 7 | `PE2-CENTRAL` | `DATCC-2A-C3` | 20000 | 329.60 | 1.00000 | 7.00000 |
| 8 | `DATCC-2A-C3` | `CC-FILOSOFIA-A-D108` | 10000 | 220.70 | 1.00000 | 8.00000 |
| 9 | `CC-FILOSOFIA-A-D108` | `POST-1A-A64` | 1000 | 200.42 | 1.00000 | 9.00000 |
| 10 | `POST-1A-A64` | `POST-1A-A65` | 1000 | 34.23 | 1.00000 | 10.00000 |
| 11 | `POST-1A-A65` | `POST-2A-A66` | 1000 | 2.67 | 1.00000 | 11.00000 |

### Modelo de latencia/capacidad

**Par más distante:** `POST-2A-A66` (Campus Central) → `QUIN-1A-A128` (Campus Balzay)

- Distancia mínima: **17.50000**
- Saltos de la ruta elegida: **11**

| Paso | Desde | Hacia | Capacidad (Mbps) | Tráfico modelado (Mbps) | Peso | Acumulado |
|---:|---|---|---:|---:|---:|---:|
| 1 | `POST-2A-A66` | `POST-1A-A65` | 1000 | 2.67 | 2.00000 | 2.00000 |
| 2 | `POST-1A-A65` | `POST-1A-A64` | 1000 | 34.23 | 2.00000 | 4.00000 |
| 3 | `POST-1A-A64` | `CC-FILOSOFIA-A-D108` | 1000 | 200.42 | 2.00000 | 6.00000 |
| 4 | `CC-FILOSOFIA-A-D108` | `DATCC-2A-C2` | 10000 | 0.00 | 1.10000 | 7.10000 |
| 5 | `DATCC-2A-C2` | `FORTIGATE-1800F-CENTRAL` | 10000 | 164.80 | 1.10000 | 8.20000 |
| 6 | `FORTIGATE-1800F-CENTRAL` | `FORTIGATE-1800F-BALZAY` | 1000 | 16.48 | 2.00000 | 10.20000 |
| 7 | `FORTIGATE-1800F-BALZAY` | `DT-0A-C12` | 10000 | 164.80 | 1.10000 | 11.30000 |
| 8 | `DT-0A-C12` | `CB-EADMI-D6` | 10000 | 7.18 | 1.10000 | 12.40000 |
| 9 | `CB-EADMI-D6` | `BAL-EADM-D3` | 10000 | 19.63 | 1.10000 | 13.50000 |
| 10 | `BAL-EADM-D3` | `QUIN-1A-A117` | 1000 | 54.06 | 2.00000 | 15.50000 |
| 11 | `QUIN-1A-A117` | `QUIN-1A-A128` | 1000 | 16.48 | 2.00000 | 17.50000 |

### Modelo de carga

**Par más distante:** `ECOK1-1A-A102` (Campus Central) → `POST-2A-A66` (Campus Central)

- Distancia mínima: **0.50548**
- Saltos de la ruta elegida: **6**

| Paso | Desde | Hacia | Capacidad (Mbps) | Tráfico modelado (Mbps) | Peso | Acumulado |
|---:|---|---|---:|---:|---:|---:|
| 1 | `ECOK1-1A-A102` | `CC-ECONOMIA-D51` | 1000 | 268.16 | 0.26816 | 0.26816 |
| 2 | `CC-ECONOMIA-D51` | `DATCC-2A-C2` | 10000 | 0.00 | 0.00000 | 0.26816 |
| 3 | `DATCC-2A-C2` | `CC-FILOSOFIA-A-D108` | 10000 | 0.00 | 0.00000 | 0.26816 |
| 4 | `CC-FILOSOFIA-A-D108` | `POST-1A-A64` | 1000 | 200.42 | 0.20042 | 0.46858 |
| 5 | `POST-1A-A64` | `POST-1A-A65` | 1000 | 34.23 | 0.03423 | 0.50281 |
| 6 | `POST-1A-A65` | `POST-2A-A66` | 1000 | 2.67 | 0.00267 | 0.50548 |

Los pares extremos cambian con el modelo. Bajo saltos, el extremo corresponde a un recorrido de **11 enlaces entre Paraíso y Campus Central**. Con el peso de latencia, el par extremo se desplaza a **Campus Central–Balzay**, porque los enlaces de 1 Gbps son penalizados más que los troncales de 10/20 Gbps.

El modelo de carga produce un resultado conceptualmente diferente: el par más distante queda dentro de Campus Central. La razón es que algunas ramas de acceso poseen utilizaciones relativamente altas, mientras que varios enlaces troncales o de respaldo presentan costos muy pequeños o nulos.

## 7. Relación con OSPF e IS-IS

Un protocolo de estado de enlace como OSPF o IS-IS necesita que el costo de las rutas sea suficientemente **estable** para que todos los routers puedan converger sobre una visión consistente de la topología.

### Peso por saltos

Un costo unitario es sencillo y estable, pero trata de igual forma un enlace lento y uno de gran capacidad. Podría seleccionar una ruta de pocos saltos que atraviese un cuello de botella.

### Peso relacionado con capacidad

Un peso que favorece enlaces de mayor capacidad se aproxima mejor a la lógica tradicional de métricas administrativas usadas en protocolos de estado de enlace: los enlaces rápidos pueden recibir costos menores, pero la métrica permanece relativamente estable mientras no cambie la configuración o la capacidad física.

El modelo `α + β/c` utilizado aquí combina ambos criterios: existe un costo básico por atravesar un enlace y una penalización adicional para enlaces de menor capacidad.

### Peso dependiente de carga instantánea

Utilizar directamente `b/c` podría parecer atractivo porque desviaría tráfico de los enlaces congestionados. Sin embargo, convertir el tráfico instantáneo en la métrica de enrutamiento puede generar **inestabilidad y oscilaciones**:

1. un enlace se congestiona;
2. su peso aumenta;
3. las rutas migran hacia otro enlace;
4. el primer enlace se descarga y el segundo se carga;
5. las métricas cambian nuevamente;
6. las rutas pueden volver a migrar.

Además, cada cambio de peso puede provocar nuevas ejecuciones del algoritmo de caminos mínimos y difusión de información de estado. Si el tráfico cambia más rápido que la red puede converger, el sistema puede oscilar.

Por esta razón, si se desea incorporar carga real a una métrica dinámica, normalmente sería necesario aplicar mecanismos como promedios temporales, histéresis, umbrales y límites a la frecuencia de actualización, en lugar de utilizar directamente la medición instantánea.

El comportamiento extraño observado en el top-10 de cercanía bajo `b/c` ilustra además otra limitación: **una ruta con muchos enlaces ociosos puede parecer prácticamente gratuita**. Por sí sola, la utilización no representa latencia, número de saltos ni confiabilidad.

## 8. Conclusión

Dijkstra y Floyd–Warshall producen resultados equivalentes, pero su conveniencia computacional depende del tipo y cantidad de consultas. Sobre esta red dispersa, Dijkstra es claramente preferible para rutas individuales y, a partir de las subredes medianas ensayadas, también resulta competitivo para obtener todos los pares ejecutándolo desde cada origen.

La elección del modelo de peso modifica la interpretación de la red. Saltos y capacidad producen rankings relativamente similares, mientras el peso basado exclusivamente en utilización altera significativamente las rutas y centralidades. Esto confirma que el “camino más corto” no es una propiedad única de la topología: depende de **qué magnitud de ingeniería se decide minimizar**.
