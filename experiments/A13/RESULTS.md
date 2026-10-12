# A13 · Resultado exploratorio: qué errores cambian más la decisión

**Estado técnico:** ejecutado en [GitHub Actions #38195865512](https://github.com/yudocyudoc/campa-a01/actions/runs/38195865512), conclusión success. Seis pruebas unitarias aprobadas. La ejecución produjo 1,044 casos de sensibilidad y comprobó **1,260 predicciones sin perturbar** contra la evidencia original de A12; no consultó WORLD.

**Evidencia permanente:** [evidence/](evidence/) (`cases.csv`, `sources.csv`, `summary.json`) y [evidence_manifest.json](evidence_manifest.json) con SHA-256 originales, hashes Git blob y procedencia del CI. Se preservó cada archivo **byte a byte** desde el [artefacto de GitHub Actions](https://github.com/yudocyudoc/campa-a01/actions/runs/38195865512/artifacts/11722534349), cuya copia temporal caduca a los 30 días. El generador versionado `run.py` sigue siendo reproducible con Python estándar. Este documento y la evidencia son **exploratorios**, posteriores al análisis A12.

## Resultado principal

La selección entre las dos familias conocidas tiene un impacto decisional menor que varios errores sobre el sistema empresarial estipulado. El resultado es **condicional** a tomar la familia ratio_p ajustada de A11 como referencia nominal; **no** demuestra que CEI pueda descubrir relaciones previamente desconocidas ni representa un contraste contra el WORLD independiente.

### Ranking completo de fuentes de error

Valores de **arrepentimiento bajo el modelo nominal** (unidades monetarias del simulador). Las medias se calculan sobre el conjunto artificial de shocks, brazos y multiplicadores, **no** sobre probabilidades o errores realmente observados.

| Fuente | Casos | Cambia K | Regret medio | Regret máximo |
|---|---:|---:|---:|---:|
| Tasa base de pedidos (base_order_rate) | 72 | 72 | 22,695.85 | 60,135.47 |
| Omisión completa del driver (gain=0) | 18 | 18 | 20,264.68 | 26,232.48 |
| Precio (price) | 72 | 36 | 14,950.84 | 75,766.54 |
| Shock futuro mal previsto | 72 | 72 | 14,092.63 | 60,135.47 |
| Familia diff_c en lugar de ratio_p | 18 | 8 | 388.05 | 2,204.72 |
| Adquisición por marketing | 72 | 35 | 339.8 | 2,204.72 |
| Intensidad de marketing | 72 | 35 | 339.8 | 2,204.72 |
| Costo variable por pedido | 72 | 26 | 299.3 | 2,845.3 |
| Retardo de cobranza | 72 | 17 | 83.8 | 772.4 |
| Churn básico | 72 | 10 | 32.9 | 336.5 |
| Costo de capacidad adicional | 72 | 8 | 25.7 | 336.5 |
| Cancelación por backlog | 72 | 0 | 0.0 | 0.0 |
| Pérdida de clientes por cancelación | 72 | 0 | 0.0 | 0.0 |
| Costos fijos | 72 | 0 | 0.0 | 0.0 |
| Costo de marketing por unidad | 72 | 0 | 0.0 | 0.0 |
| Piso de capacidad mínima | 72 | 0 | 0.0 | 0.0 |

**Advertencia sobre las medias:** familia y omisión del driver tienen **18 casos**, mientras que cada coeficiente y el error del shock tienen **72**; no son distribuciones equiprobables comparables. Los extremos de ±50% pueden representar cambios operativamente drásticos. Un valor de arrepentimiento 0 significa que la K seleccionada no cambia, no que el parámetro sea económicamente irrelevante.

### Hallazgos a interpretar con cuidado

1. **Tasa de pedidos:** el mayor promedio de arrepentimiento se concentra en un coeficiente empresarial dado como conocido por construcción. Este resultado motiva estudiar la incertidumbre en la demanda, pero no prueba que sea fácil medirla ni que su error real alcance ±50%.
2. **Driver ausente:** la ablación gain=0 produce arrepentimientos grandes. No es un baseline empresarial competitivo: es una omisión extrema y explícita.
3. **Precio:** el peor caso usa price×0.5. Dado que el precio nominal es 100 y el costo variable es 50, esa perturbación elimina el margen de contribución por pedido; el modelo mal especificado elige K90. De ahí pérdidas cercanas a todo el rango de caja. No interpretar el promedio como exposición esperada.
**Descomposición importante del precio:** su alto promedio se debe casi por completo al error extremo de ×0.50. La pérdida media es 59,243.81 en ×0.50, frente a 320.50 en ×0.75, 86.20 en ×1.25 y 152.86 en ×1.50. Por tanto, **no** interpretar el precio como segundo o tercer factor más sensible bajo errores moderados. Para la tasa base de pedidos, en cambio, incluso un error ×0.75 produce una pérdida media de 26,891.08; la sobreestimación ×1.25 produce 4,441.88. Es una asimetría condicional marcada.

4. **Familia funcional:** los máximos condicionales de 2,205 y el promedio de 388 están muy por debajo de varios errores de coeficientes o de demanda. Es evidencia exploratoria de que, **en esta decisión y bajo estos supuestos**, puede importar más saber que el canal de erosión existe y estimar los flujos del negocio que reconstruir su parametrización funcional exacta.
**Parámetros de adquisición:** `marketing_intensity` y `acquisition_per_marketing_unit` producen el mismo regret y la misma K en los casos comparados porque ambos alteran el producto de adquisición de clientes. **No generan pronósticos de caja idénticos**: `marketing_intensity` también modifica directamente el gasto de marketing, que es independiente de K en este modelo.

5. **Errores con K inalterada:** costos fijos y otros parámetros pueden cambiar la caja pronosticada, aunque no cambien la capacidad óptima; por ello cases.csv conserva los errores de pronóstico por separado.

## Protocolo y reproducibilidad

- 9 shocks × 2 brazos; 35 K; 13 coeficientes × 4 multiplicadores (0.5/0.75/1.25/1.5), familia rival, gain=0 y cuatro errores de shock.
- Se congelaron los fits originales de A11 y se usaron sus mismas ecuaciones contables y snapshot predecisional.
- Única cantidad objetivo de decisión: caja al comienzo de t24.
- Sin nueva optimización de parámetros; sin nuevo umbral o gate; **sin generación ni consulta de trayectorias WORLD**.
- Métrica: regret en el modelo nominal ratio_p por seguir K elegida bajo especificación errónea; se registra por separado el error de la previsión monetaria.
- Los promedios en este documento no son EVPI, EVPPI ni costo esperado de error.

**SHA-256 de la evidencia original, ahora preservada en el repositorio:**

- cases.csv: 203f43937e59475795c66376ae25860b9dd2917e090fa83157065938de1150b5
- sources.csv: 23f95f301f46d589166ddcbfd71aaa187abec6296cd08fdd9f90f55144b8c3b7

Los hashes coinciden con `summary.json`; `evidence_manifest.json` también conserva la huella del propio resumen (`2b709e92…`) y el commit `135c50ad…` de la corrida original. El runner preservó hashes SHA-256 de A11.contract, los ajustes, el snapshot y las curvas A12. Una prueba unitaria comprobará la integridad de los tres archivos archivados.

## Lo que A13 NO demuestra

A13 sigue usando ecuaciones empresariales conocidas, perturbaciones individuales y una referencia nominal ajustada muy próxima al WORLD original, no un generador independiente en esta corrida. No estima incertidumbres reales, no asigna priors ni costos de información, no construye una distribución conjunta y no evalúa un sistema empresarial observado. Un ranking de sensibilidad **no es** por sí mismo un ranking de valor de información.

## Continuación más informativa

En vez de buscar nuevos mecanismos funcionales por su sola divergencia matemática, considerar qué variables y relaciones son conocidas vs estimadas en una pyme real, qué datos permitirían medirlas y cuál sería la consecuencia decisional de sus incertidumbres. Una comparación futura contra un baseline empresarial competente debe incluir modelos con congestión/erosión, no solo gain=0.
