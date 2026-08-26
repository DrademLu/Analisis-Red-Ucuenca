# P7 — Localización de colectores de telemetría

## 1. Planteamiento

Se desea instalar `p` colectores de telemetría sobre la red UCuenca de forma que los equipos queden próximos a alguna instalación. En este análisis se utilizó como distancia `d_ij` el **número mínimo de saltos** entre el equipo `i` y el nodo candidato `j`.

Como modelo base, **todos los nodos se consideran candidatos** para alojar un colector. Esta hipótesis permite analizar primero el problema puramente topológico; las restricciones físicas de instalación se incorporan posteriormente como una extensión.

Sea:

- `I` el conjunto de equipos de la red;
- `J` el conjunto de ubicaciones candidatas, en este caso `J = V`;
- `d_ij` la distancia mínima en saltos entre `i` y `j`;
- `y_j = 1` si se instala un colector en `j`;
- `x_ij = 1` si el equipo `i` es atendido por el colector ubicado en `j`.

## 2. Modelo p-mediana

El objetivo de p-mediana es minimizar la distancia total, y por tanto también la distancia media, desde todos los equipos hasta su colector asignado:

\[
\min \sum_{i \in I} \sum_{j \in J} d_{ij}x_{ij}
\]

sujeto a:

\[
\sum_{j \in J} x_{ij} = 1
\qquad \forall i \in I
\]

\[
x_{ij} \le y_j
\qquad \forall i \in I,\; j \in J
\]

\[
\sum_{j \in J} y_j = p
\]

\[
x_{ij}, y_j \in \{0,1\}
\]

La primera restricción obliga a que cada equipo sea asignado a una instalación; la segunda impide asignarlo a un colector que no haya sido instalado y la tercera fija exactamente `p` colectores.

## 3. Modelo p-centro

El problema p-centro busca minimizar la peor distancia de la red. Se introduce una variable continua `z` que representa la distancia máxima:

\[
\min z
\]

con las mismas restricciones de asignación y apertura anteriores, añadiendo:

\[
\sum_{j \in J} d_{ij}x_{ij} \le z
\qquad \forall i \in I
\]

De esta forma, ningún equipo puede quedar a una distancia superior a `z` del colector al que ha sido asignado.

Para las soluciones MILP de p-centro se aplicó además un criterio secundario: una vez obtenido el **radio mínimo exacto**, se mantuvo ese valor fijo y se minimizó la suma de distancias. Esto solo sirve para escoger una solución representativa cuando existen varias configuraciones con el mismo radio óptimo.

## 4. Métodos de solución

Se implementó una **heurística voraz** para cada problema. En p-mediana se agrega en cada iteración el candidato que más reduce la suma total de distancias. En p-centro se agrega el candidato que más reduce la distancia máxima; en caso de empate se utiliza la distancia media como criterio secundario.

Como comparación se formularon ambos problemas como **programas lineales enteros mixtos (MILP)** y se resolvieron con `scipy.optimize.milp`, que utiliza HiGHS.

## 5. Resultados exactos de p-mediana

| p | Distancia media | Distancia máxima | Ubicaciones |
|---:|---:|---:|---|
| 1 | 3.605 | 6 | `INTERNET-MPLS` |
| 2 | 2.746 | 7 | `CPAR-C10 | DATCC-2A-C3` |
| 3 | 2.192 | 5 | `CPAR-C10 | DATCC-2A-C3 | DT-0A-C13` |
| 5 | 1.797 | 4 | `AGRPRI-1A-D10 | CPAR-C10 | DATCC-2A-C2 | DT-0A-C13 | INTERNET-MPLS` |

Con un único colector, la solución es **`INTERNET-MPLS`**, con una distancia media de aproximadamente **3.605 saltos**.

Con dos colectores, el óptimo se desplaza a **`CPAR-C10` y `DATCC-2A-C3`**, reduciendo la distancia media a **2.746 saltos**. Es importante notar que la distancia máxima aumenta a 7 saltos: p-mediana optimiza el promedio y no garantiza minimizar el peor caso.

Con tres colectores aparecen los cores de Central, Paraíso y Balzay, y la distancia media baja a **2.192 saltos**.

Con cinco colectores se obtiene una distancia media de **1.797 saltos** y una distancia máxima de 4. La solución distribuye instalaciones entre Central, Balzay, Paraíso, Yanuncay y la zona MPLS.

## 6. Resultados exactos de p-centro

| p | Distancia media | Distancia máxima | Ubicaciones |
|---:|---:|---:|---|
| 1 | 3.605 | 6 | `INTERNET-MPLS` |
| 2 | 2.780 | 6 | `DATCC-2A-C2 | INTERNET-MPLS` |
| 3 | 2.294 | 4 | `DATCC-2A-C3 | DT-0A-C13 | ROUTER-CAMPUS-HUAYNA-CAPAC` |
| 5 | 1.989 | 3 | `CB-EADMI-D6 | CPAR-C10 | DATCC-2A-C3 | POST-1A-A65 | ROUTER-CAMPUS-YANUNCAY` |

El comportamiento es diferente al de p-mediana.

Con `p=1`, ambos problemas coinciden en `INTERNET-MPLS` y el radio de cobertura es de **6 saltos**.

Con `p=2`, el radio no puede reducirse por debajo de 6, aunque la media mejora.

