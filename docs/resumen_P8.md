# P8 — Percolación y robustez de la red UCuenca

## 1. Metodología

Se estudió la robustez mediante eliminación progresiva de nodos y enlaces. Para nodos se emplearon cuatro estrategias: fallo aleatorio (100 realizaciones), ataque por grado descendente, ataque por intermediación descendente y ataque adaptativo por intermediación recalculada tras cada eliminación.

Se define `S(f) = |GCC(f)| / 177`, donde `GCC(f)` es la componente conexa gigante. Para esta red finita se estima `f_c` como la fracción eliminada en la que la segunda componente conexa alcanza su tamaño máximo. También se reporta `f50`, primera fracción para la que `S(f) <= 0.5`.

La eficiencia global se calculó con `E = [1/(n(n-1))] * sum_(i!=j) 1/d_ij` sobre los nodos supervivientes. La eficiencia inicial fue **E(0) = 0.2082**.

## 2. Percolación de nodos

| Estrategia | f_c | f50 |
|---|---:|---:|
| Fallo aleatorio (media 100) | 0.271 | 0.237 |
| Grado descendente | 0.011 | 0.023 |
| Intermediación descendente | 0.051 | 0.045 |
| Intermediación recalculada | 0.011 | 0.023 |

El contraste es muy fuerte. Con fallos aleatorios se requiere eliminar aproximadamente **23.7 % de los nodos** para que la componente gigante promedio caiga por debajo del 50 %. En cambio, con ataque por grado o por intermediación recalculada basta aproximadamente **2.26 %**, es decir, apenas **cuatro nodos**.

| f aprox. | Aleatorio | Grado | Intermediación fija | Intermediación adaptativa |
|---:|---:|---:|---:|---:|
| 0.05 | 0.872 | 0.373 | 0.198 | 0.051 |
| 0.10 | 0.757 | 0.051 | 0.045 | 0.034 |
| 0.20 | 0.558 | 0.028 | 0.028 | 0.017 |
| 0.30 | 0.395 | 0.017 | 0.011 | 0.011 |
| 0.50 | 0.158 | 0.006 | 0.006 | 0.011 |

Con solo 5 % de nodos eliminados, el fallo aleatorio conserva en promedio `S ≈ 0.872`, mientras el ataque adaptativo deja solamente `S ≈ 0.051`.

La desviación estándar de los 100 fallos aleatorios es apreciable: cerca de `f=0.10`, **S = 0.757 ± 0.107**; cerca de `f=0.20`, **S = 0.558 ± 0.120**. Esto muestra que el impacto de una misma cantidad de fallos depende fuertemente de qué equipos concretos resulten afectados.

### Nodos responsables de la fragilidad dirigida

El ataque por grado comienza por `DATCC-2A-C3` y `DATCC-2A-C2`, los dos nodos de mayor grado. La primera eliminación apenas fragmenta la red (`S ≈ 0.994`), pero al perder también el segundo core la componente gigante cae a **S ≈ 0.610**.

El ataque adaptativo comienza igualmente por `DATCC-2A-C3` y, tras recalcular, selecciona `DATCC-2A-C2`; después aparecen `INTERNET-MPLS`, `CPAR-C10` y los cores de Balzay. La red tolera la pérdida de uno de los cores de Central, pero no la pérdida conjunta de ambos.

## 3. Percolación de enlaces

Para enlaces se compararon fallo aleatorio (100 realizaciones), intermediación de arista fija, intermediación de arista adaptativa y un ataque que elimina primero los puentes de P1 ordenados por intermediación.

| Estrategia | f_c | f50 |
|---|---:|---:|
| Fallo aleatorio | 0.474 | 0.364 |
| Intermediación de arista | 0.005 | 0.177 |
| Intermediación adaptativa | 0.033 | 0.033 |
| Puentes de P1 primero | 0.005 | 0.220 |

El ataque adaptativo por intermediación de arista es el más destructivo según `f50`: con aproximadamente **3.35 % de los enlaces** eliminados la componente gigante ya cae por debajo de la mitad.

