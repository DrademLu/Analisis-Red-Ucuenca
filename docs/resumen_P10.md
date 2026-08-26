# P10 — Síntesis del diagnóstico de puntos críticos

## 1. Objetivo

P10 consolida la evidencia obtenida en las Fases 1 a 4 en un único ranking de criticidad. La finalidad no es sustituir las métricas individuales, sino identificar los nodos que reúnen **varios tipos de vulnerabilidad simultáneamente**: importancia de tránsito, dependencia topológica, cuello de botella de capacidad y daño dinámico.

## 2. Índice compuesto propuesto

Para cada nodo `i` se definió:

\[
I_i =
0.25 B_i +
0.10 A_i +
0.20 M_i +
0.15 P_i +
0.30 C_i
\]

donde:

- **`B_i` — intermediación (25 %):** intermediación de P1 normalizada respecto al máximo de la red. Representa cuánto depende el tránsito por caminos mínimos de ese equipo.
- **`A_i` — punto de articulación (10 %):** vale 1 si el nodo es punto de articulación y 0 en caso contrario. Su peso es deliberadamente menor porque parte de su efecto ya queda cuantificado en `P_i`.
- **`M_i` — participación en corte mínimo (20 %):** combina los cortes mínimos de P6. Para cada campus, una arista aporta a sus extremos la fracción `capacidad_arista / capacidad_total_corte`; luego se suman los campus y se normaliza.
- **`P_i` — daño de percolación (15 %):** se elimina únicamente el nodo `i` y se calcula qué fracción de los otros 176 nodos queda fuera de la componente gigante. Se normaliza respecto al mayor daño observado.
- **`C_i` — daño de cascada (30 %):** fracción de fallos **secundarios** producidos por el disparador en P9 usando `τ = 0.035`, valor situado inmediatamente alrededor del margen crítico obtenido en P9. Se utiliza un peso alto porque es la métrica que incorpora explícitamente propagación dinámica de daño.

Todos los términos salvo `A_i` quedan reescalados al intervalo `[0,1]`.

El índice no pretende afirmar que esos pesos sean únicos. Por esa razón se realizó además un análisis con **20 % para cada componente**. **8/10 nodos del top-10 permanecen en ambos rankings**, lo que indica que el diagnóstico principal es razonablemente estable frente a una elección alternativa sencilla de pesos.

## 3. Top-10 de puntos críticos

| # | Nodo | Campus | Función | Índice | Principales evidencias |
|---:|---|---|---|---:|---|
| 1 | `CPAR-C10` | Campus Paraiso | Núcleo (core) | **0.673** | betweenness=0.404; punto de articulación; corte mínimo (Campus Paraiso); percolación: 41 nodos fuera de GCC |
| 2 | `ROUTER-CAMPUS-HUAYNA-CAPAC` | Campus Paraiso | Router WAN de campus | **0.655** | betweenness=0.366; punto de articulación; corte mínimo (Campus Paraiso); percolación: 42 nodos fuera de GCC |
| 3 | `DATCC-2A-C3` | Campus Central | Núcleo (core) | **0.484** | betweenness=0.447; corte mínimo (Campus Central); cascada: +12 fallos |
| 4 | `INTERNET-MPLS` | Nube MPLS | Salida institucional / nube MPLS | **0.422** | betweenness=0.366; punto de articulación; percolación: 8 nodos fuera de GCC; cascada: +11 fallos |
| 5 | `ROUTER-CAMPUS-YANUNCAY` | Campus Yanuncay | Router WAN de campus | **0.414** | betweenness=0.128; punto de articulación; corte mínimo (Campus Yanuncay); percolación: 12 nodos fuera de GCC |
| 6 | `AGRPRI-1A-D10` | Campus Yanuncay | Agregación / distribución | **0.407** | betweenness=0.121; punto de articulación; corte mínimo (Campus Yanuncay); percolación: 11 nodos fuera de GCC |
| 7 | `HOS-0A-D05` | Campus Hospitalidad | Agregación / distribución | **0.340** | betweenness=0.045; punto de articulación; corte mínimo (Campus Hospitalidad); percolación: 4 nodos fuera de GCC |
| 8 | `ROUTER-CAMPUS-CENTRO-HISTORICO` | Sede Centro Historico | Router WAN de campus | **0.307** | betweenness=0.004; corte mínimo (Campus Central); cascada: +37 fallos |
| 9 | `PE2-CENTRAL` | Campus Central | Router PE / tránsito WAN | **0.293** | betweenness=0.288; corte mínimo (Campus Central); cascada: +5 fallos |
| 10 | `BAL-AUL2-D1` | Campus Balzay | Agregación / distribución | **0.285** | betweenness=0.111; punto de articulación; corte mínimo (Campus Balzay); percolación: 10 nodos fuera de GCC |

