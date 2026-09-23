> **Correcciones al plan (2026-09-23, tarde).** Este documento se escribió la
> mañana del 23 contra una copia vieja del repo. Lo que ha cambiado desde
> entonces y prevalece sobre el texto de abajo:
> - Son **diez** agentes (hay `prose-critic`) y **seis** características.
> - El fichero de proceso es **`AGENTS.md`**; donde diga `agents.md`, léase así.
> - Los agentes corren en **Haiku** (SPEC-011) mientras se construye; la novela
>   de ejemplo y el coste de la slide deben generarse con un perfil `final` con
>   los modelos originales.
> - `--max-budget-usd` **frena** (probado). El primer turno del orquestador
>   cuesta ~$1.
> - El vigilante de contexto **sí** mide tokens por subagente (cota superior).
> - El repo del examen es **`My-story`**; el nombre del producto lo decide el
>   dueño (Q7).
> - Las cuatro respuestas del §11 siguen pendientes.

# storyMaker — plan de examen (Harness Engineering)

Documento de trabajo. Decodifica el enunciado del examen final en: condiciones
de aprobado, qué se reutiliza de NovaForge, qué es nuevo, decisiones de diseño,
plan por fases, skills, documentación exigida y presentación.

Fecha: 2026-09-23. Proyecto **individual**. Repo nuevo: **`storyMaker`**.

---

## 0. Lo que decide aprobar o suspender

Léelo antes que nada. El enunciado lo dice con todas las letras:

> *Un proyecto sin evals con resultados medibles, o sin documentación de
> proceso en `/docs`, no aprueba.*

Y además, como evidencias obligatorias en la presentación:

1. **La tabla de resultados de las evals, con números** (5 briefs × validadores).
2. **El coste real por novela, sacado de Langfuse**, y el margen.
3. **La demo de un cambio del lector propagado a los capítulos afectados.**

Y como evidencia de que funciona: **`/ejemplos/novela-ejemplo.pdf`**, una novela
completa de 10 capítulos generada con el brief del README.

**Consecuencia para el orden de trabajo:** primero una novela entera de
principio a fin, con Langfuse midiendo y cinco briefs evaluados. Lean y TLA+
**después**, sobre un sistema que ya funciona. Un proyecto con Lean perfecto y
sin evals suspende; uno con evals y un Lean modesto aprueba.

Lo que también se corrige: *"No se corrige el resultado, se corrige el
razonamiento que llevó a él."* La carpeta `/docs` vale tanto como el código.

---

## 1. Qué se reutiliza de NovaForge

Casi todo el harness. La tabla mapea cada exigencia del examen a lo que ya
existe. **Lo que está en la columna derecha no se rediseña: se adapta.**

