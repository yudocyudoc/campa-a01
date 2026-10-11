# A06 · Separación local entre razón y diferencia

**Pregunta concreta:** para dos hipótesis con la **misma familia dinámica y parámetros de estado**, que son algebraicamente equivalentes si se mantiene fija la capacidad nominal, ¿podemos diseñar una perturbación que produzca predicciones distintas al variar independientemente demanda y capacidad?

## Qué recuperamos de G5

`g5_model_core.py` conserva sin cambios las ecuaciones de WORLD y del agente del [G5 corregido de c0.0](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_G5_Benchmark_Corregido_40_Mundos.ipynb), celdas originales 4, 6, 7, 9, 10 y 12. No se ejecuta ni reescribe el benchmark histórico de 40 mundos. El código construye dos hipótesis `first_order_relaxation` usando la verdad sintética de W016 como banco de pruebas **conocido**, no ciego.

- Relación verdadera: `(incoming_orders/nominal_capacity - 0.75)/0.25`.
- Relación rival: `(incoming_orders - nominal_capacity + 0.25×115)/(0.25×115)`.
- A capacidad 115, son algebraicamente idénticas para cualquier demanda. Con otra capacidad, son distintas **excepto cuando pedidos = capacidad**; ambas condiciones forman superficies de igualdad exacta.\n- Identidad: `ratio_normalizada = diff_normalizada` si y solo si `(K−115)×(pedidos−K)=0`. Cambiar K sin salir de pedidos=K no aporta separación.
- Usan exactamente el mismo umbral, tasa de ajuste, degradación, valor inicial y demás parámetros del estado. **Los parámetros se fijan una sola vez; jamás se recalibran durante ni después de los probes.**

## Protocolo computacional mínimo

1. Definir 23 condiciones anticipadas: control, tres cambios solo de demanda, 16 cruces de demanda y capacidad, tres pulsos temporales.
2. Simular únicamente **ambos candidatos**, sin preguntar al WORLD. Clasificar las intervenciones cruzadas/temporales por discrepancia multivariable de las predicciones, en escalas físicas fijadas.
3. Elegir las cuatro intervenciones más discriminantes por ese criterio; reservar además los cuatro controles con capacidad 115.
4. **Solo después** consultar WORLD W016 para contrastar la selección y determinar qué candidato explica sus datos.
5. Exportar `design.json`, `candidate_predictions.csv`, `world_adjudication.csv`, `selected_trajectories.csv` y `summary.json`.

El criterio `LOCAL_SEPARATOR_FOUND` exige equivalencia numérica en los controles, ajuste del modelo verdadero dentro de tolerancia numérica y al menos una perturbación elegida que dé señales diferentes. El umbral `1e-9` es únicamente una sonda **sin ruido**; no es prueba estadística ni un certificado de separación uniforme entre familias.

## Lo que NO demuestra

- No constituye una recuperación ciega de mecanismos: usamos explícitamente la ecuación real de W016 y sus parámetros para construir el caso controlado.
- No resuelve automáticamente las decisiones equivocadas de G5, ni identifica el mejor probe para los 40 mundos.
- No prueba que haya un probe separador bajo cualquier parametrización de ambas familias: otros parámetros pueden permitir compensación o equivalencia.
- No adjudica con garantías matemáticas las búsquedas adversariales G6. Las negativas se etiquetan `UNRESOLVED_OR_IMPLEMENTATION_MISMATCH`, nunca «imposible de separar».

Si el experimento encuentra un separador, el siguiente ensayo debería **introducir ajuste adversarial y comparar contra criterios de observabilidad y ruido**; si no lo encuentra, examinar si hay excitación suficiente antes de aumentar el protocolo.

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4"
python -m unittest discover -s tests -p 'test_a06.py' -v
python experiments/A06/experiment.py --out results/A06
```

GitHub Actions ejecuta en un runner público y guarda los resultados aunque una adjudicación no coincida con nuestras expectativas.
