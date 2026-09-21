# Architecture

How NovaForge is built: the stack, the rule that governs where code goes, the
nine agents with their skills, the process, and the limits.

`definitions.md` holds the vocabulary. `domain-knowledge.md` holds what is known
about writing novels this way. `verification.md` holds every guarantee with the
class of evidence that supports it. This file holds everything else.

---

## 1. The stack

| layer | choice | why |
|---|---|---|
| backend | Python 3.12, FastAPI | the orchestrator itself, not a wrapper around one |
| database | SQLite via the stdlib `sqlite3`, no ORM | small stable schema; `sqlite-vec` is a virtual table and ORMs model those badly |
| vector search | `sqlite-vec` | same file, same transaction, no second service |
| embeddings | `sentence-transformers`, local | no per-call cost, no network, runs in CI |
| frontend | React + Vite + TypeScript | — |
| frontend structure | Feature-Sliced Design v2.1 | — |
| tooling | uv + pytest; npm + vitest; GitHub Actions | CI runs on the mock engine and costs nothing |

**Context ceiling: 100,000 tokens per call**, counted before sending. Exceeding
it is an error that fails the run, not a warning.

---

## 2. The architecture, and what it is for

The frontend has a named architecture and the backend needed one. Both halves
are now governed by the same idea: **slices that do not import each other, and a
dependency direction inside each slice.**

### 2.1 Backend — vertical slices with hexagonal layering

One folder per feature, plus `commons`. Inside each feature:

```
chapters/
├── router.py        HTTP in. Request → arguments, result → response, errors → status codes.
├── models.py        Pydantic shapes, at the edge only.
├── service.py       The procedure. Imports nothing from FastAPI.
├── domain.py        The rules. Imports nothing but the standard library.
├── repository.py    SQL out, behind a Protocol.
└── prompts/         The agent prompts for this stage.
```

**Rule 1 — dependencies point inward.**
`router → service → domain`, and `service → repository` through a Protocol.
`domain.py` imports only the standard library.

This is not tidiness. It is what makes the gate testable: the `min` of five
scores, `10 − 3` per missing beat, the word band, the sheet's completeness — all
of it is arithmetic over values, and in `domain.py` it can be tested with no
database, no HTTP and no model. In v1 those rules were entangled with network
calls, so the only way to exercise them was to write a novel.

**Rule 2 — features do not import each other.**
`chapters/` does not import `bible/`. They compose in `runs/`, or share through
`commons/`. This is Feature-Sliced Design's own rule — no cross-imports between
slices on the same layer — applied to the backend, so one idea governs both
sides of the app.

### 2.2 What `commons/` is for, precisely

Not "shared code". **What nobody may skip.**

```
commons/
├── llm/       the Anthropic client and its mock; the ONLY path to a model
├── context/   ContextPacket per agent, its builder, the 100k counter
├── budget/    the cost ceiling, checked before every call
├── db/        connection, migrations, sqlite-vec, embeddings
├── config/    flow.yaml, config, profiles
└── log/       one row per call: agent, tokens in/out, cost, duration, real timestamp
```

The counter lives in `commons/llm` and that module is the only way to reach the
API. A feature therefore **cannot** send a prompt without it being counted and
charged against the ceiling. That is the point: v1 held its central guarantee
structurally, through a subagent's tool list, and calling the API directly gives
that up. Routing every call through one module puts a structural guarantee back
where the strongest one was lost.

### 2.3 Frontend — Feature-Sliced Design

Layers, highest to lowest: `app → pages → features → entities → shared`.
Imports only ever go downward; slices on a layer do not import each other; every
slice exports through its `index.ts`.

- **pages:** `library` · `new-novel` · `run` · `quality` · `manuscript` · `diagram`
- **features:** `start-run` · `watch-progress` · `configure-novel` · `compare-runs`
- **entities:** `run` · `chapter` · `critique` · `agent` · `provenance`
- **shared:** `api` (the client) · `ui` (the kit) · `lib` (utilities)

The `widgets` layer is discouraged by FSD v2.1 and is not used. The v1 panel's
`presentation` and `configurator` screens fold into `run` and `new-novel`.

The logic is ported — types, derivations, and the provenance semantics, which
are the part that took the longest to learn. The visual layer is rebuilt.

---

## 3. The nine agents and their skills

Full per-agent detail — what each receives, returns and never sees — is in
`agents.md` at the repository root. Listed here because the architecture must
state it.

| agent | stage | model | skills |
|---|---|---|---|
| `worldbuilder` | FLOW-1 | opus | — |
| `character-architect` | FLOW-2 | opus | — |
| `plot-architect` | FLOW-3 | opus | — |
| `chapter-writer` | FLOW-4 | opus | — |
| `continuity-critic` | FLOW-4 gate | sonnet | — |
| `science-critic` | FLOW-4 gate | sonnet | — |
| `outline-critic` | FLOW-4 gate | sonnet | — |
| `style-editor` | FLOW-5 | sonnet | — |
| `publisher` | FLOW-6 | sonnet | — |

The agents are prompts plus a typed context, not processes with tools. Skills are
for the *building* of this system, not for the agents inside it: an agent that
writes a chapter needs a Story Bible, not a SQLite reference. Where that changes,
the skill goes in its row.

