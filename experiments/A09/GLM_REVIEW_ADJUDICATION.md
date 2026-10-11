# A09 · Adjudicación post hoc de la revisión de GLM

**Naturaleza:** interpretación adicional del experimento A09, **sin recalcular, modificar o reetiquetar** los artefactos históricos. Una revisión externa (GLM) reportó reproducir byte-idénticamente los CSV y confirmar 16 comprobaciones independientes; la presente adjudicación se basa en las ecuaciones y la evidencia **ya conservadas** en el repositorio. No reejecuta BPTK-Py.

## 1. El modelo anidado reproduce exactamente los parámetros exigidos

Para W016 se define

```text
β = 0.75 + θ/4
f_WORLD(D,K) = 4·g_W·max(D/K − β, 0)
f_ratio_p(D,K) = g_p·max(D/K^p − τ_p, 0)
```

Con capacidades positivas, ambas funciones coinciden para **todos los D y K** cuando `p=1`, `τ_p=β`, `g_p=4·g_W`. Si además la tasa `a_p=a_W` y los estados iniciales son los mismos, sus dinámicas de primer orden coinciden. **Estas igualdades son suficientes para equivalencia en el modelo construido**; no certifican que la parametrización se haya descubierto ciegamente ni que sea única bajo observación parcial.

| Parámetro | WORLD exige | Mejor fit A08 de `ratio_p` | Desviación aproximada |
|---|---:|---:|---:|
| `p` | `1` | `0.9999999999999998` | `2.2e-16` |
| `τ` | `0.8043657644784502` | `0.8043657644784503` | `1.1e-16` |
| `a` | `0.6341171854167359` | `0.6341171854167389` | `3.0e-15` |
| `g` | `1.7582499650790180` | `1.7582499650790158` | `2.2e-15` |

La reproducción de WORLD por `ratio_p` en A08 es esperable porque `p=1` **contiene exactamente el modelo generador**. La coincidencia confirma la implementación y el ajuste numérico en un modelo anidado, no la identificación causal externa.

## 2. Lo que sí implica la obstrucción de pendientes

En regiones activas donde la respuesta latente es observable sin clipping y ambos modelos comparten la misma tasa de relajación, igualdad de las funciones de forcing en un intervalo abierto de demanda a cada K exige

```text
∂_D (g_W·u_W) = 4·g_W/K
∂_D (g_c·u_diff_c) = g_c
∂_D (g_p·u_ratio_p) = g_p/K^p
```

Con al menos dos capacidades diferentes y ganancia constante entre campos, `diff_c` no puede igualar simultáneamente `4·g_W/K`. Para la familia **específica** `ratio_p`, igualdad de pendientes en ambas K exige `p=1` y `g_p=4·g_W` (si K son positivos, distintos y ganancias son positivas). También hay que alinear umbrales y dinámica temporal para igualar el forcing y las trayectorias.

**Corolario condicionado, no regla universal de gramática:** un driver que aspire a esa equivalencia exacta necesita una **pendiente efectiva ponderada** que escale con `1/K` en las regiones activas del dominio. Esto NO significa que toda feature válida del CEI deba ser una razón, ni excluye otros mecanismos, otras transformaciones o factores dependientes del campo. Tampoco es suficiente por sí solo para identificabilidad de observaciones finitas, ruidosas o con clipping.

La ganancia del mejor `diff_c` (`0.0144565523`) cae entre las ganancias de pendiente exigidas a K115 (`0.0152891301`) y K145 (`0.0121258618`). Es **compatible** con un compromiso entre campos. Su posición intermedia no prueba que el RMS `0.016932808` sea un piso global: `tau`, `a` y la endogeneidad de pedidos también intervienen.

## 3. Corregir una lectura ambigua de la endogeneidad

En `evidence/summary.json`, `max_endogenous_input_gap_in_joint_active_samples = 1.851643254229458` incluye tanto TRAIN como HOLDOUT. Los valores calculados **directamente de `evidence/internal_trajectories.csv`**, emparejando WORLD y `diff_c` por `probe` y tiempo y filtrando `t≥8` con ambos activos y sin clipping, son:

| Partición | Instantes conjuntos activos y sin clip | Mayor diferencia absoluta de `incoming_orders` |
|---|---:|---:|
| TRAIN | 65 | **0.0234550684806720** |
| HOLDOUT | 82 | **1.851643254229458** |

El máximo global del JSON es correcto, pero su nombre puede ocultar esta diferencia. No modificar el summary histórico ni sus hashes: documentar la partición en este suplemento evita atribuir a TRAIN un extremo producido en HOLDOUT.

Las cuentas 35 observaciones K115 y 30 K145 son muestrales; no prueban variación de demanda sobre un intervalo abierto. `incoming_orders` sigue siendo **endógena** debido al feedback por cancelaciones y base de clientes.

## 4. Región activa no es equivalente a demostración para el dataset

En A09, WORLD y `ratio_p` registraron cada uno **176** tiempos activos/sin clipping y reprodujeron el comportamiento, pero esto es un control anidado.

Los siete HOLDOUT con RMS cero para `diff_c` fueron **inactivos para ambos modelos** en los instantes evaluados; no son siete pruebas independientes de igualdad causal. La saturación puede ocultar diferencias adicionales.

**Sigue sin demostrarse**: una cota inferior positiva de error adversarial sobre todo el espacio paramétrico admisible, observabilidad del estado latente desde datos externos, resistencia a ruido, ni descubrimiento causal ciego.

## 5. Próxima decisión científica

No modificar ni reinterpretar retrospectivamente la adjudicación original. Antes de un nuevo benchmark de 40 mundos, un camino pragmático sería diseñar un estimador **solo con variables observables** para detectar regiones informativas, con incertidumbre explícita. El corolario de pendiente puede motivar una intervención, pero no sustituye la comprobación de excitación, restricciones y ruido en un sistema desconocido.

## Procedencia exacta

- `experiments/A08/evidence/summary.json`: parámetros congelados y métricas de los dos rivales.
- `experiments/A09/evidence/summary.json`: proposición condicionada y soporte muestral.
- `experiments/A09/evidence/internal_trajectories.csv`: endogeneidad por partición.
- `experiments/A09/evidence_manifest.json`: SHA-256 de todos los datos históricos conservados.
