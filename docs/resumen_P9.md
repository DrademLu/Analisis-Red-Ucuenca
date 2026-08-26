# P9 — Propagación de fallos en cascada y epidemias

## 1. Modelo de fallos en cascada

Se utilizó como carga inicial de cada nodo su **centralidad de intermediación normalizada** en la red intacta:

\[
L_i = C_B(i)
\]

La capacidad de cada nodo se define como:

\[
C_i=(1+\tau)L_i
\]

Después de retirar el nodo disparador se recalcula la intermediación sobre la topología superviviente. Esta nueva intermediación representa, de forma simplificada, la **redistribución de carga por los nuevos caminos más cortos**. Todo nodo cuya carga recalculada supera su capacidad falla en la siguiente generación y el proceso se repite hasta que no aparecen nuevas sobrecargas.

Este es un modelo topológico de carga-capacidad: la intermediación funciona como **proxy de tráfico**, no como una medición real de Mbps. Se usa la versión normalizada porque es la misma magnitud empleada en P1.

### Limitación importante

Los nodos cuya intermediación inicial es cero tienen también capacidad inicial cero bajo la definición estricta `C_i=(1+τ)L_i`. Si después de una falla pasan a participar en caminos mínimos, cualquier carga positiva puede declararlos sobrecargados. Esto hace al modelo **conservador** y explica que con `τ=0` algunos nodos periféricos puedan disparar cascadas grandes. Una extensión posterior podría añadir una carga/capacidad mínima basal, pero no se hizo aquí para mantener la formulación pedida.

## 2. Margen crítico τc

Se evaluaron todos los **177 nodos** como posibles disparadores. El barrido global permitió acotar la transición entre `τ=0.035` y `τ=0.040`, y luego se refinó numéricamente el disparador que todavía producía una cascada superior al 20%.

| τ | Disparador con mayor daño | Fallos | Fracción afectada |
|---:|---|---:|---:|
| 0.000 | `CCJ-CJURIDICO-D4` | 62 | 35.0% |
| 0.035 | `ROUTER-CAMPUS-CENTRO-HISTORICO` | 38 | 21.5% |
| 0.040 | `DATCC-2A-C3` | 13 | 7.3% |

El margen crítico obtenido fue aproximadamente:

\[
\boxed{\tau_c \approx 0.0350}
\]

es decir, alrededor de **3.5% de tolerancia adicional** sobre la carga inicial. Justo por debajo de ese valor, la falla de `ROUTER-CAMPUS-CENTRO-HISTORICO` todavía provoca una cascada superior al 20% de la red; por encima, la cascada cae por debajo de ese criterio.

El disparador crítico cerca de `τc` es:

`ROUTER-CAMPUS-CENTRO-HISTORICO` — Sede Centro Histórico, capa WAN.

A `τ=0.035` provoca **38 fallos**, equivalentes al **21.5% de la red**. La cascada ocurre en cuatro generaciones con tamaños aproximados:

- generación 0: 1 nodo;
- generación 1: 2 nodos;
- generación 2: 3 nodos;
- generación 3: 32 nodos.

La secuencia empieza con el router de Centro Histórico, después afecta infraestructura de Museo y posteriormente alcanza firewalls, enlaces WAN/core y finalmente un conjunto amplio de equipos de agregación y acceso. Esto evidencia que una falla inicialmente localizada puede desplazar suficiente carga hacia otras rutas como para superar sus márgenes.

## 3. Disparadores más peligrosos

Con `τ=0`, los mayores daños observados son:

| # | Nodo disparador | Campus | Capa | Fallos | Red afectada |
|---:|---|---|---|---:|---:|
| 1 | `CCJ-CJURIDICO-D4` | Campus Central | agregacion | 62 | 35.0% |
| 2 | `HOS-0A-D05` | Campus Hospitalidad | agregacion | 61 | 34.5% |
| 3 | `ODO-0B-A52` | Campus Paraiso | acceso | 61 | 34.5% |
| 4 | `PE1-BALZAY` | Campus Balzay | wan | 61 | 34.5% |
| 5 | `POS-2C-A33` | Campus Paraiso | acceso | 61 | 34.5% |
| 6 | `CCJ-1A-A10` | Campus Central | acceso | 60 | 33.9% |
| 7 | `CCJ-1A-A11` | Campus Central | acceso | 60 | 33.9% |
| 8 | `ENF-2B-A22` | Campus Paraiso | acceso | 60 | 33.9% |
| 9 | `FORTIGATE-1800F-BALZAY` | Campus Balzay | interconexion | 60 | 33.9% |
| 10 | `HOS-0A-A10` | Campus Hospitalidad | acceso | 60 | 33.9% |

El máximo corresponde a `CCJ-CJURIDICO-D4`, cuya falla desencadena **62 fallos (35.0%)** en este modelo sin margen de tolerancia.

Sin embargo, cerca del margen crítico el comportamiento cambia radicalmente. A `τ=0.035`, `ROUTER-CAMPUS-CENTRO-HISTORICO` es el único disparador que todavía supera el 20%; el siguiente grupo de nodos genera cascadas de aproximadamente 13 fallos o menos. Esto muestra que el ranking de disparadores depende del margen operativo considerado.

## 4. Modelo SIR

Se utilizó un modelo **SIR continuo tipo Gillespie**. Cada enlace susceptible–infectado transmite con tasa `β` y cada nodo infectado se recupera con tasa `μ=1`. Se define:

\[
\lambda=\frac{\beta}{\mu}
\]

