# Fase 1 — Caracterización estructural de la red UCuenca

## 1. Verificación de los datos

Antes de realizar el análisis se verificó que la red cargada coincidiera con los valores de referencia proporcionados en el proyecto. La red contiene **177 nodos**, **209 aristas** y forma **una única componente conexa**, con una densidad aproximada de **0.0134**. Por lo tanto, el conjunto de datos fue cargado correctamente y puede utilizarse para los análisis posteriores.

## 2. Medidas estructurales básicas

| Métrica | Resultado |
|---|---:|
| Número de nodos | 177 |
| Número de aristas | 209 |
| Componentes conexas | 1 |
| Densidad | 0.013418 |
| Grado medio | 2.362 |
| Grado mínimo | 1 |
| Grado máximo | 17 |
| Coeficiente de clustering medio | 0.03433 |
| Diámetro | 11 |
| Distancia media entre pares | 5.830 |
| Asortatividad por grado | -0.1468 |
| Puntos de articulación | 47 |
| Puentes | 141 |

La **baja densidad** y el **grado medio reducido** muestran que la red es relativamente dispersa, algo coherente con una infraestructura jerárquica donde los equipos de acceso se conectan a un número limitado de dispositivos de agregación o núcleo.

El **coeficiente de clustering medio de 0.03433** también es bajo. A diferencia de una red social, donde es común que los vecinos de un nodo también estén conectados entre sí, una red de datos jerárquica normalmente evita conexiones innecesarias entre equipos del mismo nivel.

La **asortatividad negativa (-0.1468)** indica una tendencia de los nodos de alto grado a conectarse con nodos de menor grado. Esto es consistente con una estructura del tipo **core–agregación–acceso**.

## 2.1 ¿Tiene sentido hablar de "red libre de escala"?

El enunciado pide explícitamente no afirmar que la red es libre de escala solo por observar una cola en el histograma, sino aplicar una prueba estadística. Se implementó el método de **Clauset, Shalizi & Newman (2009)** — estimación de máxima verosimilitud (MLE) discreta del exponente α, selección de x_min minimizando la distancia de Kolmogorov–Smirnov (KS), y una prueba de bondad de ajuste por **bootstrap semi-paramétrico** (1000 réplicas), comparando además contra una distribución geométrica (exponencial discreta) mediante AIC. Se implementó desde cero con `numpy`/`scipy` para no añadir dependencias nuevas al proyecto (script `scripts/01_p1_caracterizacion.py`, tabla `resultados/tablas/11_prueba_ley_potencia.csv`).

| Cantidad | Resultado |
|---|---:|
| x_min óptimo | 4 |
| α (MLE) | 2.737 |
| Nodos en la cola (grado ≥ x_min) | 36 de 177 |
| Grado máximo | 17 |
| Décadas de grado cubiertas (log10(k_max/x_min)) | 0.63 |
| Distancia KS observada | 0.167 |
| p-valor bootstrap (bondad de ajuste) | 0.354 |
| AIC ley de potencia vs. exponencial | 164.8 vs. **158.6** (exponencial gana) |

**Conclusión: no hay evidencia suficiente para afirmar que la red UCuenca es "libre de escala".** El exponente ajustado (α ≈ 2.74) cae dentro del rango típico reportado para redes libres de escala (2 < α < 3), y el p-valor de bondad de ajuste (0.354 > 0.1) no permite *rechazar* la hipótesis de ley de potencia por sí sola. Sin embargo, dos evidencias adicionales pesan en contra de la afirmación:

1. **El rango de grados es demasiado angosto**: el ajuste solo cubre 0.63 décadas (de grado 4 a 17). Clauset et al. recomiendan al menos 2 décadas de rango para que una ley de potencia sea distinguible de otras distribuciones de cola pesada; aquí no se alcanza ni una década completa, y la cola de ajuste tiene apenas 36 nodos.
2. **El criterio de información (AIC) prefiere la alternativa exponencial/geométrica** sobre la ley de potencia para estos mismos datos, es decir, un decaimiento exponencial explica la cola tan bien o mejor que un decaimiento en ley de potencia.

En una red de 177 nodos con grado máximo 17, cualquier ajuste de ley de potencia tiene muy pocos grados de libertad: es fácil que *parezca* lineal en escala log-log a simple vista (como en la Figura 2) sin que eso constituya evidencia estadística real. La lectura correcta es que la red **tiene una cola de grado más pesada que una Erdős–Rényi comparable** (ver contraste con modelos nulos en P2), coherente con la existencia de unos pocos equipos de *core*/agregación con grado alto, pero el tamaño de la muestra es insuficiente para clasificarla formalmente como libre de escala frente a alternativas como la exponencial.

## 3. Centralidad de los nodos

