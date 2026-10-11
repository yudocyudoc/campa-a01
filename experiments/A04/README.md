# A04 · Reproducción de la auditoría histórica A1

**Naturaleza:** auditoría metodológica reproducida, no una nueva validación científica.

## Por qué hacemos A04 después de A03

En A03 reproducimos G5 sobre 40 mundos: 15 aciertos conjuntos de feature + clase, 25 errores, y 0 abstenciones. Aunque 34/40 identificaron la clase dinámica, 19 se equivocaron en la *feature* con la clase correcta.

Para comprender los antecedentes de esa dificultad, recuperamos **A1**, que había investigado las equivalencias entre mecanismos y relaciones, el leakage/proxy del target y la fuerza de las intervenciones.

**Advertencia de alcance:** A1 es una auditoría del antiguo **G4, con 12 mundos y 57 expresiones**, no de G5 y sus 40 mundos. Sus hallazgos sugieren mecanismos de falla, pero **no explican por sí solos ni cuantifican los 25 errores de G5**.

## Fuente congelada

- [Cuaderno A1 original](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_A1_Auditoria_Identificabilidad_Leakage.ipynb)
- [Cuaderno A1 ejecutado](https://github.com/yudocyudoc/c0.0/blob/d90ff87ba47572edd7d2084ecdc62dfba54cd14d/CEI_C0_0_B1_SD5_A1_Auditoria_Identificabilidad_Leakage_ejecutado.ipynb)
- Commit: `d90ff87ba47572edd7d2084ecdc62dfba54cd14d`.
- Blob del original: `458e12ed39404a3c13b4cd2c3105be78c0b2ee7b`.
- Blob ejecutado: `65c05c3e4e7bb7a5c2de9aa37e0ff11927fa16be`.

El runner `a1_source_reproduction.py` conserva **17 celdas analíticas** en el orden original: no modifica ecuaciones, mundos, gramáticas, parámetros, probes ni umbrales. Únicamente omite la instalación/reinicio propios de Colab, transforma `display()` a salida compacta y redirige `/content` a `results/A04`.

## Preguntas auditadas en A1

1. ¿La clase `reinforcing` se superpone matemáticamente con `smooth_delay` cuando su ganancia neta es amortiguadora?
2. ¿Qué separabilidad queda frente a rivales usando todos los probes del experimento anterior, sin reajustar?
3. ¿Qué features son casi equivalentes como señales?
4. ¿Qué features incorporan directamente el target `effective_capacity` o lo aproximan por saturación?
5. ¿Difiere la separación entre el segundo candidato global y la mejor hipótesis de **otra clase**?
6. ¿Cuántos probes tienen poder real para distinguir finalistas?

## Registro histórico que A04 comprueba

| Diagnóstico del cuaderno A1 | Referencia |
|---|---:|
| Mundos G4 | 12 |
| Expresiones | 57 |
| Grid reinforcing como primer orden estable | 12 |
| Grid reinforcing con refuerzo neto | 4 |
| Pares de features casi equivalentes | 204 |
| Features dependientes directamente del target | 3 |
| Mundos donde clase verdadera es mejor con todos los probes | 9/12 |
| Casos auditados | 12 |

La comprobación exige además identidad de las tres features con dependencia directa, tres mundos por clase, tablas para los 12 mundos y todas las salidas auxiliares. El verificador no acepta cambios de criterio para conseguir coincidencia.

**A1 nunca emitió un PASS/FAIL científico.** Por eso separamos dos resultados:
- `reproduction_status = REPRODUCED / NOT_REPRODUCED`: se reprodujo el cuaderno o no
- `scientific_verdict = NOT_ISSUED_ORIGINAL_A1_IS_DIAGNOSTIC`: el cuaderno es diagnóstico, no adjudicador de causalidad

## Ejecutar

```bash
python -m pip install "setuptools<82" "jedi>=0.16" "bptk-py[plotting]==3.2.0" "networkx>=3,<4"
CEI_A04_RESULTS_DIR=results/A04 MPLBACKEND=Agg python experiments/A04/a1_source_reproduction.py
python experiments/A04/verify_reproduction.py --input results/A04
```

El workflow público se activa en el pull request y archiva CSV y `reproduction.json` por 30 días, incluyendo evidencia en caso de discrepancias.

## Después de A04

Si A04 reproduce A1, la siguiente pregunta no es si cambiamos los modelos para forzar un buen porcentaje, sino **qué aspectos de equivalencia, confusión de feature y leakage se mantienen al pasar de G4 a los 40 mundos de G5 corregido**. Eso requeriría una comparación separada, nunca atribuir automáticamente a G5 los hallazgos de G4.
