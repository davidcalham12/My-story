# Runbook del examen — storyMaker, de `novaforge-v2` a la entrega

Plan estructurado para concretar el examen. Sin fecha de entrega confirmada,
va **por niveles con líneas de corte**: el nivel 0 es lo que aprueba; cada nivel
siguiente sólo empieza cuando el anterior está cerrado. Cuando el dueño dé la
fecha, los niveles se convierten en días.

Cada paso dice **quién** lo hace, **qué entra**, **qué sale**, **cuándo está
hecho**, y trae el **prompt** para la sesión que lo ejecuta. El proceso es el de
`AGENTS.md`: nada de código sin spec y plan aprobados; tests primero; docs en
el mismo commit.

Convenciones: **D** = dueño · **B** = sesión constructora de código · **N** =
`novaforge-05` (docs/specs/GitHub) · **Dis** = sesión de diseño.

---

## Nivel 0 — Lo que decide aprobar (cerrar antes que nada)

### 0.1 Nacimiento del repo `My-story` desde `novaforge-v2`

**Quién:** N. **Entra:** `novaforge-v2` rama `backend-v1`. **Sale:** este repo
con el harness dentro y `/docs` de arranque.

Qué copiar (no fork: el examen pide repo propio con historia propia):
`backend/`, `.claude/` entero (agentes, skill, hooks cuando existan), `config/`,
`specs/flow.yaml`, `specs/loops/LOOP-003/`, `specs/SPEC-*` y `PLAN-*` (son la
"spec inicial" y el razonamiento que el examen corrige), `docs/` completo,
`AGENTS.md`, `claude.md` → **`CLAUDE.md`**, `pyproject.toml`, `.github/`.
**No copiar** `output/` salvo `deep-space-salvage-derelict` (fixture) y el run
de LOOP-003 de 8 capítulos (evidencia). Añadir `.env.example` con `LANGFUSE_*`
sin valores y `.claude/mcp.json` con el browser MCP (Playwright).

**Hecho cuando:** `pytest` en verde en `My-story`; `CLAUDE.md` legible y en
mayúsculas; `docs/spec.md` existe (**antes** de cualquier código nuevo) y dice
qué se va a construir y por qué; el `README.md` apunta a todo.

Prompt:
> Lee `docs/HANDBOOK.md` y `docs/EXAM-RUNBOOK.md` §0.1. Trae desde
> `novaforge-v2` (rama `backend-v1`) exactamente lo listado, renombra
> `claude.md` a `CLAUDE.md`, añade `.env.example` y `.claude/mcp.json` con
> Playwright MCP, y escribe `docs/spec.md` —qué construimos y por qué— antes de
> tocar código. Corre los tests y dime el número.

### 0.2 El dominio cambia: regalo personalizado, 10 capítulos

**Quién:** N escribe la spec; D aprueba; B implementa. **Entra:** el enunciado
(`docs/EXAM-PLAN.md`). **Sale:** `SPEC-012-storymaker-domain.md` y su plan.

Cambios de dominio: género y tono **desde el brief** (ya no ciencia ficción);
perfil `gift` con `chapters: 10`, `words_per_chapter: 1000–1500`; el crítico
`science` pasa a **`brief-fidelity`** (¿la novela respeta los hechos del brief
y los integra con naturalidad?); `worldbuilder` + `character-architect` +
`plot-architect` se convierten en **planner** que además escribe la
**cronología** en SQLite. Nuevo rol **interviewer** (0.3). Perfil `final` con
`opus`/`sonnet`; runs de prueba en Haiku.

**Hecho cuando:** spec y plan aprobados en cabecera por D; una novela `gift`
de prueba (Haiku) sale completa.

### 0.3 El entrevistador y el brief con schema

**Quién:** B. **Entra:** SPEC-012. **Sale:** agente `interviewer`, JSON Schema
del brief, `POST /api/briefs`.

Recoge: destinatario (alias), edad, rasgos, recuerdos, género, tono,
extensión, palabras/temas prohibidos, ocasión, dedicatoria. Detecta faltantes y
**al menos una contradicción** (edad ↔ género/tono). El texto libre entra
**delimitado y marcado como no confiable**; sus hechos van a la bible con
`source = freetext`. El brief se valida con schema (`schema_brief`) antes de
aceptarse.

**Hecho cuando:** los cinco briefs de prueba (§0.7) pasan o se rechazan por el
motivo esperado; el nº 3 detecta la contradicción; el nº 4 no cambia el
comportamiento del sistema.

