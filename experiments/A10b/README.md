# A10b · Robustez de A10 frente a diez semillas de ruido

**Pregunta cerrada:** ¿la decisión original `ratio_p` sigue favorecida cuando varía solamente la realización del ruido del 1% sobre capacidad efectiva?

## Diseño prospectivo y reproducibilidad

- **Diez semillas prefijadas:** 20261011–20261020. La primera reproduce el experimento A10 original a nivel de CSV público.
- **Sin alterar:** W016, los cinco regímenes TRAIN y 17 HOLDOUT, horizonte de 25 meses, familias `D−cK` y `D/K^p`, límites de parámetros, DE+TRF, escalas, ventana de evaluación, criterio de abstención RMS `0.005`, y ruido gaussiano con desviación típica `1%×K` solo en capacidad efectiva.
- **Control sin ruido** ejecutado en cada semilla, que debe permanecer idéntico.
- Reportar **10/10 decisiones**, incluidos los casos `diff_c` o `ABSTAIN_UNRESOLVED`, márgenes y errores holdout; nunca seleccionar semillas favorables a posteriori.
- **No** calibrar potencia estadística ni intervalos de confianza a partir de diez semillas.

## Cambio operacional de aislamiento

A10 anterior publicaba etiquetas selladas como artefacto desde el primer job, aunque el analista no las descargaba. A10b cambia la secuencia:

1. **Productor:** simula y publica únicamente datos observables (TRAIN completo; HOLDOUT con pedidos, capacidad y capacidad efectiva inicial). Verifica que la primera semilla coincide *byte a byte* con los tres CSV públicos históricos de A10. **No genera ni sube archivos de etiquetas selladas.**
2. **Analista:** job independiente con *sparse checkout* que carece de generador G5 y de código de adjudicación; ejecuta el **analista A10 original, sin modificación**, para las diez semillas. Entrega predicciones y decisiones, con SHA-256.
3. **Adjudicador posterior:** únicamente después de que el analista haya congelado los diez resultados, **vuelve a simular el WORLD** para generar por primera vez las etiquetas holdout. Verifica que los archivos públicos regenerados coinciden por hash, llama al adjudicador original de A10 y exporta la distribución íntegra de decisiones.

El conocimiento histórico de W016 en el repositorio público sigue siendo una limitación epistemológica. La mejora es específica: **no existe artefacto de etiquetas reservado disponible durante el job de análisis**. No es cegamiento causal.

## Qué se mide

Frecuencia de `ratio_p`, `diff_c` y `ABSTAIN_UNRESOLVED` con ruido; mínimo, mediana, máximo y media del margen de entrenamiento; RMS fuera de muestra por semilla y familia, y número de escenarios previstos como inactivos.

La simulación sigue recibiendo pedidos futuros observados y endógenos. Por tanto **sigue siendo reconstrucción condicional, no una predicción autónoma del campo bajo intervención**.

## Evidencia

Los archivos de entrada, predicciones congeladas, resultados de adjudicación y etiquetas regeneradas se conservan como artefactos de GitHub Actions. Una vez verificadas las ejecuciones, los archivaremos en el repositorio con SHA-256 para que no caduquen.