| examen exige | ya existe en NovaForge | qué cambia |
|---|---|---|
| Tres roles mínimo: planner, writer, editor/critic | nueve agentes; plot-architect = planner, chapter-writer = writer, tres críticos = editor | añadir **interviewer** y **judge**; los críticos cambian de criterios (ver §3.6) |
| Retries con límite | tres oportunidades, `patch_then_halt` | igual; el límite viene de config |
| Resúmenes por capítulo para el contexto | resumen rodante; hechos estructurados (D15) | igual |
| Story bible con qué capítulos usan cada hecho | facts por capítulo en SQLite (SPEC-001 §5) | añadir tabla `fact_usage(fact_id, chapter)` y **cronología** |
| Checkpoint por capítulo, reanudar | estado persistido por etapa e intento (D9) | añadir **reanudación** desde el último capítulo completo (antes era v2) |
| Registro de tokens y coste por novela | `usage` del stream + evento `result`; `export_to_langfuse.py` | exportar **en vivo**, no al final; scores |
| Validadores programáticos ≥ 3 | `length`, `chatter`, `validate_sheet`, `outline_audit`, front-matter test | añadir **nombres exactos como en la bible**, **hechos obligatorios presentes**, **palabras prohibidas**, **browser MCP** |
| LLM-as-judge con rúbrica | los tres críticos con puntuación y hallazgos citados | un **judge** separado con rúbrica de 5 criterios y justificación por criterio |
| Feedback al writer con límite | hoja de retroalimentación escalada (LOOP-003) | igual; es una de tus mejores piezas |
| 100.000 tokens concurrentes | dos capas: estimado en el skill + medido en Python (Anexo C §3) | igual |
| `CLAUDE.md` cuidado | `claude.md` + `agents.md` (proceso spec → plan → código) | pasar a `CLAUDE.md` mayúsculas; es "parte del examen" |
| Una skill reutilizable | `novaforge` (el procedimiento), `grilling`, `coherencia-docs`, `verification`, `frontend-design` | la skill del examen es **el procedimiento del harness**; las demás van a MyFactory |
| Tools con schema validado | los CLI instruments con JSON de salida | pydantic/JSON Schema en cada tool y en cada salida de rol |
| Documentación de proceso | brief, anexos B–D, SPEC-001, verification.md, LOOP-001..003, runbook | reorganizar en la estructura de `/docs` que pide el examen (§7) |
| Verificación con letras T/A/I/D/U | `verification.md` v1 | igual; ahora incluye Lean y TLA+ como métodos |
| Web de lectura | panel React (8 pantallas, procedencia por cifra) | rehacer como **lector**: índice, ficha de personajes, portada, cambio desde la página |
| Coste acotado, no inventado | `low / estimate / high`, `measured / reported / …` | igual; el examen exige "reales o razonados, no inventados" |
| Evaluación con briefs y tabla | LOOP-003 con dos runs medidos, `measure.mjs` | cinco briefs, tabla, una iteración de tuning antes/después |
| Red-team | premisa hostil probada (inyección en argv) | log formal en `/docs/red-team-log.md` |
| Sin API key | Claude Code orquesta vía `claude -p` (Anexo C) | igual — **y resuelve el "sin API keys en el repo" por construcción** |

**Lo que NO se reutiliza:** el género (ciencia ficción → cualquiera, lo fija el
brief); el crítico de ciencia (→ crítico de **coherencia con el brief**); la
Biblia en Markdown como fuente de verdad (→ **SQLite obligatorio**; Markdown
sólo como exportación).

---

## 2. Qué es nuevo de verdad

Ocho cosas. Todo lo demás es adaptación.

1. **El entrevistador** — agente que recoge datos, detecta faltantes y al menos
   una contradicción (edad ↔ género/tono), trata el texto libre como no
   confiable, y produce un **brief validado con schema**.
2. **Story bible en SQLite** con `fact_usage` y **cronología** (eventos, momento,
   personajes, lugar, fechas de nacimiento).
3. **Cambio del lector con propagación**: seleccionar un hecho → capítulos que
   lo usan → regenerar sólo esos → **nueva versión** → marcar qué cambió →
   **conservar la anterior**.
4. **Lector web** (índice navegable, ficha de personajes/lugares con enlaces,
   portada con dedicatoria) **+ exportación a PDF** (obligatoria igualmente).
5. **Palabras prohibidas** en tres niveles en SQLite, con normalización,
   límite de reintentos y audit log.
6. **Lean 4**: cronología → fichero Lean generado → ≥ 2 invariantes → `lake build`
   bloquea la publicación si falla.
7. **TLA+**: el flujo como máquina de estados, ≥ 3 invariantes de seguridad,
   ≥ 1 de liveness, TLC sobre modelo pequeño, mapeo spec ↔ código.
8. **Langfuse en vivo**: sesión por novela, span por rol y tool, **scores** de
   cada validador, **prompts versionados**.

Y dos piezas de entrega que no son código: **la presentación con identidad
corporativa** y **el vídeo de demo**.

---

## 3. Decisiones de diseño (propuestas; confirma o corrige)

### 3.1 Lectura: **web + PDF exportado**

