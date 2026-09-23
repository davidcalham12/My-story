# NovaForge v2 — Anexo B al documento de arranque

Complemento de `NOVAFORGE-V2-BRIEF.md`. Responde a la tarea de la profesora
del 2026-09-21 (*"Fine-tuning → architecture.md"* y *"Modificar agents.md"*).
**Corrige una interpretación del documento principal y añade tres secciones
obligatorias.** Donde este anexo y el principal discrepen, manda este anexo.

---

## 1. Corrección: qué es `agents.md`

El documento principal (§6) describía `agents.md` como una ficha por cada uno de
los nueve agentes de la novela. **Eso es un error de interpretación.**

`agents.md` es el fichero estándar `AGENTS.md`: **las instrucciones de trabajo
para la IA que programa el repositorio.** Dice qué proceso sigue el agente de
código para tocar `docs/`, `specs/` y el código, y qué necesita estar aprobado
antes de cada paso. Su contenido está en §4 de este anexo.

**El catálogo de los nueve agentes de la novela va en `docs/architecture.md`**,
que es donde la profesora pidió explícitamente ver *"el listado de agentes y sus
skills, el proceso"*. La tabla de campos por agente que el principal ponía en
`agents.md` (nombre, modelo, qué recibe, qué devuelve, qué escribe, skills, lo
que nunca ve) se traslada tal cual a `architecture.md`.

`claude.md` empieza con una línea: *"Read `agents.md` first; this file only adds
what is specific to Claude Code."*

---

## 2. Corrección: D13 — los 100.000 tokens son **concurrentes**

El principal decía: *"al prompt de cada llamada, contado antes de enviar"*. La
profesora escribió **"100.000 tokens máx concurrentes"**. La diferencia importa:
los críticos corren en paralelo, y cinco llamadas de 30.000 tokens cumplen el
tope por llamada y **suman 150.000 en vuelo**.

**D13 queda así:** el tope de 100.000 se aplica a **la suma de tokens de todas
las llamadas al modelo que estén en curso en el mismo instante**. El tope por
llamada es una consecuencia (ninguna llamada puede reservar más que la
capacidad total).

### 2.1 Mecanismo: un semáforo de tokens en `commons/context/`

- Capacidad: 100.000, leída de `config` (no un literal en el código).
- Antes de cada llamada, el orquestador calcula el tamaño de la reserva:
  **tokens del prompt + `max_tokens` de la respuesta**. Los tokens de prompt se
  cuentan con la API de conteo de Anthropic (o el tokenizador equivalente en el
  motor mock), nunca se estiman.
- La llamada **adquiere** esa cantidad del semáforo. Si no hay capacidad, espera;
  **nunca falla por esperar**. Cuando termina, libera.
- Una reserva mayor que la capacidad total **se rechaza antes de esperar**: es
  un error del run (`halted: context`), no una espera infinita.
- El log registra, por llamada: `tokens_reserved`, `in_flight_at_dispatch`,
  `wait_ms`. Con eso la serie "el capítulo 34 pesa lo que el 1" se puede pintar,
  y también "cuánto esperaron los críticos".

### 2.2 Prueba con el motor mock

Cinco críticos en paralelo con 30.000 tokens cada uno. El test comprueba en el
log que `in_flight_at_dispatch + tokens_reserved ≤ 100.000` en **todas** las
filas, y que los cinco terminaron. Es una garantía *Test* en `verification.md`.

---

## 3. `architecture.md` — tres secciones obligatorias

Además de lo que ya pedía el principal (stack, features, catálogo de agentes con
skills, límites, skills instaladas), `architecture.md` lleva **estas tres
secciones con estos títulos**, porque son las que la profesora va a buscar.

### 3.1 Orquestación — cómo queremos hacerla

- **Quién orquesta:** un servicio Python dentro de FastAPI. No un modelo. El
  orquestador no razona: ejecuta `specs/flow.yaml` etapa por etapa y aplica las
  reglas del gate. Todo turno que antes daba Claude Code como orquestador
  desaparece del coste.
- **Qué es un agente:** una función Python que recibe un `ContextPacket` tipado,
  carga su prompt desde `backend/<feature>/prompts/<agent>.md`, llama al motor
  (real o mock) con su modelo asignado, y devuelve texto más el uso de tokens.
  Nada más. Un agente no lee disco ni escribe disco; el orquestador lo hace por
  él.
