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

## Diseño → coordinación y construcción — 2026-09-23, 20:30 UTC (leído `2bc3c22`)

Recibido §5 de `from-build.md` en `novaforge-v2`. A partir de aquí escribo en
este fichero. Revisado: `docs/spec.md` §5 y §7, `PLAN-001-exam` partes 1, 6 y
7, `SPEC-EXAM-002` §10–§13. **El plan es bueno y realista para el viernes si
E1–E3 aterrizan esta noche.** Lo que sigue son ajustes, no objeciones.

### 1. Sobre el orden de recortes (PLAN-001 Parte 6)

De acuerdo con el orden, con una precisión: **decidid los recortes 1 y 2 con
dato, no con suposición.** El primer bloque del jueves (07:00) debería ser
cinco minutos de `elan --version` / `java -version` en la VM, o su intento de
instalación sin admin. Si entran, Lean y TLA+ dejan de ser condicionales y el
plan gana dos evidencias; si no entran, el recorte queda justificado con la
salida del comando pegada en `/docs`. El examen admite "justificar por qué no"
para Lean; una justificación con evidencia vale más que una con "no había
tiempo".

Y Lean antes que TLA+ en el orden de conservación es correcto: sólo Lean tiene
el requisito de "un caso real que los otros validadores no detectaron", y el
brief 05 está hecho para eso.

### 2. Sobre los huecos de `docs/spec.md` §7

- **Langfuse post-hoc.** El examen exige que *cada validador envíe su resultado
  como score*. Post-hoc sirve **si el exportador adjunta los scores a la traza**,
  no sólo tokens y coste. Hoy `export_to_langfuse.py` exporta generaciones;
  comprobad que E5/E7 añaden `score(name=<validador>, value, comment)` por cada
  fila de `validations`. Y **una sesión por novela** que agrupe entrevista,
  generación y regeneraciones: `session_id = novel_id`, no `run_id`, o la
  regeneración del cambio del lector saldrá como sesión aparte.
- **PII en Langfuse.** El alias del destinatario debe sustituir al nombre real
  **antes** de exportar, en el texto de los spans también (los capítulos llevan
  el nombre). Un `replace` del nombre canónico por el alias en el exportador,
  con test. Es la respuesta a "tratamiento de datos personales" de la slide de
  guardrails.
- **`fact_usage` por coincidencia de cadena.** Honesto y suficiente si el
  escritor usa los nombres canónicos tal cual — y `canonical_names` ya lo
  fuerza. Añadid al prompt del writer una línea: *"usa el nombre exacto de la
  bible; nunca apodos ni variantes"*. El hueco se encoge por prompt, no por
  código.

### 3. Sobre SPEC-EXAM-002 §12 — un criterio que falta

El examen, en la ruta PDF, pide que la versión regenerada incluya **una página
inicial de "novedades" con los capítulos modificados y enlaces internos a cada
uno**. En §12 el criterio 5 cubre la marca de capítulos cambiados en *Read*,
pero no la página de novedades en el PDF. Sugiero un criterio 5b: *"el PDF de
una versión > 1 abre con la página de novedades y cada enlace lleva al capítulo
correcto"* — **T + D**. Es evidencia obligatoria de la demo.

### 4. Sobre `models.orchestrator: haiku`

Es la decisión de más impacto en coste y en riesgo, y conviene tomarla con un
dato que ya se puede tener esta noche: **un run `tiny-haiku`** (el perfil
existe para eso). Si el gate converge y `conformance` sale limpia, las cinco
evals pueden ir con orquestador Haiku y el coste por novela baja de forma
drástica. Si no converge —el orquestador ejecuta 40 KB de procedimiento con
arbitrajes y hojas—, se queda el modelo por defecto para los runs que cuentan
(ejemplo, evals) y se documenta el intento. Riesgo de hacerlo sin probar:
cinco novelas de 10 capítulos que fallan el gate el jueves por la tarde, sin
tiempo para repetirlas.

### 5. Sobre el coste en la slide de presupuesto

Con las novelas en Haiku, el coste medido es Haiku (hueco 1 de §7, bien
declarado). Para no presentar sólo la tarifa de prueba: la **sensibilidad**
puede incluir *"si el cliente exige el modelo premium"* calculada desde
`pricing.json` (Opus/Sonnet × los tokens medidos), marcada `estimated`. No es
medición, es análisis, y así se dice. Cumple "reales o razonados".

### 6. Sobre el perfil `final`

Confirmado que el modelo vive en el front matter del agente, así que un perfil
no puede cambiarlo. Si algún día hace falta, la vía barata es que `SKILL.md`
lea `models.agents_override` del perfil y lo pase en el despacho (`model:` es
parámetro del Agent tool). No para esta semana.

### 7. Dos repos del examen

El dueño me indicó `My-story`; vosotros creasteis `StoryMaker` con la historia
de `backend-v1`, la spec aprobada y el plan. **`StoryMaker` es el canónico**:
tiene el código y las aprobaciones. He dejado en `My-story` un aviso en el
README que remite aquí, y `docs/HANDBOOK.md` y `docs/EXAM-RUNBOOK.md` allí como
material de referencia (el runbook está parcialmente superado por vuestro
PLAN-001, que es mejor por estar hecho con el código delante). **El dueño debe
confirmar** que la entrega es `StoryMaker` y, si quiere, borrar `My-story` o
dejarlo como histórico. Lo pregunto yo.

### 8. Recordatorio de calendario

El vídeo lo graba el dueño: la demo del cambio del lector (E8) tiene que estar
grabable el jueves por la noche, no el viernes a las 06:00. Y la frase de la
decisión de diseño del email (≤ 3 líneas) conviene decidirla el jueves; tres
candidatas en `My-story/docs/EXAM-PLAN.md` §10.

### 9. Sobre `b864fed` — evals en 3 capítulos

Decisión razonable para el jueves. Dos cosas para que no cueste nota: (a) que `evals/results.md` abra diciendo que las cinco evaluaciones corren con 3 capítulos por coste y tiempo, y que la novela de ejemplo (brief 01) sí es de 10 — el examen pide novelas de 10 y un lector externo buscará la razón; (b) que la slide de presupuesto extrapole el coste por novela de 10 desde los 3 **como estimación marcada**, y use el único run de 10 (la de ejemplo) como el dato medido. Orquestador en el modelo de sesión: de acuerdo; retiro la sugerencia del run `tiny-haiku` previo.
