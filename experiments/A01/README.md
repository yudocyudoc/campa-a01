# A01 · Prueba de arranque reproducible

**Pregunta:** ¿Puede GitHub Actions ejecutar un experimento Python independiente, verificar sus invariantes y conservar resultados descargables?

**No es una prueba de descubrimiento causal ni una reproducción de c0.0.** Los dos mecanismos son ejemplos escritos manualmente: producción fija y producción dependiente de demanda. Se simulan con las mismas cantidades y una perturbación inicial común de +10 panes.

## Ejecutar localmente

Requiere Python 3.11 o posterior; no instala paquetes ni consume APIs.

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python experiments/A01/experiment.py --out results/A01
```

Se generan `results/A01/manifest.json` y `results/A01/trajectories.csv`. La carpeta `results/` no se versiona: el workflow publica sus archivos como artefacto asociado a la ejecución.

## Criterio de aprobación

Los tests pasan, el manifiesto declara cuatro escenarios con sus huellas y el CSV se publica. Las curvas distintas solo demuestran que las reglas ilustrativas se comportan de manera diferente.

## Qué sigue después

Integrar una reproducción de **un** experimento existente de `c0.0` con BPTK-Py, conservando entradas y resultados originales. Evaluar la reproducibilidad antes de construir una nueva campaña científica.