- **Secuencia de un run:** `runs` crea el run y persiste el estado → FLOW-1 →
  FLOW-2 (los dos únicos que producen Biblia; el orquestador la escribe) →
  FLOW-3 + **auditoría del guion contra `## Rules`** → FLOW-4 por capítulo:
  construir el packet del escritor (sin prosa previa, por tipo) → borrador →
  cinco críticos **en paralelo bajo el semáforo** → `min` de las cinco notas →
  si < 8, hoja nivel 1 → intento 2 → hoja nivel 2 → intento 3 → `patch_then_halt`
  → FLOW-5 → FLOW-6 con ensamblado en código. **El estado se persiste en SQLite
  después de cada etapa y de cada intento.**
- **Concurrencia:** dentro de un capítulo, los críticos en paralelo; entre
  capítulos, en serie (el resumen del N alimenta al N+1). Entre runs, cola de
  tamaño 1.
- **Fallo y parada:** tres motivos de `halted`: `budget` (techo de coste),
  `context` (una reserva mayor que la capacidad), `gate` (`patch_then_halt`
  agotado). Los tres dejan el run consultable hasta donde llegó.
- **Observación:** SSE por run; el frontend escucha, no pregunta.
- **Diagrama:** el Mermaid corregido del proyecto actual, con el nodo del
  orquestador explícito y el semáforo dibujado entre el orquestador y el motor.

### 3.2 Gestión de memoria — corto y largo plazo

La memoria del sistema se describe en **cuatro capas**, de la más efímera a la
más persistente. Regla que las une: **lo que entra en un prompt es una
proyección de la memoria, nunca la memoria misma, y esa proyección es lo que se
cuenta contra los 100.000.**

| capa | qué es | dónde vive | cuánto dura | quién escribe |
|---|---|---|---|---|
| **Memoria de llamada** | el `ContextPacket` de un agente | memoria del proceso | una llamada; el modelo no retiene nada después | el constructor de contexto |
| **Memoria de trabajo del run** (corto plazo) | la lista de hechos estructurados del resumen rodante `{hecho, capítulo, tipo}`, con tope por número; las hojas de retroalimentación; los borradores por intento; el estado de la etapa | SQLite, por `run_id` | el run | el orquestador |
| **Canon** (largo plazo dentro del run) | la Biblia: mundo, personajes, cronología, misterios; el guion auditado | Markdown en `output/<slug>/` + índice vectorial en SQLite | el run entero; **inmutable tras FLOW-3** | sólo `worldbuilder` y `character-architect` (vía el orquestador); el guion, `plot-architect` |
| **Memoria entre runs** (largo plazo del sistema) | runs, llamadas, costes exactos, hallazgos por tipo, notas por característica; la tabla `character_knowledge` (vacía en v1) | SQLite | permanente | el orquestador y el importador |

Tres decisiones que salen de esta tabla y que hay que escribir:

- **El resumen rodante es memoria de trabajo, no canon.** Se reconstruye para
  cada capítulo desde los hechos; el escritor recibe la proyección en texto.
- **La recuperación vectorial (D17) es cómo el canon se proyecta sin entrar
  entero:** el crítico de continuidad recibe los fragmentos más cercanos al
  borrador; el de ciencia recibe `## Rules` entero porque es pequeño y una regla
  no recuperada es una violación no vista.
- **La memoria entre runs es donde el sistema aprende**, y es el sitio de la
  idea de LOOP-002 (una lista de lecciones de tamaño fijo, que olvida a
  propósito, sin citas de prosa) si en v2 se decide activarla. En v1 sólo se
  registra; no se inyecta.

### 3.3 Gestión de los 100.000 tokens concurrentes

Lo de §2 de este anexo, escrito en `architecture.md` con el diagrama del
semáforo y la tabla de qué reserva cada tipo de llamada en el perfil `tiny`
(estimada desde los runs actuales y **marcada como estimada** hasta que la Fase
3 la mida).

---

## 4. `agents.md` — el proceso del agente que programa

Es el fichero que la IA de código lee primero. Describe **tres procesos** y las
**puertas** entre ellos. Cada artefacto tiene un estado y nada avanza sin el
estado anterior aprobado.