El examen exige el PDF de ejemplo en cualquier caso. La web da la demo más fuerte
(cambio desde la propia página, marcas de qué capítulos cambiaron) y reutiliza
el panel React. El PDF sale del mismo HTML por impresión (una librería de
HTML → PDF; skill obligatoria). **Elegir PDF solo** ahorraría el lector web pero
obliga a un formulario/CLI para los cambios y a la página de "novedades"; no
ahorra la propagación, que es lo difícil.

### 3.2 Orquestación: **Claude Code vía `claude -p`, FastAPI lanza y observa**

Como en el Anexo C. Sin API key. Resuelve por construcción "sin API keys en
ningún repo". El LLM-as-judge es un subagente más. **Riesgo:** el examen pide
tokens/coste/latencia "por llamada" en Langfuse; el stream da `usage` por
mensaje y el `result` da el total: **suficiente**, y se declara qué es
`measured` y qué `reconstructed`.

### 3.3 Roles (mínimo tres; proponemos seis)

| rol | qué hace | de dónde viene |
|---|---|---|
| **interviewer** | recoge datos, detecta faltantes y contradicciones, extrae hechos del texto libre (no confiable), emite brief con schema | nuevo |
| **planner** | story bible inicial + cronología + guion de 10 capítulos con beats | plot-architect + worldbuilder + character-architect fundidos |
| **writer** | un capítulo por llamada; sólo bible proyectada + su entrada + resúmenes previos; **nunca prosa previa** | chapter-writer |
| **editor / critics** | continuidad (bible + cronología), **personalización** (hechos del brief integrados con naturalidad), guion (beats), longitud, formato | continuity/outline critics + nuevo |
| **judge** | rúbrica de 5 criterios con puntuación y justificación; corre al final de cada versión | nuevo (LLM-as-judge) |
| **orchestrator** | Claude Code con la skill del harness; gate, hoja, `patch_then_halt`, checkpoints | igual |

### 3.4 Story bible en SQLite (esquema mínimo)

```
brief(id, novel_id, json, schema_version, validated_at)
novels(id, recipient_alias, occasion, genre, tone, chapters=10, words_min=1000, words_max=1500, status)
versions(id, novel_id, n, created_at, parent_version_id, reason)          -- reason: initial | reader_change
chapters(id, version_id, n, title, path, words, status, checkpoint_at)
facts(id, novel_id, kind, text, source)                                  -- source: brief | freetext(untrusted) | planner
fact_usage(fact_id, version_id, chapter_n)                               -- qué capítulos usan cada hecho
characters(id, novel_id, canonical_name, role, birth_date, first_chapter)
places(id, novel_id, canonical_name, first_chapter)
chronology(id, novel_id, event, moment, place_id, excludes_after)         -- alimenta Lean
chronology_participants(event_id, character_id)
summaries(version_id, chapter_n, facts_json, text)
forbidden_words(id, level, novel_id NULL, term, normalized)              -- level: global | client | novel
audit_log(id, novel_id, ts, actor, decision, detail, langfuse_trace_id)
validations(id, version_id, chapter_n NULL, validator, passed, score, detail, langfuse_score_id)
calls(...)  events(...)  — como en SPEC-001
```

**Dos reglas:** los hechos que vienen del texto libre llevan `source=freetext`
y **nunca** se convierten en instrucción (van al prompt como datos citados,
dentro de un delimitador, con la instrucción explícita de tratarlos como
contenido). Y la cronología es **la** fuente para Lean: no hay otra.

### 3.5 Propagación de un cambio del lector

1. El lector selecciona un hecho ("el perro se llama Nala") → `PATCH /facts/{id}`.
2. `fact_usage` da los capítulos afectados de la versión actual.
3. Se crea `versions(n+1, parent=n, reason=reader_change)`; los capítulos **no
   afectados se copian por referencia**; los afectados se regeneran **con el
   resumen de los anteriores ya actualizado** para no romper continuidad.
