# NovaForge v2 — Anexo C: Claude Code es el orquestador; no hay API key

Complemento de `NOVAFORGE-V2-BRIEF.md` y del Anexo B. **Revierte la decisión D2
y todo lo que dependía de ella.** Donde este anexo discrepe del principal o del
Anexo B, manda este anexo.

Fecha: 2026-09-22.

---

## 1. La restricción, y la decisión que anula

**No hay API key de Anthropic y no hay forma de conseguirla.** El único acceso al
modelo es la sesión de Claude Code del usuario (suscripción, no API).

Por tanto:

- **D2 queda anulada.** El backend **no** llama a la API de Anthropic. **Ningún
  fichero del proyecto importa el SDK de Anthropic** ni lee `ANTHROPIC_API_KEY`.
  Si la sesión constructora lo ha añadido, se quita.
- **Claude Code es el orquestador**, como en el proyecto actual: ejecuta
  `.claude/skills/novaforge/SKILL.md` y despacha los nueve agentes como
  subagentes con su lista `tools:`.
- **FastAPI es el servidor que lo lanza, lo observa y lo guarda.** Es
  exactamente lo que hoy hacen los cuatro plugins de Vite, movido a Python y con
  SQLite detrás.

Esto no es una degradación respecto a lo que la profesora pidió: sigue habiendo
backend FastAPI, frontend React, SQLite y tope de 100k. Cambia *quién habla con
el modelo*: Claude Code, no un cliente HTTP.

---

## 2. Cómo funciona

### 2.1 Lanzar un run

`backend/runs/` arranca **un subproceso** por novela:

```bash
claude -p --output-format stream-json --verbose --permission-mode acceptEdits \
  --allowedTools Read Write Edit Glob Grep Agent \
  "Bash(wc *)" "Bash(mkdir *)" "Bash(cat *)" "Bash(ls *)" \
  "Bash(node *)" "Bash(python *)" "Bash(date *)" "Bash(diff *)" \
  < prompt.txt
```

Es el comando que ya funciona en el proyecto actual (traspaso §11), con
`Bash(python *)` añadido para la recuperación vectorial (§4, D17).

Reglas que vienen de errores ya cometidos y no se repiten:

- **La tarea va por stdin, nunca en argv.** Pasarla como argumento con
  `shell: true` fue inyección de comandos durante una hora.
- **`stream-json` exige `--verbose`.** Sin él no salen los eventos.
- **El tool de subagente se llama `Agent`**, no `Task`.
- **No usar `--restricted`**: rompe `--agent` y Claude Code cae a agentes
  internos. La lista `tools:` de cada agente es la frontera.
- `prompt.txt` lleva `premise:`, `profile:` y opcionalmente `tone:`. Nada más.

### 2.2 Observar

El subproceso emite **una línea JSON por evento**. `backend/runs/` la lee según
llega y hace tres cosas:

1. **La reenvía por SSE** al frontend, tal cual o resumida.
2. **Persiste el estado** en SQLite: etapa actual, capítulo, intento, agente en
   curso. Se detecta por los eventos de herramienta (`Agent` con el nombre del
   subagente) y por las rutas `output/<slug>/...` que aparecen en las escrituras
   — así aprende el `slug` del run, que hoy el panel ya hace.
3. **Acumula tokens y coste** de los mensajes con `usage`, para el techo (§3).

### 2.3 Terminar

El último evento es `result`. Trae **`total_cost_usd`, `duration_ms` y
`num_turns` del run entero, orquestador incluido.** Se escribe a
`output/<slug>/cost.json` y a la tabla de runs. **Esto resuelve el factor 8 del
coste por medición, no por rediseño:** la cifra real la da Claude Code.

Si el proceso muere sin `result`, el run queda `halted: process` con lo que
llegó a escribir.

### 2.4 Requisitos de la máquina

- `claude` en el `PATH` y **con sesión iniciada** en la misma máquina que
  FastAPI. Un usuario, local (D6): es la misma máquina, así que no hay problema
  de credenciales remotas.
- Un run a la vez (cola de 1): **un solo proceso `claude -p` vivo**.
- En Windows, el subproceso se lanza **sin shell**, con la lista de argumentos
  explícita, y el prompt por stdin.

