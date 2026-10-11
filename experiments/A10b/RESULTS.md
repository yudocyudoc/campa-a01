# A10b · Robustez frente a diez realizaciones del ruido observacional

**Primera campaña completa de referencia:** [GitHub Actions 38182540105](https://github.com/yudocyudoc/campa-a01/actions/runs/38182540105).  
**Diseño sin cambios respecto de A10:** W016, cinco escenarios TRAIN, 17 HOLDOUT, familias `diff_c` y `ratio_p`, DE+TRF y umbral de abstención `0.005`.  
**Semillas predefinidas:** `20261011` a `20261020`; ruido gaussiano de desviación típica **1% de K**, agregado únicamente a la capacidad efectiva observada, con clipping físico.  
**Evidencia permanente:** [164 archivos originales](evidence/) separados por frontera (41 públicos, 31 del analista y 92 de adjudicación/regeneración), con [manifiesto de hashes SHA-256](evidence_manifest.json) y verificación cruzada contra la corrida ejecutada. El workflow de archivado con escritura fue eliminado.  
**Lectura epistemológica:** frecuencias descriptivas bajo una familia verdadera conocida y anidada. Ni identificación causal general ni previsión de una intervención endógena.

## Resultado principal (condición con ruido)

| Indicador de las diez ejecuciones | Resultado |
|---|---:|
| Decide `ratio_p` | **10/10** |
| Decide `diff_c` | **0/10** |
| Se abstiene | **0/10** |
| Margen RMS TRAIN: mínimo | **0.007598** |
| Margen RMS TRAIN: mediana | **0.008961** |
| Margen RMS TRAIN: máximo | **0.010070** |
| Umbral de abstención sin modificación | **0.005000** |

El menor margen está por encima del umbral, por lo que **ninguna** de las diez semillas cambió la decisión ni obligó a abstenerse. La primera semilla, `20261011`, reprodujo byte-idénticamente los tres CSV públicos de A10. No se eligieron semillas después de observar el resultado.

## Calidad de predicción en los 17 holdouts sellados

**RMS de fracción de capacidad efectiva observada**, tras recalcular las etiquetas *después* de congelar las predicciones:

| Resumen entre semillas | `ratio_p` | `diff_c` |
|---|---:|---:|
| Mínimo | 0.007150 | 0.018748 |
| Mediana | **0.008671** | **0.020876** |
| Máximo | 0.009164 | 0.021336 |
| Media | 0.008345 | 0.020591 |

El resultado de cada semilla, incluidos el margen de decisión y los RMS individuales, figura en `all_seed_scores.csv` y `A10b_summary.json`. Los parámetros `ratio_p` tuvieron `p` entre **0.993698 y 1.006347**, alrededor del valor 1 incluido por construcción en la biblioteca de candidatos. No interpretamos ese rango de diez ajustes como intervalo de confianza.

El analista también predijo que **siete de 17 escenarios** mantendrían inactivos ambos modelos durante toda la ventana evaluada, en las diez semillas. Sigue siendo un resultado del **mismo mundo W016**, no una validación en nuevos mecanismos.

## Qué se modificó respecto de A10

**Solo la realización del ruido y el acceso a las etiquetas.**

1. **Productor:** publica TRAIN observable y HOLDOUT con pedidos/capacidad/condición inicial; verifica el CSV original de A10. **No crea ni publica archivos sellados**, por lo que el analista no puede descargar un artefacto de etiquetas todavía inexistente.
2. **Analista:** *sparse checkout* de A10 `contract.py` y `analyst.py` sin modificación; ejecuta el mismo optimizador y umbral para cada semilla. Congela los diez reportes y las predicciones completas antes de continuar.
3. **Adjudicador:** solo entonces ejecuta el generador conocido, reconstruye etiquetas, verifica que la regeneración reproduce por SHA-256 los datos públicos y adjudica **todas** las decisiones, incluidas las negativas. Registra el resultado sin ningún reajuste.

Esta separación mejora la **barrera procedimental de acceso**. No equivale a cegamiento criptográfico absoluto ni elimina el conocimiento histórico de W016 en el código público.

## Qué no podemos concluir

- Diez semillas de una única intensidad de ruido **no** establecen potencia estadística, estabilidad frente a ruido correlacionado o extrapolación a distintos mundos.
- `D/K^p` **incluye** la ecuación verdadera cuando `p=1`, y los rivales fueron diseñados previamente.
- Los pedidos futuros de los holdouts siguen siendo **covariables observadas y endógenas**: A10b mide reconstrucción condicional, no la anticipación del efecto de cambiar la capacidad.
- No se evaluaron fallos donde toda la biblioteca de hipótesis es falsa; que un candidato gane entre dos no garantiza identificación causal.

**Veredicto acotado:** A10 es **estable frente a las diez realizaciones predefinidas del 1% de ruido** para W016: recupera la familia anidada con margen superior al criterio de abstención y mantiene menor error fuera de muestra. La próxima frontera científica continúa siendo una intervención prospectiva donde el analista no conozca los pedidos futuros.