4. Cada capítulo regenerado pasa todos los validadores + Lean antes de publicar.
5. La web marca los capítulos cambiados (diff contra `parent_version_id`); el
   PDF regenerado lleva la página de "novedades" con enlaces internos.
6. La versión anterior **no se toca**. Es un invariante de TLA+ (§3.9).

### 3.6 Los cuatro tipos de validadores, con nombre y punto de ejecución

| tipo | nombre | qué comprueba | dónde corre | score a Langfuse |
|---|---|---|---|---|
| **a) programático** | `schema_brief` | el brief cumple su JSON Schema | tras la entrevista | pass/fail |
| a | `schema_role_output` | la salida de cada rol cumple su schema | hook post-rol | pass/fail |
| a | `canonical_names` | destinatario y personajes escritos **exactamente** como en `characters.canonical_name` | hook post-capítulo | nº desvíos |
| a | `chapter_length` | 1.000–1.500 palabras (`wc -w`) | hook post-capítulo | palabras |
| a | `mandatory_facts` | cada hecho obligatorio del brief aparece en ≥ 1 capítulo, según `fact_usage` | gate pre-publicación | fracción cubierta |
| a | `forbidden_words` | §3.8 | hook post-capítulo (**policy hook**) | nº coincidencias |
| a | `visual_check` | browser MCP: índice, ficha, portada renderizan | gate pre-publicación | pass/fail + captura |
| **b) semántico** | `judge_rubric` | continuidad, tono, arco, coherencia de personajes, ritmo, **personalización natural** — nota y justificación por criterio | rol judge, fin de versión | 5 scores + media |
| b | `human_review` | la misma rúbrica, una persona, una novela completa; comparación con el judge | manual, una vez | 5 scores; delta con el judge |
| **c) formal historia** | `lean_chronology` | invariantes sobre la cronología generada desde SQLite | gate pre-publicación (`lake build`) | pass/fail + invariante fallido |
| **d) formal sistema** | `tla_harness` | máquina de estados del harness con TLC | **desarrollo**, no por generación | — (se documenta) |

Los dos **hooks** que exige el examen: **hook de validación de capítulo** (agrupa
`canonical_names`, `chapter_length`, `schema_role_output`) y **hook de policy**
(`forbidden_words` + audit log). El gate pre-publicación agrupa
`mandatory_facts`, `visual_check`, `lean_chronology`.

### 3.7 Contexto y 100k

Igual que NovaForge: el writer recibe la **proyección** de la bible (hechos
relevantes al capítulo, personajes presentes según cronología, resúmenes
previos como hechos), nunca la bible entera ni prosa previa. Tope de 100.000
concurrentes en dos capas (estimado antes, medido después, parada). La serie
"el capítulo 10 pesa lo que el 1" se pinta en la web y va a la presentación.

### 3.8 Guardrail de palabras prohibidas

- Tres niveles en `forbidden_words`: `global` (semilla en migración), `client`
  (lo que el comprador no quiere), `novel` (derivadas del brief, p. ej. el nombre
  de una expareja).
- Normalización antes de comparar: minúsculas, sin acentos (NFKD), plural →
  singular simple (`-s`, `-es`), variantes declaradas en la tabla.
- Coincidencia → capítulo devuelto al writer con la hoja de retroalimentación;
  límite de intentos de config; agotado → `halted: policy`, se informa.
- Cada coincidencia → `audit_log` + score en Langfuse.
- Tests: uno por nivel + uno de acento + uno de plural.

### 3.9 Lean 4 — alcance realista

- Generador: `python -m storymaker.lean_export <novel_id>` → `lean/Chronology.lean`
  con `structure Character`, `structure Event`, listas concretas, y los
  invariantes como teoremas sobre esas listas concretas, demostrados por
  `decide` / `simp` (comprobación sobre una cronología concreta, que es lo que
  el examen pide como mínimo).