El resultado muestra dos familias principales de criticidad. La primera corresponde a **puntos de entrada/salida de campus con poca redundancia topológica**, especialmente Paraíso y Yanuncay. La segunda corresponde a **equipos de tránsito institucional**, como los cores de Central, `INTERNET-MPLS`, routers PE y elementos capaces de desencadenar cascadas.

## 4. Fichas individuales

### 1. `CPAR-C10`

**Campus:** Campus Paraiso  
**Función:** Núcleo (core)  
**Índice compuesto:** **0.673**

**Evidencias:** intermediación = **0.4043**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Paraiso); su eliminación aislada deja **41 nodos** fuera de la componente gigante.

**Consecuencia estimada:** riesgo de aislamiento de una región institucional grande; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.
### 2. `ROUTER-CAMPUS-HUAYNA-CAPAC`

**Campus:** Campus Paraiso  
**Función:** Router WAN de campus  
**Índice compuesto:** **0.655**

**Evidencias:** intermediación = **0.3663**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Paraiso); su eliminación aislada deja **42 nodos** fuera de la componente gigante.

**Consecuencia estimada:** riesgo de aislamiento de una región institucional grande; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.
### 3. `DATCC-2A-C3`

**Campus:** Campus Central  
**Función:** Núcleo (core)  
**Índice compuesto:** **0.484**

**Evidencias:** intermediación = **0.4468**; participa en **1 corte(s) mínimo(s)** (Campus Central); a τ=0.035 produce **12 fallos secundarios**.

**Consecuencia estimada:** su indisponibilidad reduce o compromete la capacidad de salida hacia Internet; puede inducir sobrecargas secundarias.
### 4. `INTERNET-MPLS`

**Campus:** Nube MPLS  
**Función:** Salida institucional / nube MPLS  
**Índice compuesto:** **0.422**

**Evidencias:** intermediación = **0.3657**; es **punto de articulación**; su eliminación aislada deja **8 nodos** fuera de la componente gigante; a τ=0.035 produce **11 fallos secundarios**.

**Consecuencia estimada:** puede aislar una rama o conjunto de equipos; puede inducir sobrecargas secundarias.
### 5. `ROUTER-CAMPUS-YANUNCAY`

**Campus:** Campus Yanuncay  
**Función:** Router WAN de campus  
**Índice compuesto:** **0.414**

**Evidencias:** intermediación = **0.1278**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Yanuncay); su eliminación aislada deja **12 nodos** fuera de la componente gigante.

**Consecuencia estimada:** puede aislar una rama o conjunto de equipos; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.
### 6. `AGRPRI-1A-D10`

**Campus:** Campus Yanuncay  
**Función:** Agregación / distribución  
**Índice compuesto:** **0.407**

**Evidencias:** intermediación = **0.1214**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Yanuncay); su eliminación aislada deja **11 nodos** fuera de la componente gigante.

**Consecuencia estimada:** puede aislar una rama o conjunto de equipos; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.
### 7. `HOS-0A-D05`

**Campus:** Campus Hospitalidad  
**Función:** Agregación / distribución  
**Índice compuesto:** **0.340**

**Evidencias:** intermediación = **0.0451**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Hospitalidad); su eliminación aislada deja **4 nodos** fuera de la componente gigante.

**Consecuencia estimada:** puede aislar una rama o conjunto de equipos; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.
### 8. `ROUTER-CAMPUS-CENTRO-HISTORICO`

**Campus:** Sede Centro Historico  
**Función:** Router WAN de campus  
**Índice compuesto:** **0.307**

**Evidencias:** intermediación = **0.0044**; participa en **1 corte(s) mínimo(s)** (Campus Central); a τ=0.035 produce **37 fallos secundarios**.

**Consecuencia estimada:** su indisponibilidad reduce o compromete la capacidad de salida hacia Internet; es capaz de iniciar una cascada sistémica.
### 9. `PE2-CENTRAL`

**Campus:** Campus Central  
**Función:** Router PE / tránsito WAN  
**Índice compuesto:** **0.293**

**Evidencias:** intermediación = **0.2881**; participa en **1 corte(s) mínimo(s)** (Campus Central); a τ=0.035 produce **5 fallos secundarios**.

**Consecuencia estimada:** su indisponibilidad reduce o compromete la capacidad de salida hacia Internet; puede inducir sobrecargas secundarias.
### 10. `BAL-AUL2-D1`

**Campus:** Campus Balzay  
**Función:** Agregación / distribución  
**Índice compuesto:** **0.285**

**Evidencias:** intermediación = **0.1107**; es **punto de articulación**; participa en **1 corte(s) mínimo(s)** (Campus Balzay); su eliminación aislada deja **10 nodos** fuera de la componente gigante.