El ataque a puentes produce un efecto inmediato particularmente importante. El primer puente seleccionado es `CPAR-C10 — ROUTER-CAMPUS-HUAYNA-CAPAC`, que también apareció como puente en P1 y como corte mínimo de Campus Paraíso en P6. Al eliminar una sola arista (`1/209 ≈ 0.48 %`) `S` cae de 1.0 a **0.763**, separando una componente de aproximadamente 42 nodos.

No todos los puentes tienen el mismo impacto. Muchos son enlaces de ramas de acceso que separan uno o pocos equipos; por ello atacar todos los puentes primero no es tan destructivo como recalcular continuamente la arista de mayor intermediación.

## 4. Eficiencia global

La eficiencia aporta información adicional al tamaño de la componente gigante. Tras eliminar solo los **dos nodos de mayor grado** (`f ≈ 0.0113`), la componente gigante aún contiene aproximadamente **61.0 %** de los nodos originales, pero la eficiencia ya ha caído a **44.7 % de E(0)**. En el ataque por intermediación fija, tras cuatro eliminaciones (`f ≈ 0.0226`), `S ≈ 0.701` mientras la eficiencia es aproximadamente **60.7 % de E(0)**.

Esto ocurre porque pueden perderse atajos y aumentar las distancias entre equipos que todavía permanecen conectados. Por ello el rendimiento topológico puede degradarse antes de que la componente gigante colapse completamente.

Como la definición estándar utiliza `n(n-1)` de los nodos supervivientes, en etapas de fragmentación extrema la eficiencia puede dejar de ser monótona al cambiar también el denominador. La interpretación más útil se concentra en la etapa previa al colapso y en la comparación con `E(0)`.

## 5. Comparación con los modelos nulos de P2

Los modelos Erdős–Rényi y de configuración no siempre son conexos en `f=0`, por lo que se reportan curvas absolutas y una comparación normalizada por el tamaño inicial de la componente gigante.

### Curvas absolutas

| Ataque | Modelo | S(0) | AUC de S | f50 absoluto |
|---|---|---:|---:|---:|
| fallo_aleatorio | Configuracion | 0.798 | 0.276 | 0.226 |
| fallo_aleatorio | Erdos-Renyi | 0.872 | 0.281 | 0.271 |
| fallo_aleatorio | UCuenca | 1.000 | 0.278 | 0.237 |
| grado_desc | Configuracion | 0.798 | 0.059 | 0.045 |
| grado_desc | Erdos-Renyi | 0.872 | 0.115 | 0.107 |
| grado_desc | UCuenca | 1.000 | 0.045 | 0.023 |

### Degradación relativa al estado inicial

| Ataque | Modelo | AUC relativa | f50 relativo |
|---|---|---:|---:|
| fallo_aleatorio | Configuracion | 0.346 | 0.322 |
| fallo_aleatorio | Erdos-Renyi | 0.322 | 0.311 |
| fallo_aleatorio | UCuenca | 0.278 | 0.237 |
| grado_desc | Configuracion | 0.074 | 0.062 |
| grado_desc | Erdos-Renyi | 0.132 | 0.113 |
| grado_desc | UCuenca | 0.045 | 0.023 |

La comparación más importante es con el modelo de **configuración**, porque conserva la secuencia de grados. Bajo fallos aleatorios, UCuenca presenta `f50 relativo ≈ 0.237`, mientras la configuración llega a **0.322**. Bajo ataque por grado la diferencia es aún mayor: **0.023 frente a 0.062**.

Por tanto, UCuenca resulta **más frágil de lo que su secuencia de grados por sí sola haría esperar**. La ubicación concreta de los hubs, puntos de articulación y puentes dentro de la arquitectura jerárquica introduce vulnerabilidades adicionales.

## 6. ¿Se verifica el patrón “robusta a fallos aleatorios y frágil a ataques dirigidos”?

Sí, **cualitativamente**, pero con un matiz. El `f50` de nodos cambia de aproximadamente **0.237** para fallos aleatorios a **0.023** para ataques por grado/adaptativos, una diferencia superior a un orden de magnitud. A `f≈0.05`, el fallo aleatorio conserva alrededor del 87 % de los equipos en la componente gigante, mientras el ataque adaptativo deja aproximadamente el 5 %.