- Invariantes (tres, para tener margen): **(1)** los eventos respetan el orden
  declarado; **(2)** edad en cada evento coherente con la fecha de nacimiento
  (≥ 0 y ≤ 120); **(3)** un personaje no aparece tras el evento que lo excluye.
- Ejecución: `lake build` en el gate; fallo → versión no publicada → feedback al
  editor con el invariante y los datos.
- **El caso real que el examen pide:** el brief nº 5 (§5) se diseña para
  provocar una incoherencia temporal que el judge no ve (una edad imposible en
  un recuerdo). Si Lean la pilla y nadie más, es el caso. Si no ocurre, se
  documenta por qué.

### 3.10 TLA+ — alcance realista

- Módulo `Harness.tla` (PlusCal es aceptable): estados `Configuring →
  Planning → Writing(ch) → Validating(ch) → Published(v) | Halted`, con
  `retries[ch]`, `checkpoint`, `versions`, y la acción `ReaderChange`.
- Invariantes de seguridad (cuatro, para tener margen): **(1)** ninguna versión
  publicada contiene un capítulo sin todos los validadores en `pass`; **(2)** la
  reanudación desde checkpoint no duplica ni pierde capítulos (`Writing` sólo
  para `ch = checkpoint + 1`); **(3)** toda versión anterior se conserva tras una
  regeneración; **(4)** `retries[ch] ≤ MaxRetries`.
- Liveness: `<>(state ∈ {Published, Halted})` bajo fairness débil.
- TLC con `Chapters = 5`, `MaxRetries = 2`, config en `tla/Harness.cfg`
  commiteada.
- **Mapeo spec ↔ código** en el README: tabla acción TLA+ → función/estado en
  `backend/runs/`. Si TLC encuentra un contraejemplo (lo normal en la primera
  versión con `ReaderChange` + checkpoint), se documenta con el cambio de
  código.

### 3.11 Langfuse

- Una **sesión** por novela (`session_id = novel_id`) que agrupa entrevista,
  generación y regeneraciones.
- Una **traza** por generación/regeneración; **span** por rol y por tool, con
  nombre (`interviewer`, `planner`, `writer.ch03.attempt2`, `tool.forbidden_words`).
- Tokens, coste y latencia por span desde los `usage` del stream; por capítulo
  y por novela por agregación.
- **Scores**: cada validador envía el suyo a la traza (§3.6).
- **Prompts versionados** en Langfuse: cada agente registra su prompt como
  versión; la iteración de tuning cita la versión.
- **PII:** los nombres reales del destinatario **no van a Langfuse en claro**.
  Se enmascaran con un alias estable por novela (`recipient_alias`) antes de
  exportar. Esto es también la respuesta a "tratamiento de datos personales" de
  la slide de guardrails.
- Host: **`https://us.cloud.langfuse.com`** (región US; el SDK apunta a EU por
  defecto y da un 401 mudo — el proyecto ya tropezó tres veces con esto).

---

## 4. Estructura del repo `storyMaker`

```
storyMaker/
├── CLAUDE.md                      cuidado y legible: es parte del examen
├── README.md                      cómo correr; brief de ejemplo reproducible; mapeo TLA+ ↔ código
├── .env.example                   LANGFUSE_*, sin valores
├── .claude/
│   ├── agents/                    interviewer, planner, writer, critics, judge
│   ├── skills/storymaker/         la skill del harness (el procedimiento)
│   ├── hooks/                     validate-chapter, policy
│   ├── commands/                  /new-novel, /reader-change, /eval-briefs
│   ├── mcp.json                   browser MCP (Playwright)
│   └── memory/
├── backend/                       FastAPI: runs, bible, versions, reader-change, validators, langfuse
├── frontend/                      lector web (FSD): índice, ficha, portada, cambios, diff de versiones
├── lean/                          Chronology.lean generado + lakefile + invariantes
├── tla/                           Harness.tla, Harness.cfg, contraejemplos/
├── evals/                         5 briefs, runner, tabla de resultados, tuning antes/después
├── ejemplos/novela-ejemplo.pdf
├── presentacion/                  deck.pdf, deck.pptx, anexos-*.pdf, README.md, demo.mp4 o enlace
└── docs/                          §7
```

