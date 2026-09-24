# Guion del deck — storyMaker

Para montar en Claude Design sobre el sistema **Qaracter design FRM** (PLAN-001 E11).
Cada slide: título, lo que se dice y la evidencia que la respalda. Las cifras
marcadas `PENDIENTE` se rellenan desde los runs de hoy; las marcadas
`estimado` son análisis, no medición, y así se escriben en la slide.

Estado: borrador 2026-09-24, 14:40 UTC, escrito antes de la novela de ejemplo.

---

## 1. Portada
- Qaracter → cliente ficticio · *storyMaker: novelas personalizadas para regalar* · 25-09-2026 · el dueño.

## 2. El problema
- Diez capítulos de 1.000–1.500 palabras en los que el destinatario reconoce su nombre, su historia y sus detalles, y que se leen de principio a fin sin tropiezos.
- Se evalúa el razonamiento y las evals con números, no la prosa.
- **La decisión:** no es un sistema nuevo. Es NovaForge v2 adaptado: gate de seis características, tres intentos, Story Bible, archivo en SQLite, procedencia en cada cifra. (spec §0)

## 3. Configuración y lectura
- Entrevista (FLOW-0) → `Brief` validado por schema; faltan datos o hay contradicción → se decide **en código**, el agente sólo extrae y pregunta.
- El texto libre del comprador nunca es instrucción: queda como fila `facts.source = freetext` (brief 04).
- Lectura en **PDF**: portada personalizada, dedicatoria, índice enlazado, ficha de personajes y lugares con enlace a su primer capítulo.
- Evidencia: `evals/results.md` (FLOW-0, 5 de 5 como se esperaba), `ejemplos/novela-ejemplo.pdf` `PENDIENTE`.

## 4. Arquitectura del harness
- Diagrama: `docs/diagrams/harness.md`.
- **Conductor por etapas** (SPEC-EXAM-003): Python lanza un proceso de Claude Code nuevo por unidad (mundo, reparto, guion, cada capítulo, cierre); el estado vive en disco. Nada en un run pasa de 100.000 tokens concurrentes.
- El escritor de capítulos no lee capítulos anteriores: sólo la Bible, su entrada del guion y el resumen acumulado. El contexto no crece con el libro.
- Roles: planificador (`plot-architect`), escritor (`chapter-writer`), editor (cuatro críticos + `style-editor`), más `interviewer` y `judge`; agentes en Haiku, el orquestador en el modelo de sesión (spec §8, con el porqué medido).

## 5. Validación, evals y observabilidad
- Tabla de validadores por tipo (a/b/c/d): `docs/diagrams/validators.md`.
- Tabla brief × validador: `evals/results.md` — FLOW-0 medido; mitad novela `PENDIENTE` (evals de 3 capítulos, declarado: spec §8).
- `judge_rubric`: seis criterios 0–10 con justificación; frente a la revisión humana de una novela `PENDIENTE`.
- Métodos formales: **TLA+ con TLC en verde, 18.253 estados**, cuatro propiedades de seguridad y terminación (`tla/README.md`). Lean: `PENDIENTE` o declarado con motivo.
- Iteración de ajuste: brief 01 antes/después con la versión del prompt `PENDIENTE`.
- Una traza de Langfuse: sesión por novela, traza por versión, span por llamada, scores por validador.

## 6. Guardarraíles
- Palabras prohibidas a tres niveles (global, cliente, novela), normalizadas (mayúsculas, tildes, plural simple); un acierto devuelve el capítulo por la hoja de feedback; agotados los intentos → `halted: policy`; cada decisión en `audit_log`.
- Dos hooks `PostToolUse` sobre escrituras en `output/*/chapters/`: `validate-chapter` y `policy`.
- Datos personales: el alias del destinatario sustituye al nombre real antes de exportar a Langfuse.
- Red-team: `docs/red-team-log.md` — incluye los fallos propios (orquestadores huérfanos facturando; una novela cerrada como completa sin libro).

## 7. Presupuesto
Todo lo medido sale de `output/*/cost.json` (evento `result` de Claude Code).

| concepto | cifra | procedencia |
|---|---|---|
| novela de ejemplo, orquestador único: 3 de 10 capítulos, 127 turnos, 49 min | **14,86 $** | medido (`leo-and-the-other-side-of-the-hill`) |
| → por capítulo con orquestador único | ~4,95 $ | medido / 3 |
| conductor, unidades mundo + reparto, 25 turnos, 3,3 min | **1,40 $** | medido (`leo-and-bruno-cross-the-hill`) |
| novela de ejemplo completa, 10 capítulos | `PENDIENTE` | medido hoy |
| cada eval de 3 capítulos | `PENDIENTE` | medido hoy |
| novela de 10 extrapolada desde las evals de 3 | `PENDIENTE` | **estimado**, se marca así |
| techo por novela | 60 $ | decisión del dueño, spec §8 |

**Sensibilidad** (estimado, desde `config/pricing.json`): los agentes van en Haiku 4.5 (1 $/5 $ por Mtok). Si el cliente exige el modelo premium para los agentes, la parte de agentes se multiplica por **×2 con Sonnet 5** y **×5 con Opus 5** con las mismas tarifas; el orquestador ya va en el modelo de sesión y no cambia. Se calcula con los tokens medidos de la novela de ejemplo y se etiqueta `estimado`.

Mensaje de la slide: *un techo por debajo de lo que cuesta el trabajo no ahorra dinero, compra un libro roto* (el techo de 15 $ se agotó en el capítulo 3; red-team caso 10).

## 8. Demo: el lector pide un cambio
- Un dato del brief 01 cambia (`python -m backend.versions.change <slug> --fact <id> --to "…"`).
- `fact_usage` dice qué capítulos lo usan; sólo esos se regeneran, por el mismo gate.
- `dist/v2/novel.pdf` abre con la página de **novedades** que enlaza a cada capítulo cambiado; `dist/v1/` queda intacto.
- Es el vídeo.

## 9. Cierre
- La frase de diseño (la misma del email, ver `README.md`).
- Lo que queda fuera, declarado: servidor MCP, login, linters de prosa, lector web con selección (spec §5).

## 10. Contraportada
- Qaracter · contacto.

## Anexos (primer recorte si falta tiempo, PLAN-001 Parte 6 punto 5)
- A. Arquitectura · B. Máquina de estados TLA+ (`docs/diagrams/state-machine.md`) · C. Tabla de evals · D. Esquema SQLite (`docs/diagrams/sqlite-schema.md`) · E. Red-team log.
