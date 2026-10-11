# A05 · Auditoría post hoc de fallos en los 40 mundos de G5

**Estado:** diagnóstico descriptivo sobre evidencia reproducida, **no** nueva campaña de descubrimiento ni prueba causal.  
**Fecha de elaboración:** 2026-10-10 (hora de México).  
**Fuente principal:** [A03, run 38112227083](https://github.com/yudocyudoc/campa-a01/actions/runs/38112227083), artifact `a03-g5-40-world-results`, SHA-256 del ZIP `5e6f95b1a622771082d51e5d5b6876fd5b1bd1e312f40146a6b0e8e7c5c16eea`.  
**Cuaderno:** `c0.0/CEI_C0_0_B1_SD5_G5_Benchmark_Corregido_40_Mundos_ejecutado.ipynb`, commit fuente `d90ff87ba47572edd7d2084ecdc62dfba54cd14d`.  
**Archivos examinados:** `generalization_summary.csv`, `performance.csv`, `decision_baseline.csv`, `feature_leakage_audit.csv`, `structural_class_audit.csv` y los 40 `W###/multiregime_evidence.csv` y `W###/sequential_history.csv`.

## Resumen ejecutivo

| Medida sobre 40 mundos | Casos |
|---|---:|
| Familia dinámica correcta | 34 |
| Familia y feature generadora correctas (métrica histórica) | 15 |
| Familia correcta, feature incorrecta | 19 |
| Familia incorrecta | 6 |
| Reparación aceptada (veredicto operativo) | 39 |
| Agente retenido sin reparación | 1 (W001) |
| Dos hipótesis finales empatadas numéricamente | 15 |
| Éxitos históricos con empate final | 6 |
| Éxitos históricos sin empate final | 9 |
| Decisión coincidente con el oráculo | 36 |
| Mejor política constante *ex post* coincidente | 36 |

El problema principal **no se reduce a confundir las cuatro familias**. La selección de la feature generadora falla con mucha más frecuencia, y existe evidencia de ambigüedad residual incluso en algunos resultados clasificados como correctos.

## Hallazgo 1 · Quince empates que el gate no trató como incertidumbre

En **15/40** mundos, el primer y segundo candidato de `multiregime_evidence.csv` presentan el mismo `mean_multiregime` hasta tolerancia absoluta de `1e-10`. En los 15 casos, son **dos expresiones diferentes dentro de una misma familia**: `ratio::incoming_orders/nominal_capacity` y `diff::incoming_orders-nominal_capacity`.

Casos:
- Ganador correcto pero empatado (6): `W010 W021 W023 W029 W030 W033`.
- Ganador equivocado con empate (9): `W012 W015 W016 W017 W024 W025 W027 W036 W039`.

En esos 15 mundos, el margen entre los dos primeros globales es aproximadamente cero (magnitudes ~`1e-15`). Sin embargo, los 15 recibieron `REPAIR_ACCEPTED`, porque el gate utilizado se basaba en el margen frente a **otra familia** (`class_separation`), que oscilaba entre **0.247 y 0.889**.

**Implicación:** separar familias no demuestra que se haya distinguido la feature dentro de la familia elegida. De los 15 `COMMIT_CORRECT` históricos, **6 no tienen un ganador único por error numérico**. Los otros 9 sí presentan una única mejor hipótesis bajo la biblioteca, datos y tolerancia utilizados; esto **no equivale** a prueba de identificabilidad estructural global.

## Hallazgo 2 · La biblioteca sí contiene el mecanismo correcto

Para los 40 mundos, `multiregime_evidence.csv` incluye al menos un candidato con la pareja correcta (familia verdadera y `ratio::incoming_orders/nominal_capacity`). Por tanto, el problema del benchmark no se explica simplemente por ausencia de la respuesta verdadera en la gramática.

En **19 mundos**, el algoritmo prefirió otra feature aun acertando la clase. Hay **7 casos** con clase correcta y empate numérico entre `ratio` y `diff`: `W012 W016 W017 W024 W025 W027 W036`. En el resto de errores, una explicación alternativa obtuvo mejor score, lo que exige estudiar si la intervención no separó candidatos, si el criterio de error favoreció un proxy o si la calibración produjo equivalencias locales. Ninguna de esas explicaciones queda certificada solo por esta auditoría.

Ejemplo `W016`: `first_order_relaxation` correcta, pero gana `diff::incoming_orders-nominal_capacity`. Su score coincide numéricamente con `ratio::incoming_orders/nominal_capacity` en base, `demanda_alta_capacidad_holgada` y `marketing_push`. El gate da `REPAIR_ACCEPTED`.

## Hallazgo 3 · El primer probe no discrimina a los finalistas

Los **40** mundos comienzan con `demanda_alta_capacidad_holgada`. En los 40 archivos `multiregime_evidence.csv`, tanto la hipótesis finalmente seleccionada como la hipótesis generadora correcta tienen **error cero** en ese probe. Esto **no demuestra que el probe sea inútil**: descarta candidatos adicionales. Pero no discrimina entre esas dos explicaciones relevantes; la carga decisiva pasa al probe siguiente.

Un diseño más informativo no debe limitarse a escoger el probe con mayor discrepancia global; también necesita medir la **diferencia entre el mejor candidato y sus rivales equivalentes o casi equivalentes**.

## Hallazgo 4 · Confusión entre diferencia y razón, sin prueba de causalidad

Con capacidad nominal constante `K` dentro de un régimen:

```text
r = incoming_orders / K
d = incoming_orders - K

d = K * (r - 1)
```

Las expresiones son transformaciones afines de la misma señal cuando `K` permanece fijo. Variar `K` puede romper esa relación global, pero no garantiza discriminación si se observa una región saturada, sin activación o con parámetros compensatorios.

**Hipótesis plausible, no resultado adjudicado:** algunos empates de G5 son compatibles con equivalencia observacional *bajo los probes seleccionados*. La auditoría no prueba equivalencia para todos los parámetros ni para cualquier intervención.

## Hallazgo 5 · La etiqueta histórica mezcla resultados distintos

`W001` termina en `RETAIN_AGENT` tras un solo probe; no hubo `REPAIR_ACCEPTED` ni acción propuesta. No obstante, su `primary_outcome` es `COMMIT_WRONG`.

La fuente revela la regla explícita: `classify_final_at_threshold` devuelve `COMMIT_WRONG` si `invariant_break <= 0.10`, antes de comprobar el compromiso. Esto puede ser una **penalización deliberada de la incapacidad de falsar al agente**, no necesariamente un bug. Sin embargo, contar este caso junto a 24 reparaciones erróneas produce un resumen ambiguo.

Conservar los números históricos **15 correctos / 25 incorrectos / 0 ABSTAIN** para comparabilidad, pero reportar por separado **39 reparaciones aceptadas, una retención, 24 reparaciones aceptadas clasificadas incorrectas y 15 aceptadas clasificadas correctas**. No reescribir los datos originales.

## Hallazgo 6 · Decisiones: 90% sin mejora frente a referencia constante

El CEI coincide con la acción oráculo en **36/40**. La mejor acción constante elegida **ex post** (más capacidad permanente) también coincide en **36/40**. Por tanto, el ejercicio no demuestra ganancia decisional frente a esa referencia; además la selección `ex post` favorece a la línea base.

Los cuatro no-aciertos decisionales del CEI son `W001` (sin acción), `W022`, `W026` y `W036`. `W036` es especialmente ilustrativo: reconoce la familia `pipeline_delay`, pero confunde `diff` con `ratio` y propone una política distinta a la del oráculo.

## Hallazgo 7 · No debemos importar las cifras A1/G4 a G5

La auditoría original A1 utilizó **12 mundos G4 y 57 expresiones**. Su hallazgo de **204 parejas** de features casi equivalentes es un antecedente, **no** un cálculo para estos 40 mundos. G5 usa una gramática primaria reducida a **18 features auditadas como seguras frente a dependencia directa del target** (archivo `feature_leakage_audit.csv`). Eso tampoco excluye cualquier proxy indirecto: solo acredita el chequeo implementado.

En los **40 mundos de G5** existe evidencia independiente de redundancia: los 15 empates finales descritos arriba. Esos son los números que hay que utilizar para una conclusión específica sobre G5.

## Prioridad de investigación después de esta revisión

1. **No retocar retrospectivamente G5.** Congelar las etiquetas, la selección de probes, los grids y los resultados como referencia.
2. **Separar tres veredictos:** clase distinguida, feature distinguida y decisión diferenciada de una línea base. En empates de la feature, reportar incertidumbre explícita, incluso si la clase está separada.
3. **Diseñar una prueba limitada `ratio` vs `diff`** variando demanda, capacidad y horizonte dentro de regiones realmente activas, y comparar predicciones ya fijadas **sin recalibrarlas después de observar el WORLD**.
4. **Ejecutar búsqueda adversarial** para determinar si hay parámetros bajo los cuales las dos explicaciones permanecen indistinguibles, evitando concluir que la ausencia de un separador en una búsqueda heurística implica imposibilidad matemática.
5. Solo después valorar una nueva campaña con LLM/Mermaid para proponer mecanismos fuera de la gramática.

## Reproducción de esta inspección

Desde un equipo con GitHub CLI autenticado:

```bash
gh run download 38112227083 -R yudocyudoc/campa-a01 \
  -n a03-g5-40-world-results -D results/A03
```

Examinar `results/A03/generalization_summary.csv` y los `multiregime_evidence.csv` y `sequential_history.csv` de cada caso. Un empate aquí significa **diferencia absoluta en `mean_multiregime` menor o igual a `1e-10`** tras excluir `__agent_original__`; no es una certificación de equivalencia universal.

**Nota de procedencia:** análisis realizado sobre el artifact público de la ejecución reproducida de A03, no sobre cifras reconstruidas a partir de un resumen. No se generaron mundos nuevos ni se modificaron las reglas científicas.