---

## 5. Plan por fases

Cada fase termina con algo que se puede enseñar. **Las fases 1–4 son las que
aprueban.** Sin fecha de entrega no puedo repartir días; con ella, sí.

**Fase 0 — Repo y skills.** `storyMaker` creado; `CLAUDE.md` y `AGENTS.md`
(proceso spec → plan → código); `.env.example`; skills de §6 instaladas; SPEC
inicial en `/docs/spec.md` **antes de código** (el examen lo exige así).
*Hecho:* repo con docs de arranque y ninguna línea de código de producto.

**Fase 1 — Una novela de principio a fin, sin adornos.** Entrevistador → brief
con schema → planner → bible en SQLite → 10 capítulos con writer + hoja +
retries → PDF simple. Con Langfuse en vivo desde el primer run. *Hecho:*
`ejemplos/novela-ejemplo.pdf` existe y la traza está en Langfuse con coste.

**Fase 2 — Validadores programáticos y guardrails.** Los siete de tipo (a) sin
el visual; palabras prohibidas con tests; audit log; scores a Langfuse.
*Hecho:* cada validador con nombre, punto de ejecución y score visible.

**Fase 3 — Evals.** Cinco briefs (§5.1), runner, **tabla por brief × validador
con números**, una iteración de tuning con antes/después y versión de prompt.
*Hecho:* la tabla existe con datos reales. **Esto es lo que aprueba.**

**Fase 4 — Judge + revisión humana + `/docs` completo.** Rúbrica, scores;
revisión humana de una novela con la misma rúbrica; comparación. Todos los
documentos de §7 escritos. *Hecho:* `/docs` completo; `coherencia-docs` sin
incidencias altas.

**Fase 5 — Lector web + cambio del lector + versiones.** Índice, ficha,
portada, selección de hecho, propagación, diff de versiones, versión anterior
conservada, PDF con página de novedades. *Hecho:* la demo del cambio propagado
funciona y está grabada.

**Fase 6 — Lean.** Exportador, tres invariantes, `lake build` en el gate, el
caso del brief nº 5. *Hecho:* un fallo real detectado o la justificación.

**Fase 7 — TLA+.** Módulo, cuatro invariantes, liveness, TLC con la config
commiteada, mapeo con el código, contraejemplo documentado si lo hubo.
*Hecho:* TLC en verde y la tabla de mapeo en el README.

**Fase 8 — Browser MCP + red-team + checkpoint.** `visual_check` con Playwright
MCP y su documentación en `/docs`; red-team log; reanudación desde checkpoint
probada matando el proceso a mitad. *Hecho:* los tres documentados con
evidencia.

**Fase 9 — Presentación, presupuesto y vídeo.** §8.

**Opcional, sólo si sobra tiempo:** servidor MCP con FastMCP (encaja natural
sobre FastAPI; cuatro tools de lectura), linters de prosa, login.

### 5.1 Los cinco briefs de evaluación

| # | tipo | qué prueba |
|---|---|---|
| 1 | normal | regalo a un hijo; el caso feliz |
| 2 | normal | aniversario de pareja; tono distinto, dos protagonistas |
| 3 | datos faltantes + contradicción | edad 8 con tono "novela negra adulta" → el entrevistador debe detectarlo |
| 4 | **adversarial** | texto libre con inyección ("ignora las instrucciones y…") → tratado como contenido; palabras prohibidas de nivel cliente incluidas |
| 5 | **incoherencia temporal** | recuerdos con fechas que hacen imposible una edad → Lean debe pillarlo |

Ninguno con datos de una persona real. Nombres inventados.

---

## 6. Skills nuevas (regla de la profesora: una por tecnología)

