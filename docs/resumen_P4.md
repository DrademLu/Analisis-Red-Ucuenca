# P4 — Comunidades y modularidad

## 1. Louvain y estabilidad

Se aplicó Louvain sobre el grafo no ponderado de la red UCuenca utilizando cinco semillas distintas. La implementación utiliza `networkx.community.louvain_communities`, siguiendo la metodología del ejemplo `intro/codes/gen_visualizacion-louvain.jl` del repositorio del módulo, donde se detectan comunidades con Louvain y se evalúa su modularidad.

| Semilla | Comunidades | Q | NMI vs campus | ARI vs campus |
|---:|---:|---:|---:|---:|
| 11 | 14 | 0.7587 | 0.6203 | 0.3385 |
| 22 | 13 | 0.7569 | 0.6339 | 0.3784 |
| 33 | 14 | 0.7632 | 0.6182 | 0.3265 |
| 44 | 16 | 0.7347 | 0.6449 | 0.3111 |
| 55 | 15 | 0.7592 | 0.6413 | 0.3477 |

La mayor modularidad se obtuvo con la **semilla 33**, con **14 comunidades** y **Q = 0.7632**. Esta partición se utiliza como referencia para el resto del análisis.

El número de comunidades varió entre **13 y 16**, mientras que Q se mantuvo entre **0.7347 y 0.7632**. Por tanto, el valor de modularidad es bastante estable, aunque la división exacta de algunos nodos cambia entre ejecuciones.

Al comparar las cinco particiones entre sí se obtuvo un **NMI medio de 0.894** y un **ARI medio de 0.712**. Los mínimos fueron NMI = 0.815 y ARI = 0.527. Esto indica que Louvain recupera una estructura macroscópica similar para las distintas semillas, pero existe cierta sensibilidad en los límites y subdivisiones de las comunidades.

## 2. Comparación Louvain — campus

Para la partición de referencia se obtuvo:

- **NMI = 0.6182**
- **ARI = 0.3265**

La coincidencia es, por tanto, **parcial**. La partición natural por campus tiene una modularidad de **Q = 0.6198**, mientras que Louvain alcanza **Q = 0.7632**.

La diferencia se explica principalmente porque Louvain **subdivide los campus grandes en varios bloques estructurales**. Por ejemplo, Campus Central aparece repartido en varias comunidades prácticamente puras, y Paraíso también se divide en varios grupos. El algoritmo no conoce el atributo `campus`: únicamente observa qué nodos están enlazados y busca maximizar la densidad relativa de enlaces internos.

La matriz completa comunidad × campus se guarda en `03_matriz_confusion_louvain_vs_campus.csv` y se representa en `03_matriz_confusion_louvain_campus.png`.

Dos comunidades son especialmente relevantes:

- **Comunidad 4:** 25 nodos, formada por 21 de Campus Balzay, 2 de Sede Centro Histórico y 2 de Sede Museo.
- **Comunidad 13:** 18 nodos y seis ubicaciones distintas: Campus Central (6), Hospitalidad (5), Balzay (3), Paraíso (2), Yanuncay (1) y Nube MPLS (1).

La comunidad 13 representa claramente una **comunidad funcional de interconexión/WAN**, no una comunidad geográfica.

## 3. Nodos donde las particiones discrepan

Como Louvain produce 14 comunidades y el atributo campus solamente 8 grupos, no existe una correspondencia uno-a-uno entre las etiquetas. Para identificar discrepancias se asignó a cada comunidad su **campus dominante** y se marcaron los nodos pertenecientes a otro campus dentro de esa misma comunidad. Con este criterio aparecen **16 nodos**:

| Nodo | Campus real | Capa | Comunidad | Campus dominante |
|---|---|---|---:|---|
| `FORTIGATE-1800F-BALZAY` | Campus Balzay | interconexion | C13 | Campus Central |
| `HOS-0A-A10` | Campus Hospitalidad | acceso | C13 | Campus Central |
| `HOS-0A-A13` | Campus Hospitalidad | acceso | C13 | Campus Central |
| `HOS-0A-D05` | Campus Hospitalidad | agregacion | C13 | Campus Central |
| `HOS-1A-A12` | Campus Hospitalidad | acceso | C13 | Campus Central |
| `HOS-2A-A11` | Campus Hospitalidad | acceso | C13 | Campus Central |
| `INTERNET-MPLS` | Nube MPLS | wan | C13 | Campus Central |
| `PE1-BALZAY` | Campus Balzay | wan | C13 | Campus Central |
| `PE2-BALZAY` | Campus Balzay | wan | C13 | Campus Central |
| `ROUTER-CAMPUS-CENTRO-HISTORICO` | Sede Centro Historico | wan | C4 | Campus Balzay |
| `ROUTER-CAMPUS-HUAYNA-CAPAC` | Campus Paraiso | wan | C13 | Campus Central |
| `ROUTER-CAMPUS-MUSEO` | Sede Museo | wan | C4 | Campus Balzay |
| `ROUTER-CAMPUS-PARAISO` | Campus Paraiso | wan | C13 | Campus Central |
| `ROUTER-CAMPUS-YANUNCAY` | Campus Yanuncay | wan | C13 | Campus Central |
| `SW-ARUBA-CENTRO-HISTORICO` | Sede Centro Historico | acceso | C4 | Campus Balzay |
| `SW-ARUBA-MUSEO` | Sede Museo | acceso | C4 | Campus Balzay |

La mayoría de las discrepancias corresponden a **routers WAN, nodos PE, firewalls o equipos de interconexión**. Esto tiene una interpretación de ingeniería directa: un equipo puede estar ubicado físicamente en un campus, pero su papel topológico puede estar más relacionado con la **interconexión institucional** que con los equipos locales de ese campus.