**Consecuencia estimada:** puede aislar una rama o conjunto de equipos; su indisponibilidad reduce o compromete la capacidad de salida hacia Internet.


## 5. Lectura del ranking

### Paraíso domina los dos primeros puestos

`CPAR-C10` y `ROUTER-CAMPUS-HUAYNA-CAPAC` aparecen en las posiciones 1 y 2 porque reúnen simultáneamente:

- intermediación muy alta;
- condición de punto de articulación;
- participación directa en el corte mínimo de Paraíso;
- gran daño de fragmentación cuando se elimina uno de ellos.

La pareja coincide con el enlace `CPAR-C10 — ROUTER-CAMPUS-HUAYNA-CAPAC`, que ya había aparecido en P1 como puente, en P6 como único corte mínimo de Paraíso y en P8 como uno de los enlaces con mayor impacto. Por tanto, esta zona constituye el **single point of failure más claramente respaldado por métricas independientes**.

### Campus Central es crítico por tránsito, no por una sola articulación

`DATCC-2A-C3`, `PE2-CENTRAL` e `INTERNET-MPLS` aparecen por su elevado papel de tránsito y/o por el daño secundario que producen. `DATCC-2A-C3`, por ejemplo, no es punto de articulación individual, lo que confirma la redundancia parcial del core de Central; sin embargo, concentra la mayor intermediación de toda la red y participa en el corte mínimo de Central.

Esto es importante: **no ser un punto de articulación no significa no ser crítico**. Un nodo puede disponer de una ruta alternativa y aun así ser operacionalmente crítico porque al fallar desplaza una gran cantidad de tránsito hacia pocos caminos restantes.

### El caso de Centro Histórico demuestra el valor de incluir cascadas

`ROUTER-CAMPUS-CENTRO-HISTORICO` tiene una intermediación estática muy baja y no es punto de articulación, pero aparece en el puesto **8** porque a `τ=0.035` su falla desencadena **37 fallos secundarios**, el mayor daño dinámico encontrado cerca del margen crítico.

Si P10 se construyera únicamente con centralidades de P1, este equipo prácticamente desaparecería del diagnóstico. Su aparición demuestra por qué era necesario integrar P9: **un nodo aparentemente poco central puede convertirse en un disparador peligroso después de la redistribución de cargas**.

## 6. Qué significa operacionalmente el top-10

El ranking no debe interpretarse como “los diez equipos que necesariamente fallarán primero”, sino como una **lista de prioridad para reducción de riesgo**.

Los nodos superiores deberían recibir prioridad en medidas como:

- verificación real de redundancia y failover;
- mantenimiento no simultáneo de rutas alternativas;
- monitoreo de carga y alarmas;
- endurecimiento de seguridad y parcheo;
- disponibilidad de repuestos/configuraciones de respaldo;
- evaluación de nuevos enlaces en P11.

Además, el tipo de intervención depende de la métrica dominante. Un punto de articulación requiere principalmente **camino alternativo**; un nodo de alta intermediación pero no articulación requiere revisar **capacidad y balance de tráfico**; y un disparador de cascada requiere suficiente **margen operativo** en los elementos que absorberán la carga tras su falla.

## 7. Limitaciones del índice

El índice compuesto es una herramienta de priorización, no una medida física absoluta de riesgo. Existen tres limitaciones importantes:

1. Los pesos son decisiones de modelado; la sensibilidad 8/10 muestra estabilidad razonable, pero algunos puestos pueden cambiar.
2. La participación en cortes mínimos depende de las capacidades estimadas en P6.
3. El daño de cascada depende del modelo simplificado de P9 y del valor de tolerancia elegido; la intermediación es un proxy de carga, no tráfico real medido.

Por ello el ranking debe leerse como **evidencia cuantitativa para decidir qué puntos inspeccionar y reforzar primero**, no como sustituto de mediciones reales, inventario físico y pruebas de failover.

## 8. Conclusión

El diagnóstico integrado identifica como prioridad máxima la salida de **Campus Paraíso**, seguida por los elementos de tránsito del core/WAN institucional y la salida de Yanuncay. La evidencia más consistente se obtiene cuando varias fases apuntan al mismo elemento: `CPAR-C10` y `ROUTER-CAMPUS-HUAYNA-CAPAC` son simultáneamente centrales, puntos de articulación, participantes del corte mínimo y responsables de una fragmentación grande.

P10 también revela casos que una única métrica no detectaría. `ROUTER-CAMPUS-CENTRO-HISTORICO`, pese a su baja centralidad estática, entra al top-10 debido a su capacidad de iniciar una cascada severa. Esta combinación de **vulnerabilidad estructural, capacidad y dinámica** es la base que debe utilizarse en P11 para justificar las cinco intervenciones de rediseño.
