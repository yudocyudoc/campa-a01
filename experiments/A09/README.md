# A09 · Auditoría de regímenes y separabilidad condicionada

## Objetivo

Comprobar cuáles de los cinco regímenes de entrenamiento y 17 holdouts de A08 **activan efectivamente las diferencias** entre el WORLD W016 y su mejor rival `pedidos − c×capacidad`. Separar:

1. **Inactividad del driver** (la perturbación no activa el mecanismo).
2. **Actividad con salida sin clipping** (la dinámica puede afectar a la capacidad).
3. **Salida clipeada/saturada** (aunque el driver esté activo, el efecto no es directamente observable en la capacidad).
4. **Incompatibilidad algebraica de mapas de respuesta**, condicionada a supuestos que los datos finitos no necesariamente cumplen.

**No se vuelve a entrenar ningún rival.** Se reutilizan exactamente los parámetros de A08: `a08_frozen_fit.json` registra fuente y SHA, y el pipeline comprueba los RMS de entrenamiento y holdout originales antes de marcar `COMPLETED`.

## Instrumentación

Se reconstruyen las ecuaciones BPTK originales mediante `build_world` y `build_repair_model` de A08 sin modificaciones. Se solicitan adicionalmente variables que los modelos ya calculaban:
- WORLD: `hidden_signal`, `hidden_excess`, `hidden_state`, `primitive_impact`.
- Candidatos: `derived_signal`, `stress_excess`, `latent_state`, `primitive_impact`.
- En los tres: `incoming_orders`, `nominal_capacity`, `effective_capacity`, `backlog`, `cash`.

Cada fila registra actividad y clipping por separado: **inactivo con salida clipeada es posible** cuando persiste memoria del estado latente. Las ecuaciones de `hidden_excess`, `stress_excess` y clipping se validan directamente contra los valores reconstruidos; se prueba la identidad de actualización de Euler de la dinámica de primer orden.

**Advertencia adicional:** en G5 `incoming_orders` es endógena debido a la retroalimentación por `customer_base`, cancelaciones y churn. Por eso una comparación del mismo escenario nominal no asegura **igual demanda interna** entre el WORLD y el rival. A09 registra esa discrepancia y **no la trata como un experimento de entrada verdaderamente exógena**.

## Proposición analítica — alcance preciso

Sea `D` la demanda, `K` la capacidad positiva, `theta` el umbral del WORLD, `beta = 0.75+0.25×theta`. En régimen activo:

```text
excess_WORLD = (4/K)×(D−beta×K)
excess_DIFF  = (D−c×K−tau)
```

Para `first_order_relaxation`, al observar el impacto latente `Y` sin clipping, con **una misma tasa de relajación `a>0`**, se tiene `Y' = a(−Y + g×excess)`.

Si ambos modelos tienen que representar **la misma respuesta como función de D sobre un intervalo abierto activo** a dos capacidades `K1 != K2`, las pendientes de sus términos impulso respecto de D deberían coincidir:

```text
g_DIFF = 4×g_WORLD/K1
g_DIFF = 4×g_WORLD/K2
```

Para `g_WORLD > 0`, esto es imposible con una única ganancia fija `g_DIFF`. Esto prueba una **incompatibilidad de mapas de forcing bajo las hipótesis indicadas**, no certifica directamente un mínimo RMS de trayectorias en los datos finitos de A08. De hecho, la tasa ajustada del rival difiere de la verdadera, la demanda es endógena y puede existir clipping.

## Qué exporta

- `internal_trajectories.csv`: 22 escenarios × 3 modelos × 25 tiempos con actividad, saturación, driver, stock, impacto y variables observables.
- `regime_counts.csv`: número de pasos activos, inactivos, clipeados y activo-sin-clip por caso/modelo.
- `a08_scores_rechecked.csv`: 22 × 2 RMS frente al WORLD en las mismas ventanas y escalas de A08.
- `euler_identity.csv`: comprobación de actualización de primer orden.
- `summary.json`: proposición analítica, apoyos muestrales, limitaciones y hashes.

Las etiquetas son **retrospectivas** y usan estados latentes conocidos al evaluador. No son un detector operativo para datos reales ni una regla de selección de probes.

## Criterio científico

- `COMPLETED` sólo si la reconstrucción de A08 reproduce los anclajes numéricos y las ecuaciones reportadas.
- `conditional_model_level_obstruction=true` reconoce el teorema bajo sus supuestos.
- `certificate_for_actual_finite_A08_observations=false` registra que los supuestos no se verifican automáticamente en las trayectorias muestreadas.

Un resultado de actividad insuficiente o clipping **no es prueba de equivalencia global**, y un teorema de mapas activos **no prueba identificabilidad ciega general**.

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4" "scipy>=1.11,<2"
python -m unittest discover -s tests -p 'test_a09.py' -v
python -m experiments.A09.experiment --out results/A09
```
