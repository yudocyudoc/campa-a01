# A10 · Resultados del analista observacional con evaluación sellada

**Referencia ejecutada:** [GitHub Actions 38126170978](https://github.com/yudocyudoc/campa-a01/actions/runs/38126170978) (4 jobs: productor, analista en checkout restringido, adjudicador y pruebas).  
**Condiciones de observación:** sin ruido y con ruido gaussiano SD=1% de capacidad nominal solo en `effective_capacity`, acotado a límites físicos; semilla `20261011`.  
**Diseño:** W016, cinco escenarios de entrenamiento, 17 de evaluación, 25 meses por escenario; la capacidad efectiva posterior a t0 de holdout **no** estuvo disponible al analista.  
**Evidencia permanente:** [`evidence/`](evidence/) (12 archivos originales) y [`evidence_manifest.json`](evidence_manifest.json), SHA-256 verificado a partir de los cuatro artefactos de la corrida exitosa. El workflow temporal de archivado fue retirado.  
**Estado:** `COMPLETED` en el pipeline y en la adjudicación. Los resultados negativos o abstenciones estaban permitidos, no se forzó una decisión.

## Resultados: ajuste TRAIN frente a holdouts sellados

| Métrica RMS sobre fracción `effective_capacity/K` | Sin ruido | Ruido 1% |
|---|---:|---:|
| TRAIN: `D−cK` | 0.015829141 | 0.017080218 |
| TRAIN: `D/K^p` | 6.371e-13 | 0.009417241 |
| Margen TRAIN (diferencia) | 0.015829141 | 0.007662977 |
| Decisión desde TRAIN, umbral heurístico 0.005 | **`ratio_p`** | **`ratio_p`** |
| HOLDOUT: `D−cK` | 0.018939548 | 0.020498413 |
| HOLDOUT: `D/K^p` | 4.626e-13 | 0.008622531 |
| HOLDOUT: referencia capacidad nominal constante | 0.339685365 | 0.337699118 |

La familia `ratio_p` contiene por construcción al generador (p=1). La elección correcta en este mundo **no demuestra** descubrimiento causal general ni victoria frente a una biblioteca de alternativas desconocidas. La línea base de capacidad nominal constante es deliberadamente simple; no implica superioridad frente a estrategias de pronóstico empresarial competentes.

### Parámetros recuperados desde observaciones (sin verdad del WORLD como entrada)

| Parámetro `ratio_p` | Sin ruido | Ruido 1% |
|---|---:|---:|
| Umbral efectivo `tau` | 0.80436576448 | 0.80948583783 |
| Tasa `a` | 0.63411718542 | 0.63401309946 |
| Ganancia `g` | 1.75824996508 | 1.76265629507 |
| Exponente `p` | 0.9999999999998 | 0.99922331678 |

El analista optimizó los parámetros con TRAIN usando exclusivamente capacidad efectiva **observable** y entrada `incoming_orders`/capacidad nominal, sin `hidden_excess`, `primitive_impact` ni stocks latentes del WORLD.

El método conoce la dinámica de primer orden y los dos tipos de driver **antes** de leer los datos: por tanto, la recuperación de p≈1 es una verificación de inferencia dentro de una familia anidada, no descubrimiento de una estructura previamente desconocida.

### Regiones potencialmente informativas sin etiquetas latentes

La regla heurística identifica instantes donde las **predicciones de las dos hipótesis** difieren en más de 0.005 de fracción de capacidad y no quedan ambas saturadas. Se calcula sin los resultados holdout.

| Resumen de los 17 holdouts | Sin ruido | Ruido 1% |
|---|---:|---:|
| Instantes post-t8 con diferencia candidata potencialmente informativa | **90** | **89** |
| Escenarios con alguna diferencia candidata >0.005 | **10/17** | **10/17** |
| Escenarios con ambos candidatos inactivos durante 17/17 meses de evaluación | **7/17** | **7/17** |

Los siete escenarios predichos como inactivos coinciden con la pauta del diagnóstico oracle-only A09. **Esto no es validación independiente de un detector general**: W016 es conocido públicamente en el proyecto y la clasificación compara exclusivamente dos candidatos elegidos de antemano.

## Disciplina de separación de datos

El pipeline implementa tres espacios operativos:

1. Productor: genera G5 W016 original; transfiere TRAIN observable completo y HOLDOUT con pedidos/capacidad nominal y capacidad efectiva inicial t0. Las etiquetas futuras se guardan aparte.
2. Analista: GitHub job con **sparse checkout solo de `contract.py` y `analyst.py`**, sin `g5_extended_core.py` ni archivos de evidencia de A09 en su árbol de trabajo. No recibe el artefacto de etiquetas selladas y escribe predicciones/decisión antes de la adjudicación.
3. Adjudicador: recibe posteriormente etiquetas y pronósticos; verifica hashes y que estén presentes **todos los 17 escenarios** de cada condición, sin recalibrar modelos.

El generador está publicado en el propio repositorio: **no existe cegamiento epistemológico independiente** ante un investigador que haya leído el mundo W016. La barrera sirve para detectar accesos indebidos en la implementación.

## Límite fundamental: observación no equivale a intervención

El modelo predice capacidad efectiva **condicionada a pedidos y capacidad nominal ya observados durante los holdouts**. Como pedidos son **endógenos** al backlog, churn y base de clientes, esta evaluación no demuestra capacidad de anticipar el efecto contrafactual de cambiar la capacidad de una empresa.

Tampoco usa las series de cancelaciones, clientes, backlog y caja como predictores en el estimador final, aunque las exporta en TRAIN como información observable. El modelo reducido se concentra en `effective_capacity`, pedido y capacidad nominal.

El ruido se agregó únicamente a mediciones de capacidad efectiva, en **una sola realización** con semilla fija; no hay intervalos de confianza, potencia estadística, replicación bajo otros mundos ni ruido correlacionado en las entradas.

**Siguiente pregunta de investigación**, separada de A10: diseñar una evaluación prospectiva en la que el analista proponga o seleccione intervenciones sin usar pedidos futuros derivados del WORLD, para comprobar si su ventaja se mantiene cuando no conoce anticipadamente el campo endógeno que generará la decisión.