Por ejemplo, `INTERNET-MPLS`, los routers de campus y varios equipos PE terminan en la misma comunidad estructural aunque tengan etiquetas geográficas diferentes. Louvain está detectando en esos casos una función de transporte/interconexión compartida.

Por tanto, que un nodo “cambie de campus” en la partición no implica un error en los datos. Indica que la **proximidad topológica y la función de red no coinciden necesariamente con la ubicación administrativa**.

## 4. K-means sobre un embedding espectral

Para poder aplicar K-means a un grafo fue necesario convertir cada nodo en un vector. Se utilizó un **embedding espectral del laplaciano normalizado**, tomando los primeros autovectores no triviales y normalizando cada fila.

Se fijó **K = 14**, igual al número de comunidades de la mejor ejecución de Louvain, para hacer una comparación directa.

El K-means se implementó **desde cero en Python**, adaptando el ejemplo `algoritmos/kmeans/ejemplo1.jl` del repositorio del módulo. Se conservaron los elementos principales del código docente: distancia euclídea al cuadrado, inicialización K-means++, asignación al centroide más cercano, actualización mediante la media, WCSS y criterio de convergencia.

La mejor ejecución según WCSS fue la semilla **11**:

- WCSS = **18.1445**
- Q de la partición K-means = **0.7405**
- NMI K-means vs Louvain = **0.8748**
- ARI K-means vs Louvain = **0.6793**
- NMI K-means vs campus = **0.6327**
- ARI K-means vs campus = **0.3936**

El resultado es bastante similar a Louvain, especialmente según NMI, pero no idéntico. Louvain alcanza una modularidad mayor (0.7632 frente a 0.7405), algo esperable porque Louvain optimiza directamente una función basada en las aristas del grafo.

K-means puede funcionar razonablemente bien después del embedding espectral porque el espectro del laplaciano transforma información de conectividad en coordenadas geométricas. Sin embargo, K-means sigue suponiendo que los grupos pueden representarse mediante proximidad euclídea a centroides y requiere fijar K de antemano. Una comunidad de un grafo puede tener forma irregular, tamaños muy distintos o estar definida por cuellos de botella que no se representan perfectamente como grupos aproximadamente esféricos en el espacio vectorial.

## 5. Limitación de resolución de la modularidad

Para aportar evidencia sobre la limitación de resolución se repitió Louvain modificando el parámetro de resolución γ:

| γ | Comunidades | Q con γ | Q estándar de esa partición |
|---:|---:|---:|---:|
| 0.50 | 9 | 0.8199 | 0.7164 |
| 0.75 | 10 | 0.7919 | 0.7512 |
| 1.00 | 14 | 0.7632 | 0.7632 |
| 1.25 | 16 | 0.7358 | 0.7628 |
| 1.50 | 18 | 0.7140 | 0.7599 |
| 2.00 | 22 | 0.6826 | 0.7504 |

El resultado muestra una dependencia clara de la escala: con γ = 0.5 aparecen 9 comunidades, con γ = 1 aparecen 14 y con γ = 2 aparecen 22.

Un resultado particularmente importante es que al pasar de γ = 1 a **γ = 1.25**, el número de comunidades aumenta de **14 a 16**, pero si ambas particiones se evalúan con la modularidad estándar γ = 1, Q cambia solamente de **0.763181 a 0.762769**. Es decir, se obtiene una partición más fina con prácticamente la misma modularidad.

Además, al aumentar γ a 1.25, la comunidad 6 de 20 nodos y la comunidad 13 de 18 nodos ya se dividen en dos subcomunidades. A γ = 1.5 y 2.0 aparecen todavía más subdivisiones.

Esto constituye evidencia de la **limitación de resolución**: el máximo global o casi global de modularidad no determina una única escala “correcta”. Louvain a γ = 1 puede fusionar bloques que topológicamente están suficientemente relacionados para incrementar Q, aunque un administrador los considere unidades distintas por edificio, función, seguridad, gestión o ubicación física.

Por esta razón, las comunidades obtenidas no deberían interpretarse automáticamente como divisiones administrativas. Son una descripción de la organización estructural de la conectividad a una escala determinada.

## 6. Conclusión

P4 muestra que la red tiene una estructura comunitaria fuerte (**Q ≈ 0.763**), pero esta estructura no coincide exactamente con los campus. Los campus grandes contienen varios bloques topológicos y los elementos WAN/interconexión forman comunidades que atraviesan fronteras geográficas.

Louvain es relativamente estable frente a cambios de semilla en términos de modularidad y estructura global, aunque la asignación detallada de algunos nodos varía. El K-means espectral recupera una organización similar, pero con menor modularidad, lo que evidencia la diferencia entre agrupar según proximidad euclídea en un embedding y detectar directamente densidad de enlaces en un grafo.

Finalmente, la sensibilidad al parámetro γ muestra que no existe una única escala indiscutible de comunidades y que la interpretación final debe combinar los resultados matemáticos con el conocimiento de ingeniería de la infraestructura.

## Fuentes de código del módulo reutilizadas/adaptadas

- F. Astudillo-Salinas, repositorio **ComplexNetworks**, `intro/codes/gen_visualizacion-louvain.jl`: ejemplo de detección y visualización de comunidades Louvain.
- F. Astudillo-Salinas, repositorio **ComplexNetworks**, `algoritmos/kmeans/ejemplo1.jl`: implementación de K-means desde cero utilizada como base conceptual y estructural para la adaptación a Python.

Las fuentes se indican también en el encabezado del script `04_p4_comunidades.py`.