Con `p=3`, p-centro consigue reducir la peor distancia a **4 saltos** utilizando `DATCC-2A-C3`, `DT-0A-C13` y `ROUTER-CAMPUS-HUAYNA-CAPAC`.

Con `p=5`, la distancia máxima baja a solamente **3 saltos**, aunque la distancia media (**1.989**) es peor que la obtenida por p-mediana (**1.797**). Esto refleja exactamente la diferencia entre ambos objetivos: p-mediana favorece el rendimiento promedio, mientras p-centro sacrifica parte del promedio para proteger a los equipos más alejados.

## 7. Heurística voraz frente al óptimo

### p-mediana

| p | Objetivo voraz | Objetivo exacto | Diferencia |
|---:|---:|---:|---:|
| 1 | 3.605 | 3.605 | 0.00% |
| 2 | 2.780 | 2.746 | 1.23% |
| 3 | 2.305 | 2.192 | 5.15% |
| 5 | 1.797 | 1.797 | 0.00% |

La heurística funciona bastante bien. Para `p=1` encuentra el óptimo; para `p=2` queda ligeramente por encima; para `p=3` la diferencia es más visible; y para `p=5` alcanza una solución con el mismo valor objetivo que el MILP, aunque no necesariamente con exactamente el mismo conjunto de nodos.

### p-centro

| p | Objetivo voraz | Objetivo exacto | Diferencia |
|---:|---:|---:|---:|
| 1 | 6.000 | 6.000 | 0.00% |
| 2 | 6.000 | 6.000 | 0.00% |
| 3 | 5.000 | 4.000 | 25.00% |
| 5 | 4.000 | 3.000 | 33.33% |

En p-centro la limitación de la heurística se observa con mayor claridad. Para `p=3` el método voraz deja un radio de 5 saltos, mientras que la solución exacta demuestra que puede alcanzarse **4**. Para `p=5`, el voraz alcanza 4 pero el MILP reduce la peor distancia a **3 saltos**.

## 8. Comparación con las centralidades de P1

Los resultados coinciden **parcialmente** con los nodos centrales de P1.

Con `p=1`, `INTERNET-MPLS` es una elección natural: ocupa el **primer lugar en centralidad de cercanía** y el cuarto en intermediación.

Sin embargo, al aumentar `p`, comienzan a aparecer nodos que no están entre los más centrales globalmente. Por ejemplo, en la solución p-mediana con cinco colectores aparece `AGRPRI-1A-D10`, que ocupa aproximadamente la posición **39 por cercanía**. En p-centro con cinco colectores aparece `CB-EADMI-D6`, posición **37 por cercanía**, y el caso más extremo es **`POST-1A-A65`**, que ocupa aproximadamente la posición **161 por cercanía** y 54 por intermediación.

Esto no es una contradicción. Una centralidad responde a la pregunta:

> “¿Qué nodo está bien situado respecto al conjunto de la red?”

El problema de localización responde en cambio a:

> “¿Qué conjunto de `p` nodos, actuando simultáneamente, cubre mejor a todos los equipos?”

Cuando ya existe un colector en una región central, instalar otro colector muy cerca de él puede aportar poco. Es preferible ubicar la siguiente instalación en una región menos central pero mal cubierta. Por eso un nodo periférico puede formar parte de la solución óptima de p-centro: su función no es ser central respecto a toda la red, sino **reducir la distancia del peor sector actualmente descubierto**.

El caso `POST-1A-A65` ilustra especialmente bien esta diferencia: individualmente es muy poco central, pero en la solución de cinco p-centros contribuye a que ningún equipo de toda la institución quede a más de tres saltos de un colector.

## 9. Restricciones prácticas omitidas

El modelo base supone que cualquier nodo puede alojar un colector, lo cual no necesariamente es realista. Una restricción especialmente importante sería la **elegibilidad física de la instalación**: un equipo puede no disponer de energía disponible, espacio en rack, acceso administrativo o condiciones de seguridad suficientes.

Esto puede incorporarse definiendo un parámetro binario `a_j`, donde `a_j = 1` si el nodo es apto para recibir un colector, y añadiendo:

\[
y_j \le a_j
\qquad \forall j
\]

Así se excluyen automáticamente ubicaciones no viables.

También sería posible incorporar costos de licencia o instalación mediante un presupuesto, capacidades máximas de procesamiento de cada colector o exigir redundancia de monitoreo. Por ejemplo, si cada colector tiene capacidad `Q_j` y cada equipo genera `q_i` unidades de telemetría, podría agregarse:

\[
\sum_i q_i x_{ij} \le Q_j y_j
\]

De esta manera el modelo dejaría de ser únicamente topológico y se aproximaría mejor a una decisión de despliegue real.

## 10. Conclusión

P7 muestra que la ubicación óptima de recursos depende del criterio utilizado. La p-mediana minimiza la experiencia promedio y, con cinco colectores, alcanza una distancia media de aproximadamente **1.80 saltos**. El p-centro prioriza equidad de cobertura y consigue que ningún equipo quede a más de **3 saltos**, a cambio de una distancia media ligeramente mayor.

Los nodos más centrales de P1 son buenos candidatos iniciales, pero no determinan por sí solos la solución. Cuando se instalan varias facilidades, el valor de una ubicación depende de **qué zonas ya están cubiertas por los demás colectores**. Por ello, “el nodo más central” y “el mejor conjunto de ubicaciones” son problemas relacionados pero distintos.


