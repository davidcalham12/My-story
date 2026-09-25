# Anexo J — Demo del cambio del lector (v3)

El lector cambia **un hecho** y solo se reescriben los capítulos que lo usan. Es la
evidencia obligatoria nº 3 de la presentación.

## El cambio

- Hecho 36: **"the cardboard observatory"** → **"the wooden treehouse observatory"**.
- `fact_usage` dice qué capítulos lo usan: **3 y 10**. Solo esos se reescriben; el resto
  del libro se toma tal cual de la v2.
- Resultado: **v3**, hija de **v2**, publicada el
  2026-09-24T21:34:49Z. La v2 no se toca: cada versión se escribe una sola vez.
- El PDF abre con la página **"What changed"**, que enlaza a los capítulos reescritos:
  `ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`.

## Un cambio que no llega no es un cambio

El primer capítulo 3 pasó las seis características **sin mencionar el observatorio**:
ningún crítico comprueba que el hecho cambiado esté. Desde `e0b7c38` se comprueba en
código antes de aceptar: la frase nueva debe aparecer y ninguna variante de la vieja
(mayúsculas, plural, artículo; la frase, no la palabra). No es una séptima
característica: es la condición de aceptación del cambio del lector.

| capítulo | "wooden treehouse observatory" | comprobación |
|---|---|---|
| 3 | 2 | OK |
| 10 | 1 | OK |

## Lo que costó

| # | tipo | detalle | total | min | orquestador |
|---|---|---|---|---|---|
| 3 | reader_change | dist/_aborted-change-1 | no medido | — | — |
| 4 | reader_change | dist/_aborted-change-2 | 7,52 $ | 25,8 | claude-opus-5[1m] |
| 5 | reader_change | dist/v3 | 4,57 $ | 19,5 | claude-sonnet-5 |
| 6 | redo | dist/v3 _redo-20260924T212801Z | 1,50 $ | 6,7 | claude-sonnet-5 |

Los intentos sin versión son evidencia, no se borran: uno cortado por el límite de gasto
de la organización (en Opus) y uno detenido por el operador sin stream conservado.