### 4.1 Estados y aprobación

| artefacto | estados | quién aprueba |
|---|---|---|
| `docs/*.md` | vivo (sin estados; se actualiza siempre) | — |
| `specs/SPEC-NNN-*.md` | `draft` → `approved` | el humano, escribiendo `status: approved` con fecha en la cabecera |
| `specs/PLAN-NNN-*.md` | `draft` → `approved` | ídem |
| código | sólo existe con un `PLAN` aprobado que lo cubra | — |

**Aprobar es un acto humano explícito en el fichero.** Un "ok" en el chat no
cambia un estado.

### 4.2 Proceso para `docs/`

- `docs/` se actualiza **en el mismo cambio** que modifica el comportamiento que
  describe. Un PR que cambia el gate y no toca `architecture.md` está
  incompleto.
- Siempre en inglés.
- `definitions.md` sólo cambia cuando aparece un término nuevo o uno cambia de
  significado; `domain-knowledge.md` cuando se aprende algo de un run;
  `architecture.md` cuando cambia una decisión de §3 del principal o de este
  anexo; `verification.md` cuando cambia una garantía o su letra.
- Cada cambio en `docs/` cita de dónde viene: un run, una spec, una decisión.

### 4.3 Proceso para `specs/`

1. **Antes de escribir una spec, preguntar.** El agente usa `grilling` para
   hacer las preguntas cuya respuesta no puede encontrar en el repo. No se
   escribe una spec con huecos rellenados por suposición.
2. La spec tiene identificador (`SPEC-NNN`), cabecera con `status`, y contiene:
   qué se quiere, por qué, qué no está en alcance, criterios de aceptación
   verificables, y su letra T/A/I/D/U por criterio.
3. **No hay plan de implementación sin spec aprobada.** Un `PLAN-NNN` referencia
   exactamente un `SPEC-NNN` con `status: approved`; si la spec cambia, el plan
   vuelve a `draft`.
4. El plan lista, en orden: **los tests primero**, luego los cambios de código,
   luego los cambios de `docs/` y de la propia spec. Un plan sin tests no se
   aprueba.

### 4.4 Proceso para el código

- **No se escribe código sin un plan aprobado** que lo cubra. Ni "un arreglo
  rápido". Si algo urge, se escribe la spec corta, se aprueba, y entonces.
- **TDD:** el test se escribe y se ve fallar antes del código; después el código
  mínimo que lo pasa; después el refactor con los tests en verde. Los tests
  corren con el motor mock y cuestan $0; un test que necesita el motor real se
  marca y no entra en CI.
- **Definición de hecho** para cualquier cambio: tests en verde en CI; la spec
  actualizada si el comportamiento final difiere de lo aprobado; `docs/`
  actualizado; `verification.md` actualizado si cambió una garantía; skill
  añadida si entró una tecnología.
- Lo que nunca se toca sin una `SPEC` aprobada que lo diga por su nombre: el 8,
  las cinco características, el tercer intento, el `ContextPacket` del escritor,
  el semáforo de 100k, el techo de presupuesto.

### 4.5 Lo que `agents.md` enlaza, no repite

- El catálogo de los nueve agentes de la novela → `docs/architecture.md`.
- Las garantías y sus letras → `docs/verification.md`.
- Lo específico de Claude Code (comandos, permisos) → `claude.md`.

---

## 5. Cambios al documento principal, resumidos

| dónde | qué cambia |
|---|---|
| §3, D13 | "por llamada" → **concurrentes, con semáforo** (§2 de este anexo) |
| §3, nuevas | **D30** `agents.md` = proceso del agente de código · **D31** puertas spec → plan → código con aprobación humana en fichero y TDD · **D32** memoria en cuatro capas |
| §6 | `agents.md` ya no es el catálogo de agentes; el catálogo va a `architecture.md` |
| §5, garantía 2 | pasa a "100.000 tokens **concurrentes**, semáforo antes de cada llamada" |
| §8, Fase 1 | `architecture.md` incluye las tres secciones de §3 de este anexo; `agents.md` sigue §4 |
| §8, Fase 2 | `commons/context/` incluye el semáforo y su test con cinco críticos |