Se calcularon las centralidades de grado, intermediación, cercanía y vector propio. La centralidad de intermediación es especialmente útil para identificar equipos que participan frecuentemente en los caminos más cortos entre otros nodos.

| Posición | Nodo | Campus / función | Intermediación |
|---:|---|---|---:|
| 1 | DATCC-2A-C3 | Campus Central / core | 0.4468 |
| 2 | CPAR-C10 | Campus Paraíso / core | 0.4043 |
| 3 | ROUTER-CAMPUS-HUAYNA-CAPAC | Campus Paraíso / WAN | 0.3663 |
| 4 | INTERNET-MPLS | Nube MPLS / WAN | 0.3657 |
| 5 | PE2-CENTRAL | Campus Central / WAN | 0.2881 |
| 6 | DT-0A-C13 | Campus Balzay / core | 0.2235 |
| 7 | FORTIGATE-1800F-CENTRAL | Campus Central / interconexión | 0.1863 |
| 8 | DATCC-2A-C2 | Campus Central / core | 0.1706 |
| 9 | FORTIGATE-1800F-BALZAY | Campus Balzay / interconexión | 0.1490 |
| 10 | PE2-BALZAY | Campus Balzay / WAN | 0.1460 |

El nodo **DATCC-2A-C3** presenta la mayor intermediación de toda la red. Esto significa que una proporción importante de los caminos más cortos entre equipos atraviesa este dispositivo, por lo que constituye un candidato importante para posteriores análisis de criticidad.

También se observa que varios equipos de **core, WAN e interconexión** aparecen entre los primeros lugares. Esto muestra que la importancia estructural de un nodo no depende únicamente de su número de conexiones, sino también de su posición dentro de la red.

## 4. Puntos de articulación y puentes

Se identificaron **47 puntos de articulación** y **141 puentes**.

Un punto de articulación es un nodo cuya eliminación incrementa el número de componentes conexas de la red. De forma análoga, un puente es una arista cuya eliminación desconecta alguna parte del grafo.

La presencia de **141 puentes sobre un total de 209 enlaces** indica que una parte considerable de la infraestructura representada no dispone de un camino alternativo en el modelo. Esto es especialmente relevante para las siguientes fases, ya que permite localizar posibles puntos únicos de fallo.

Estos resultados deben interpretarse teniendo en cuenta la forma en que fue construido el grafo. Algunos mecanismos de redundancia física, como enlaces agrupados o redundancias internas, pueden quedar representados mediante una sola arista en un grafo simple.

## 5. Interpretación preliminar

Los resultados muestran que la red UCuenca posee una estructura claramente jerárquica y poco densa. Los valores bajos de clustering y la asortatividad negativa son consistentes con una arquitectura donde los nodos de acceso dependen de equipos de agregación y núcleo.

Por otra parte, la gran cantidad de puentes y puntos de articulación sugiere que existen sectores de la red con poca redundancia topológica. Los nodos con alta intermediación, especialmente aquellos pertenecientes a las capas de core, WAN e interconexión, serán candidatos importantes para analizar en las fases posteriores de flujo máximo, percolación, fallos en cascada y diagnóstico de puntos críticos.

En consecuencia, esta primera caracterización sirve como base para identificar posteriormente **qué equipos y enlaces representan los principales puntos de vulnerabilidad de la infraestructura**.


Sí. Estas tres preguntas son precisamente las que convierten P1 de una tabla de métricas en un **análisis de ingeniería**; el enunciado incluso advierte que no responderlas limita fuertemente la calificación de P1. 

Con los resultados que obtuvimos de la red real, podemos responderlas bastante bien.

## 1. ¿Por qué el clustering medio es tan bajo comparado con una red social?

Obtuvimos:

[
\bar C = 0.0343
]

Es decir, el clustering medio es aproximadamente **3.4 %**, un valor bajo.

Esto tiene sentido porque la red UCuenca es una **red tecnológica jerárquica**, no una red social. En una red social existe un fenómeno muy común: si A conoce a B y A conoce a C, es bastante probable que B y C también se conozcan. Eso produce muchos **triángulos** y, por tanto, clustering elevado.

En la red UCuenca ocurre algo diferente. Un equipo de acceso normalmente se conecta hacia un equipo de agregación, y este a su vez hacia el core:

```text
      CORE
       │
  AGREGACIÓN
   /   |   \
 A1   A2   A3
```

No existe una razón funcional para que `A1`, `A2` y `A3` estén conectados entre sí:

```text
 A1 ─── A2
  \     /
    A3
```

Hacerlo incrementaría enlaces, puertos, complejidad y costo sin aportar necesariamente una ventaja operacional.

Por eso la arquitectura **core → agregación → acceso favorece estructuras tipo árbol o estrella**, que tienen pocos triángulos.

