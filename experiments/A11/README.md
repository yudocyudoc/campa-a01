# A11 · Primera intervención prospectiva en campo endógeno

**Pregunta:** con datos históricos y el estado disponible antes de una decisión, ¿puede el analista escoger una política de capacidad e **imaginar los pedidos futuros endógenos** sin que el WORLD se los entregue? ¿Qué tan cerca queda del mejor cambio de capacidad del menú y del no-cambio?

## Diseño congelado

- Caso sintético conocido: W016 de G5, mecanismo interno `first_order_relaxation`.
- Datos de aprendizaje: exactamente cinco regímenes históricos públicos de A10, observados hasta t24. Dos brazos: sin ruido y medición de capacidad efectiva con ruido de 1% en los historiales.
- Nuevo escenario de decisión: capacidad base **115**, estado inicial observable al momento **t8**, shock de mercado exógeno **+50 pedidos desde t8** conocido en el plan. **No se entregan pedidos futuros**, backlog futuro, cancelaciones futuras ni caja futura.
- Acciones disponibles (t8 a t24): mantener capacidad nominal **90, 115, 145 o 180**. La base de comparación es 115. La selección precomprometida maximiza **caja al inicio de t24**; desempata a favor de menor capacidad.
- Modelo de respuesta: ambas familias de A10 `orders−cK`, `orders/K^p`; parámetros ajustados por `A10.optimize` SIN CAMBIAR límites, starts, semilla, objetivo, optimizador ni criterio de abstención 0.005. Si se abstiene, acción **no cambiar capacidad** (115).
- **Conocimiento compartido explícito:** el analista recibe las ecuaciones y coeficientes del negocio (pedidos desde base de clientes, adquisición/churn, acumulación de backlog y cancelaciones, cobranza, costos). **Solo el driver dinámico y sus parámetros se ajustan**. Esto es comprobación prospectiva condicionada a que el modelo de negocio sea conocido, no inferencia ciega de todas las ecuaciones empresariales.

## Separación técnica y epistemológica

1. **Productor:** copia los cinco historiales A10 y genera solamente el **estado previo a actuar en t8**: stocks observables de clientes, backlog, cuentas por cobrar y caja, junto con pedidos/capacidad efectiva del instante anterior. No genera ni exporta ninguna trayectoria futura de intervenciones.
2. **Analista aislado:** checkout limitado sin W016, generador ni adjudicador. Reajusta ambos drivers con TRAIN observable, reconstruye el estado de impacto para t8 desde la capacidad observada en t7 **solo si no estaba clipeada** y avanza las ecuaciones empresariales con pedidos internos pronosticados por retroalimentación. Congela una predicción para cada una de las cuatro políticas y ambas familias, y su elección.
3. **Adjudicador:** exclusivamente después de recibir el artefacto congelado, genera por primera vez cuatro contrafactuales WORLD de G5 con shock idéntico y capacidad modificada en t8–24. Comprueba hashes, t8 stock común, errores de series, caja final, arrepentimiento de decisión y ganancia frente a no actuar.

La regla de reconstrucción del estado latente depende de un observable anterior sin saturación; si esta condición falla, el experimento **debe detenerse sin inventar un estado**.

## Qué constituye éxito o fracaso

No hay regla retrospectiva que fuerce éxito. El resultado informa:
- Familia escogida desde entrenamiento o abstención.
- Acción de capacidad elegida antes de consultar WORLD.
- RMS de pedidos (verdaderamente endógenos), capacidad efectiva, backlog, clientes y caja para las **cuatro políticas**, con datos de t8 a t24.
- Dinero real de la caja t24 para acción elegida, mantenimiento y mejor acción del menú conocida solo en adjudicación.
- **Regret** = caja del mejor del menú − caja de la acción seleccionada; valor positivo significa decisión subóptima. No se confunde bajo error de pronóstico con buen resultado decisional.

## Limitaciones

- El simulador, las ecuaciones empresariales y los coeficientes públicos siguen basándose en el mismo modelo G5. **No hay descubrimiento independiente del feedback**; el analista recibe explícitamente la estructura del negocio.
- La familia `ratio_p` incluye el mecanismo verdadero (p=1). W016 es un mundo públicamente conocido. Un mejor resultado no demuestra causalidad generalizable.
- Se conoce la magnitud del **shock exógeno** y la política de capacidad; lo que se prohíbe son los **pedidos futuros endógenos**.
- Dos condiciones de historia (con y sin ruido), no diez semillas nuevas; A10b ya las auditó.
- Las opciones se limitan a cuatro cambios de capacidad y un horizonte finito; la caja t24 es una función objetivo artificialmente simplificada.
- No se demuestra identificabilidad global ni extrapolación a una empresa real.

**Evidencia:** archivada en tres artefactos separados: pre-decisión, predicciones congeladas, adjudicación futura (se copiarán a Git con hashes una vez verificadas).
