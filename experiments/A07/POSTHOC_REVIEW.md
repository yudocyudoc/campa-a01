# A07 · Auditoría crítica posterior a la ejecución

**Estado:** revisión post hoc del resultado científico; **no modifica** la simulación, los datos, los parámetros, el gate ni la ejecución histórica.

**Contexto:** revisión externa de Claude suministrada por el investigador, contrastada con `experiments/A07/experiment.py`, `experiments/A06/g5_model_core.py` y los **cinco archivos reales** del [artefacto A07 / run 38119372061](https://github.com/yudocyudoc/campa-a01/actions/runs/38119372061/artifacts/11694684262). La revisión externa indicó explícitamente que no había ejecutado A07 ni verificado el artefacto. Este documento sí revisó los CSV y JSON de la corrida. No se volvió a correr la simulación.

## 1. Redundancia algebraica **exacta**: solo tres parámetros efectivos

La sección original del README enunciaba **cuatro** grados de libertad `(tau, excursion, adjustment_rate, degradation)` después de eliminar `baseline`. En el caso `first_order_relaxation` con estado inicial del stock latente igual a cero, eso es incorrecto.

Con `D = incoming_orders - nominal_capacity`, `E = excursion > 0` y `tau = baseline + threshold×E`, el input efectivo es `max((D-tau)/E,0)`. Si el estado satisface

```text
dX/dt = a·(max((D−tau)/E,0) − X), X(0)=0
impact = degradation·X
```

al definir `Z = E·X`, resulta:

```text
dZ/dt = a·(max(D−tau,0) − Z), Z(0)=0
impact = (degradation/E)·Z
```

Así, para las observaciones consideradas, solo son efectivos `(tau, a, g)`, con `g = degradation/E`. La redundancia de escala/ganancia es **matemática y exacta** en este modelo; el documento RESULTS la presentaba demasiado débilmente como una «dirección redundante en el régimen evaluado».

Los seis ajustes guardados en `fit_multistart.csv` confirman la identidad numérica:

| Brazo | Inicio | E | degradation | g = degradation/E | RMS train |
|---|---:|---:|---:|---:|---:|
| K115 | 0 | 28.750000 | 0.439562 | 0.01528913013 | 7.34e-16 |
| K115 | 1 | 30.238254 | 0.462317 | 0.01528913013 | 1.31e-14 |
| K115 | 2 | 43.113794 | 0.659172 | 0.01528913013 | 1.46e-14 |
| K115+K145 | 0 | 29.910310 | 0.433433 | 0.01449109170 | 0.017377586 |
| K115+K145 | 1 | 31.571213 | 0.457501 | 0.01449109170 | 0.017377586 |
| K115+K145 | 2 | 44.706807 | 0.647850 | 0.01449109165 | 0.017377586 |

**Corrección para A08:** optimizar directamente `tau`, `adjustment_rate` y `g`, sin `E` y `degradation` como grados independientes.

## 2. El brazo de capacidad fija es un control positivo algebraico

Para capacidad fija `K0=115`, razón `orders/K0` y diferencia `orders−K0` son señales ligadas por una transformación afín. La parametrización rival puede reproducir exactamente el driver normalizado mediante el ajuste analítico que se proporcionó como primer inicio.

En `fit_multistart.csv`, el primer intento termina con `nfev_scipy = 1`, cinco llamadas reales de residual incluyendo derivadas numéricas y RMS `7.34e-16`. **No es un descubrimiento de optimización**: certifica que el control matemáticamente equivalente se ejecuta correctamente.

## 3. La selección de holdouts está informada por el oráculo

`TRUE_REPAIR` replica exactamente el WORLD bajo todas las condiciones probadas: `world_error_ratio=0` en los cuatro holdouts por brazo. En consecuencia,

```text
candidate_disagreement = RMS(TRUE_REPAIR − rival)
                       = RMS(WORLD − rival)
```

en esta construcción sin ruido.

Aunque el script conserva la secuencia computacional «seleccionar antes de ejecutar WORLD holdout», la selección **ya conoce el modelo generador y sus parámetros**. Es válida para encontrar un separador adversarial local, **no es selección genuinamente ciega a la verdad**. Las cuatro cifras reportadas están condicionadas a maximizar discrepancia entre **17 candidatos**, con balance por estrato: no son una muestra representativa de probes.

## 4. Distribución de los 17 probes (no solo los cuatro elegidos)

Medido sobre las 34 filas de `candidate_only_probes.csv`:

| Métrica | Entrenamiento K115 | Entrenamiento K115+K145 |
|---|---:|---:|
| Probes en catálogo | 17 | 17 |
| Con discrepancia numérica ≤1e-9 | 7 | 7 |
| Con discrepancia >0.01 RMS | 10 | 10 |
| Mediana RMS | 0.013815 | 0.017280 |
| Media RMS | 0.052558 | 0.047808 |
| Máximo RMS elegido | 0.367640 | 0.317023 |

Ambos brazos seleccionaron `K180/S70`, pulso `K250/S70`, `K145/S70` y `K90/S0`. Es informativo que **7 de 17** no discriminen ni siquiera a este par conocido y **10 de 17** superen el umbral heurístico. No se infiere frecuencia poblacional: es un catálogo diseñado por nosotros.

## 5. El segundo brazo NO es simplemente «no concluyente»

En el brazo con capacidad 115 y 145, el mejor RMS de entrenamiento del rival fue **0.017377586**, contra un error numérico ~0 del modelo generador. Los tres inicios convergieron al mismo RMS dentro de precisión de reporte; ninguno reportó `at_parameter_boundary`. Todos reportaron `success=true`, finalización `xtol`, con `nfev_scipy` 18, 23 y 22 y llamadas totales de residual 54, 71 y 70.

Esto es **evidencia de discriminación dentro del entrenamiento bajo el ajuste adversarial intentado**. El rótulo original `NO_STRONG_CLAIM_TRAIN_FIT_OR_SEPARATION_INSUFFICIENT` se refería exclusivamente a no poder atribuir la diferencia de holdout al *nuevo* campo después de haber logrado un ajuste convincente de entrenamiento; si se lee como «ninguna evidencia de separación», es engañoso.

**No demuestra** que el mínimo global de la familia rival sea mayor que cero: SciPy TRF, tres puntos iniciales y un presupuesto finito no certifican un óptimo global. El valor 0.01 se usó tanto como umbral de ajuste creíble como de separación práctica, sin calibración de ruido. Estas decisiones se deben separar y declararse heurísticas.

## 6. Problemas de validez pendientes

- Un solo WORLD: `W016`, una familia dinámica (`first_order_relaxation`), sin ruido y sin desconocimiento real de la verdad.
- Rival restringido a `orders − 1×capacity`. No se ensayó `orders − c×capacity` con `c` libre.
- Un rival `orders/K^p` con `p` libre **incluye la razón verdadera cuando `p=1`**; por lo tanto, sería un control de modelos anidados, no un rival necesariamente falso.
- `tests/test_a07.py` solo valida invariantes del diseño, no el resultado del ajuste, la identidad exacta entre drivers, ni la clasificación final del análisis.
- El precompromiso `design_frozen_before_holdout.json` es un archivo escrito **dentro del mismo proceso**. Sirve para rastreabilidad operacional, pero no equivale a preregistro externo inmutable.

## 7. Conclusiones corregidas

**Comprobado:** la transformación afín hace equivalentes los drivers bajo capacidad constante. Un campo que varía la capacidad permite separar, para esta pareja con parámetros fijados/reajustados como arriba, sus predicciones en condiciones activas. El entrenamiento con dos capacidades ya puso en evidencia una diferencia de ajuste para los intentos de optimización registrados.

**No comprobado:** identificación ciega, capacidad de distinguir a todos los rivales de familias más amplias, mínimo global del error adversarial, poder estadístico bajo ruido, ni ventaja decisional de CEI en empresas reales.

**Criterio propuesto para A08, sin burocracia adicional:** usar un rival de tres parámetros efectivos; añadir `orders − cK` y un control anidado `orders/K^p`; reportar el catálogo completo, el error de entrenamiento y el de holdout **por separado**; no seleccionar probes con la verdad generadora conocida si la pregunta es inferencia ciega. Sin recalcular ni reetiquetar el resultado histórico A07.