Además, que el clustering sea bajo **no significa automáticamente que la red esté mal diseñada o no tenga redundancia**. La redundancia puede concentrarse en determinadas zonas críticas mediante enlaces alternativos, equipos duplicados o enlaces físicos agrupados, sin necesidad de formar triángulos en toda la red.

### Redacción para el informe

> El coeficiente de clustering medio obtenido fue de **0.0343**, lo que indica una baja presencia de conexiones entre vecinos de un mismo nodo. Este comportamiento es esperable en una red de infraestructura jerárquica. A diferencia de una red social, donde la formación de triángulos es frecuente debido a que los contactos de una persona suelen relacionarse entre sí, en una red de datos los dispositivos de acceso tienden a conectarse verticalmente hacia equipos de agregación y estos hacia el núcleo, sin requerir conexiones laterales entre todos los dispositivos del mismo nivel. Por tanto, la baja agrupación observada es coherente con la arquitectura core–agregación–acceso y no debe interpretarse por sí sola como falta de redundancia.

---

# 2. ¿Por qué la asortatividad es negativa y qué dice sobre la jerarquía?

Nuestro resultado fue:

[
r=-0.1468
]

La asortatividad por grado pregunta, básicamente:

> ¿Los nodos con muchas conexiones tienden a conectarse con otros nodos que también tienen muchas conexiones?

Si la respuesta fuera sí:

[
r>0
]

Si los nodos muy conectados tienden a conectarse con nodos poco conectados:

[
r<0
]

Y justamente eso ocurre aquí.

Tenemos equipos centrales con grados relativamente altos, por ejemplo:

| Nodo                   | Capa       |  Grado |
| ---------------------- | ---------- | -----: |
| `DATCC-2A-C3`          | core       | **17** |
| `DATCC-2A-C2`          | core       | **16** |
| `AGRPRI-1A-D10`        | agregación | **12** |
| `BAL-AUL2-D1`          | agregación | **12** |
| `CC-ARQUITECTURA-D107` | agregación | **10** |

Estos dispositivos concentran conexiones hacia muchos equipos más periféricos, que normalmente tienen pocos enlaces.

Es decir, aparece repetidamente algo como:

```text
           acceso (grado bajo)
                  │
acceso ─── AGREGACIÓN ─── acceso
                  │
           acceso (grado bajo)
```

o:

```text
          agregación
              │
agregación ─ CORE ─ agregación
              │
          agregación
```

Por tanto, **nodos de alto grado se conectan frecuentemente con nodos de menor grado**, produciendo asortatividad negativa.

Esto es precisamente lo que esperaríamos de una red jerárquica.

No significa que `-0.1468` sea una disasortatividad extrema; es una **tendencia negativa moderada**. Pero su signo y magnitud son coherentes con la organización funcional de la infraestructura.

### Redacción para el informe

> La asortatividad por grado obtenida fue de **−0.1468**, indicando una tendencia disasortativa: los nodos con mayor grado tienden a conectarse con nodos de grado inferior. Este comportamiento es consistente con la arquitectura jerárquica de la red. Los equipos de core y agregación concentran múltiples conexiones provenientes de equipos periféricos o de acceso, mientras que estos últimos poseen normalmente pocos enlaces. En consecuencia, la asortatividad negativa constituye evidencia estructural de la jerarquía **core–agregación–acceso**, en lugar de una organización donde los nodos altamente conectados se enlacen principalmente entre ellos.

---

# 3. ¿Coinciden grado e intermediación?

Aquí la respuesta interesante es:

**coinciden parcialmente, pero no completamente.**

De los **10 nodos con mayor grado** y los **10 con mayor intermediación**, solamente **5 aparecen en ambas listas**:

* `DATCC-2A-C3`
* `DATCC-2A-C2`
* `CPAR-C10`
* `DT-0A-C13`
* `INTERNET-MPLS`

Eso ya nos da una respuesta cuantitativa clara.

Mira algunos casos especialmente reveladores:

| Nodo                         |  Grado | Intermediación | Lectura                                                   |
| ---------------------------- | -----: | -------------: | --------------------------------------------------------- |
| `DATCC-2A-C3`                | **17** |     **0.4468** | alto en ambas                                             |
| `DATCC-2A-C2`                | **16** |         0.1706 | muchas conexiones locales                                 |
| `AGRPRI-1A-D10`              | **12** |         0.1214 | alto grado, menor papel global                            |
| `BAL-AUL2-D1`                | **12** |         0.1107 | alto grado, menor papel global                            |
| `CPAR-C10`                   |      7 |     **0.4043** | pocas conexiones comparativamente, pero posición crítica  |
| `ROUTER-CAMPUS-HUAYNA-CAPAC` |  **3** |     **0.3663** | caso extremo: muy pocas conexiones, enorme intermediación |
| `INTERNET-MPLS`              |      8 |     **0.3657** | conector entre regiones de la red                         |

El caso de `ROUTER-CAMPUS-HUAYNA-CAPAC` es especialmente bueno para explicar la diferencia.

