# A12 · Resultado: gate negativo de valor decisional incremental

**Ejecución completa:** [GitHub Actions 38186398116](https://github.com/yudocyudoc/campa-a01/actions/runs/38186398116).  
**Decisión del gate:** `NO_MATERIAL_DECISION_DISAGREEMENT`. **WORLD no fue ejecutado**: el job de adjudicación quedó `skipped` por el requisito material.  
**Fuente:** parámetros y estado PREDECISIÓN congelados de A11; mismas ecuaciones contables conocidas y validadas contra las trayectorias A11 originalmente predichas. **No se volvió a optimizar ningún candidato.**  
**Evidencia permanente:** [`evidence/`](evidence/) (18 escenarios y 1,260 valoraciones de políticas) y [`evidence_manifest.json`](evidence_manifest.json), con SHA-256 verificados.

## Conclusión

La rejilla de A12 contiene casos donde las dos familias recomiendan capacidades diferentes, pero **ninguno** tiene un desacuerdo material conforme al umbral simétrico predefinido.

| Indicador | Sin ruido | Ruido de 1% |
|---|---:|---:|
| Shocks de la rejilla | 9 | 9 |
| Shocks con distinta recomendación de K | **4** | **4** |
| Shocks donde ambos arrepentimientos relativos alcanzan 5% | **0** | **0** |
| Shocks que califican en ambos brazos | \- | **0/9** |
| Mínimo exigido para WORLD | \- | **3/9** |

En los cuatro shocks de desacuerdo las capacidades preferidas difieren solamente **5 unidades**. El máximo valor robusto, tomando el **mínimo de ambos arrepentimientos de ambas condiciones** para el mismo shock, ocurre en **shock 70: 1.217946% del rango de caja**. Queda por debajo del 5%.

Esto es evidencia **negativa acotada**: la identificación del driver correcto no muestra aquí una ventaja de decisión suficientemente grande para pasar a otra intervención G5 bajo **la función objetivo, rejilla y criterio elegidos**. No demuestra que identificar mecanismos carezca de utilidad fuera de este escenario.

## Las divergencias reales de la biblioteca

Los números son pérdidas **predichas por cada modelo** si adoptase la decisión preferida por el rival, nunca resultados del WORLD.

| Shock | Mejor K de `ratio_p` | Mejor K de `diff_c` | Pérdida bajo `ratio_p` al seguir `diff_c` | Pérdida bajo `diff_c` al seguir `ratio_p` | Puntaje robusto entre brazos |
|---|---:|---:|---:|---:|---:|
| 30 | 150 | 145 | 337 | 158 | 0.342% |
| **70** | **195** | **190** | **938** | **808** | **1.218%** |
| 80 | 205 | 200 | 2,205 | 403 | 0.591% |
| 100 | 230 | 225 | 312 | 943 | 0.208% |

Las pérdidas monetarias de la tabla corresponden al **brazo sin ruido**; la columna de puntaje robusto aplica el menor resultado de ambos brazos.

Especialmente en shock 80, el efecto es asimétrico:

- `ratio_p` estima que equivocarse le costaría **2,205 / 67,813 = 3.25%** del rango.
- `diff_c` estima que equivocarse le costaría **403 / 68,149 = 0.59%**.

Ese es justamente el problema que resuelve el criterio bilateral: una diferencia de acción no equivale a que *ambos* mecanismos consideren costosa la decisión contraria.

El máximo unilateral de 3.25% también queda por debajo del umbral de 5% del gate, pero aun sin ese dato la prueba simétrica sería negativa.

## Comparación con tres decisiones ingenuas

A12 contrastó las dos políticas de cada modelo con tres referencias sin consultar resultados futuros del WORLD:

1. **No cambiar:** K115.
2. **Capacidad máxima:** K260.
3. **Aproximación al pico de demanda no congestionada:** cálculo con base inicial de clientes, adquisición y churn básico, ignorando pérdidas por backlog; K175 para shock70 y K185 para shock80.

Ejemplo, pérdidas de caja **previstas por `ratio_p`** respecto del mejor K de esa familia:

| Shock | No cambiar K115 | Máxima K260 | Pico ingenuo | Seguir la elección de `diff_c` |
|---|---:|---:|---:|---:|
| 70 | 56,715 | 10,557 | 16,367 | **938** |
| 80 | 61,082 | 8,923 | 18,089 | **2,205** |

Esto separa dos preguntas:

- **¿Sirve utilizar una simulación empresarial para elegir mejor que las reglas ingenuas?** Los propios candidatos predicen diferencias considerables, pero aún no podemos afirmar que sean ganancias realizadas sin consultar el WORLD.
- **¿Sirve identificar `ratio_p` en vez de `diff_c` para tomar esa decisión?** En esta rejilla, la mejora estimada entre familias es comparativamente pequeña y no alcanza el gate.

La utilidad de modelar el campo, de identificar su mecanismo y de ejecutar la decisión correcta son **tres afirmaciones distintas**.

## Integridad del diseño y de la prueba

- Las nueve intensidades `20,30,…,100`, las 35 capacidades `90,95,…,260`, el objetivo caja pre-flow t24, la cuota **3/9** y el umbral **5% bilateral** quedaron incorporados al diseño A12 antes de ejecutar este barrido A12. **Son decisiones informadas por A11**, no preregistro ciego al WORLD histórico.
- `A12.forecast` replica numéricamente el cálculo prospectivo original de A11 en los cuatro K históricos con shock50, para ambas familias y ambos brazos; también coteja las predicciones **congeladas** archivadas de A11.
- El job de barrido hizo *sparse checkout* solo de las ecuaciones contables conocidas y los datos previos A11. No incluyó el generador G5, resultados `WORLD` ni el adjudicador.
- GitHub Actions produjo `gate.json`, `scenarios.csv` y `candidate_policy_cash.csv`. La evidencia original y su procedencia/hashes se copiaron intactos al repositorio.
- La condición de GitHub Actions para ejecutar el WORLD **quedó evaluada como falsa**; no hay artefacto `a12-conditional-world-results`.
- La campaña y las pruebas unitarias terminaron correctamente. Un rechazo científico del gate **no es un fallo del pipeline**.

## Límites e interpretación

El umbral relativo de 5% no es un criterio económico universal. **2,205 unidades monetarias del simulador pueden ser relevantes** según presupuesto, riesgo y consecuencias de una pyme. A12 no cuantifica costos reales de inferencia del CEI ni establece si 2,205 justificaría una decisión distinta en otra organización.

La biblioteca incluye el generador verdadero (`ratio_p`), ambas familias comparten ecuaciones empresariales conocidas y los ajustes se obtuvieron de un único mundo sintético. El objetivo es terminal y determinista; no incluye probabilidad de quiebra, riesgo de faltantes, costos no lineales ni tiempo de recuperación.

**Decisión pragmática:** con este objetivo y biblioteca, no ampliar W016 automáticamente. Una futura investigación sobre valor decisional exigiría cambiar justificadamente la función objetivo, las intervenciones disponibles o la familia rival; no solo buscar un shock donde la distancia entre fórmulas sea mayor.
