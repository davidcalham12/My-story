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

---

## 6. Respuesta de diseño — 2026-09-23, tarde (leídos `3b8e818` y `from-build.md`)

Recibido todo: la colocación de los documentos, la regla del buzón en
`AGENTS.md` §1, `from-build.md` y **SPEC-010**. Gracias por la auditoría: es
mejor de lo que yo tenía.

**Corrección propia, primero.** La tabla del §2 de este fichero decía que el
vigilante de contexto *"no puede por falta de dato: el stream no trae `usage`
por subagente"*. **Era falso.** SPEC-010 W2 demuestra que cada `task_progress`
trae `usage.total_tokens` (13.921 en el fixture; 7 de 7 en el run
`night-translator`) y que el parser sumaba `input_tokens + cache_*`, claves que
ese evento no tiene. Tres runs se leyeron como "sin datos" por un nombre de
clave. Retiro la afirmación; la fila queda así: *vigilante de contexto → fallaba
por parser, no por canal; arreglo en PLAN-010; la cifra es el total del
subagente (entrada + salida), cota superior del paquete, y así se etiqueta.* La
"prueba 2" del §2 queda cerrada por la auditoría, no hace falta el run.

**Un punto de proceso para el dueño, no para la sesión.** SPEC-010 lleva
`approved_by: … standing approval given in chat`. `AGENTS.md` §1 dice, con
razón, que un ok en el chat no cambia un estado y que la aprobación es un acto
humano escrito en el fichero. Dos salidas honestas: el dueño ratifica editando
él la cabecera (una línea), o la spec vuelve a `draft` hasta que lo haga. Lo
señalo porque es exactamente la regla que un lector externo va a comprobar.

**SPEC-009.** Sigue `draft`; correcto. Añadir a su P0 lo que SPEC-010 §2 saca:
`pages/run` importa `pages/quality` y FSD lo prohíbe — lo compartido baja a
`entities` o `widgets`. Y las menciones caducas a "cinco características /
cuatro críticos" en `Quality.tsx` van con ese mismo trabajo.

**El run que murió (`salvage-crew-…`, 02:45Z).** Recomendación: **trackear su
`output/` tal cual** y dejar que el barrido lo marque `halted: process`. Es el
primer caso real de §3.14 (*un run que muere a mitad no archiva nada*): evidencia
para `verification.md`, no basura. Si el dueño prefiere borrarlo, que quede una
línea en `domain-knowledge.md` diciendo que existió y por qué se descartó.

**Tres sesiones ahora** (diseño, `novaforge-05`, "continuación con
repositorios"). Acepto la regla de un committer a la vez. Diseño se
autolimita: sólo toca `docs/handoff/from-design.md`, `docs/brief/` y specs
nuevas en `draft`; siempre `git pull --rebase` antes; **nunca `backend/` ni
`frontend/`**. Este commit es el primero desde diseño y el buzón es el aviso.

**Sin cambios, pendiente del dueño:** aprobar SPEC-009 en cabecera; las cuatro
respuestas del examen (fecha, web+PDF, Java/elan, my-factory); qué son los
"dos días".

**`my-factory`.** Visto `b654582` con las siete skills de la VM. Regla para
todos: cada enlace nuevo de la profesora es una fila fechada en
`references/README.md`, en el mismo commit en que se use.

---

## 7. Respuesta de diseño — 2026-09-23, tarde (leídos hasta `055c31d`)

**Visto y bien:** PLAN-010 completo en cuatro commits con tests rojos antes;
el registro corregido (`e2f4a83`) — el stream traía la cifra desde siempre;
SPEC-010 aprobado con la frase literal del dueño y el ida y vuelta escrito;
SPEC-009 aprobado. **Falta `PLAN-009`**: las 48 horas del frontend cuentan
desde su aprobación (Q4), así que hasta que exista no ha empezado el reloj.

**SPEC-011 (Haiku), dos observaciones para el dueño, no objeciones:**

1. **El coste de un run está en el orquestador, no en los agentes**
   (`domain-knowledge.md` §2.2: la mayor parte de los turnos son suyos). Pasar
   los diez agentes a Haiku abarata la parte pequeña; el orquestador sigue en el
   modelo por defecto de la sesión (`models.orchestrator: null`). Si el motivo
   es la cuota, el ahorro real está en ese knob — y §4 de la spec ya nombra el
   riesgo de tocarlo. Que el dueño decida sabiéndolo.
2. **Todo lo medido hasta hoy deja de ser comparable**, y W3 lo dice bien. Lo
   que añadiría: un perfil `final` que restaure `opus`/`sonnet` en los agentes,
   para que la novela de ejemplo del examen (`ejemplos/novela-ejemplo.pdf`) y el
   coste de la slide de presupuesto se generen con los modelos que se van a
   vender, no con los de prueba. Es un fichero de perfil, no una decisión de
   arquitectura; se puede escribir ya y usar después.

**Buzón:** `from-build.md` sigue en `42fe1b7` (15:48). Los commits cuentan la
historia, pero la regla de `AGENTS.md` §1 es actualizar el fichero al cerrar
cada bloque; con PLAN-010 cerrado tocaba. Sin prisa, pero que no se quede.

**Sigue pendiente del dueño:** el nombre de la identidad visual (Q7) — sin él
`frontend/DESIGN.md` no puede empezar, y es lo primero de P0.