Sin embargo, frente al modelo de configuración UCuenca no es especialmente robusta incluso ante fallos aleatorios. La topología jerárquica y la gran cantidad de puentes hacen que se deteriore más rápido que redes aleatorizadas con la misma secuencia de grados.

## 7. Consecuencias operativas

### Mantenimiento

No debe planificarse mantenimiento solo por la cantidad de equipos desconectados, sino por **qué equipos se intervienen simultáneamente**. En particular, `DATCC-2A-C3` y `DATCC-2A-C2` no deberían quedar fuera de servicio al mismo tiempo. Antes de intervenir un enlace crítico debe comprobarse que el camino redundante esté realmente operativo.

Una política razonable es clasificar ventanas de mantenimiento por criticidad topológica, verificar failover antes de retirar un elemento y evitar mantenimientos simultáneos sobre equipos pertenecientes al mismo conjunto crítico.

### Respuesta ante incidentes de seguridad

Un atacante puede priorizar cores, routers, firewalls o enlaces de alto tránsito, por lo que el comportamiento relevante se parece más al ataque dirigido que al fallo aleatorio. La defensa debe priorizar nodos de alto grado/intermediación y puentes de gran impacto.

La estrategia adaptativa añade otra conclusión: después de aislar un elemento crítico, **la criticidad del resto cambia**. Una respuesta a incidentes debería recalcular la topología efectiva tras cada aislamiento en vez de depender únicamente de un ranking calculado antes del incidente.

## 8. Conclusión

P8 muestra una fuerte sensibilidad de la red UCuenca a ataques dirigidos. La selección informada de apenas dos a cuatro nodos puede desarticular grandes regiones de la infraestructura. En enlaces, `CPAR-C10 — ROUTER-CAMPUS-HUAYNA-CAPAC` reaparece como un punto crítico: una sola eliminación separa cerca de una cuarta parte de la red.

La comparación con el modelo de configuración confirma además que la fragilidad no depende únicamente de la distribución de grados, sino de la organización jerárquica específica y de la ubicación de la redundancia.


Sí, **sí está respondida en el `.md`**, y bastante explícitamente.

La respuesta aparece en dos secciones principales:

* **Sección 6: “¿Se verifica el patrón ‘robusta a fallos aleatorios y frágil a ataques dirigidos’?”** Ahí se concluye que **sí, cualitativamente**, porque el `f50` pasa de aproximadamente **0.237 en fallos aleatorios** a **0.023 en ataques por grado/adaptativos**; además, con solo ~5 % de nodos eliminados, el fallo aleatorio conserva cerca del 87 % de la componente gigante, mientras el ataque adaptativo la reduce a ~5 %. 

* **Sección 7: “Consecuencias operativas”**, donde se responde específicamente qué implica para mantenimiento y seguridad. Para mantenimiento, se indica que no debe planificarse solo por cantidad de equipos fuera de servicio, sino por **qué equipos se intervienen simultáneamente**; se menciona explícitamente evitar sacar a la vez `DATCC-2A-C3` y `DATCC-2A-C2`, verificar failover y clasificar ventanas según criticidad.  Para seguridad, se señala que un atacante puede priorizar cores, routers, firewalls o enlaces críticos, por lo que el escenario relevante se parece más al ataque dirigido; además, después de aislar un elemento debe **recalcularse la criticidad** porque el ranking cambia dinámicamente. 

Además, el MD añade un matiz importante: aunque UCuenca sí es mucho más resistente a fallos aleatorios que a ataques dirigidos, **no es especialmente robusta frente al modelo de configuración con la misma secuencia de grados**; de hecho resulta más frágil, lo que indica que la vulnerabilidad no proviene solo de tener hubs, sino de **cómo están ubicados dentro de la jerarquía y de la presencia de puentes/puntos de articulación**. 

Así que esa pregunta concreta está **completamente cubierta**. Si quieres, puedo incluso reforzar esa sección con un pequeño párrafo más “académico” para que quede todavía más evidente al profesor.
