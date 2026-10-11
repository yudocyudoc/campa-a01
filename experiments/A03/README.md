# A03 · Reproducción histórica de CEI C0.0 / SD5-G5

## Pregunta

¿Puede el laboratorio público **reproducir** el benchmark de 40 mundos de C0.0 SD5-G5, incluidas sus equivocaciones, sin recalibrar reglas, parámetros ni criterios?

No se intenta mejorar el resultado de G5, ni afirmar que G5 demuestre causalidad.

## Fuente y adaptación

- Fuente: [c0.0 — G5, cuaderno sin ejecutar](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_G5_Benchmark_Corregido_40_Mundos.ipynb).
- Fuente de respuestas históricas: [G5 ejecutado](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_G5_Benchmark_Corregido_40_Mundos_ejecutado.ipynb).
- Commit congelado: `d90ff87ba47572edd7d2084ecdc62dfba54cd14d`.
- Git blob del cuaderno fuente: `730420a744d91d195ec1eca60ef3c4dd9468e063`.
- Referencia de 40 casos: `historical_reference.json`, extraída **literalmente** del log de la celda 16 del cuaderno ejecutado.

`g5_source_reproduction.py` concatena las **11 celdas de código científico** del cuaderno original en el mismo orden. Solo se omite la celda 3 de auto-instalación de Colab; `display()` produce texto breve y la ruta de exportación cambia a `CEI_A03_RESULTS_DIR`. No se cambiaron semillas, modelos, estimadores, parámetros, familias, presupuestos, criterios de aceptación ni evaluación.

## Anclas archivadas

| Métrica | G5 original |
|---|---:|
| Mundos sintéticos | 40, diez por familia |
| `COMMIT_CORRECT` | 15 |
| `COMMIT_WRONG` | 25 |
| `ABSTAIN` | 0 |
| Exactitud condicionada a compromiso | 37.5% |
| Pruebas medias por mundo | 2.275 |
| Pruebas informativas medias | 2.175 |
| Acuerdo de decisión CEI vs oráculo | 90% |
| Política constante de referencia | 90% |

La prueba automática **no acepta simplemente 15/25**: compara para cada uno de los 40 mundos la familia verdadera, familia seleccionada, variable explicativa y resultado con el archivo archivado. También comprueba seis controles de integridad y ocho valores numéricos agregados.

El resultado original fue desfavorable para la generalización: 62.5% de compromisos estructurales incorrectos. Reproducirlo es un resultado técnico positivo, no una mejora científica.

## Ejecución pública

Se ejecuta automáticamente sobre el pull request de A03 o manualmente desde GitHub Actions cuando el workflow está disponible en la rama principal.

Entorno: Ubuntu, Python 3.11 y BPTK-Py 3.2.0 (backend Rust disponible). El job tiene límite de 75 minutos para evitar consumo ilimitado de runner. Si falla, debe conservar la evidencia disponible en un artefacto del run; no se cambiarán los criterios históricos para forzar PASS.

## Interpretación

El G5 conserva riesgos y límites que posteriores auditorías A1/G6 estudiaron, incluyendo alias de mecanismos, leakage, dominio de parámetros y suficiencia de probes. **A03 no corrige ni reinterpreta G5**. Tras reproducirlo, será razonable decidir qué parte del diagnóstico científico vale la pena recuperar en A04.
