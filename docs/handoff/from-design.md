# from-design — buzón de la sesión de diseño → sesión constructora

Actualizado: 2026-09-23. Léelo entero al empezar la sesión. Cuando termines un
bloque, escribe tu estado en `docs/handoff/from-build.md` (usa la skill
`handoff`) y no esperes a que nadie te lo pida.

**Regla para `AGENTS.md`** (añadir como §0 o al final de §1):

> Al empezar cualquier sesión, lee `docs/handoff/` antes que nada. Al terminar
> un bloque de trabajo, actualiza tu fichero de ahí. Las dos sesiones que
> trabajan en este repo no pueden hablarse; este directorio es la conversación,
> y queda versionada.

---

## 1. Qué hay de nuevo en el repo (colocado por el dueño)

- `specs/SPEC-009-frontend-v2.md` — la spec del frontend. **Es la prioridad
  de las próximas 48 horas.** Grill primero (el repo responde: lee
  `frontend/src` y el `web/src` de v1 en el repo viejo), aprobación del dueño en
  la cabecera, `PLAN-009`, tests primero, P0 en el orden de la spec.
- Este fichero.

## 2. Estado de los validadores — ¿hacen lo que se les pidió?

Leído de `backend-v1`: `checks.py`, `domain.py`, `conformance.py`, `report.py`,
`SKILL.md`, `domain-knowledge.md` §8, `verification.md` §3 y §9, los dos runs
reales.

| validador | ¿funciona? | evidencia | qué falta |
|---|---|---|---|
| `length`, `chatter` | **sí** | gate en código puro, tests | — |
| `decide`, `promote` | **sí** | los únicos que rechazan; `conformance` los recomputa; 2 runs conformes | `patch_then_halt` nunca alcanzado en un run real (§3.1) |
| `check_rules`, `check_promises`, `check_summary`, `check_prose`, `check_log` | **sí** | registro `BY_STAGE`, `checks.py` los ejecuta por etapa | informan, no bloquean — por diseño |
| `validate-sheet` (Node) | **sí** | `--self-test` en CI; corre antes de cada hoja | port a Python retirado a conciencia |
| `conformance` | **sí** | 4 intentos comprobados por run, conformant | ciego a un run que no escribió sus intentos (§3.13) |
| vigilante de presupuesto | **a medias** | `--max-budget-usd` en argv + suma en Python | **nunca se ha alcanzado el techo: no se sabe si el flag frena bajo suscripción** (§3.21) |
| vigilante de contexto (100k) | **no puede** | probado sólo con paquete inyectado | **el stream no trae `usage` por subagente: 27 despachos, 0 filas con tokens** (§3.5, §8.4). No es un fallo del código: es que el dato no llega |
| 4 críticos de modelo | **sí** | 2 runs; `prose` bloquea (7→10), continuidad ya no | no reproducen; clase D |
| auditor del guion (`science-critic`, FLOW-3) | **sí** | $0,07–0,13; encontró defectos que el gate no vio | es un modelo, clase D, decidido así |
| búsqueda vectorial | **construida y sin cablear** | módulo + tests | §3.15 — spec propia |
| capas de memoria (hechos, `character_knowledge`) | **construidas y sin correr** | §7.7 | — |

**Resumen:** 13 aritméticos + 5 de modelo = 18 instrumentos. Los 16 que pueden
funcionar, funcionan y está probado. Los 2 que no (contexto, presupuesto) no
funcionan **por falta de dato**, no por defecto de código, y ambos están
declarados. Para el examen: **0 envían scores a Langfuse todavía**.

**Dos pruebas baratas que cierran huecos grandes — hazlas en las 48 h:**

1. **`--max-budget-usd` con techo artificial.** Perfil `tiny` con
   `max_cost_usd: 1.0`. Un run real. Si el flag frena, §3.21 se cierra con
   evidencia y la letra sube a T. Si no frena, el vigilante de Python es la
   única línea y hay que decirlo. Cuesta ~$1.
2. **Buscar los tokens en el stream.** Con `--verbose`, revisa si algún evento
   distinto de `task_progress` (`assistant` con `usage`, `tool_result` del
   `Agent`) trae los tokens del subagente. Si existen y el parser no los lee, es
   parser, no stream. Si no existen en ningún evento, §3.5 queda como
   imposibilidad del canal y se escribe así.

## 3. Incoherencia para `coherencia-docs`

`specs/SPEC-001-commons.md` (aprobada 21-09) dice *"the real Anthropic client
behind a flag"*. Anexo C, `README.md` y `pyproject.toml` dicen que no hay SDK ni
lo habrá. Es un `OBS`. Resolver con nota en la spec, no borrando.

## 4. Plan de 48 horas, por prioridad

**Día 1**

1. Los doce endpoints de lectura del §"Backend surface" de SPEC-009, sobre el
   archivo. Sin ellos no hay frontend. Spec corta o dentro de PLAN-009.
2. `frontend/DESIGN.md` con `frontend-design`. **Antes de ningún componente.**
3. Manuscript. Quality completa (tabla del gate, *por qué se repitió*,
   desacuerdo entre críticos).
4. Prueba del `--max-budget-usd` a $1 (§2 arriba).

**Día 2**

5. Diagram desde `/api/flow`. Run completo con el carril del orquestador.
6. NewNovel simple + avanzado. Presentation (replay).
7. CI en verde: `tsc`, `vitest`, `vite build`, regla de tokens (AC-2).
8. `verification.md` v4 con lo que cambió; `from-build.md` con el estado.

Lo que **no** entra en 48 h y se dice: P1 de SPEC-009, Langfuse scores, Lean,
TLA+, el entrevistador, la story bible con cronología. Todo eso es el examen
(`docs/brief/STORYMAKER-EXAM-PLAN.md` cuando el dueño lo coloque).

## 5. my-factory

La profesora exige que **todos los enlaces y recomendaciones** que va pasando
estén en `my-factory`. El repo está vacío. El dueño va a comitear una semilla
con `references/` (todos los enlaces hasta hoy, fechados) y `skills/` (las
dieciséis skills que están en `~/.claude/skills/`). A partir de ahí: **cada
enlace nuevo que llegue va a `references/`**, con fecha y una línea de para qué
sirve, en el mismo commit en que se use.
