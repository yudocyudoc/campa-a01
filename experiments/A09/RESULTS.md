# A09 · Resultado auditado de regímenes y observabilidad condicionada

**Ejecución de referencia:** [GitHub Actions 38124252708](https://github.com/yudocyudoc/campa-a01/actions/runs/38124252708) · [Artefacto A09](https://github.com/yudocyudoc/campa-a01/actions/runs/38124252708/artifacts/11696915024).  
**Fuente:** W016 de G5 y parámetros de A08 `9e42b0cb6ee4c50b23df3cfecc49e7597afc73e7`; sin reajustes, ecuaciones de simulación originales.  
**Adjudicación cuantitativa post hoc:** [GLM_REVIEW_ADJUDICATION.md](GLM_REVIEW_ADJUDICATION.md) presenta la igualdad algebraica del control anidado \`ratio_p\`, las condiciones del corolario de pendiente y la discrepancia endógena separada en TRAIN/HOLDOUT. Conserva intactos los resultados originales.  
**Estado técnico:** `COMPLETED`, cinco pruebas analíticas, verificación de todas las ecuaciones internas y reproducción exacta de los anclajes numéricos A08.  
**Límite científico:** teorema **condicional sobre mapas dinámicos activos**, no certificación de mínimo RMS global ni identificación ciega a partir de los datos finitos.

## Cobertura y reproducción

- **22 escenarios** originales: cinco de entrenamiento y 17 holdouts.
- **3 modelos** por escenario (`world`, `diff_c`, `ratio_p`), **25 instantes** por trayectoria. Total **1650** filas de señales internas.
- RMS A08 de entrenamiento (rival `diff_c`): **0.016932807979581306**; `ratio_p`: **4.681212562e-15**.
- Mediana RMS holdout de `diff_c`: **0.009338569193045822**; máximo **0.3388815942356633**; 7/17 por encima del umbral heurístico 0.01.
- Máximo error de actualización de Euler medido en los estados reconstruidos: **4.44e-16**.
- La rama `ratio_p` recupera todos los RMS originales (control anidado que contiene al WORLD).

## El dato más importante: por qué siete holdouts dieron error cero

Los siguientes siete regímenes tienen error cero entre el WORLD y el rival `diff_c` **y están inactivos en los 17 instantes posteriores al mes 8 en ambos modelos**:

| Escenario | WORLD activo | Rival activo | Clip en WORLD | Clip en rival |
|---|---:|---:|---:|---:|
| K145, shock 0 | 0/17 | 0/17 | 0 | 0 |
| K180, shock 0 | 0/17 | 0/17 | 0 | 0 |
| K180, shock 25 | 0/17 | 0/17 | 0 | 0 |
| K220, shock 0 | 0/17 | 0/17 | 0 | 0 |
| K220, shock 25 | 0/17 | 0/17 | 0 | 0 |
| K220, shock 50 | 0/17 | 0/17 | 0 | 0 |
| K220, shock 70 | 0/17 | 0/17 | 0 | 0 |

Aquí los datos no pueden discriminar dos formas de activar un mecanismo que **no se activa**. La coincidencia de resultados no es por sí sola evidencia de equivalencia de los mecanismos en otras condiciones.

## Activación y clipping en todos los escenarios

Contamos los 17 tiempos `t≥8` por escenario. La actividad del input y el clipping de la salida son ejes **separados**: el estado latente puede conservar efecto incluso después de dejar de recibir impulso.

| Modelo | Activo en TRAIN (85 tiempos) | Clip en TRAIN | Activo en HOLDOUT (289 tiempos) | Clip en HOLDOUT | Activo y sin clip, TOTAL |
|---|---:|---:|---:|---:|---:|
| WORLD | 85 | 16 | 165 | 58 | 176 |
| `diff_c` | 81 | 16 | 149 | 66 | 148 |
| `ratio_p` | 85 | 16 | 165 | 58 | 176 |

**Ejemplo de saturación:** en `holdout_K90_S25`, `S50` y `S70`, el WORLD está activo **17/17** veces, pero **16/17** instantes están clipeados; solo queda uno activo sin clipping. Una intervención puede activar la causa y, sin embargo, ocultar su magnitud en el observable de capacidad.

Las trayectorias de backlog y caja pueden conservar memoria e informar indirectamente, pero la tabla no establece si alcanzan a identificar de modo único la causa.

## La incompatibilidad algebraica que sí podemos demostrar

El WORLD tiene exceso activo

```text
u_W(D,K) = (4/K)×[D−βK]_+
β = 0.75 + 0.25×threshold
```

El rival `diff_c` tiene `u_R(D,K) = [D−cK−tau]_+`. Para una relajación lineal con **la misma tasa `a>0`** y respuesta observable sin clipping, la igualdad de *mapas de forcing* como función de D en un intervalo abierto activo exige que una única ganancia `g_R` satisfaga simultáneamente

```text
g_R = 4×g_W/115
g_R = 4×g_W/145
```

Con `g_W≈0.439562>0`, los valores requeridos son, respectivamente, **≈0.0152891** y **≈0.0121258**. No pueden ser ambos el mismo `g_R`.

Esta es una **obstrucción algebraica estructural condicionada**, no una demostración de un piso de error numérico para las trayectorias reales de A08. La diferencia se explica porque:

- WORLD y rival de A08 **no tienen exactamente la misma tasa de relajación** (`0.634117...` frente a `0.625740...`).
- Los datos contienen solo un número finito de tiempos, **no** igualdad de respuesta para un intervalo abierto de valores de demanda.
- `incoming_orders` es **endógena** en G5: cambios en capacidad producen efectos en churn y clientes; por tanto, órdenes internas entre modelos pueden diferir.
- El clipping y la inactividad reducen información directa en ciertos regímenes.

La auditoría cuenta **35** instantes de entrenamiento conjuntamente activos y sin clipping en K=115, y **30** en K=145, con 35 y 30 valores distintos de demanda, respectivamente. Eso da **soporte muestral** para estudiar el régimen activo, pero no reemplaza las condiciones del teorema; los valores distintos no crean por sí solos un intervalo abierto ni igualan tasas de respuesta.

Por eso el JSON anota simultáneamente:

```text
conditional_model_level_obstruction = true
certificate_for_actual_finite_A08_observations = false
```

## Interpretación para CEI

La tesis limitada que A09 soporta es que **no todo cambio del campo suministra información discriminante**:

- **Inactivo:** las hipótesis coinciden porque no son estimuladas.
- **Activo y clipeado:** el estímulo existe, pero una parte de su efecto no se lee directamente en capacidad efectiva.
- **Activo sin clipping:** región potencialmente informativa para separar drivers, especialmente si demanda y capacidad varían de manera independiente y las dinámicas temporales están identificadas.

Estas etiquetas se calcularon con **variables latentes del WORLD y del rival**, accesibles solo al evaluador sintético. No son todavía una regla de inferencia operativa sobre una empresa que solo aporta datos observables.

## Siguiente decisión pragmática

Antes de construir una nueva campaña de mundos, separar el teorema de mapas activos de un eventual certificado sobre trayectorias finitas bajo saturación. Si interesa pasar a datos reales, sustituir el acceso a `hidden_excess` y `primitive_impact` por **estimadores observacionales**, definir niveles de ruido y analizar qué señales y periodos permiten realmente distinguir los mecanismos. Un `PASS` de optimización no certifica causalidad.
