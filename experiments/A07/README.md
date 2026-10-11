# A07 · Adversario reajustable entre razón y diferencia

**Pregunta:** si el modelo rival que utiliza `pedidos − capacidad` puede ajustar parámetros a observaciones de entrenamiento del WORLD, ¿existe una perturbación **fuera de entrenamiento** en la que diverja de la explicación `pedidos / capacidad`?

## Continuidad científica

- **A03/G5:** 40 mundos, 15 `COMMIT_CORRECT`, 25 `COMMIT_WRONG`; frecuentes errores de *feature* dentro de la familia acertada.
- **A05:** el diagnóstico de empates y de separación de clase versus separación de feature ([PR #5](https://github.com/yudocyudoc/campa-a01/pull/5)).
- **A06:** separación numérica local de dos parametrizaciones fijas sin permitir reajuste.
- **A07:** el rival **se entrena**, con tres puntos iniciales y un optimizador acotado, y se enfrenta a intervenciones no vistas.

Se reutilizan **sin modificación** las ecuaciones BPTK-Py originales de G5 exportadas a `experiments/A06/g5_model_core.py`. El WORLD usado para evaluar es W016, familia `first_order_relaxation`. **Es un caso sintético conocido: no hay cegamiento de la identidad del WORLD ni descubrimiento independiente.**

## Hipótesis comparadas y libertad del rival

Modelo verdadero, conocido a priori por el evaluador: activador basado en `incoming_orders / nominal_capacity`.

Adversario: activador `incoming_orders − nominal_capacity`, con cuatro grados efectivos de libertad:
- ubicación efectiva del umbral `tau = baseline + threshold × excursion`;
- escala positiva `excursion`;
- tasa de ajuste del stock latente;
- ganancia de degradación de la capacidad.

La combinación `baseline + threshold × excursion` elimina redundancia algebraica de parametrización: fijar el valor explícito `threshold` no restringe las funciones de activación representables mientras `baseline` siga libre.

Se conservan familia dinámica, stocks, causalidad del bucle y el resto de ecuaciones de G5. **No se reajusta ningún parámetro después de elegir y consultar los holdouts.**

## Brazos de entrenamiento (establecidos antes de la corrida)

| Brazo | Condiciones para ajustar el adversario |
|---|---|
| `fixed_capacity` | Capacidad 115, shocks de demanda 0, 25 y 70 |
| `cross_capacity` | Las tres anteriores, más capacidad 145 con shocks 25 y 50 |

La segunda condición es más exigente porque el adversario ya ha visto cambios del campo durante el entrenamiento. Se usan mínimos cuadrados no lineales `scipy.optimize.least_squares`, tres inicios deterministas, límites publicados y 42 evaluaciones de función por intento como máximo según SciPy. El mejor intento se escoge **únicamente por error de entrenamiento**.

No se afirma que estas búsquedas hayan encontrado el óptimo global: el ajuste es acotado y la función objetivo puede ser no convexa y no suave.

## Selección ciega al resultado holdout

1. Leer las respuestas del WORLD **solo en el conjunto de entrenamiento**, permitido para calibrar el adversario.
2. Ajustar el adversario en cada brazo y congelar sus parámetros.
3. En **17 holdouts candidatos**, simular el par `ratio` y `diferencia` sin observar el WORLD.
4. Elegir cuatro pruebas, a lo sumo una por estrato de capacidad o pulso, según **mayor discrepancia entre predicciones candidatas**.
5. Guardar `design_frozen_before_holdout.json` y el SHA de `candidate_only_probes.csv`.
6. **Solo entonces** consultar el WORLD en los cuatro holdouts seleccionados, sin reajustar.

Se mide RMS normalizado de **capacidad efectiva, backlog y caja**, en unidades preestablecidas, de los meses 8 a 24. La diferencia entre el error rival y el error de la razón mide separación local fuera de muestra.

## Interpretación y límites

- `COMPLETED`: **éxito técnico**, independientemente del resultado científico (también hay hallazgos negativos).
- `LOCAL_ADVERSARY_DISCRIMINATED`: entrenamiento con RMS no mayor a 0.01 y al menos un holdout donde el rival supera a la razón por más de 0.01 RMS. Ese umbral es **heurístico y sin calibración de ruido**, no significancia estadística.
- `NO_STRONG_CLAIM_TRAIN_FIT_OR_SEPARATION_INSUFFICIENT`: entrenamiento demasiado malo o separación insuficiente para una afirmación fuerte bajo este criterio.

**No se prueba** identificabilidad global de familias, optimización adversarial exhaustiva, robustez al ruido, aplicabilidad a datos reales, ni la capacidad de CEI para descubrir ciegamente el mecanismo. Un fallo de optimización tampoco demuestra que separar el mecanismo sea imposible.

## Salidas

- `fit_multistart.csv`: todos los ajustes e intentos.
- `candidate_only_probes.csv`: evaluación de los 17 probes por cada brazo, sin consultar WORLD.
- `design_frozen_before_holdout.json`: selección y parámetros preadjudicación.
- `heldout_adjudication.csv`: comparación final únicamente sobre los holdouts seleccionados.
- `summary.json`: métricas, diferencias, límites y hashes de archivos.

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4" "scipy>=1.11,<2"
python -m unittest discover -s tests -p 'test_a07.py' -v
python experiments/A07/experiment.py --out results/A07
```

El job tiene límite de 45 minutos, sin credenciales externas y publica la evidencia también cuando hay fallos.