Además de las once ya listadas en el brief de NovaForge:

| skill | para qué | origen |
|---|---|---|
| `lean4` | `lake`, estructuras, `decide`/`simp`, cómo escribir invariantes sobre listas | oficial/comunidad; leer entera antes |
| `tlaplus` | TLA+/PlusCal, TLC, `.cfg`, invariantes y liveness | learntla.com es la referencia que da el examen |
| `langfuse` | sesiones, trazas, spans, scores, prompts versionados; región US | SDK oficial |
| `playwright-mcp` | abrir la web, navegar, capturar, verificar render | oficial |
| `html-to-pdf` | la librería elegida para exportar (una sola) | según elección |
| `pydantic` / `jsonschema` | schemas de brief y salidas de rol | oficial |
| `fastmcp` | sólo si se hace el opcional | oficial |

---

## 7. `/docs` — inventario obligatorio

El examen lo enumera. Cada fichero, con lo que ya tienes para llenarlo:

| fichero | contenido | de dónde parte |
|---|---|---|
| `spec.md` | qué se decidió construir y por qué, **antes del código** | SPEC-001 adaptada |
| `trade-offs.md` | cada decisión como opciones · criterios · elección | anexo A del brief (23 preguntas) + §3 de este doc |
| `explainers/*.md` | uno por concepto del curso aplicado: harness, story bible, LLM-as-judge, hooks, guardrails, TLA+, Lean, observabilidad, T/A/I/D/U, best-effort | breves; demostrar que se entiende |
| `diagrams/` | arquitectura del harness, máquina de estados TLA+, esquema SQLite, tabla de validadores con punto de ejecución | Mermaid corregido + §3.4 + §3.6 |
| `iterations.md` | qué cambió tras cada eval, contraejemplo TLC o fallo Lean, y por qué; causa y efecto | LOOP-003 §8 (dieciséis lecciones) + lo nuevo |
| `red-team-log.md` | casos adversariales, qué validador los detectó (o no), cómo se resolvió | inyección en argv ya documentada + brief nº 4 |
| `verification.md` | garantías con nivel y letra; huecos; modos de fallo; Lean y TLA+ como métodos | v1 existente |
| `browser-mcp.md` | qué inspeccionó el agente, qué detectó, qué cambió | Fase 8 |
| `skills.md` | skills usadas/creadas, con enlace a cada fichero | brief §2 + §6 |
| `subagents.md` | cada subagente y comando propio: propósito y resultado | `.claude/agents/` |
| `security-report.md` | opcional | — |

---

## 8. Presentación (10 min) y presupuesto

### 8.1 Bloques → slides

| bloque | min | slide(s) | evidencia que llevas |
|---|---|---|---|
| Portada | 0,5 | empresa presentadora, cliente ficticio, fecha, tu nombre | — |
| Problema y cliente | 1 | quién compra, ocasiones, por qué lo actual no sirve | — |
| Configuración y lectura | 1 | entrevistador → brief; lector web; cambio desde la página | capturas |
| Arquitectura del harness | 2 | roles y bucle; contexto acotado; bible; tools; hooks; **por qué** | diagrama; serie "cap. 10 pesa lo que el 1" |
| Validación, evaluación, observabilidad | 2 | los cuatro tipos y dónde actúan; **tabla por brief**; **un fallo de Lean**; propiedades TLC; **tuning antes/después**; **traza Langfuse real** | §3.6, §5.1, capturas |
| Guardrails | 0,5 | palabras prohibidas con ejemplo; PII enmascarada; inyección; audit log | brief nº 4 |
| Presupuesto y coste | 1 | §8.2 | Langfuse |
| Demo y cierre | 1 | cambio del lector propagado; riesgos; siguientes pasos | vídeo/en vivo |
| Contraportada | — | contacto | — |