Tiene solamente:

[
k=3
]

pero es el **tercer nodo con mayor intermediación de toda la red**:

[
C_B \approx 0.3663
]

¿Cómo puede ocurrir?

Porque el grado mide una propiedad **local**:

> ¿Con cuántos vecinos está conectado directamente este nodo?

Mientras que la intermediación mide una propiedad mucho más **global**:

> ¿Cuántos caminos entre otros nodos necesitan atravesarlo?

Imagina:

```text
████████ Campus A
       \
        X ───── Y
               /
████████ Campus B
```

`X` podría tener solamente dos o tres vecinos.

Pero si es la única puerta entre dos regiones grandes, prácticamente toda comunicación entre ambas pasa por él.

Por eso tendría:

* grado bajo;
* betweenness altísimo.

---

## Los nodos de alto grado tienen un papel de concentración

Por ejemplo:

```text
            A
            |
       B ─ SWITCH ─ C
           / | \
          D  E  F
```

El switch tiene muchos vecinos directos.

Su importancia está asociada a **agregar o distribuir conexiones locales**.

Por eso encontramos entre los primeros por grado varios dispositivos de agregación:

* `AGRPRI-1A-D10`
* `BAL-AUL2-D1`
* `CC-ARQUITECTURA-D107`
* `CP-EADMINA1-D6`
* `CC-MONJAS-D126`

---

## Los nodos de alta intermediación tienen un papel de tránsito

En cambio, entre los primeros por betweenness aparecen:

* routers WAN;
* `INTERNET-MPLS`;
* firewalls;
* equipos core;
* nodos de interconexión.

Por ejemplo:

```text
Campus A ── Router ── MPLS ── Router ── Campus B
```

Estos dispositivos pueden no atender directamente a muchos equipos.

Pero están situados en **corredores obligatorios entre regiones completas de la infraestructura**.

Eso explica por qué aparecen:

`ROUTER-CAMPUS-HUAYNA-CAPAC`

`PE2-CENTRAL`

`FORTIGATE-1800F-CENTRAL`

`FORTIGATE-1800F-BALZAY`

`PE2-BALZAY`

entre los primeros por intermediación aunque no estén entre los nodos de mayor grado.

---

# Esta es probablemente la mejor respuesta para colocar directamente en P1

> **Comparación entre centralidad de grado e intermediación.** Los nodos más centrales según ambas medidas coinciden solo parcialmente. De los diez primeros nodos de cada ranking, cinco aparecen en ambos: `DATCC-2A-C3`, `DATCC-2A-C2`, `CPAR-C10`, `DT-0A-C13` e `INTERNET-MPLS`. Esta diferencia se debe a que ambas métricas representan funciones distintas dentro de la infraestructura. La centralidad de grado mide la conectividad local del equipo, por lo que favorece principalmente a dispositivos core o de agregación que concentran numerosos enlaces directos. En cambio, la centralidad de intermediación mide la participación del nodo en los caminos que conectan diferentes regiones de la red, por lo que destaca routers WAN, firewalls y equipos de interconexión.
>
> Un ejemplo representativo es `ROUTER-CAMPUS-HUAYNA-CAPAC`, que posee únicamente **grado 3**, pero alcanza una intermediación de aproximadamente **0.3663**, situándose como el tercer nodo de mayor intermediación. Esto indica que, aunque dispone de pocas conexiones directas, ocupa una posición estratégica para comunicar partes importantes de la infraestructura. En contraste, nodos como `AGRPRI-1A-D10` o `BAL-AUL2-D1` poseen grado 12 pero una intermediación considerablemente menor, reflejando principalmente una función de concentración local.
>
> Por tanto, **un nodo con muchas conexiones no es necesariamente el nodo más crítico para mantener comunicada la red**. Los nodos de alto grado representan principalmente puntos de concentración de dispositivos, mientras que los de alta intermediación representan corredores o puertas de enlace cuya falla puede afectar la comunicación entre regiones completas.

## En conjunto, las tres métricas cuentan una historia coherente

Podemos resumir P1 de esta manera:

**Clustering bajo →** la red no está organizada para formar grupos densamente interconectados, sino jerárquicamente.

**Asortatividad negativa →** los nodos centrales con muchas conexiones alimentan a numerosos nodos periféricos con pocas conexiones.

**Grado ≠ intermediación →** existen dos tipos diferentes de importancia: **concentradores locales** y **conectores globales**.

Y esa última diferencia es particularmente importante para el resto del proyecto: cuando lleguemos a **percolación y fallos dirigidos**, probablemente eliminar un nodo con intermediación alta pero grado moderado resulte mucho más dañino que eliminar simplemente uno de los nodos con más vecinos. Esa es justamente una de las hipótesis que P8–P10 nos permitirán comprobar.
