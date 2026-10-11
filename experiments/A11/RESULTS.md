# A11 · Adjudicación de intervención prospectiva con pedidos endógenos

**Diseño:** [README](README.md).  
**Primera ejecución validada:** [GitHub Actions 38183600988](https://github.com/yudocyudoc/campa-a01/actions/runs/38183600988) — los cuatro jobs de producción/analista/adjudicación/tests finalizaron exitosamente.  
**Nota de auditoría:** el hallazgo del control negativo sobre `diff_c` se detectó *después* de la corrida al leer los pronósticos originales congelados. Se añadió un campo de diagnóstico al adjudicador para que futuras ejecuciones también lo reporten automáticamente; **no se modifican predicciones, entrenamiento ni regla de elección**.

## Resultado prospectivo registrado antes de consultar WORLD

El analista recibió: cinco regímenes históricos públicos A10 y el estado al principio de **t8** (stock de clientes, backlog, receivables, caja, pedidos y capacidad efectivos del instante anterior). Conocía la magnitud del shock exógeno desde t8 (**+50**) y un conjunto acotado de cuatro intervenciones (K = 90, 115, 145, 180).

**No recibió futuros pedidos, ingresos, cancelaciones o caja**, ni estados latentes del WORLD. Para proyectarlos usó las ecuaciones de negocio dadas a priori y parámetros del driver ajustados desde los datos observados.

| Métrica TRAIN | Sin ruido | Ruido 1% |
|---|---:|---:|
| Familia elegida | `ratio_p` | `ratio_p` |
| Margen RMS frente a `diff_c` | 0.015829141 | 0.007662977 |
| Umbral original de abstención | 0.005 | 0.005 |
| Acción preferida (capacidad desde t8) | **180** | **180** |
| Caja t24 pronosticada con K=180 | **19,476.154** | **19,476.154** |

La acción se eligió maximizando caja t24 prevista en el menú de políticas, con desempate por menor K; si el analista se hubiera abstenido, habría elegido la política de no cambio K115. No se aplicó ningún ajuste a resultados futuros.

## Resultados WORLD — generación posterior al freeze

| Capacidad t8–t24 | Caja real en t24 | Diferencia frente a K115 |
|---|---:|---:|
| K90 | −34,213.024 | −7,260.042 |
| K115, sin cambio | −26,952.982 | 0 |
| K145 | −3,443.798 | +23,509.183 |
| **K180** | **19,476.154** | **+46,429.135** |

Los dos brazos escogieron la misma acción y en este menú **K180 fue la elección ex post del WORLD**. Por tanto:

- `regret` en caja del mejor del menú frente a la política elegida = **0**.
- Ganancia de caja respecto de K115 = **+46,429.135 unidades monetarias del simulador**.
- Sin ruido, el error RMS normalizado al anticipar pedidos de K180 fue **0**, backlog **0**, clientes **0**, caja **0**, y capacidad efectiva **≈1.07e−12**.
- Con ruido histórico de capacidad efectiva de 1%, los RMS de pedidos, backlog, clientes y caja en K180 también fueron **0**, y capacidad efectiva RMS **0.00430919**.

No se interpretan esos valores como pronósticos monetarios para una pyme real.

## Hallazgo negativo decisivo: el mecanismo correcto **no fue necesario para elegir la mejor política**

**Control post hoc sobre artefacto de predicciones congeladas:** ambas familias `ratio_p` y `diff_c` dieron a K180 la mayor caja prevista, en ambos brazos. Bajo K180, **ambas también predijeron la misma caja terminal de 19,476.154**, pese a que sus trayectorias de capacidad efectiva no coincidieron.

Este hallazgo impide atribuir la **decisión correcta** al éxito de inferencia causal del CEI. Las ecuaciones empresariales compartidas y el menú de políticas ya favorecían la opción de mayor capacidad para la función objetivo definida. En esta región, discrepancias de driver no cambian pedidos atendidos, backlog ni caja, aunque sí cambian capacidad efectiva pronosticada.

La simulación muestra una capacidad de **pronóstico prospectivo condicionado**: el modelo reconstruye los pedidos futuros a partir del estado empresarial y feedback conocido, sin recibir esos pedidos del WORLD. Sin embargo, A11 **no aporta evidencia positiva de valor estratégico incremental** de discriminar `ratio_p` frente a `diff_c` para la política examinada.

## Restricciones del experimento

1. **Las reglas de negocio eran conocidas y correctas por construcción**: pedido base de clientes, adquisición, cancelaciones, churn, ventas, cobranza y costos. Solo se identificaba la respuesta dinámica `first_order_relaxation` y su driver dentro de dos familias previamente elegidas.
2. La verdadera familia `ratio_p` existe en la biblioteca candidata (p=1). Esta prueba no es descubrimiento ciego de mecanismos.
3. El shock exógeno +50 desde t8 y las cuatro capacidades candidatas fueron conocidos antes de decidir. Los pedidos endógenos posteriores **no**.
4. El mundo continúa siendo W016 sintético y público; las observaciones históricas incluyen escenarios previos de la misma estructura G5.
5. Se evaluó un único menú y un único objetivo (caja al inicio t24), no cambios de precios, inversión, calendarios o incertidumbre externa. **No se demuestra robustez decisional fuera de este menú**.
6. La ganancia económica pronosticada frente a no cambio se debe a las reglas de G5 y puede variar radicalmente en sistemas reales.
7. Evaluar una política óptima dentro de una biblioteca pequeña no constituye identificación causal general ni optimización empresarial universal.

## Siguiente interrogante científico

**No ampliar automáticamente a más mundos antes de examinar si las familias rivales realmente recomiendan acciones distintas.** Sería mucho más informativo diseñar prospectivamente un escenario o política donde los modelos discrepen *antes* de observar resultados, congelar ambas políticas y compararlas con el WORLD. La selección debe usar únicamente los pronósticos candidatos, no la verdad generadora, para no repetir la circularidad A07.

Esto pondría a prueba el **valor decisional de conocer el mecanismo**, no únicamente el funcionamiento de una simulación cerrada correctamente conectada.
