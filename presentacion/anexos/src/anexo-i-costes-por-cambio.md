# Anexo I — Costes por cambio y margen (Langfuse)

El coste de cada cambio hecho a la novela de ejemplo, leído de los eventos `result`
de Claude Code (medido) y confirmado en Langfuse (`GET /api/runs/{id}/costs`,
SPEC-EXAM-008). Los minutos son `result.duration_ms`.

## La novela de ejemplo, cambio a cambio

| # | cambio | total | orquestador | agentes | min | procedencia |
|---|---|---|---|---|---|---|
| 1 | generar | 53,17 $ | 48,79 $ · claude-opus-5[1m] | 4,38 $ | 118,6 | measured |
| 2 | continuar | 21,03 $ | 19,34 $ · claude-opus-5[1m] | 1,69 $ | 50,7 | measured |
| 3 | cambio del lector | no medido | no medido · — | no medido | — | absent |
| 4 | cambio del lector | 7,52 $ | 6,64 $ · claude-opus-5[1m] | 0,88 $ | 25,8 | measured |
| 5 | cambio del lector (v3) | 4,57 $ | 4,16 $ · claude-sonnet-5 | 0,41 $ | 19,5 | measured |
| 6 | rehacer capítulo (v3) | 1,50 $ | 1,34 $ · claude-sonnet-5 | 0,16 $ | 6,7 | measured |

**Total conocido: 87,80 $**, en 6 cambios; los marcados *no medido* no
dejaron un `result` (proceso detenido o stream no conservado) y no se cuentan como 0.

## El libro: 10 capítulos

- **Coste del libro** (generar + continuar): **74,20 $**.
- **Orquestador**: 68,13 $ (**92%**); **agentes (Haiku)**: 6,08 $ (**8%**).
- El orquestador relee todo su contexto en cada turno; es la mayor parte de la factura.
  Pasar de Opus a Sonnet redujo el mismo capítulo de 7,52 $ a 4,24 $.

## Margen

| concepto | valor | procedencia |
|---|---|---|
| tokens por novela | 74,20 $ | medido |
| infraestructura + operación | 6,00 $ | supuesto |
| precio de venta | 129,00 $ | supuesto |
| **margen por novela** | **38%** | calculado |

## Evals (perfil `eval`, 1 capítulo)

| run | total | orquestador | agentes | min | procedencia |
|---|---|---|---|---|---|
| finisterre-lighthouse-retirement | 25,80 $ | 11,75 $ | 14,05 $ | 14,4 | measured |
| stone-collector-birthday-adventure | no medido | no medido | no medido | — | absent |