---

## 3. Los 100.000 tokens concurrentes, sin poder contar antes

Con Claude Code orquestando, **Python no monta los prompts** y no puede reservar
tokens antes de despachar. El semáforo del Anexo B §2 **no es implementable**
tal como estaba. Lo honesto es decirlo y sustituirlo por dos capas:

**Capa 1 — dentro de `SKILL.md`, antes de despachar cada agente.** El
orquestador (Claude Code) mide el paquete que va a enviar con `wc -w` y aplica
la conversión `tokens ≈ palabras × 1,35`, marcada como **`estimated`**. Si el
estimado supera el tope por llamada, **no despacha**: recorta (resumen, número
de fragmentos recuperados) y vuelve a medir. Para la concurrencia, el
procedimiento fija **cuántos críticos pueden ir en paralelo** según el tamaño
estimado de cada paquete: si cinco no caben bajo 100.000, van en dos tandas.
Esto es un procedimiento, no una garantía; se escribe así en `verification.md`
(*Inspection*).

**Capa 2 — en Python, después del hecho.** Cada mensaje del stream trae
`usage` con tokens de entrada reales. `backend/runs/` los registra por llamada
y mantiene la suma de los que están en curso. Si la suma supera 100.000, el run
se marca **`halted: context`** y el proceso se termina. Es una comprobación real
sobre cifras medidas (*Test* sobre el runner con un stream grabado), pero llega
después de la llamada, no antes.

**La serie "el capítulo 34 pesa lo que el 1" sí se puede pintar**, y con datos
`measured`: los `usage` del stream son reales.

---

## 4. Cascada: qué decisiones cambian

| # | antes | ahora |
|---|---|---|
| **D2** | FastAPI orquesta llamando a la API | **Claude Code orquesta; FastAPI lanza `claude -p`, observa el stream, persiste** |
| **D3** | eliminar `generate.ts` | **igual**: la única implementación del pipeline es `SKILL.md` |
| **D7** | `flow.yaml` cargado por Python | `flow.yaml` sigue siendo el contrato; **lo sigue `SKILL.md`**. Python **valida** que `SKILL.md` no contradiga a `flow.yaml` ni a `config/` (test de consistencia), pero no ejecuta las etapas |
| **D8** | prompts en `backend/<feature>/prompts/` | **se quedan en `.claude/agents/*.md`**, que es donde Claude Code los lee. `backend/` no tiene prompts |
| **D13** | semáforo de tokens antes de despachar | **dos capas** (§3): procedimiento estimado en `SKILL.md` + comprobación medida y parada en Python |
| **D14** | `ContextPacket` tipado sin campo de prosa previa | **vuelve la garantía estructural del proyecto actual**: `chapter-writer` tiene `tools: Glob` y no puede leer contenido. Un test en Python **lee el front matter y falla** si esa línea cambia |
| **D16** | embeddings locales | **igual** |
| **D17** | los críticos recuperan por vector | **el orquestador recupera por ellos**: antes de despachar al crítico de continuidad ejecuta `python -m novaforge.search <slug> "<texto>"` por `Bash(python *)`, y pega los fragmentos en el prompt del crítico. El crítico sigue con `tools: Glob`. Los fragmentos son sólo de Biblia y resúmenes, **nunca de capítulos** |
| **D19** | coste exacto por llamada desde la API | **coste exacto del run entero desde el evento `result`**, más el desglose por agente desde los `usage` del stream. Es **mejor** que antes: incluye al orquestador |
| **D20** | techo comprobado antes de cada llamada | **vigilante en Python**: coste acumulado desde los `usage` del stream; al superar el techo, termina el proceso → `halted: budget`. Comprobar si la CLI ofrece un flag de presupuesto máximo para `-p` y usarlo como primera línea si existe; el vigilante es la segunda |
| **D23** | motor mock que respete la premisa | **el mock es un `claude` falso**: un ejecutable que emite un `stream-json` **grabado** de un run `tiny` real. Con él se prueban a $0 el runner, el parser, la persistencia, el SSE, el techo y el corte de contexto. **Lo que no se puede probar a $0 es el procedimiento de `SKILL.md`**: eso se prueba con runs reales y se mide con los instrumentos de LOOP-003 |
| **D24** | instrumentos de LOOP-003 a Python | **igual**: leen ficheros, no les afecta quién orquesta |
| Anexo B §3.1 | "quién orquesta: un servicio Python; no un modelo" | **quién orquesta: Claude Code ejecutando `SKILL.md`; FastAPI es el lanzador, el observador y el archivo** |
| Anexo B §3.2 | memoria de llamada = `ContextPacket` tipado | memoria de llamada = **el prompt del subagente, montado por el orquestador según `SKILL.md`**; el resto de las cuatro capas, igual |

