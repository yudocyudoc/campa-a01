# A14 · Esqueleto SD mínimo × elección robusta de capacidad

**Pregunta exploratoria:** ¿cuánto valor decisional del simulador G5 completo conserva un modelo deliberadamente más sencillo? ¿Puede una decisión de capacidad minimax-regret, frente a incertidumbre en un shock futuro de demanda, compensar parte de esa simplificación?

## Matriz 2×2 principal

| Modelo candidato | Capacidad nominal | Capacidad robusta |
|---|---|---|
| Completo (A11.contract, ratio_p congelado) | Referencia nominal | Benchmark robusto condicionado al modelo completo |
| Mínimo (erosión, demanda, backlog y costos; sin cancelaciones, churn inducido ni demora de cobro nuevo) | ¿Cuánto se pierde al simplificar? | ¿La robustez compensa el error estructural? |

Tres ablaciones adicionales permiten identificar qué parte del esqueleto explica las diferencias:

- no_cancellations: elimina cancelaciones (y por consecuencia churn inducido por cancelación), preserva cobranza detallada.
- no_churn_feedback: mantiene cancelaciones pero elimina su efecto en el número de clientes.
- immediate_collections: mantiene el negocio intacto salvo cobro instantáneo de pedidos *nuevos*, con cobro amortizado de cuentas por cobrar históricas t8.

No se vuelven a estimar tau, rate, gain y shape: incluso el modelo mínimo retiene el driver ratio_p congelado de A11. Este ejercicio NO demuestra recuperación automática del mecanismo.

## Política y evaluación

- Dos brazos de A11; nueve shocks nominales de A12 20..100; 35 capacidades K90..K260 cada cinco.
- Incertidumbre futura: ±25% del shock nominal; 201 shocks equiespaciados incluyendo límites y nominal. Los puntos no son probabilidades.
- Regla nominal: escoger K que maximiza la caja prevista a inicio de t24 bajo el modelo candidato y shock nominal.
- Regla minimax-regret: calcular por K el mayor arrepentimiento en esos 201 shocks **bajo el propio candidato**, y escoger la K cuyo máximo es menor; empates a 1e-6: menor K.
- Una vez que cada candidato escoge ambas K, evaluarlas contra el **mismo modelo completo A11 ratio_p nominal**: regret en shock central; peor regret en banda; media no probabilística sobre la rejilla; sesgo de predicción.
- El candidato simplificado no puede consultar al modelo completo para elegir K. El completo funciona como benchmark teórico condicionado y como evaluador de decisiones.
- Todas las curvas completas de los 630 casos ratio_p archivados en A12 se reproducen previamente, tolerancia 1e-7.

## Esqueleto contable

Se conservan cartera de clientes, backlog, driver de erosión, capacidad efectiva, demanda endógena y costos operativos. No se cancela backlog ni se aplica churn por cancelaciones; sí permanece churn fijo.

En la variante inmediata, la cartera histórica de cuentas por cobrar t8 se recupera al retardo conocido y se extingue sin entradas nuevas; las ventas posteriores se cobran en el mismo período. Ese ingreso de cuentas históricas es independiente de K. Las curvas monetarias estimadas por modelos con distinto cobro no son directamente comparables en nivel absoluto: se comparan únicamente las capacidades elegidas y su caja evaluada por el modelo completo.

## Límites

Exploratorio tras A13, sin WORLD, sin nuevo gate, sin reentrenamiento y con coeficientes conocidos por construcción. No hay datos de una panadería real. Un modelo que recomienda bien bajo ratio_p no necesariamente lo hace bajo otro generador.

El modelo mínimo conserva parámetros de mecanismo ya ajustados, por tanto **no** es un agente descubridor de estructura, ni un baseline empresarial convencional competitivo. El sistema de estados y la separación de ablations son hipótesis de diseño explícitas.

## Reproducir

Ejecutar en la raíz del repositorio con Python 3.11 estándar:

    python -m unittest discover -s tests -p test_a14.py -v
    python -m experiments.A14.run --out results/A14

El resultado comprende 180 filas de políticas (2 brazos × 9 shocks × 5 modelos × 2 reglas) en policies.csv, diez filas resumidas en summary.csv y summary.json con hashes y limitaciones. La evidencia permanente se archivará después de reproducirla y revisarla; artefactos Actions duran 30 días.
