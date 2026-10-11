# A10 · Analista observacional con resultados de evaluación sellados

**Pregunta:** ¿podemos reconocer cuándo dos modelos producen predicciones distintas y escoger o abstenernos **usando solo señales empresariales observables**, sin consultar los estados latentes del WORLD?

Este es un paso respecto a A09, que utilizó `hidden_excess`, `primitive_impact` y stocks internos del generador. **A10 no es descubrimiento causal independiente:** el dominio, los modelos candidatos y el generador sintético W016 están disponibles en el repositorio público. La barrera es **operacional/de ejecución**, no un cegamiento epistemológico frente a un investigador que ya conoce W016.

## Barrera de información real entre jobs de GitHub Actions

1. **Productor** (conoce WORLD): simula W016 en los mismos 5 regímenes TRAIN y 17 HOLDOUT de A08. Empaqueta exclusivamente una lista blanca de series observables: pedidos, capacidad nominal y efectiva, backlog, cancelaciones, clientes y caja. Genera dos condiciones: sin ruido y ruido gaussiano de medición equivalente al 1% de K **solo en capacidad efectiva**, acotado a la región física. Comparte TRAIN completo; de HOLDOUT comparte solo pedidos/capacidad y capacidad efectiva inicial del mes cero.
2. **Analista** (checkout limitado a `contract.py` y `analyst.py`): recibe el archivo **público**, jamás las etiquetas de capacidad efectiva de HOLDOUT ni la fuente del WORLD en su árbol de trabajo. Ajusta con TRAIN dos candidatos `orders−c·capacity` y `orders/capacity^p`, con tres parámetros dinámicos efectivos y uno de forma. Los optimiza con DE más tres refinamientos, fija una decisión (incluyendo `ABSTAIN_UNRESOLVED`) **desde TRAIN**, pronostica condicionalmente capacidad efectiva de todos los 17 escenarios y anticipa regiones activas o clipeadas según **los modelos candidatos**, no según estados internos del WORLD.
3. **Adjudicador** (job posterior): recibe la predicción congelada, el archivo público y las etiquetas selladas; verifica hashes y orden de entrega, calcula RMS fuera de muestra y el desempeño de una predicción de capacidad nominal constante.

Todos los resultados, incluidos posibles errores, empates y abstenciones, se registran. **El pipeline no ajusta nada a etiquetas holdout**.

## ¿Qué observa y qué calcula el analista?

Entrada: `incoming_orders`, `nominal_capacity`, `effective_capacity`, `backlog`, `cancellations`, `customer_base`, `cash` para TRAIN. En holdout, de estas variables el analista únicamente recibe **pedidos, capacidad nominal y capacidad efectiva inicial**.

Respuesta de cada candidato: dinámica condicional de primer orden sobre fracción de capacidad:

```text
z[0] = max(0, 1 − effective_capacity[0]/K[0])    # condición inicial observada
force[t] = g × max(feature(D[t],K[t]) − tau,0)
z[t+1] = (1−a)z[t] + a·force[t]
C_pred[t] = K[t] × max(1−z[t], minimum_fraction)
```

Se reporta `minimum_fraction=0.40` como una **regla de operación suministrada**. No se lee `hidden_state` ni `primitive_impact`.

La elección entre familias se basa en el error de entrenamiento sobre fracciones `effective_capacity/K` en meses 8–24. Una ventaja de RMS no mayor de 0.005 produce `ABSTAIN_UNRESOLVED`, como **umbral práctico no calibrado**. Además se reporta discrepancia temporal entre modelos y predicción de clipping por candidato.

## Límites importantes

- **Las órdenes de holdout son observadas, no pronosticadas.** En G5 dependen endógenamente de los resultados empresariales. Por ello este experimento comprueba capacidad de *reconstrucción condicional de entrada/salida*, **no** anticipación de contrafactuales ni respuesta autónoma a intervenciones futuras.
- El candidato `orders/K^p` incluye al generador sintético exacto si `p=1`. Un resultado favorable no demuestra causalidad independiente.
- El analista conoce de antemano la estructura de primer orden, las dos familias candidatas y el piso físico de capacidad. No descubre una gramática desconocida.
- El ruido de 1% se agrega únicamente a la capacidad efectiva observada, no a pedidos ni capacidad nominal, y no reproduce sistemas reales de medición ni permite hablar de potencia estadística.
- Clasificar regiones informativas usando las predicciones candidatas puede fallar si ambas hipótesis están equivocadas; la concordancia con la verdad se mide únicamente en el adjudicador.
- GitHub publica históricamente el código generador: el checkout restringido es una **disciplina operacional**, no una garantía criptográfica de desconocimiento de W016.

## Evidencia de CI

- `a10-public-observations`: entrenamiento observable y covariables de evaluación, sin estados latentes ni resultados posteriores a t0 de holdout.
- `a10-analyst-predictions`: parámetros ajustados, decisiones previas a evaluación, predicciones y clasificación candidata de regiones informativas.
- `a10-sealed-labels`: etiquetas holdout ocultas al analista.
- `a10-sealed-adjudication`: métricas de evaluación y línea base.

Se conserva la opción de abstención como resultado válido. No reinterpretar las etiquetas históricas de A03–A09.
