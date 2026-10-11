# A08 · Rival con capacidad libre y control anidado

**Pregunta:** ¿qué sucede cuando el mecanismo rival de G5 dispone de mayor flexibilidad y eliminamos la redundancia exacta de parámetros encontrada en A07?

## Modelos y parámetros efectivos

Modelo generador original, sintético y conocido: `incoming_orders / nominal_capacity`; dinámica de W016, `first_order_relaxation`.

Dos modelos candidatos con las ecuaciones dinámicas originales:
- `diff_c`: `incoming_orders − c × nominal_capacity`; parámetro `c` libre. Con `c=1` recupera el rival de A07.
- `ratio_p`: `incoming_orders / nominal_capacity**p`; parámetro `p` libre. **Con `p=1` incluye exactamente el modelo verdadero**: control anidado, no un adversario necesariamente falso.

Se ajustan tres parámetros dinámicos efectivos `tau` (umbral en unidades de la feature), `rate` (ajuste del estado) y `g` (degradación/escala), además del parámetro de forma `c` o `p`. Se fija escala `excursion=1` y `degradation=g`, eliminando la redundancia algebraica exacta de A07.

Los modelos están implementados en `g5_extended_core.py`, copia del núcleo G5 de A06 con **únicamente dos nuevas ramas de constructor de driver** (`diff_c` y `ratio_p`); el generador WORLD, stocks y todas las demás ecuaciones se conservaron.

## Diseño congelado

- **Entrenamiento:** los cinco regímenes del brazo `cross_capacity` de A07, con K=115 y K=145 y diferentes shocks. La observación del WORLD se permite solo aquí durante el ajuste.
- **Optimización por familia:** SciPy `differential_evolution` con semilla fija, 12 generaciones y población relativa 4, seguida de tres minimizaciones locales deterministas, máximo 60 `nfev` cada una. Se registran resultados de todos los intentos y llamadas reales al residual.
- **Congelamiento de ajuste:** `design_before_holdout.json` se escribe y hace hash de `fit_attempts.csv` antes de consultar el WORLD en evaluación.
- **Evaluación:** **los 17 holdouts completos** de A07, sin selección por máximo ni descarte de probes desfavorables. Se conserva la distribución, mediana, media y máximo de RMS normalizado.
- Métricas sobre capacidad efectiva, backlog y caja, meses 8–24, escalas fijas (115, 115 y 20,000).

El umbral `0.01` es **heurístico** y sin calibración con ruido real. La ejecución termina exitosamente incluso si el adversario iguala al modelo verdadero: no se fuerza un resultado favorable.

## Adjudicación por separado

- `COMPLETED` = resultados computados y exportados.
- `train_rms` = capacidad de imitación en entrenamiento con el optimizador y presupuesto utilizado, **no mínimo global certificado**.
- `holdout_rms` = error fuera de muestra sin reajuste; se informa en los 17 regímenes, no solo los de mayor discrepancia.
- El control analítico `ratio_p` con `p=1` y parámetros verdaderos se verifica aparte; no se le da al optimizador como inicio y no se presenta como mecanismo «descubierto».
- El resultado de `diff_c` se trata como una cota superior del mínimo de la familia rival encontrado, nunca como prueba de que no exista solución mejor.

## Interpretación y límites

La razón y la diferencia tienen pendientes diferentes respecto de pedidos al variar K: `∂(orders/K)/∂orders = 1/K` frente a `∂(orders−cK)/∂orders=1`. Esto permite estudiar escenarios en los que una única transformación afín no iguala ambas señales. **No demuestra por sí mismo que sus trayectorias de stocks sean distinguibles** bajo clipping, parámetros ajustables y horizontes limitados.

A08 utiliza **un solo WORLD conocido**, sin ruido, sin prueba ciega de descubrimiento, y una optimización heurística finita. Un mínimo aparentemente positivo es evidencia numérica, **no un piso estructural certificado**.

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4" "scipy>=1.11,<2"
python -m unittest discover -s tests -p 'test_a08.py' -v
python experiments/A08/experiment.py --out results/A08
```

La rama experimental se ejecuta en GitHub Actions. El artefacto conserva los resultados y los intentos de optimización incluso si surge una discrepancia.
