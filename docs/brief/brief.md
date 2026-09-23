# NovaForge v2 — documento de arranque para la sesión que construye

**Versión final.** Escrito para una sesión de Claude Code que empieza **sin
historial** en la máquina donde vive la copia actual del proyecto
(`C:\Users\student\Desktop\novaforge`, commit `b61b5b7`). Contiene todas las
decisiones ya tomadas —las 23 del anexo A, ninguna abierta—, las skills que hay
que instalar con sus comandos, la estructura del repo nuevo, las garantías que no
se negocian y el orden de trabajo.

Fecha: 2026-09-21. Idioma: el usuario escribe en español; **todo lo que entra en
el repositorio va en inglés** (documentación, código, comentarios, prompts).

---

## 0. Cómo usar este documento

1. Léelo entero antes de tocar nada.
2. Lee después, en este orden: el documento de traspaso vigente del proyecto
   actual (el que empieza por *"NovaForge — contexto completo para retomar el
   trabajo"*, fecha 2026-09-21), `specs/loops/LOOP-003/README.md`, y los tres
   artifacts de la profesora (§1.2).
3. Ejecuta el **paso 0** (skills, §2) antes de crear el repo. Es un requisito de
   la profesora.
4. Sigue el orden de trabajo de §8. Cada fase tiene su criterio de "hecho".
5. Cuando algo de aquí contradiga lo que encuentres en el disco, **el disco es el
   hecho y este documento es la intención**: dilo y sigue con la intención salvo
   que rompa una garantía de §5.
6. **No hay preguntas pendientes.** Todo lo que necesitabas decidir está en §3.
   Si encuentras una decisión que no está, tómala por la opción más simple,
   escríbela en `docs/architecture.md` bajo "decisiones tomadas al construir", y
   sigue.

---

## 1. Contexto en diez líneas

NovaForge es un harness multiagente que escribe novelas. Su afirmación central:
**el escritor de un capítulo nunca recibe la prosa de un capítulo anterior**;
recibe la Biblia de la historia, su entrada del guion y un resumen acotado.

Lo que existe hoy (rama `claude-orchestrator`): nueve agentes como subagentes de
Claude Code, un gate de cinco características con tres oportunidades escaladas
(LOOP-003), un panel React que ya lanza novelas vía `claude -p`, ocho novelas en
disco, y dos costes reales medidos. Funciona. Pero el orquestador es una sesión
de Claude Code, el "backend" son plugins de un servidor de desarrollo, no hay
base de datos, hay una segunda implementación del pipeline en el navegador que
ya divergió, y **el coste real es 8 veces el estimado** porque los turnos del
orquestador no se miden.

La profesora pide **el mismo proyecto como si se hiciera de cero**: el
conocimiento se queda, el código se rehace con FastAPI + React + SQLite, un tope
de contexto de 100.000 tokens, y una documentación de arranque en `docs/`.

### 1.1 Requisitos de la profesora, literales

- Repo nuevo. Carpeta `docs/` con `definitions.md`, `domain-knowledge.md`,
  `architecture.md`. En la raíz, `agents.md` y `claude.md`.
- `architecture.md` recoge **lo que no es estrictamente definición ni
  conocimiento del dominio**: el sistema frontend + backend con las tecnologías
  indicadas, **la lista de agentes y sus skills**, y **el proceso**.
- FastAPI para el backend. React para el frontend.
- **Límite de contexto del modelo: 100.000 tokens.**
- SQLite, compatible con búsqueda vectorial (`sqlite-vec`).
- Backend: **una carpeta por feature, más una carpeta `commons`**.
- Frontend: **Feature-Sliced Design**.
- **Cada tecnología, librería o framework que se añada al proyecto implica
  añadir una skill de esa tecnología** para que el agente sepa usarla.
- `verification.md` (= validation = evaluation): se genera con una skill
  construida a partir del artifact de metodologías de verificación (§1.2),
  pasándole el contexto actual como semilla.
- Usar la skill *grill me* para ir refinando los documentos con preguntas.

### 1.2 Fuentes externas

| qué | dónde |
|---|---|
| Ontología — definiciones | https://claude.ai/artifact/4SxM2Tuc3UwihHoxGu9K4y |
| Ontología — diagramas Mermaid | https://claude.ai/artifact/9gn89g44w6F5xYRa8LMm2M |
| Metodologías de verificación (para la skill) | https://claude.ai/artifact/Rass3RVfaN5KSJDdG2FQhR |
| Feature-Sliced Design | https://feature-sliced.design/docs/get-started/overview |
| FSD — docs para LLMs | https://feature-sliced.design/docs/llms |
| FSD — skill oficial | https://github.com/feature-sliced/skills |
| SQLite — skill | https://github.com/SecureSkills-io/sqlite-skill |
| grill-me / grilling — skill | https://github.com/mattpocock/skills |
| frontend-design — skill | https://github.com/anthropics/skills |

La ontología define: entidades (Work, World, Character, Faction, Location,
Scene, Chapter, Beat…), capas de anatomía (premisa → guion → beats → prosa),
**capas de contexto** (Canon fijo, estado rodante, libro de continuidad, libro
de pistas sembradas, *knowledge-state* por personaje, y el **Scene Context
Packet** que las reúne), nueve dimensiones de calidad y cinco puertas. Casi todo
NovaForge ya está ahí con otro nombre; lo que no tiene es el *knowledge-state*
por personaje —que la ontología señala como la fuente más común de errores de
continuidad— y el libro de pistas.

---

## 2. Paso 0 — Skills

**Regla de la profesora, permanente:** cada tecnología que entre en el proyecto
lleva su skill. Se escribe en `claude.md`.

**Regla de seguridad, permanente:** toda skill se **lee entera antes de
instalarse**. Una skill es texto con instrucciones; si contiene código que se
ejecute, scripts que descarguen cosas, o pide credenciales, no se instala y se
avisa. Se anota la fuente y la licencia de cada una en `docs/architecture.md`.

Las skills de usuario van en `~/.claude/skills/<nombre>/SKILL.md`
(Windows: `C:\Users\<usuario>\.claude\skills\`). Un SKILL.md lleva front matter
YAML con `name` y `description`, y debajo las instrucciones. Al escribirlas en
Windows, **no usar `Set-Content` sin cuidar el BOM** (ya corrompió guiones em en
dos ficheros de agente): usar `Out-File -Encoding utf8` o el editor.

### 2.1 Lista completa — diez skills

| # | skill | origen | cómo |
|---|---|---|---|
| 1 | `grill-me` | mattpocock/skills (MIT) | copiar `skills/productivity/grill-me/SKILL.md` |
| 2 | `grilling` | mattpocock/skills (MIT) | copiar `skills/productivity/grilling/SKILL.md` — `grill-me` es un atajo que llama a esta; **hay que instalar las dos** |
| 3 | `frontend-design` | anthropics/skills | copiar `skills/frontend-design/SKILL.md` |
| 4 | `feature-sliced-design` | feature-sliced/skills | `npx skills add https://github.com/feature-sliced/skills --skill feature-sliced-design` |
| 5 | `sqlite` | SecureSkills-io/sqlite-skill | según el README del repo; leerla entera antes |
| 6 | `sqlite-vec` | la profesora la nombró **sin URL** | localizarla en los marketplaces de skills de Claude Code; comprobar que enseña `sqlite-vec` real (tabla virtual `vec0`, embeddings como BLOB, consulta KNN). Si no hay una fiable, escribirla desde la documentación oficial de `sqlite-vec` |
| 7 | `verification` | **se construye** desde el artifact de la profesora | ver §2.2 |
| 8 | `fastapi` | buscar oficial o de referencia; si no, escribirla | mínima: convenciones, arranque, tests, errores típicos |
| 9 | `react` | ídem | ídem |
| 10 | `sentence-transformers` | ídem | la añade la decisión D16 (embeddings locales); ídem |
| 12 | `tdd` | mattpocock/skills (`skills/engineering/tdd/` — SKILL.md + `tests.md` + `mocking.md`) | red → green por rebanadas verticales; tests sólo en *seams* acordados; sin tautologías. Es el TDD que exige `agents.md` §4.4, con criterio |
| 13 | `writing-for-agents` | mattpocock/skills (`skills/productivity/writing-for-agents/` — SKILL.md + `SKILL-MECHANICS.md`) | cómo escribir `CLAUDE.md`, `AGENTS.md` y skills: punteros de contexto, jerarquía de información, poda. **`CLAUDE.md` es parte del examen**; esta skill es la que lo hace bien |
| 14 | `code-review` | mattpocock/skills (`skills/engineering/code-review/SKILL.md`) | revisión en dos ejes con subagentes: estándares del repo y fidelidad a la spec. Encaja con el paso 9 del runbook; la spec se le pasa por ruta |
| 15 | `handoff` | mattpocock/skills (`skills/productivity/handoff/SKILL.md`) | compacta una conversación en un documento de traspaso, redactando secretos y PII. Para pasar contexto entre la sesión de diseño y la constructora |
| 16 | `ponytail` | DietrichGebert/ponytail (`skills/ponytail/SKILL.md`, MIT) — **sólo la skill, no sus hooks de Node** | "el mejor código es el que no se escribe": escalera YAGNI → ya existe → stdlib → nativo → dependencia instalada → una línea → mínimo. Es la lección de la profesora "no siempre lo agéntico es mejor" convertida en reflejo. Nunca perezosa con validación en fronteras de confianza, seguridad ni lo pedido explícitamente |
| — | `to-spec` (no instalada) | mattpocock/skills | publica a un gestor de incidencias que no usamos. **Se toma su plantilla** para las `SPEC-*`: Problem · Solution · User Stories · Implementation Decisions (sin rutas ni código) · Testing Decisions · Out of Scope |
| 11 | `coherencia-docs` | maujimenez4/MyFactory (`.claude/Skills/coherencia-docs/SKILL.md`) | copiar el `SKILL.md`. Revisa la coherencia entre `definitions`, `domain-knowledge`, `architecture`, `verification` y `CLAUDE.md`: referencias rotas, contradicciones, deriva de términos, estado obsoleto, requisitos sin letra. Informe → plan → edición sólo con aprobación. **Crear `docs/_authority.md`** con nuestra tabla de autoridad (ver runbook, paso 2) para adaptarla sin modificar la skill |

Rutas de descarga directa de las tres primeras:

```
https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grill-me/SKILL.md
https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/grilling/SKILL.md
https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md
```

Cuando entre cualquier otra dependencia (una librería de SSE, una de gráficos,
un cliente HTTP…), misma regla: skill antes de la primera línea que la use.

### 2.2 Construir la skill `verification`

1. Leer el artifact de metodologías de verificación (§1.2). Contiene tres
   bloques: **8 métodos de verificación de artefactos** (type checking, análisis
   estático, ejecución simbólica, verificación formal, tests unitarios y de
   integración, property-based, mutation, contract testing); **11 de
   verificación de procesos de agentes** (trazabilidad en tiempo de ejecución,
   evals, sandbox, guardrails, revisión humana, verificación multiagente, CI/CD,
   despliegue progresivo, red-teaming, model checking); y la clasificación
   **T/A/I/D/U** por requisito: *Test, Analysis, Inspection, Demonstration,
   Unverifiable*.
2. Escribir `~/.claude/skills/verification/SKILL.md`: una skill que, dado un
   contexto de sistema, **produce un `verification.md`** que lista cada garantía
   del sistema, le asigna su letra T/A/I/D/U, dice con qué método se verifica y
   qué evidencia deja. El artifact es un catálogo neutro sin criterio de
   selección; **el criterio lo pone la skill**: preferir Test sobre Analysis,
   Analysis sobre Inspection, y declarar *Unverifiable* sin vergüenza cuando lo
   sea.
3. Usarla en la Fase 1 (§8) para generar `docs/verification.md` con este
   documento y las garantías de §5 como semilla.
4. **Anexo D manda sobre el criterio:** `verification.md` lleva epígrafe de
   *best effort*, nivel de criticidad por garantía (fija la letra mínima), la
   sección de **huecos conocidos y riesgos asumidos**, la tabla "código antes
   que agente" y qué propagación frena cada validador.

---

## 3. Decisiones cerradas

Las 23 se cerraron con el usuario en dos rondas de *grill* (anexo A tiene cada
pregunta con su porqué). **Ninguna está abierta.**

### 3.1 Arquitectura

| # | decisión | elección |
|---|---|---|
| D1 | Desde dónde nace el repo | la copia actual en `student`; la de la otra máquina es vieja |
| D2 | Qué es FastAPI | ~~el orquestador, en Python, llamando a la API de Anthropic~~ **ANULADA (Anexo C): no hay API key. Claude Code orquesta ejecutando `SKILL.md`; FastAPI lanza `claude -p`, observa el stream y persiste.** Arrastra D7, D8, D13, D14, D17, D19, D20, D23 — ver Anexo C §4 |
| D3 | `generate.ts` (pipeline en el navegador) | **se elimina**; una sola implementación |
| D4 | Nombre del repo | `novaforge` |
| D5 | Features del backend | `runs`, `bible`, `outline`, `chapters`, `style`, `publish` + `commons` |
| D6 | Usuarios | uno, local, sin autenticación, cola de tamaño 1; **`run_id` en todas las tablas** |
| D7 | Dónde vive el procedimiento | `specs/flow.yaml` cargado por Python; números en `config/*.json`; **cero literales en el orquestador** |
| D8 | Prompts de los agentes | Markdown en `backend/<feature>/prompts/<agent>.md`, cargados por Python |
| D9 | Cómo ejecuta el backend una novela | tarea en segundo plano en el mismo proceso; **estado persistido en SQLite tras cada etapa y cada intento** |
| D10 | Progreso en vivo | **SSE** (`StreamingResponse`) |
| D11 | Idioma de la documentación | inglés |
| D12 | Herramientas | Python 3.12 + `uv` + `pytest`; Node 20 + `npm` + `vitest`; CI en GitHub Actions con el motor mock |

### 3.2 Contexto, coste y modelo

| # | decisión | elección |
|---|---|---|
| D13 | A qué se aplica el tope de 100k | **a la suma de tokens en vuelo en el mismo instante** (la profesora dijo *concurrentes*): semáforo de tokens antes de cada llamada, reserva = prompt + `max_tokens`; una reserva mayor que la capacidad es error del run. Ver Anexo B §2 |
| D14 | Cómo se traduce la lista `tools:` a código | cada agente recibe un **`ContextPacket` tipado**; el del escritor **no tiene campo** para prosa previa; un test lo comprueba; el tamaño del prompt se registra por capítulo |
| D15 | Forma del resumen rodante | **lista de hechos estructurados** `{hecho, capítulo, tipo}`, tope por número de hechos, convertida a texto al entrar en el prompt |
| D16 | Embeddings para `sqlite-vec` | **modelo local** (`sentence-transformers`), coste cero, funciona en CI; detrás de una interfaz por si se cambia |
| D17 | Qué recuperan los críticos por vector | **continuidad** recupera fragmentos de personajes, cronología y resumen; **ciencia** recibe `## Rules` **entero**; **guion** recibe su entrada del outline entera |
| D18 | Esquema del *knowledge-state* por personaje | tabla `character_knowledge(run_id, character, fact_id, learned_in_chapter)` **creada ya, vacía**, apuntando a los hechos de D15 |
| D19 | Modelos | Opus para los cuatro autores, Sonnet para los cinco críticos/editores; `pricing.json` se conserva; el coste pasa de acotado a **exacto** (input/output separados) |
| D20 | Presupuesto | **techo comprobado antes de cada llamada**; superarlo **detiene el run** con `halted: budget`, lo generado queda consultable |

### 3.3 Datos y calidad

| # | decisión | elección |
|---|---|---|
| D21 | Acceso a la base de datos | `sqlite3` de la librería estándar + migraciones SQL numeradas; **sin ORM** |
| D22 | Las ocho novelas existentes | **se importan a SQLite**; el importador es la primera prueba del esquema |
| D23 | Motor simulado | **sí, y que respete la premisa**; las garantías de §5 son tests que corren a $0 |
| D24 | Instrumentos de LOOP-003 | **se portan a Python**; los `.mjs` quedan como referencia hasta que los `--self-test` den lo mismo; el validador de la hoja corre *dentro* del pipeline |
| D25 | Problemas abiertos que entran en v1 | **auditar el guion contra `## Rules` antes de FLOW-4** y corregir §2 de LOOP-003; el resto a v2 |
| D26 | `verification.md` | cada garantía de §5 con su letra T/A/I/D/U, método y evidencia; la reproducibilidad del gate es *Demonstration* para "este run pasó" y *Unverifiable* para "este texto pasa" |

### 3.4 Frontend

| # | decisión | elección |
|---|---|---|
| D27 | Portar o rehacer | **portar la lógica** (tipos, derivaciones, procedencia) a `entities`/`shared`; **rehacer la capa visual** con `frontend-design` |
| D28 | Páginas FSD | `library` · `new-novel` · `run` · `quality` · `manuscript` · `diagram` |
| D29 | Features / entities / shared | features: `start-run`, `watch-progress`, `configure-novel`, `compare-runs` · entities: `run`, `chapter`, `critique`, `agent`, `provenance` · shared: cliente API, kit UI, utilidades. `presentation` y `configurator` actuales se funden en `new-novel` y `run` |

---

## 4. Estructura del repo nuevo

```
novaforge/
├── claude.md                    instrucciones para Claude Code (§6)
├── agents.md                    los nueve agentes: rol, modelo, contexto que recibe, skills
├── README.md
├── docs/
│   ├── definitions.md           el diccionario (de la ontología, adaptado)
│   ├── domain-knowledge.md      lo que se sabe del dominio y lo aprendido en los runs
│   ├── architecture.md          stack, features, agentes+skills, proceso, límites, skills instaladas
│   └── verification.md          garantías con T/A/I/D/U (generado por la skill)
├── specs/
│   ├── flow.yaml                las seis etapas; lo carga el backend
│   └── loops/                   LOOP-003 y los que vengan, con sus instrumentos en Python
├── config/
│   ├── novel.config.json        la base completa
│   ├── profiles/                tiny · small · medium · full · stress
│   └── pricing.json
├── backend/
│   ├── commons/
│   │   ├── llm/                 cliente Anthropic + motor mock; devuelve texto y uso de tokens
│   │   ├── context/             ContextPacket por agente, constructor, contador de 100k
│   │   ├── budget/              techo de coste por run, comprobado antes de cada llamada
│   │   ├── db/                  sqlite3, migraciones SQL, sqlite-vec, embeddings locales
│   │   ├── config/              carga de flow.yaml + config + perfiles
│   │   └── log/                 una fila por llamada: agente, tokens in/out, coste, duración, ts real
│   ├── runs/                    crear, listar, estado, SSE de progreso, importador de runs viejos
│   ├── bible/                   FLOW-1 y FLOW-2
│   ├── outline/                 FLOW-3 + auditoría del guion contra ## Rules (D25)
│   ├── chapters/                FLOW-4: escritor, cinco críticos, gate, hoja, tres oportunidades
│   ├── style/                   FLOW-5
│   ├── publish/                 FLOW-6: sinopsis + ensamblado en código, nunca por un agente
│   └── tests/                   con motor mock; corren en CI a $0
├── frontend/                    React + Vite + TS, Feature-Sliced Design
│   └── src/
│       ├── app/
│       ├── pages/               library · new-novel · run · quality · manuscript · diagram
│       ├── widgets/
│       ├── features/            start-run · watch-progress · configure-novel · compare-runs
│       ├── entities/            run · chapter · critique · agent · provenance
│       └── shared/              api · ui · lib
└── output/                      prosa y Biblia en Markdown, por slug (la BD guarda lo estructurado)
```

**Qué guarda SQLite y qué se queda en disco:** la base es el sistema de registro
de runs, llamadas, notas, hallazgos, hojas, decisiones del gate, hechos del
resumen, tokens y coste. La prosa y la Biblia siguen en Markdown en
`output/<slug>/`, referenciadas por ruta. Tabla de embeddings por fragmento con
clave a la fila de origen, para `sqlite-vec`. Tabla `character_knowledge` creada
vacía (D18).

---

## 5. Garantías que hay que preservar

Vienen del proyecto actual y **no se negocian** al rehacer. Cada una entra en
`verification.md` con su letra.

1. **El escritor no recibe prosa previa.** Ahora: el `ContextPacket` del escritor
   no tiene campo para ello (tipo) + test que falla si el constructor lo incluye
   + tamaño del prompt registrado por capítulo, que debe salir plano.
2. **Tope de 100.000 tokens concurrentes**: un semáforo de tokens en
   `commons/context/`; cada llamada reserva prompt + `max_tokens` antes de
   despachar y espera si no hay capacidad; una reserva mayor que la capacidad es
   un error del run, no una advertencia. Ver Anexo B §2.
3. **Cinco características, cada una 0–10, todas ≥ 8**, agregación `min`:
   continuity, science, outline (10 − 3 por beat ausente − 1 por beat fuera de
   orden), length (`wc -w`, 10 en banda / 0 fuera), chatter (0 si no empieza
   por `# Chapter`). Dos son aritmética y reproducen; tres son modelo y no.
4. **Tres oportunidades, escaladas**: intento 2 recibe la hoja nivel 1 (cita,
   qué falla, contra qué, cómo debe quedar descrito); intento 3 recibe la
   frase literal de reemplazo. `on_fail` = **`patch_then_halt`**: el orquestador
   aplica los reemplazos (arbitrándolos antes) y repuntúa; si aun así falla,
   **el run se detiene**. Nunca `accept_with_warnings`.
5. **Las cuatro reglas del redraft**, cada una aprendida fallando: devolver el
   borrador y no sólo los hallazgos; pedir sustituciones `{find, replace, why}`
   aplicadas literalmente; un crítico sin veredicto usable se excluye, no cuenta
   como 10 ni como 0; se queda el mejor borrador, no el último.
6. **La hoja de retroalimentación**: las cinco notas siempre; lista de NO TOCAR;
   cuatro campos por hallazgo o no se envía; lista de RESUELTO; todos los
   hallazgos, peor primero; validada antes de enviar; nunca cita prosa de un
   capítulo anterior; guardada por `slug`.
7. **Lo prohibido de LOOP-003 §8.3**: bajar el 8, menos de cinco características,
   un cuarto intento, recortar hallazgos, enviar una hoja no validada, cambiar la
   hoja y la fórmula de outline en el mismo capítulo.
8. **Sólo dos agentes escriben la Biblia** (worldbuilder, character-architect).
   Los demás devuelven texto y el orquestador escribe.
9. **El libro se ensambla en código**, nunca por un agente.
10. **El guion se audita contra `## Rules` antes de escribir** (D25): un beat
    que encargue algo que el mundo prohíbe se rechaza antes de FLOW-4.
11. **Procedencia en cada cifra**: `measured` · `reported` · `reconstructed` ·
    `estimated` · `absent`. Lo no medible se dice no medible, nunca cero.
12. **El coste no se inventa.** Con la API directa es exacto; para los runs
    importados sigue siendo `low / estimate / high` con el sello `reconstructed`.
13. **Techo de presupuesto antes de cada llamada** (D20). Superarlo detiene.
14. **Ningún agente declara género**: el género sale de la premisa.
15. **Ningún prompt pide un rango sin criterio** (lección de la profesora):
    cuando se pide una cantidad, se dice con qué regla se decide.
16. **Seguridad**: credenciales sólo del entorno, nunca en ficheros ni en argv;
    tareas por stdin; rutas servidas comprobadas sobre la ruta normalizada;
    ninguna escritura en PowerShell sin cuidar el BOM.

---

## 6. `claude.md` y `agents.md` — qué deben contener

> **Corrección (Anexo B §1):** `agents.md` es el `AGENTS.md` estándar — el
> proceso de trabajo de la IA que programa el repo (docs → spec aprobada → plan
> aprobado → código con TDD). **No** es el catálogo de los nueve agentes de la
> novela: ese catálogo, con la tabla de campos de abajo, va en
> `docs/architecture.md`. Lo que sigue se lee con esa corrección.

**`claude.md`** (lo lee Claude Code al abrir el repo):

- Qué es el proyecto en tres líneas y la afirmación central.
- Idioma: repo en inglés.
- Cómo levantar backend, frontend y tests; que los tests corren con el motor
  mock y cuestan $0; que el motor real requiere la variable de entorno y **nunca
  una clave en el chat ni en un fichero**.
- La regla "cada tecnología nueva → su skill, antes de usarla".
- Que `specs/flow.yaml` y `config/` mandan sobre el código; que el orquestador
  no contiene literales de estructura ni de números.
- Las garantías de §5 en forma de lista corta, con enlace a `verification.md`.
- Lo que no se toca sin decisión explícita: el 8, las cinco características, el
  `ContextPacket` del escritor, `patch_then_halt`, el techo de 100k.

**`agents.md`** — una ficha por agente, nueve:

| campo | qué va |
|---|---|
| nombre y etapa | `worldbuilder` / FLOW-1, etc. |
| modelo | opus / sonnet |
| qué recibe | los campos de su `ContextPacket`, uno a uno |
| qué devuelve | el contrato de salida (formato exacto, envoltorio JSON si lo hay) |
| qué escribe | sólo los dos de la Biblia; el resto "nada, devuelve texto" |
| skills | las que usa |
| lo que nunca ve | para el escritor: prosa previa; para el crítico de ciencia: nada fuera de `## Rules` |

La lista de agentes con sus skills va **también** en `architecture.md`, porque
la profesora lo pidió ahí explícitamente.

Los nueve: `worldbuilder` (FLOW-1, opus), `character-architect` (FLOW-2, opus),
`plot-architect` (FLOW-3, opus), `chapter-writer` (FLOW-4, opus),
`continuity-critic`, `science-critic`, `outline-critic` (gate, sonnet),
`style-editor` (FLOW-5, sonnet), `publisher` (FLOW-6, sonnet).

---

## 7. Qué se traslada y qué no

**Se traslada (conocimiento):** `specs/flow.yaml` y su división de propiedad;
`config/` entero incluidos los cinco perfiles y `pricing.json`; el contenido de
los nueve prompts de agente (sin el front matter); todo LOOP-003 con sus dos
instrumentos y sus dos runs; la plantilla de la hoja; las ocho novelas de
`output/`; `types.ts`, `derive.ts` y la semántica de procedencia del panel; el
diagrama Mermaid corregido; las dieciséis lecciones de §8 del traspaso actual
(cada una con su causa raíz).

**No se traslada (código):** los plugins de Vite; `generate.ts`; `orchestrate.ts`
y `claude.ts` (la ruta por `claude -p`); `.claude/skills/novaforge/SKILL.md` como
procedimiento ejecutable — su contenido se **traduce** a Python paso a paso, y
cada paso traducido se marca en un checklist para que no se pierda ninguno de los
dieciséis arreglos.

**Se corrige al trasladar:** §2 de LOOP-003 (el capítulo 3 del test no falló por
el escritor: el beat 7 era imposible); el log escribe timestamps reales por
llamada y `duration_ms`; se guardan los borradores rechazados; el resumen pasa a
hechos estructurados (D15).

---

## 8. Orden de trabajo

Cada fase termina con algo que se puede enseñar. No se pasa a la siguiente sin
cerrar el criterio de "hecho".

**Fase 0 — Skills.** §2 completo. *Hecho:* las diez skills instaladas, cada una
leída, con fuente y licencia anotadas en `docs/architecture.md`.

**Fase 1 — Documentos.** Repo nuevo; `docs/definitions.md` y
`docs/domain-knowledge.md` a partir de la ontología y del traspaso actual;
`docs/architecture.md` con §3, §4, §6 y la lista de agentes con skills;
`docs/verification.md` generado con la skill de verificación; `claude.md` y
`agents.md`. Después, **una sesión de *grill me* sobre los cuatro documentos**
hasta que la frontera esté vacía; las respuestas se incorporan a los documentos.
*Hecho:* los documentos aguantan una ronda de preguntas sin huecos y la
profesora los puede leer.

**Fase 2 — Backend, con mock.** `commons` entero (llm con mock que respeta la
premisa, context + contador de 100k, budget, db + esquema + migraciones +
importador, config, log). Después las seis features en orden de `flow.yaml`,
cada una con sus tests sobre el mock, y los instrumentos de LOOP-003 portados.
*Hecho:* una novela `tiny` completa con el motor mock en CI, con las garantías
1–10 y 13–15 de §5 como tests que pasan, y las ocho novelas viejas importadas y
consultables.

**Fase 3 — Motor real.** Cliente Anthropic detrás de la bandera, coste exacto
por llamada, techo comprobado antes de cada una. *Hecho:* una novela `tiny` real
con coste exacto registrado; comparar contra los $7,45 del run equivalente
actual y explicar la diferencia.

**Fase 4 — Frontend.** Plan de tokens con `frontend-design` **antes** de
codificar; estructura FSD (D28, D29); portar `entities` y `shared` desde la
lógica actual; pantallas contra la API, progreso por SSE. *Hecho:* lanzar `tiny`
desde el botón, verlo avanzar, abrirlo en la Biblioteca y en Calidad.

**Fase 5 — Vector.** `sqlite-vec` + embeddings locales, Biblia y resúmenes
indexados, el crítico de continuidad recuperando fragmentos (D17). *Hecho:*
tokens por crítico antes y después, medidos, en el mismo run con la misma
premisa.

**Fase 6 — Lo abierto de v1.** Auditoría del guion contra `## Rules` antes de
FLOW-4 (D25). *Hecho:* el perfil `stress` ya no muere en el capítulo 3 por un
beat imposible: lo rechaza la auditoría antes de escribir.

---

## 9. Lo que NO hay que hacer

- No arrancar desde la copia vieja (la de un solo run y sin `web/`).
- No empezar a codificar sin las skills de la Fase 0.
- No mantener dos implementaciones del pipeline. Una, en Python.
- No añadir literales de estructura ni de números al orquestador: vienen de
  `flow.yaml` y `config/`.
- No dar al escritor ningún camino a prosa previa, ni "para debug".
- No aceptar un capítulo con advertencias. `patch_then_halt`.
- No inventar coste ni tokens: procedencia en cada cifra.
- No pedir ni escribir claves. Entorno, siempre.
- No pedir rangos sin criterio en ningún prompt.
- No tocar el 8, las cinco características ni el tercer intento sin registrarlo
  como cambio formal.
- No meter un ORM, una librería o un framework sin su skill.
- No dejar el estado del run sólo en memoria: a la base tras cada etapa e
  intento.

---

## Anexo A — Las 23 preguntas del *grill* y sus respuestas

Registro de cómo se llegó a §3, para que la sesión constructora vea el porqué y
no reabra lo cerrado. Todas las respuestas fueron "de acuerdo con la
recomendación".

**Ronda 1**

1. **Desde qué copia arranca el repo.** La copia viva está en `student`; la otra
   es vieja (un run, sin `web/`, sin git). → Desde `student`. *Perderíamos el
   outline-critic, las cuatro reglas del redraft, los validadores y los ocho
   runs si naciera de la copia vieja.*
2. **Qué es FastAPI respecto al orquestador.** → El orquestador mismo, en Python,
   llamando a la API. *El factor 8 del coste son turnos de orquestador sin medir;
   en Python el orquestador es código y cada token se cuenta; el tope de 100k
   sólo lo garantiza quien monta el prompt; dos implementaciones ya divergieron.
   Se pierde el aislamiento "por herramientas" y se cambia por tipos + test +
   contador por llamada.*
3. **A qué se aplica el tope de 100k.** → Al prompt de cada llamada, contado
   antes de enviar. *Es el Scene Context Packet en número; convierte la tesis
   "el capítulo 34 mide lo que el 1" en una serie medida.*
4. **Para qué la búsqueda vectorial.** → Que los críticos recuperen fragmentos en
   vez de recibirlo todo; esquema preparado para el knowledge-state por
   personaje. *Única opción que reduce contexto y coste a la vez; los críticos
   son el 51% del gasto.*
5. **Usuarios.** → Uno, local, sin autenticación, cola de 1, `run_id` en todo.
   *Proyecto de curso; que escalar sea configuración.*
6. **Nombre del repo.** → `novaforge`.
7. **Features del backend.** → Una por etapa de `flow.yaml` más `runs` y
   `commons`. *Cada carpeta tiene un agente dueño; lo que nadie debe saltarse
   —100k y coste— vive en commons.*
8. **Motor simulado.** → Sí, y que respete la premisa. *El de `main` la ignoraba
   y por eso nunca demostró nada; con mock las garantías son tests a $0.*
9. **Qué problemas abiertos entran en v1.** → Auditar el guion contra las reglas
   y corregir §2 de LOOP-003. *Causa raíz del run muerto en el test de estrés;
   el resto es diseño del gate y va a su propio loop.*
10. **Frontend: portar o rehacer.** → Portar la lógica, rehacer la capa visual.
    *La procedencia y las derivaciones son lo que costó aprender; la fuente de
    datos cambia de ficheros a API.*
11. **Las ocho novelas.** → Se importan. *Únicos datos reales; el importador
    prueba el esquema.*

**Ronda 2**

12. **Progreso en vivo.** → SSE. *Sólo hace falta backend → navegador.*
13. **Forma del resumen rodante.** → Lista de hechos estructurados con tope por
    número. *Un tope por número es contable; un tope de palabras no lo era; cada
    hecho lleva su capítulo de origen.*
14. **Embeddings.** → Modelo local. *Coste cero, sin red, funciona en CI; volumen
    pequeño; detrás de una interfaz.*
15. **Qué recuperan los críticos.** → Continuidad recupera; ciencia recibe todas
    las reglas; guion recibe su entrada entera. *Una regla no recuperada es una
    violación no vista: ahí manda la exhaustividad.*
16. **Base de datos.** → `sqlite3` estándar, sin ORM. *Diez tablas; sqlite-vec es
    una tabla virtual que los ORM manejan mal; cada dependencia es una skill.*
17. **Instrumentos de LOOP-003.** → Portar a Python. *Un solo lenguaje; el
    validador de la hoja corre dentro del pipeline.*
18. **Páginas y features FSD.** → Las de D28 y D29. *El panel actual reordenado
    por capas.*
19. **Esquema del knowledge-state.** → Tabla creada ya, vacía. *Crearla ahora es
    una migración; después es rehacer el importador.*
20. **Letra T/A/I/D/U del gate.** → Demonstration / Unverifiable. *Tres de cinco
    características son juicio de un modelo; decir Test sería mentir.*
21. **Cómo ejecuta el backend un run.** → Tarea en el mismo proceso, estado en
    SQLite tras cada etapa e intento. *Con cola de 1 nada justifica un
    trabajador aparte; hoy `state.json` sólo existe al final.*
22. **Herramientas.** → Python 3.12 + uv + pytest; Node 20 + npm + vitest;
    GitHub Actions con mock. *Convención, no diseño; lo no negociable es CI a $0.*
23. **Techo de presupuesto a mitad de run.** → Se detiene, `halted: budget`, lo
    generado queda consultable. *Un techo que avisa y sigue no es un techo; es lo
    que dejó un run en $49.*
