# A02 · Reproducir el C0.0 fundacional

**Estado:** experimento de reproducibilidad; no es un hallazgo causal nuevo.

## Pregunta

¿La campaña pública puede volver a ejecutar, sobre un runner Linux limpio y con BPTK-Py 3.2.0, el primer mundo de CEI C0.0 y obtener las mismas conclusiones operativas y valores numéricos que el cuaderno original?

## Fuente histórica congelada

- Repositorio: [yudocyudoc/c0.0](https://github.com/yudocyudoc/c0.0)
- Archivo: [CEI_C0_0_SD_Grafo_Colab.ipynb](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_SD_Grafo_Colab.ipynb)
- Commit fuente: `d90ff87ba47572edd7d2084ecdc62dfba54cd14d`
- Git blob fuente: `fc66a1c85031c62243d24c03965ec849391bb371`
- Registro histórico: 14 checks `True`, verificados al final del cuaderno ejecutado; salida `C0.0: PASS`.

## Alcance y transformación

`c00_source_reproduction.py` conserva las celdas de código analítico del cuaderno, en orden; excluye únicamente instalación propia de Colab, visualizaciones puramente ilustrativas y presentación de una ruta ya identificada. No modifica ecuaciones, condiciones, valores, escenarios, relaciones ni los 14 criterios originales. Se cambia la ruta de exportación `/content/cei_c00_outputs` por `CEI_A02_RESULTS_DIR` y se añade una impresión equivalente para las vistas tabulares de Jupyter.

El mundo contiene cinco stocks: `customer_base`, `backlog`, `maintenance_debt`, `receivables`, `cash`. Compara el efecto de marketing, capacidad y mantenimiento sobre backlog y caja. El grafo diferencia la representación del agente del mundo sintético.

## Qué compara la verificación

1. Los **14 checks originales**, por identidad y resultado.
2. **12 anclas numéricas** reproducidas de la tabla archivada de cinco escenarios; tolerancia absoluta 0.001 o relativa 1e-6, nunca ajuste.
3. Los archivos de evidencia CSV/GraphML, junto con un manifiesto `reproduction.json` con SHA-256 de cada artefacto.

Una discrepancia se registra como `NOT_REPRODUCED` y provoca fallo del job; los archivos disponibles se publican también cuando hay errores.

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4"
CEI_A02_RESULTS_DIR=results/A02 MPLBACKEND=Agg python experiments/A02/c00_source_reproduction.py
python experiments/A02/verify_reproduction.py --input results/A02
```

La ejecución automática se activa por modificaciones de A02 en un pull request. También puede lanzarse desde Actions al integrar el workflow a la rama principal.

## Limitaciones

El mundo verdadero está público y se ejecuta deliberadamente: A02 prueba reproducción técnica y numérica. No puede utilizarse para adjudicar generación ciega de mecanismos por un LLM. Tampoco modifica ni resuelve los fallos de generalización detectados posteriormente en G5 ni la identificabilidad adversarial de G6.