Para cada valor de `λ` se ejecutaron **500 realizaciones**, comenzando desde un nodo infectado elegido aleatoriamente. Como criterio operacional para una red finita, se consideró “brote grande” aquel que termina afectando a más del **20%** de los equipos.

La predicción de campo medio pedida por el enunciado es:

\[
\lambda_c^{MF} \approx \frac{\langle k\rangle}{\langle k^2\rangle}
\]

Con:

\[
\langle k\rangle=2.3616, \qquad
\langle k^2\rangle=12.6893
\]

se obtiene:

\[
\boxed{\lambda_c^{MF} \approx 0.186}
\]

En la simulación se definió como **umbral empírico operacional** la primera `λ` para la cual al menos el 10% de las realizaciones produce un brote final superior al 20% de la red. Con ese criterio:

\[
\boxed{\lambda_c^{emp} \approx 0.75}
\]

El valor empírico es bastante mayor que la aproximación de campo medio. Esto no debe interpretarse como que la fórmula esté “mal”: la expresión de campo medio supone una red grande y suficientemente mezclada, mientras UCuenca es pequeña, jerárquica, modular y contiene numerosos puentes y ramas terminales. Además, el umbral empírico usado aquí es un criterio operacional de severidad para una red finita, no exactamente el mismo objeto límite de la teoría.

El indicador de susceptibilidad finita alcanza su máximo en torno a `λ≈1.40`, lo que confirma que la transición es ancha y no aparece como un punto crítico perfectamente definido.

## 5. Inmunización: aleatoria vs centralidad

Se compararon dos estrategias con el mismo presupuesto:

\[
m=10 	ext{ equipos}
\]

La inmunización por centralidad parchea los diez nodos de mayor intermediación de P1, entre ellos `DATCC-2A-C3`, `CPAR-C10`, `ROUTER-CAMPUS-HUAYNA-CAPAC`, `INTERNET-MPLS`, `PE2-CENTRAL` y los principales nodos core/WAN.

La comparación se realizó con `λ=1.0` y **1000 simulaciones por estrategia**:

| Estrategia | m | Brote final medio | P(brote >20%) | Reducción media vs base |
|---|---:|---:|---:|---:|
| ninguna | 0 | 10.13% | 22.3% | 0.0% |
| aleatoria | 10 | 8.03% | 17.4% | 20.8% |
| centralidad | 10 | 1.82% | 0.0% | 82.1% |

Con inmunización aleatoria, el tamaño medio del brote disminuye aproximadamente **20.8%** respecto a no inmunizar. En cambio, inmunizar los diez nodos de mayor intermediación reduce el brote medio alrededor de **82.1%** y, en estas 1000 realizaciones, ningún brote superó el 20% de la red.

La razón es estructural: los nodos de alta intermediación conectan regiones enteras de la infraestructura. Parchearlos no solo protege diez equipos, sino que rompe múltiples rutas potenciales de propagación entre comunidades y campus.

## 6. Analogía con un sistema eléctrico de potencia

El modelo tiene una analogía directa, aunque simplificada, con una red de transmisión eléctrica:

- **Carga `L_i`:** en la red de datos representa tránsito topológico aproximado mediante intermediación; en una red eléctrica correspondería al flujo o esfuerzo soportado por un elemento de transmisión.
- **Capacidad `C_i`:** en datos representa el margen de tolerancia antes de considerar el nodo sobrecargado; en potencia corresponde a límites térmicos, operativos o de estabilidad de líneas, transformadores y otros elementos.
- **Redistribución:** cuando se pierde un nodo o enlace, el tráfico busca caminos alternativos; en una red eléctrica, la salida de un elemento redistribuye los flujos por la red restante de acuerdo con las leyes eléctricas.
- **Cascada:** si los nuevos flujos superan límites de otros elementos, las protecciones pueden desconectarlos, produciendo nuevas redistribuciones y una posible falla en cascada.

La analogía tiene una limitación fundamental: **los flujos eléctricos reales no siguen caminos mínimos**. Deben satisfacerse las leyes de Kirchhoff y, en estudios reales, modelos de flujo de potencia DC o AC. Por tanto, el modelo de P9 captura el mecanismo conceptual de sobrecarga–redistribución–nueva falla, pero no sustituye un análisis eléctrico.

Como referencia de la **bibliografía del módulo**, Newman (2010) presenta el marco general de procesos dinámicos sobre redes y propagación en sistemas complejos; Latora, Nicosia y Russo (2017) desarrollan también robustez, difusión y dinámica sobre redes complejas.

## 7. Conclusiones

P9 evidencia dos formas distintas de propagación de riesgo. En el modelo de cascada, un margen de tolerancia de apenas unos puntos porcentuales separa escenarios con fallas contenidas de uno en el que un único disparador WAN puede afectar más del 20% de la infraestructura. En el modelo SIR, la topología jerárquica dificulta la propagación respecto a la predicción homogénea de campo medio, pero una vez superada la región de transición aparecen brotes extensos.

La conclusión operacional más fuerte proviene de la inmunización: **parchear según centralidad es muy superior a parchear al azar con el mismo presupuesto**. Esto refuerza los resultados de P1 y P8: la red concentra conectividad y tránsito en un conjunto relativamente pequeño de nodos core, WAN e interconexión, por lo que proteger esos elementos produce un beneficio desproporcionado.

## Referencias del módulo

- Newman, M. E. J. (2010). *Networks: An Introduction*. Oxford University Press.
- Latora, V., Nicosia, V., & Russo, G. (2017). *Complex Networks: Principles, Methods and Applications*. Cambridge University Press.