### 0.4 Story bible en SQLite con `fact_usage` y cronología

**Quién:** B. **Sale:** tablas `facts`, `fact_usage(fact_id, version_id, chapter_n)`,
`characters(canonical_name, birth_date…)`, `places`, `chronology(event, moment,
place, excludes_after)`, `chronology_participants`, `versions`, `forbidden_words`,
`audit_log`, `validations`. El planner las llena; el writer recibe la
**proyección** (hechos relevantes, personajes presentes según cronología,
resúmenes como hechos). **Checkpoint por capítulo**: estado persistido; si el
proceso muere, `POST /api/runs/{id}/resume` reanuda desde el último capítulo
completo (cierra §3.16 de `verification.md`).

**Hecho cuando:** `mandatory_facts` (cada hecho obligatorio del brief aparece
en ≥ 1 capítulo según `fact_usage`) pasa en una novela real; matar el proceso a
mitad y reanudar produce la misma novela sin duplicar capítulos.

### 0.5 Langfuse en vivo con scores

**Quién:** B. **Entra:** `tools/export_to_langfuse.py` de `my-factory` (hoy
exporta al final). **Sale:** exportación **durante** el run.

Sesión por novela (`session_id = novel_id`, agrupa entrevista + generación +
regeneraciones); traza por generación; span por rol y por tool con nombre
(`writer.ch03.attempt2`, `tool.forbidden_words`); tokens/coste/latencia por
span desde `usage`; **cada validador envía su score** a la traza; prompts
versionados. Host **US**. **PII enmascarada**: el nombre real del destinatario
nunca va a Langfuse; se usa `recipient_alias`.

**Hecho cuando:** una novela real aparece en Langfuse con sus spans, sus
scores y su coste, y el nombre del destinatario no aparece en ningún span.

### 0.6 Validadores programáticos y guardrails (tipo a)

**Quién:** B. Ya existen 13 instrumentos; se añaden los del examen:
`canonical_names` sobre el destinatario, `mandatory_facts`, **`forbidden_words`**
(tres niveles en SQLite: `global` semilla, `client`, `novel`; normalización
minúsculas/acentos/plural/variantes; coincidencia → hoja al writer con límite;
agotado → `halted: policy`; cada coincidencia → `audit_log` + score). **Dos
hooks**: `validate-chapter` (nombres, longitud, schema de salida) y `policy`
(palabras prohibidas + audit). Tools con schema (pydantic). **Tests**: uno por
nivel + acento + plural.

**Hecho cuando:** el brief nº 4 dispara el guardrail de nivel `client` y queda
en el audit log y en Langfuse.

### 0.7 Las cinco evals y la tabla con números

**Quién:** B corre; N documenta. **Entra:** `evals/briefs/01..05.json` (uno
normal hijo, uno pareja, uno con faltantes + contradicción, uno **adversarial**
con inyección en el texto libre, uno con **incoherencia temporal**). **Sale:**
`evals/results.md`: tabla brief × validador con pasa/falla y números; **una
iteración de tuning** con antes/después y versión de prompt en Langfuse.

**Hecho cuando:** la tabla existe con datos reales de cinco runs. **Esto es lo
que aprueba.**

### 0.8 La novela de ejemplo y `/docs` completo

**Quién:** B genera; N documenta. **Sale:** `ejemplos/novela-ejemplo.pdf` (10
capítulos, perfil **`final`**, brief del README), y `/docs` con: `spec.md`,
`trade-offs.md`, `explainers/`, `diagrams/`, `iterations.md` (parte de
`REPORT-backend-v1.md` y los LOOP), `red-team-log.md`, `verification.md`,
`skills.md`, `subagents.md`, `browser-mcp.md` (cuando exista).

**Hecho cuando:** `coherencia-docs` sin incidencias altas; cada fichero cita de
dónde sale cada afirmación.

**Línea de corte 0.** Con 0.1–0.8 el proyecto aprueba. Todo lo siguiente sube
nota.

---

## Nivel 1 — La experiencia del cliente

### 1.1 Frontend P0 de SPEC-009, adaptado al examen

**Quién:** D aprueba `PLAN-009`; B construye. Primero `frontend/DESIGN.md`
con `frontend-design` — **necesita el nombre de la identidad (Q7)**. Luego las
páginas de SPEC-009 más las del examen: **portada con dedicatoria**, **índice
navegable**, **ficha de personajes y lugares** desde la bible con enlace al
capítulo de primera aparición.

