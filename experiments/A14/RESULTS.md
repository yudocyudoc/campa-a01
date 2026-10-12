# A14 · Resultados: un esqueleto SD conserva decisiones, pero no caja prevista

**Ejecución auditada:** [CI A14 #38198655969](https://github.com/yudocyudoc/campa-a01/actions/runs/38198655969), ocho tests originales OK, 630 pronósticos completos ratio_p A12 cotejados, 180 combinaciones de modelo/política/shock/brazo. Código sin acceso a WORLD por sparse checkout. **Evidencia permanente:** [evidence/](evidence/) (policies.csv, summary.csv, summary.json) y [evidence_manifest.json](evidence_manifest.json), con hashes SHA-256 y blobs Git idénticos al artefacto de CI.

## Resultado decisional (condicionado al fit A11 ratio_p)

Promedios sobre 18 escenarios: 9 shocks nominales × 2 brazos. **Peor arrepentimiento** significa el máximo dentro de los 201 shocks de ±25% en **cada escenario**, y la columna reporta la *media* de esos 18 máximos. Unidades monetarias del simulador, no ganancias reales ni EVPI.

| Modelo para elegir capacidad | Regla | Regret nominal medio bajo referencia completa | Media del peor regret de ±25% | Mayor peor regret de los 18 escenarios |
|---|---|---:|---:|---:|
| Completo | Nominal | 0 | 14,667.38 | 25,418.87 |
| Completo | Minimax-regret | 1,819.66 | 4,691.77 | 8,186.01 |
| Mínimo | Nominal | **345.60** | **11,971.87** | 24,811.67 |
| Mínimo | Minimax-regret | **2,352.99** | **5,162.46** | 8,186.01 |

Con referencia completa, la robustez reduce la media de las peores pérdidas de 14,667.38 a 4,691.77 (≈68.0%), pagando una penalización nominal media de 1,819.66. Con esqueleto mínimo, reduce la media de las peores pérdidas de 11,971.87 a 5,162.46 (≈56.9%), pagando una penalización nominal media de 2,352.99 frente al óptimo de la referencia.

**La política robusta del mínimo resulta solo 470.69 unidades por encima de la política robusta del completo** en esta métrica (≈10.0% más); ninguna de las dos conoce realmente el shock futuro. No implica que robustez cure cualquier modelo malo.

## Ablaciones de las retroalimentaciones

| Modelo candidato | K nominal frente a completo | K robusta frente a completo | Error absoluto medio de caja prevista en K elegida |
|---|---|---|---:|
| Sin cancelaciones (y churn inducido) | Igual en 18/18 | Igual en 18/18 | 1.51 (nominal) |
| Sin churn inducido por backlog | Igual en 18/18 | Igual en 18/18 | 1.51 (nominal) |
| Sin demora de cobro nuevo | +5 K en 10/18; igual en 8/18 | +5 K en 12/18; igual en 6/18 | 32,223.54 (nominal) |
| Esqueleto mínimo (tres cambios) | **Igual que sin demora de cobro** | **Igual que sin demora de cobro** | 32,223.54 (nominal, aproximadamente) |

**Interpretación:** el impacto decisional de la simplificación, en esta rejilla, proviene casi totalmente de tratar las ventas nuevas como cobradas inmediatamente en vez de diferidas. Omitir las cancelaciones y su vínculo con churn no modifica ninguna K óptima de este barrido. **Esto NO demuestra que cancelaciones y churn sean irrelevantes en negocios o shocks más extremos**: su dinámica puede importar fuera de estas políticas y ventanas; tampoco estima si esos procesos podrían identificarse en datos reales.

El modelo mínimo sigue utilizando cartera de clientes, backlog, erosión de capacidad ratio_p con parámetros ya ajustados, costos y estado predecisión observados. No es un sistema de una sola ecuación y no descubre por sí solo el mecanismo.

## Ejemplos de una misma decisión bajo incertidumbre

Brazo sin ruido, referencia completa A11; se evaluaron 201 shocks por banda:

| Shock central | Completo nominal (K) | Completo robusto (K) | Mínimo nominal (K) | Mínimo robusto (K) | Mayor regret bajo referencia: completo robusto / mínimo robusto |
|---|---:|---:|---:|---:|---:|
| 50 | 170 | 180 | 175 | 185 | 3,732 / 4,532 |
| 70 | 195 | 205 | 195 | 210 | 5,463 / 5,782 |
| 90 | 215 | 235 | 220 | 240 | 7,177 / 7,977 |

Se eligen capacidades mayores bajo minimax porque, en estos escenarios, subestimar demanda cuesta más que sobredimensionar ligeramente. La protección tiene un **costo nominal**; no es una mejora gratuita.

## Caveat más importante: decisión y pronóstico son dos productos distintos

Al cobrar de inmediato las ventas futuras, el esqueleto desplaza fuertemente la caja estimada. El error absoluto medio en caja pronosticada de la política nominal mínima es **32,223.54**, aunque el regret medio de su **decisión** sea solo 345.60. El dinero previsto por modelos con distinta temporización contable no se compara entre sí directamente; la K seleccionada se evalúa siempre bajo la misma referencia completa.

Un modelo puede servir para **elegir bien una capacidad** y servir mal para **prever liquidez**. No se debe convertir este resultado en una afirmación general de precisión económica.

## Interpretación epistemológica

1. **Resultado exploratorio, no WORLD adjudicado:** la referencia es el ajuste ratio_p de A11 (que se aproximó al WORLD original), no una nueva intervención contra el generador independiente.
2. **Estructura privilegiada:** el modelo mínimo conserva el driver correcto, los parámetros dinámicos aprendidos de A11 y las demás ecuaciones empresariales conocidas; no hemos probado extracción de estructura por LLM ni sd-ai.
3. **Reglas de riesgo:** minimax-regret usa el propio candidato para elegir; ningún modelo simple ve resultados de la referencia antes de escoger K.
4. **Perturbación exógena:** ±25% sobre shock futuro es una convención exploratoria, no una distribución medida; la media de 201 shocks no es esperanza económica.
5. **No confundir interpretación:** A14 prueba una simplificación *concreta* (principalmente cobranza), no que cualquier SD mínimo preserve decisiones. Tampoco demuestra que la simplificación baste para riesgo de caja, inventario o crédito.

## Próximo paso que A14 deja abierto

En una panadería real sería necesario decidir primero la **pregunta de decisión**: capacidad, horario, inventario, exposición a quiebra o liquidez. Estos objetivos pueden exigir modelos de distinta complejidad. Para medir CEI-SD frente a una alternativa convencional, el siguiente estudio debe analizar si un sistema puede reconstruir **relaciones necesarias** con observables parciales, no solo qué simplificación funciona después de haberle dado los parámetros del mecanismo.

**Conclusión limitada:** en la familia G5, bajo decisión única de capacidad orientada a caja pre-flujo t24, un SD simplificado con driver dinámico dado y una política minimax robusta conserva gran parte de la calidad decisional del completo, aunque sacrifica precisión monetaria sustancial.