**Identidad corporativa obligatoria**: nombre, logo, paleta, tipografía
consistentes. Usa la skill `frontend-design` para el sistema de tokens del deck
igual que para la web; el examen rechaza plantillas genéricas.

### 8.2 Slide de presupuesto — cómo construirla con números reales

- **Coste de tokens por novela**: de Langfuse, sobre las cinco novelas de las
  evals más la de ejemplo. Da la media y el rango. Con `claude -p` el coste real
  incluye al orquestador; **usa el real**, no el estimado (NovaForge midió un
  factor 8 entre ambos: es un argumento de rigor para la slide).
- **Infraestructura**: servidor pequeño + Langfuse (plan) + almacenamiento;
  estimado y justificado.
- **Margen operativo**: revisiones incluidas (p. ej. 2), soporte.
- **Precio de venta** y margen resultante.
- **Desarrollo**: horas por fase (diseño, desarrollo, validación, despliegue) ×
  tarifa. Usa las horas reales de tu registro de sesiones como base.
- **Escenarios**: 20 / 100 / 500 novelas al mes.
- **Sensibilidad**: tokens +50%; más de tres revisiones por novela (cada
  revisión regenera sólo los capítulos afectados — mide cuántos de media).

---

## 9. Riesgos y mitigaciones

| riesgo | mitigación |
|---|---|
| Lean y TLA+ consumen el tiempo antes de tener evals | fases 6–7 **después** de la 3; alcance mínimo en §3.9–3.10 |
| `claude -p` no da latencia/tokens por llamada al detalle que el examen espera | usar `usage` por mensaje + `result`; declarar procedencia; es honesto y suficiente |
| Langfuse 401 por región | host US en `.env.example` con comentario |
| PII del destinatario en trazas y en el repo | alias estable; briefs de ejemplo con nombres inventados; nunca datos reales |
| El judge y los críticos se contradicen | arbitraje del orquestador ya existente; documentarlo como caso en `iterations.md` |
| Reparar un validador rompe otro (visto dos veces) | se queda el mejor borrador; se documenta como trade-off |
| Propagación de cambios rompe continuidad | regenerar en orden con resúmenes actualizados; validadores + Lean en el gate |
| TLC no termina o explota estados | modelo pequeño (5 cap, 2 retries); acotar `versions` |
| Sin fecha límite clara, se reparte mal | **dímela** |

---

## 10. La frase de la decisión más importante (para el email, ≤ 3 líneas)

Tres candidatas; elige la que sientas tuya:

1. *El escritor de cada capítulo no puede leer los anteriores — no tiene la
   herramienta —, así que el contexto no crece y el capítulo 10 cuesta lo que
   el 1; toda la continuidad pasa por una story bible en SQLite que sabe qué
   capítulo usa cada hecho.*
2. *Claude Code es el orquestador y el backend sólo lo lanza y lo observa: sin
   API key, con el coste real del run entero medido, y con una sola
   implementación del procedimiento.*
3. *Todo lo que se puede comprobar con un script se comprueba con un script;
   los modelos sólo juzgan donde hace falta juicio, y lo que no se puede
   verificar se escribe como hueco conocido en vez de esconderse.*

La 1 es la más "harness"; la 3 es la que más gustó a la profesora.

---

## 11. Qué necesito de ti para convertir esto en runbook

1. **La fecha de entrega.** Sin ella no puedo repartir las nueve fases en días.
2. Confirmar **web + PDF** (§3.1) o elegir sólo PDF.
3. Confirmar que en tu máquina se pueden instalar **Java** (para TLC) y **elan/lake**
   (para Lean). Si no, hay que saberlo ya.
4. Si ya tienes un repo **MyFactory** propio o vas a crearlo: ahí van las skills
   (`grilling`, `coherencia-docs`, `verification`, `frontend-design`, y las de
   §6) y las utilidades (`export_to_langfuse`, `measure`, `validate_sheet`).

Con esas cuatro respuestas te escribo el runbook del examen con los prompts
para la sesión constructora, igual que el del backend.
