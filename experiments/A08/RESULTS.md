# A08 · Resultados de dos adversarios generalizados

**Ejecución auditada:** [GitHub Actions 38122052685](https://github.com/yudocyudoc/campa-a01/actions/runs/38122052685)  
**Artefacto crudo:** [a08-generalized-adversaries-results](https://github.com/yudocyudoc/campa-a01/actions/runs/38122052685/artifacts/11694883299).  
**Commit ejecutado:** `04474aeecf3f1c31797fec1262b433f261fedeab`.  
**Estado técnico:** `COMPLETED`, workflow y suite general PASS.  
**Estado científico:** evidencia local para W016; **sin mínimo global certificado ni prueba de descubrimiento causal ciego**.

Se verificaron los cuatro archivos originales (`fit_attempts.csv`, `all_17_holdouts.csv`, `design_before_holdout.json`, `summary.json`) y sus hashes. La auditoría revisó los **17 holdouts de ambas familias**, los ocho intentos de ajuste y el control anidado.

## Resultado ejecutivo

| Indicador | `D − cK` | `D/K^p` |
|---|---:|---:|
| Mejor RMS de entrenamiento (cinco regímenes K=115,145) | **0.016932808** | **4.68 × 10⁻¹⁵** |
| Parámetro de forma | c=**1.0070633** | p=**1.0000000** |
| Mediana RMS, 17 holdouts | 0.009338569 | ≈2.52 × 10⁻¹⁵ |
| Media RMS, 17 holdouts | 0.047428990 | ≈2.52 × 10⁻¹⁵ |
| Mayor RMS, 17 holdouts | **0.338881594** | ≈7.85 × 10⁻¹⁵ |
| Holdouts con RMS numéricamente no nulo (umbral 1e-8) | **10/17** | **0/17** |
| Holdouts con RMS mayor a 0.01, heurístico | **7/17** | **0/17** |

La familia anidada `D/K^p` contiene exactamente al generador cuando `p=1`; recuperarlo **no demuestra identificación causal ciega**, aunque sí confirma que la optimización puede hallar una representación equivalente en esta prueba. El control anidado con parámetros construidos a partir de la verdad tiene RMS `7.07e-16` en entrenamiento; se verificó por separado y **no se usó como inicio del optimizador**.

El rival `D−cK` mejora ligeramente respecto del `D−K` fijo de A07 (RMS de entrenamiento 0.017377586 → 0.016932808), pero sigue teniendo un ajuste imperfecto sobre cinco regímenes.

## Auditoría del optimizador

**`D−cK`:** el ensayo `differential_evolution` agotó el presupuesto (208 evaluaciones, RMS 0.089725956). Los tres refinamientos locales terminaron con `success=true`, `ftol` satisfecho y RMS esencialmente idénticos: `0.0169328079795813`, `0.0169328079795875` y `0.0169328079795834`. El mejor ajuste fue:

```text
tau  = -24.7527201422
rate =   0.6257397729
g    =   0.0144565523
c    =   1.0070633038
```

**`D/K^p`:** la búsqueda global (208 evaluaciones) terminó al agotar presupuesto con RMS 0.051584. El refinamiento desde su mejor candidato sí convergió en 38 `nfev` (182 llamadas de residual incluyendo Jacobianos), con error `4.68e-15` y `p=1` exacto dentro de redondeo. **Los otros dos inicios** terminaron inmediatamente en regiones de gradiente prácticamente nulo, con `gtol` pero errores grandes (RMS 2.052 y 1.395). El código registra esos intentos; un `solver_success=true` no implica solución científicamente válida.

Las dos familias tienen tres parámetros efectivos de dinámica `(tau, rate, g)` y uno de forma, sin el parámetro redundante `excursion` de A07. **No hay certificación global de mínimos**: un óptimo numérico reproducible bajo varios inicios sigue siendo una aproximación, no un teorema.

## Distribución íntegra de los holdouts

| Holdout | RMS `D−cK` | RMS `D/K^p` |
|---|---:|---:|
| `holdout_K90_S0` | 0.033049 | 5.073e-15 |
| `holdout_K90_S25` | 0.009339 | 3.284e-15 |
| `holdout_K90_S50` | 0.009339 | 3.094e-15 |
| `holdout_K90_S70` | 0.009339 | 2.890e-15 |
| `holdout_K145_S0` | 0.000000 | 0 |
| `holdout_K145_S70` | 0.099675 | 7.848e-15 |
| `holdout_K180_S0` | 0.000000 | 0 |
| `holdout_K180_S25` | 0.000000 | 0 |
| `holdout_K180_S50` | 0.035182 | 1.285e-15 |
| `holdout_K180_S70` | 0.338882 | 7.274e-15 |
| `holdout_K220_S0` | 0.000000 | 0 |
| `holdout_K220_S25` | 0.000000 | 0 |
| `holdout_K220_S50` | 0.000000 | 0 |
| `holdout_K220_S70` | 0.000000 | 0 |
| `pulse_K80_S25` | 0.021988 | 2.516e-15 |
| `pulse_K90_S50` | 0.030287 | 3.318e-15 |
| `pulse_K250_S70` | 0.219215 | 6.187e-15 |

**7/17** holdouts de `D−cK` no generaron discrepancia observable, incluso con esta familia rival. No equivale a éxito causal del rival; esas intervenciones pueden no excitar la región donde las ecuaciones divergen.

## Qué se sostiene

1. Para **W016**, el mecanismo anidado `D/K^p` alcanza ajuste casi perfecto en entrenamiento y todas las condiciones fuera de muestra, con `p=1`.
2. Para el rival `D−cK`, el mejor error encontrado en entrenamiento fue `0.016933`, pese a la libertad adicional `c`, la parametrización sin redundancia y varios refinamientos. Es evidencia numérica **a favor de** diferenciación bajo los regímenes probados, no una demostración universal.
3. Al evaluar **todos** los 17 holdouts, hay 10 donde las trayectorias no coinciden y 7 donde sí coinciden numéricamente; una intervención debe activar diferencias observables y no solo cambiar nominalmente el campo.
4. La selección no se basó en los valores de holdout: se evaluó el catálogo completo. Pero **la verdad W016 era conocida** para el diseñador, de modo que no debe afirmarse independencia epistemológica o recuperación ciega.

## Qué sigue sin demostrarse

- Mínimo global de la familia `D−cK` y piso estructural no nulo.
- Identificabilidad con observación ruidosa, incompleta o más corta.
- Generalización a los otros 39 mundos de G5 o a dinámicas no lineales distintas.
- Descubrimiento autónomo de la familia y sus causas por el CEI.

**Recomendación pragmática:** antes de ampliar mundos o gramáticas, buscar una **cota analítica condicionada** en el dominio activo de presión/capacidad, o un certificado de optimización global delimitado; no asumir que ampliar iteraciones de DE convierte un número en prueba.