### 1.2 Cambio del lector con propagación y versiones

**Quién:** B. Seleccionar un hecho → `PATCH /api/facts/{id}` → `fact_usage` da
los capítulos → `versions(n+1, parent=n)` → se regeneran **sólo** esos, en
orden, con los resúmenes actualizados → todos los validadores + Lean (si ya
existe) → la web marca los capítulos cambiados; **la versión anterior se
conserva**. PDF regenerado con página de "novedades". **Es la demo obligatoria.**

### 1.3 Judge con rúbrica y revisión humana

**Quién:** B hace el judge; **D hace la revisión humana**. Rúbrica de 5
criterios (continuidad, tono, arco, coherencia de personajes, ritmo +
personalización natural), nota y justificación por criterio, score a Langfuse.
D lee una novela completa con la misma rúbrica; se compara en `evals/`.

**Línea de corte 1.** Con esto la demo se sostiene sola.

---

## Nivel 2 — Los formales y el browser

### 2.1 Lean 4 — cronología

**Quién:** B (skill `lean4` primero). Exportador `chronology → lean/Chronology.lean`;
tres invariantes sobre la cronología concreta (orden temporal; edad coherente
con nacimiento; nadie tras su evento excluyente), demostradas por
`decide`/`simp`; `lake build` en el gate de publicación; fallo → no se publica
→ feedback al editor. El brief nº 5 debe hacerlo saltar; si no, se documenta.

### 2.2 TLA+ — el harness

**Quién:** B (skill `tlaplus`). `tla/Harness.tla` (PlusCal vale): estados
configuración → planificación → escritura(ch) → validación(ch) → publicación(v)
| halted; `retries`, `checkpoint`, `ReaderChange`. Cuatro invariantes de
seguridad + una liveness; TLC con `Chapters=5, MaxRetries=2`, `.cfg` commiteado;
tabla acción ↔ código en el README; contraejemplos documentados con su fix.

### 2.3 Browser MCP y red-team

**Quién:** B. `visual_check` con Playwright MCP en el gate (índice, ficha,
portada renderizan); `docs/browser-mcp.md` con qué inspeccionó, qué detectó y
qué cambió. `docs/red-team-log.md` con el brief nº 4 y la inyección por argv ya
documentada.

**Línea de corte 2.** Con esto están los cuatro tipos de validador.

---

## Nivel 3 — Entrega

### 3.1 Presentación (10 min) y presupuesto

**Quién:** Dis diseña con D; N monta. Identidad corporativa (la de Q7). Los
bloques del examen con sus tiempos. **Slide de presupuesto**: coste por novela
desde Langfuse con perfil `final` (media y rango), infraestructura, margen,
precio, horas de desarrollo × tarifa, tres volúmenes, sensibilidad (tokens +50 %,
más de 3 revisiones). Anexos: TLA+ comentado, tabla de evals, esquema SQLite,
red-team, capturas de Langfuse. Deck en PDF + editable; `presentacion/README.md`.

### 3.2 Vídeo y email

Demo del cambio del lector propagado, en la web o en el PDF regenerado.
Email a la dirección del enunciado con los dos links de commit final y la
frase de la decisión más importante (tres candidatas en `EXAM-PLAN.md` §10).

---

## Opcional (sólo si sobra)

Servidor MCP con FastMCP (`list_novels`, `get_chapter`, `list_versions`,
`query_story_bible`, `download_novel`), linters de prosa, login, agente de
seguridad. Cada uno con su skill.

---

## Reglas transversales

- **Modelos:** Haiku en todo run de prueba; perfil `final` (Opus autores,
  Sonnet críticos) sólo para `novela-ejemplo.pdf` y la slide de coste. El
  orquestador cuesta ~$1 por turno inicial: cada run de prueba innecesario es
  un dólar.
- **Cuota:** Sonnet 5 para vigilancia y tareas mecánicas; Fable para diseño.
- **Cada tecnología nueva → skill antes de la primera línea** (`lean4`,
  `tlaplus`, `langfuse`, `playwright-mcp`, `html-to-pdf`, `pydantic`).
- **Cada enlace de la profesora → `my-factory/references/`**, fechado.
- **Buzón:** `docs/handoff/` aquí igual que en `novaforge-v2`; actualizar al
  cerrar cada bloque.
- **Sin datos reales de personas** en briefs de prueba, trazas ni repo.

## Qué falta del dueño para convertir niveles en días

Fecha de entrega · nombre de la identidad · web+PDF · Java/elan en la VM.
