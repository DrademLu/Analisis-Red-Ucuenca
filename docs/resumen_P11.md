# P11 — Propuesta de rediseño acotada y cuantificada

## 1. Criterio de diseño

La propuesta parte del diagnóstico integrado de P10, pero no intenta simplemente conectar los nodos con mayor centralidad. El objetivo es usar solamente **cinco cambios de topología** para reducir dependencias identificadas en varias fases:

- puentes y puntos de articulación de P1;
- cuellos de botella y cortes mínimos de P6;
- sensibilidad ante ataque dirigido de P8;
- puntos críticos consolidados en P10.

Se priorizaron enlaces que creen **caminos realmente alternativos**, evitando concentrar las cinco mejoras en un único nodo central.

## 2. Cinco intervenciones propuestas

| ID | Nodo A | Nodo B | Capacidad [Gbps] | Problema que resuelve |
|---|---|---|---:|---|
| I1 | `CP-EADMINA1-D6` | `ROUTER-CAMPUS-PARAISO` | 10 | Crea una salida alternativa para una de las ramas más grandes de Paraíso y contribuye a eliminar la dependencia del enlace CPAR-C10--ROUTER-CAMPUS-HUAYNA-CAPAC. |
| I2 | `CP-ODONTOLOGIA-D4` | `ROUTER-CAMPUS-PARAISO` | 10 | Da un segundo bypass del core CPAR-C10 para otra rama importante y evita concentrar toda la mejora en un único edificio. |
| I3 | `DT-0A-C12` | `PE2-BALZAY` | 20 | Simetriza la salida de los dos cores de Balzay hacia PE2. Actualmente el enlace 2x10G directo está representado solo desde DT-0A-C13. |
| I4 | `AGRPRI-1A-D10` | `INTERNET-MPLS` | 10 | Introduce un segundo uplink MPLS para Yanuncay y elimina al ROUTER-CAMPUS-YANUNCAY como punto de articulación. |
| I5 | `HOS-0A-D05` | `PE2-CENTRAL` | 10 | Agrega un segundo camino WAN para Hospitalidad y elimina como puente el uplink HOS-0A-D05--INTERNET-MPLS. |

### I1 — `CP-EADMINA1-D6 -- ROUTER-CAMPUS-PARAISO`, 10 Gbps

Esta conexión crea un uplink alternativo desde una de las ramas de agregación más grandes de Paraíso hacia el router WAN secundario ya representado en la red.

Su valor no consiste únicamente en agregar capacidad. También crea un ciclo que evita que todo el tráfico de esa rama dependa de `CPAR-C10` y del corredor `CPAR-C10 -- ROUTER-CAMPUS-HUAYNA-CAPAC`.

### I2 — `CP-ODONTOLOGIA-D4 -- ROUTER-CAMPUS-PARAISO`, 10 Gbps

Se agrega un segundo bypass desde otra rama importante de Paraíso. Utilizar dos ramas diferentes evita que la nueva redundancia dependa de un único switch de agregación.

Con I1 e I2, el enlace `CPAR-C10 -- ROUTER-CAMPUS-HUAYNA-CAPAC` deja de ser puente, y el router Huayna-Cápac deja de ser punto de articulación.

### I3 — `DT-0A-C12 -- PE2-BALZAY`, 20 Gbps

El dataset ya representa un enlace `DT-0A-C13 -- PE2-BALZAY` de **2×10 Gbps**, mientras el segundo core de Balzay (`DT-0A-C12`) no dispone de un enlace directo equivalente.

La intervención propone simetrizar ese diseño, de modo que ambos cores puedan alcanzar PE2 de forma directa. Se asumen **20 Gbps** para mantener consistencia con el enlace existente.

### I4 — `AGRPRI-1A-D10 -- INTERNET-MPLS`, 10 Gbps

Debe interpretarse como un **segundo circuito MPLS de Yanuncay**, no como un cable literal hacia una nube abstracta.

El resultado es importante: el enlace

`AGRPRI-1A-D10 -- ROUTER-CAMPUS-YANUNCAY`

deja de ser puente y `ROUTER-CAMPUS-YANUNCAY` deja de ser punto de articulación.

Además, el flujo máximo calculado para Yanuncay aumenta de 10 a **11 Gbps**, alcanzando prácticamente la capacidad conjunta que sus enlaces de acceso pueden inyectar bajo los supuestos de P6.

### I5 — `HOS-0A-D05 -- PE2-CENTRAL`, 10 Gbps

Hospitalidad tenía un único uplink representado hacia `INTERNET-MPLS`. El nuevo circuito proporciona una segunda salida por una ruta diferente.

El flujo máximo de Hospitalidad no aumenta porque el cuello de botella sigue estando en sus cuatro accesos de 1 Gbps, pero el enlace `HOS-0A-D05 -- INTERNET-MPLS` deja de ser puente. Es un caso donde **la mejora buscada es redundancia, no mayor throughput**.

## 3. Resultados antes / después

La propuesta completa produce:

