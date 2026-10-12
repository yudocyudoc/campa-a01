# A13 · Matriz exploratoria de arrepentimiento por fuente de error

**Pregunta:** ¿qué errores del modelo afectan más a la decisión de capacidad del sistema empresarial W016? Se distinguen omisión del driver, confusión entre familias, coeficientes conocidos del negocio mal estimados y desconocimiento de la demanda futura.

## Estatuto científico

- **Exploratorio, posterior a A12**: sin nuevo gate, sin umbral de materialidad y sin escoger después el shock más favorable.
- Referencia contrafactual: la familia ratio_p ajustada y congelada en A11, por brazo. **NO se presenta como verdad WORLD ni se adjudica contra WORLD.** 
- Objetivo: caja al inicio de t24; menú fijo K90, K95, ..., K260.
- Se recorren los nueve shocks 20..100 de A12 y los dos brazos (sin ruido y ruido 1%). Los resultados particulares de shock 70/80 son post hoc, ya señalados por A12.
- Antes de modificar ningún supuesto, el código reconstruye las **1,260 predicciones archivadas de A12** y las compara con su CSV original.
- Se conservan la historia predecisión, las ecuaciones empresariales estipuladas y los ajustes A11 congelados. No se reentrena ningún modelo.

## Perturbaciones de una en una

1. **Familia funcional:** decidir con el ajuste diff_c; evaluar bajo ratio_p nominal.
2. **Omisión del driver:** decidir usando ratio_p pero con gain=0; evaluar bajo ratio_p nominal.
3. **Coeficientes estipulados:** modificar individualmente cada una de las 13 entradas de BUSINESS por ×0.50, ×0.75, ×1.25 y ×1.50. Afectan solo a la simulación futura, no al snapshot histórico.
4. **Demanda futura:** pronosticar con shock×0.50, ×0.75, ×1.25 o ×1.50 y evaluar en el shock nominal.

En cada caso se optimiza K con el modelo erróneo y se evalúa esa elección bajo la referencia nominal.

## Métricas

- Capacidad seleccionada, capacidad nominalmente óptima y diferencia entre ambas.
- **Arrepentimiento bajo referencia nominal:** caja nominal óptima menos caja nominal de la capacidad elegida.
- **Error de caja pronosticada** en la capacidad elegida y en la capacidad nominalmente óptima.

Un parámetro puede alterar mucho la caja prevista y aun así dar **arrepentimiento decisional cero** si no cambia la K seleccionada. Eso no implica irrelevancia económica.

Se genera cases.csv (matriz de escenarios), sources.csv (resumen por fuente) y summary.json (diseño, límites, verificación y hashes). Los promedios en el ranking son descriptivos sobre una rejilla artificial, **no expectativas económicas ni EVPI/EVPPI**: no se asignaron probabilidades de error.

## Barrera de información y límites

La ejecución CI utiliza sparse checkout solo del contrato A11, ajustes y estado congelados, predicciones A12 y código de A13. Verifica físicamente que el generador WORLD y los adjudicadores estén ausentes.

Las perturbaciones no son simultáneas. El gain=0 es una ablación deliberadamente sencilla, no un rival empresarial justo. Los coeficientes del negocio eran estipulados, no descubiertos. Una gran pérdida hipotética no prueba que una variable convenga investigarse primero: faltan incertidumbres empíricas, disponibilidad, costo y calidad de la información.

## Reproducir

Desde la raíz del repositorio, con Python 3.11 estándar:

    python -m unittest discover -s tests -p test_a13.py -v
    python -m experiments.A13.run --out results/A13

Los artefactos de GitHub Actions se conservan 30 días. El resultado interpretado se añadirá en RESULTS.md tras comprobar la ejecución.