Only `worldbuilder` and `character-architect` produce the Story Bible. Every
other agent returns text and the orchestrator writes the file.

---

## 4. The process

Six stages, defined in `specs/flow.yaml` and loaded by the backend. The
orchestrator holds **no literal** of structure or number: stage order comes from
the spec, thresholds and counts from `config/`.

1. **FLOW-1 worldbuild** → `bible/world.md`
2. **FLOW-2 characters** → `characters.md`, `timeline.md`, `mysteries.md`
3. **FLOW-3 outline** → `outline.md`, then **the commission is audited against
   `## Rules`** before any chapter is written
4. **FLOW-4 chapters** → the gate: five characteristics, three attempts,
   `patch_then_halt`
5. **FLOW-5 style** → a pass that may not change a word
6. **FLOW-6 publish** → synopsis, and the book assembled in code

A run executes as a background task in the same process, with state written to
SQLite after every stage and every attempt. Progress reaches the browser over
Server-Sent Events. The stream is a view; the database is the record.

### Storage split

SQLite is the system of record for runs, calls, findings, sheets, gate
decisions, summary facts, tokens and cost. Prose and the Story Bible stay as
Markdown under `output/<slug>/`, referenced by path. Embeddings live in a `vec0`
table keyed back to the row they came from.

---

## 5. Skills installed for building this

Phase 0 of the build. Every skill was read in full before installing — a skill is
text with instructions, and one containing executable code, a downloader, or a
request for credentials is not installed. Installed under
`~/.claude/skills/<name>/SKILL.md`.

| # | skill | source | licence |
|---|---|---|---|
| 1 | `grill-me` | `mattpocock/skills` | MIT |
| 2 | `grilling` | `mattpocock/skills` | MIT |
| 3 | `frontend-design` | `anthropics/skills` | Apache-2.0 |
| 4 | `feature-sliced-design` | `feature-sliced/skills`, with its 9 references | MIT |
| 5 | `sqlite` | written for this project | — |
| 6 | `sqlite-vec` | written here from the `asg017/sqlite-vec` README and official Python docs | extension: MIT / Apache-2.0 |
| 7 | `verification` | written here from the build brief §2.2 | — |
| 8 | `fastapi` | written for this project | — |
| 9 | `react` | written for this project | — |
| 10 | `sentence-transformers` | written for this project | — |

**Standing rule: a technology entering the project brings its skill, before the
first line that uses it.**

### 5.1 Why `SecureSkills-io/sqlite-skill` was rejected

Named by URL in the build brief, read in full, not installed, for three
independent reasons.

1. **Not a Claude Code skill.** No YAML front matter, so it does not load. It
   documents a CLI for a different product.
2. **SQL injection in four commands.** Values are parameterised; table and column
   names are interpolated into the statement, and in `import` they come from a
   JSON file. It also locates `sqlite3` with `which`, which Windows lacks.
3. **Wrong tool.** It wraps the `sqlite3` CLI from Node; this project uses
   Python's stdlib module.

The replacement covers what is actually needed and states the
identifier-allowlist rule the rejected skill got wrong.

### 5.2 The verification skill's missing source

The build brief says to build it from the professor's verification-methodologies
artifact (`c71637b1`). That artifact is not shared with this account. It was
built from the summary in the brief instead, and says so inside itself, asking
whoever obtains the artifact to correct it and state what changed. The brief's
summary names eleven agent-process methods and lists ten; the skill records the
gap rather than inventing the eleventh.

The two ontology artifacts *are* available and were used for `definitions.md`.

---

## 6. Decisions taken while building

Recorded here as the brief's §0 requires, for decisions it did not settle.

**The backend needed an architecture and did not have one.** "A folder per
feature plus commons" is a layout, not an architecture: it says where files go,
not what may import what. §2.1 adopts vertical slices with hexagonal layering —
the mirror of the frontend's FSD — because the guarantees have to live somewhere
that cannot be bypassed, and a layout alone cannot provide that.

**The repository is at `Desktop/novaforge-v2`, and is named `novaforge`.** The
v1 tree stays in place, working and readable: its eight novels are imported and
its procedure is translated stage by stage, and overwriting the reference while
still reading from it would be an avoidable risk.

**`npx skills add` was not used** for `feature-sliced-design`. It installs before
the skill can be read, which the brief's own security rule forbids. The
repository was cloned, read, and copied by hand.

---

## 7. Limits

Stated here and classified in `verification.md`.

- **The gate does not reproduce.** Three of its five characteristics are model
  judgements. "It passed the gate" is a statement about one run.
- **No tamper-evident audit.** The log is a record the orchestrator writes.
- **One writer at a time**, one user, no authentication. Local tool.
- **Retrieval is not exhaustive.** Where a check must see everything — every rule,
  every beat — the whole thing is passed and nothing is retrieved.
- **The writer's isolation is now typed, not structural.** In v1 the chapter
  writer held a tool list that could not return file contents; the prose was
  unreachable. In v2 it is a `ContextPacket` with no field for prose, plus a test.
  That is a real downgrade in the class of evidence and `verification.md` says so
  rather than inheriting v1's language.