| Métrica | Antes | Después | Variación absoluta | Variación |
|---|---:|---:|---:|---:|
| Número de puentes | 141.000000 | 136.000000 | -5.000000 | -3.55% |
| Puntos de articulación | 47.000000 | 45.000000 | -2.000000 | -4.26% |
| Distancia media [saltos] | 5.830380 | 5.494992 | -0.335388 | -5.75% |
| Eficiencia global | 0.208212 | 0.217910 | +0.009698 | +4.66% |
| AUC S(f), ataque adaptativo | 0.033882 | 0.037298 | +0.003415 | +10.08% |
| f50, ataque adaptativo | 0.022599 | 0.022599 | +0.000000 | +0.00% |
| S(f) con 5% de nodos eliminados | 0.050847 | 0.112994 | +0.062147 | +122.22% |

Los cambios principales son:

- puentes: **141 → 136**;
- puntos de articulación: **47 → 45**;
- distancia media: **5.830 → 5.495 saltos**, reducción de **5.75 %**;
- eficiencia global: **0.2082 → 0.2179**, incremento de **4.66 %**;
- AUC de robustez bajo ataque adaptativo: **+10.08 %**;
- con aproximadamente 5 % de los nodos atacados, la componente gigante pasa de **S≈0.051** a **S≈0.113**.

El `f50` del ataque adaptativo no cambia: permanece alrededor de **0.0226**. Por tanto, cinco enlaces no eliminan la fragilidad inicial frente a una secuencia óptima de ataques. La mejora aparece principalmente en la capacidad de la red para conservar una componente mayor **después de las primeras pérdidas críticas**.

### Puentes eliminados

La propuesta hace que dejen de ser puentes:

1. `CPAR-C10 -- ROUTER-CAMPUS-HUAYNA-CAPAC`
2. `CP-EADMINA1-D6 -- CPAR-C10`
3. `CP-ODONTOLOGIA-D4 -- CPAR-C10`
4. `AGRPRI-1A-D10 -- ROUTER-CAMPUS-YANUNCAY`
5. `HOS-0A-D05 -- INTERNET-MPLS`

Y dejan de ser puntos de articulación:

- `ROUTER-CAMPUS-HUAYNA-CAPAC`
- `ROUTER-CAMPUS-YANUNCAY`

Esto es particularmente valioso porque ambos routers aparecieron entre los puntos críticos del diagnóstico.

## 4. Flujo máximo por campus

| Campus | Antes [Gbps] | Después [Gbps] | Variación |
|---|---:|---:|---:|
| Campus Central | 44.0 | 44.0 | +0.0% |
| Campus Balzay | 23.0 | 23.0 | +0.0% |
| Campus Paraiso | 10.0 | 20.0 | +100.0% |
| Campus Yanuncay | 10.0 | 11.0 | +10.0% |
| Campus Hospitalidad | 4.0 | 4.0 | +0.0% |

El resultado más importante ocurre en **Paraíso**, donde el flujo máximo pasa de:

\[
10\text{ Gbps} \rightarrow 20\text{ Gbps}
\]

es decir, **+100 %**.

Yanuncay pasa de 10 a 11 Gbps. Central, Balzay y Hospitalidad permanecen iguales porque sus cortes limitantes se encuentran en otros lugares de la red.

Esto no significa que las intervenciones en Balzay y Hospitalidad sean inútiles: en ambos casos su propósito principal es introducir **redundancia de camino**.

## 5. Percolación bajo ataque dirigido

Se reutilizó la estrategia más severa de P8: eliminar el nodo con mayor intermediación, **recalculando la intermediación después de cada eliminación**.

La propuesta aumenta el área bajo la curva `S(f)` de:

\[
0.03388 \rightarrow 0.03730
\]

equivalente a una mejora aproximada del **10.08 %**.

A `f≈0.05`:

- red original: `S≈0.051`;
- red propuesta: `S≈0.113`.

Es decir, después de eliminar aproximadamente el 5 % de los equipos mediante un ataque adaptativo, la nueva red conserva una componente gigante **más de dos veces mayor** que la original.

Sin embargo, el `f50` permanece igual. Esto indica que siguen existiendo combinaciones muy críticas, especialmente alrededor de los cores de Central y de la salida institucional, que cinco enlaces no alcanzan a eliminar completamente.

## 6. Comparación contra dos alternativas

Se construyeron dos líneas base ingenuas:

1. **Alternativa por grado:** tomar el nodo de mayor grado y agregar los primeros cinco enlaces faltantes hacia otros nodos de grado alto.
2. **Alternativa por intermediación:** hacer lo mismo usando los nodos de mayor betweenness.

Los resultados son:

