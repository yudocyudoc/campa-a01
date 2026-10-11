# A07 · Resultado de la campaña adversarial

**Corrección interpretativa posterior:** [POSTHOC_REVIEW.md](POSTHOC_REVIEW.md) documenta una redundancia algebraica exacta, confirma todas las cifras con los CSV/JSON y explica que la selección de holdouts conoce la parametrización generadora. Este archivo conserva los resultados históricos y las etiquetas originales.\n\n**Fecha de ejecución:** 2026-10-11 (UTC)  
**Corrida:** [GitHub Actions 38119372061](https://github.com/yudocyudoc/campa-a01/actions/runs/38119372061)  
**Artefacto:** [`a07-adversarial-refit-results`](https://github.com/yudocyudoc/campa-a01/actions/runs/38119372061/artifacts/11694684262), cinco archivos (disponibilidad limitada por política de retención de GitHub).  
**Resultado técnico:** `COMPLETED`; pruebas unitarias y regresión general aprobadas.  
**Clasificación científica:** local, paramétrica, sintética y sin validación estadística con ruido.

## Resultado por brazo

| Medición | Capacidad fija | Entrenamiento con dos capacidades |
|---|---:|---:|
| Condiciones de entrenamiento | 3 (K=115) | 5 (K=115 y 145) |
| RMS normalizado en entrenamiento (mejor de tres inicios) | 7.34 × 10⁻¹⁶ | 0.017377586 |
| Calidad de ajuste según umbral heurístico RMS ≤ 0.01 | Aceptable | No aceptable |
| Probes de holdout con diferencia numérica | 4/4 | 4/4 |
| Probes de holdout con diferencia mayor a 0.01 | 4/4 | 4/4 |
| Mayor error rival en holdout (RMS normalizado) | 0.367639892 | 0.317023237 |
| Clasificación | `LOCAL_ADVERSARY_DISCRIMINATED` | `NO_STRONG_CLAIM_TRAIN_FIT_OR_SEPARATION_INSUFFICIENT` |

El modelo verdadero `ratio` reprodujo el WORLD hasta la precisión numérica en todos los holdouts evaluados. Un RMS de 0.01 **no** representa un umbral estadístico ni un nivel de ruido real; fue definido de forma heurística antes de correr.

## Evaluación fuera de muestra (sin reajuste)

| Probe seleccionado | Error del rival, brazo K=115 | Error del rival, brazo K=115+145 |
|---|---:|---:|
| Capacidad 180, shock 70 | 0.367640 | 0.317023 |
| Pulso: capacidad transitoria 250, shock 70 | 0.236199 | 0.202714 |
| Capacidad 145, shock 70 | 0.120294 | 0.102387 |
| Capacidad 90, shock 0 | 0.041870 | 0.049459 |

Los cuatro probes se eligieron solo con las predicciones del par `ratio` y `diff`. Las observaciones del WORLD en holdout se consultaron **después de guardar** `design_frozen_before_holdout.json`. Ninguno de estos holdouts participó en el ajuste.

## Lo que aprendimos

### 1. La confusión con capacidad fija es genuina, no un defecto de optimización

El rival `diff`, con parámetros reajustados, obtuvo RMS de entrenamiento `7.34e-16`. Esencialmente reprodujo exactamente los datos en tres regímenes distintos de demanda, todos con capacidad 115.

La coincidencia deriva de la transformación afín entre razón y diferencia cuando K permanece fijo. El rival **sí** tenía una explicación observacionalmente compatible en ese campo. Al variar K fuera del entrenamiento, esa compatibilidad desapareció en los cuatro probes seleccionados, con errores de 0.042 a 0.368.

### 2. Variar capacidad ya dificulta el ajuste en TRAINING

En el segundo brazo, el rival observó dos capacidades antes de afrontar holdouts. Los tres intentos del optimizador convergieron a RMS cercano a `0.017377586`, superior al umbral heurístico `0.01`. Por tanto, aunque los cuatro holdouts mostraron discrepancias, **no adjudicamos una demostración limpia de separación nueva respecto de un rival que imitara bien el entrenamiento**: el rival ya presentaba falta de ajuste.

Esto es compatible con una diferencia estructural provocada por el cruce de demanda y capacidad. Pero un optimizador local de tres arranques y presupuesto acotado **no prueba** que ninguna parametrización adversarial pueda hacerlo mejor.

### 3. Los parámetros del adversario también tienen redundancia

En el brazo K=115, las tres soluciones tuvieron:
- ubicación efectiva del umbral `tau ≈ -22.497937`;
- tasa de ajuste `≈ 0.634117`;
- diferentes parejas escala/ganancia: `(28.75, 0.43956)`, `(30.23825, 0.46232)`, `(43.11379, 0.65917)`.

La razón `ganancia / escala` permanece aproximadamente constante. **Auditoría posterior:** para esta dinámica lineal de primer orden y estado latente inicial cero, es una identidad algebraica exacta: el modelo tiene tres grados de libertad efectivos (`tau`, tasa de ajuste, `ganancia/escala`), no cuatro. Las diferentes combinaciones de escala y ganancia son representaciones equivalentes, no recuperaciones independientes de parámetros. No debe atribuirse a cada parámetro un significado recuperado de manera única.

### 4. El método de diseño seleccionó las mismas cuatro intervenciones en ambos brazos

El orden de los mejores probes, basado en discrepancia de predicciones y balance por estratos, no cambió tras la recalibración. Esto es un resultado local; no implica que esos probes sean óptimos globalmente ni robustos frente a perturbaciones de ruido o adversarios distintos.

## Veredicto

- **Sí:** una hipótesis errónea puede ajustar perfectamente el entrenamiento de capacidad fija y luego ser discriminada por cambios de campo fuera de muestra.
- **No demostrado:** que todas las parametrizaciones posibles de la familia `diff` sean separables de `ratio` en un dominio amplio.
- **No demostrado:** que CEI pueda descubrir el mecanismo correcto de forma ciega, ni que la ventaja sobreviva bajo ruido y datos incompletos.
- **No demostrado:** que el fracaso del rival en el segundo brazo sea un límite matemático, en vez de una propiedad del dominio y optimizador examinados.

## Siguiente pregunta útil

Una futura prueba adversarial debe permitir una búsqueda más amplia sobre el dominio y medir la **separación mínima que sobrevive** después de recalibrar al rival sobre un conjunto de intervenciones informativas. Al optimizar el peor caso, debemos separar cuidadosamente «no se encontró un imitador» de «se demostró que ningún imitador existe».

Para evitar elección retrospectiva del horizonte o los probes, las nuevas condiciones y el criterio deberían registrarse en una campaña independiente, sin reescribir A07.