Todo lo demás del principal y del Anexo B se mantiene: features del backend,
FSD, SQLite sin ORM, importador de las ocho novelas, `patch_then_halt`, la hoja,
las garantías, el proceso spec → plan → código.

---

## 5. Lo que se gana y lo que se pierde, dicho claro

**Se gana**

- Funciona **sin API key**, con la sesión que ya existe.
- **El coste real del run entero**, orquestador incluido, viene medido en el
  evento `result`. El factor 8 deja de ser un agujero y pasa a ser un dato.
- **La garantía estructural** del `chapter-writer` (no *puede* leer prosa
  previa) se conserva tal cual; es lo más sólido que tiene el proyecto.
- **Una sola implementación** del pipeline: `SKILL.md`. Python no lo duplica.

**Se pierde**

- **Reservar tokens antes de despachar.** El tope de 100k pasa a ser
  procedimiento estimado + parada medida después. En `verification.md` la
  primera capa es *Inspection* y la segunda *Test*; ninguna es "garantía previa".
- **Probar el procedimiento a $0.** El runner sí; `SKILL.md` no. Cada prueba del
  pipeline real consume la suscripción.
- **Reanudar un run a mitad.** Un proceso `claude -p` que muere no se reanuda;
  el run queda `halted` y consultable. Reanudar sería otro run.

---

## 6. `backend/` — qué queda de cada feature

| carpeta | qué hace ahora |
|---|---|
| `commons/db` | igual: SQLite, migraciones, `sqlite-vec`, embeddings locales |
| `commons/runner` | **nuevo**: lanza `claude -p`, lee el stream, lo reparte (SSE, persistencia, contadores). Sustituye a `commons/llm` y `commons/context` |
| `commons/budget` | el vigilante de coste y de contexto sobre el stream |
| `commons/config` | igual; **además valida `SKILL.md` contra `flow.yaml` y `config/`** |
| `commons/log` | una fila por llamada a subagente, desde los `usage` del stream: agente, tokens reales, `ts` real |
| `runs` | crear (escribe `prompt.txt`, lanza), listar, estado, SSE, `cost.json`, importador |
| `bible` · `outline` · `chapters` · `style` · `publish` | **ya no ejecutan etapas.** Cada una expone la lectura de sus artefactos (`bible/*.md`, `outline.md`, críticas, hojas, `book.md`) y sus instrumentos: `outline` tiene la auditoría contra `## Rules` (D25) como script que el orquestador invoca por `Bash(python *)`; `chapters` tiene `measure` y `validate-sheet` portados |
| `search` | **nuevo módulo en `commons`**: `python -m novaforge.search` para D17 |

---

## 7. Qué decirle ahora a la sesión constructora

Texto para pegar tal cual:

> No hay API key de Anthropic y no la va a haber. Quita el SDK de Anthropic y
> cualquier lectura de `ANTHROPIC_API_KEY`. El orquestador es Claude Code: el
> backend lanza `claude -p --output-format stream-json --verbose` como subproceso
> con el prompt por stdin, lee el stream línea a línea, lo reenvía por SSE,
> persiste el estado en SQLite y escribe `cost.json` desde el evento `result`.
> Es lo que hacen los plugins de Vite del proyecto actual, en Python. Los
> prompts de los agentes se quedan en `.claude/agents/`. El tope de 100k se
> aplica en dos capas: estimado en `SKILL.md` antes de despachar y medido en
> Python desde los `usage` del stream, con parada. El mock es un `claude` falso
> que reproduce un stream grabado. Todo lo demás del brief sigue igual. Detalles
> en el Anexo C.