| Diseño | Puentes | Articulaciones | Distancia media | Eficiencia | AUC ataque adaptativo | f50 | S(5%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base | 141 | 47 | 5.830 | 0.2082 | 0.03388 | 0.0226 | 0.051 |
| Propuesta diagnostica | 136 | 45 | 5.495 | 0.2179 | 0.03730 | 0.0226 | 0.113 |
| Alternativa grado ingenuo | 138 | 45 | 4.521 | 0.2524 | 0.03388 | 0.0226 | 0.051 |
| Alternativa intermediacion ingenua | 140 | 46 | 4.658 | 0.2441 | 0.03388 | 0.0226 | 0.051 |

Las alternativas ingenuas obtienen mejores valores de **distancia media y eficiencia global**. Esto ocurre porque crean enlaces largos hacia un mismo hub (`DATCC-2A-C3`), introduciendo atajos artificialmente eficaces.

Pero esa solución presenta dos problemas.

Primero, **concentra todavía más la arquitectura alrededor de un nodo que P10 ya clasificó como crítico**. Bajo ataque adaptativo, ambas alternativas mantienen exactamente la misma AUC que la red original (`≈0.03388`), mientras la propuesta diagnóstica la incrementa a `≈0.03730`.

Segundo, su factibilidad es inferior: implican varios enlaces directos entre campus terminados en el mismo core de Central, mientras la propuesta utiliza en lo posible equipos WAN y rutas ya existentes para construir redundancia distribuida.

Por tanto, las alternativas ingenuas serían atractivas si el único objetivo fuera reducir el número de saltos. La propuesta resulta preferible si el objetivo del proyecto es **robustez operacional sin crear un nuevo super-hub**.

## 7. Costo y factibilidad cualitativa

No existen coordenadas, longitudes de fibra, disponibilidad de ductos ni inventario de puertos en el dataset. Por ello no es posible presentar un costo monetario defendible.

La factibilidad relativa puede clasificarse así:

- **I1 e I2 — Paraíso:** media-alta. Son enlaces intra-campus hacia un router existente. Requieren verificar distancias entre edificios, ductos y puertos 10G.
- **I3 — Balzay:** alta si `DT-0A-C12`, `DT-0A-C13` y `PE2-BALZAY` están realmente coubicados o unidos por infraestructura de data center. Sería esencial verificar puertos y ópticas 10G disponibles.
- **I4 — Yanuncay:** media. Implica contratar o construir un segundo circuito MPLS. Para que exista redundancia real, debe tener diversidad física de ruta respecto al enlace actual.
- **I5 — Hospitalidad:** media. También requiere un circuito metropolitano adicional hasta una terminación PE alternativa. Si ambos circuitos usan el mismo ducto, poste, proveedor o equipo intermedio, la redundancia topológica del modelo no sería redundancia física real.

Una conclusión importante es que **dos enlaces dibujados como distintos en el grafo no garantizan diversidad física**.

## 8. Limitaciones

El estudio no captura varios factores necesarios antes de ejecutar una obra real:

1. **Ubicación geográfica y longitud de fibra.** El grafo no contiene coordenadas ni rutas de ductería.
2. **Puertos disponibles.** No conocemos cuántos puertos 10/20 Gbps libres tienen los switches, routers o PE.
3. **Capacidades reales de 181 enlaces.** Muchas fueron estimadas en P6.
4. **SRLG y fallos comunes.** Dos enlaces pueden compartir ducto, energía, proveedor o equipo de transporte.
5. **Tráfico dinámico.** Las centralidades y flujos no sustituyen matrices de tráfico horarias reales.
6. **Protocolos y políticas.** OSPF/IS-IS, MPLS, VRF, STP, LAG y políticas de routing pueden impedir que una conexión físicamente existente sea utilizada como supone el grafo.
7. **Presupuesto real.** No pueden compararse CAPEX/OPEX sin metraje, obra civil, transceptores, licencias y cotizaciones.
8. **Disponibilidad del nodo extremo.** Una ruta nueva hacia un equipo crítico no elimina la necesidad de redundar energía, chasis y planos de control.

Por estas razones, los cinco enlaces son una **priorización técnica para estudios de factibilidad**, no una orden directa de construcción.

## 9. Respuesta final de ingeniería

Si administrara esta red y tuviera presupuesto para estudiar/construir cinco enlaces, priorizaría:

1. `CP-EADMINA1-D6 -- ROUTER-CAMPUS-PARAISO`, 10 Gbps.
2. `CP-ODONTOLOGIA-D4 -- ROUTER-CAMPUS-PARAISO`, 10 Gbps.
3. `DT-0A-C12 -- PE2-BALZAY`, 20 Gbps.
4. `AGRPRI-1A-D10 -- INTERNET-MPLS`, 10 Gbps como segundo circuito MPLS.
5. `HOS-0A-D05 -- PE2-CENTRAL`, 10 Gbps como ruta WAN alternativa.

La razón no es que unan simplemente “los nodos más importantes”. Se seleccionan porque eliminan **cinco puentes**, eliminan dos puntos de articulación WAN, duplican el flujo máximo de Paraíso, reducen la distancia media, aumentan la eficiencia y mejoran la supervivencia bajo un ataque adaptativo, al mismo tiempo que distribuyen la redundancia entre varias sedes.

La propuesta no es óptima para todas las métricas: un esquema ingenuo de enlaces largos hacia el core Central reduce más la distancia media. Sin embargo, ese esquema concentra aún más la red alrededor de `DATCC-2A-C3` y no mejora la robustez frente al ataque adaptativo. Para una red institucional, la decisión más defendible es **sacrificar parte de la ganancia en distancia para obtener redundancia distribuida**.
