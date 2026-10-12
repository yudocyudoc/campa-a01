# A12 · Gate de valor decisional incremental (sin WORLD antes de calificar)

**Pregunta:** ¿existe una franja de decisiones en la que identificar correctamente el driver de W016 reporte una ventaja estratégica material sobre escoger la política del rival? A11 demostró capacidad de pronóstico cerrado, pero **ambas familias recomendaron K180**: una buena decisión que no requería acertar el mecanismo.

A12 pone la **viabilidad decisional por delante** de más campañas. Las predicciones candidatas se calculan sin acceso a G5 WORLD y con parámetros congelados de A11. El análisis de relevancia puede arrojar un negativo; si no satisface el umbral, **ninguna** simulación contrafactual de WORLD se ejecuta.

## Diseño fijado antes de la corrida A12

Las elecciones de esta etapa son **posteriores a las revisiones exploratorias de A11**, no un preregistro epistemológicamente ciego a W016. No se han reajustado modelos ni utilizado nuevas etiquetas WORLD para seleccionar los escenarios.

- Dos familias: `ratio_p` y `diff_c`, cada una con los parámetros originales de ambos brazos A11 (sin ruido, ruido 1%).
- Misma dinámica de `first_order_relaxation` y exactamente las ecuaciones empresariales estipuladas en A11; la simulación de A12 está validada contra la función `A11.forecast()` y las predicciones originales congeladas en K90/115/145/180, shock +50.
- Rejilla de **9 shocks** (20, 30, …, 100) y **35 capacidades** (90, 95, …, 260). **No** se prueban perturbaciones y objetivos adicionales después de conocer el resultado.
- Objetivo fijo: caja al inicio del mes 24; regla de desempate: diferencias de caja ≤1e−6 se resuelven escogiendo la capacidad menor.
- Un shock es *decisionalmente material* solo si **las políticas recomendadas por las familias son distintas** y **ambas** perderían al menos el **5% de su propio rango de caja** por seguir la política del otro modelo.
- El gate autoriza un WORLD posterior solo si esto sucede en **al menos 3 de los 9 shocks en AMBOS brazos**. Dos conjuntos no coincidentes entre brazos no bastan.
- Si autoriza, se elige el shock **solo por pronósticos candidatos**, priorizando el mayor mínimo de arrepentimiento normalizado entre ambos brazos; solo entonces se ejecuta una adjudicación G5 para esas políticas y tres líneas base.

La fracción del 5%, la cuota de un tercio y la tolerancia son **convenciones de diseño**, no umbrales calibrados estadísticamente.

## La medida es simétrica

Para el modelo `m`, `K_m` maximiza su caja prevista `U_m(K)` en las 35 opciones, y `K_n` maximiza la del rival:

```text
R_m = U_m(K_m) − U_m(K_n)
R_n = U_n(K_n) − U_n(K_m)
r_m = R_m / [max_K U_m(K) − min_K U_m(K)]
r_n = R_n / [max_K U_n(K) − min_K U_n(K)]

score = min(r_m, r_n)
material = (K_m != K_n) AND (r_m >= .05) AND (r_n >= .05)
```

Es importante exigir los dos lados: un modelo podría estimar que una decisión equivocada le cuesta miles, mientras el otro queda indiferente entre ambas. Un desacuerdo de políticas no es automáticamente valor práctico.

## Las tres referencias ingenuas

Todas calculadas desde el mismo estado previo y sin etiquetas del WORLD:

1. **No cambiar capacidad:** K115.
2. **Capacidad máxima:** K260.
3. **Capacidad próxima al pico previsto de demanda:** se estima la demanda máxima suponiendo crecimiento de clientes por adquisición menos churn básico, sin acumulación ni cancelaciones por backlog; se redondea a la capacidad disponible más cercana. Es una regla deliberadamente simplificada que **no depende** de `ratio_p` ni `diff_c`.

Para cada una se informa el arrepentimiento *estimado por ambas hipótesis*. Sin adjudicación WORLD, **no se proclama ningún arrepentimiento verdadero**.

## Barrera de información

- Job `candidate-only-gate`: *sparse checkout* solo de contratos, parámetros congelados y snapshot predecisional de A11. Sin `g5_extended_core`, sin `world_policy_outcomes.csv` y sin el adjudicador A12. Ejecuta 1,260 simulaciones candidatas (9×35×2 familias×2 brazos), produce 18 filas de escenarios, 1,260 filas de curvas de caja y `gate.json`.
- Job `world-only-if-gate-passes`: sujeto a `world_authorized=true`, después de congelar y archivar el gate. Calcula en WORLD la acción elegida y referencias, registrando **también el resultado negativo**. Si el gate falla, este job queda `skipped`.
- Tests unitarios sin BPTK validan la continuidad matemática con A11, un caso material y otro solo unilateral, el cálculo de la referencia ingenua y la ausencia de imports del generador en el analista.

## Alcance de un resultado negativo

`NO_MATERIAL_DECISION_DISAGREEMENT` **no** demuestra que conocer el mecanismo sea inútil en general. Solo que los dos ajustes dados de A11 no justifican una nueva simulación bajo **esta rejilla, esta función objetivo y esta condición simétrica del 5%**.

Si ocurre, el próximo trabajo no debería aumentar el número de mundos ni bajar el RMS: cambiar el objetivo decisional (riesgo de insolvencia, cumplimiento, recuperación, etc.), la biblioteca de mecanismos o la naturaleza de las intervenciones, con razones substantivas.

## Ejecutar

```bash
python -m unittest discover -s tests -p 'test_a12.py' -v
python -m experiments.A12.gate --out results/A12/gate
```

El comando de puerta **no importa BPTK ni crea resultados WORLD**. Una adjudicación solamente puede invocarse si `gate.json` confirma los criterios.
