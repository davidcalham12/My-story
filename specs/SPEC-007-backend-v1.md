---
id: SPEC-007
title: NovaForge backend v1 — launcher, observer and archive for the Claude Code orchestrator
status: approved
owner: David Calderon
approved_by: David Calderon (dictated in chat, 2026-09-22; written by the building session at his request)
approved_on: 2026-09-22
supersedes: —
renamed_from: SPEC-001-backend-v1 (2026-09-22; the number collided with SPEC-001-commons)
depends_on: docs/architecture.md, docs/verification.md, specs/flow.yaml, specs/loops/LOOP-003/README.md
---

# SPEC-007 — NovaForge backend v1

A Software Requirements Specification, in one document, for the first functional
backend. Written against `docs/` (definitions, domain knowledge, architecture,
verification) and the four start-up addenda (B, C, D). Where this spec and
`docs/architecture.md` disagree, stop and reconcile before planning; the gap
between the two must tend to zero (see §12).

Per `AGENTS.md`: no implementation plan until this spec is approved; no code until
PLAN-007 is approved; tests first.

## 1. Introduction

### 1.1 Purpose

Deliver a FastAPI service that launches, observes and archives NovaForge novel
runs. The orchestrator is Claude Code, executing
`.claude/skills/novaforge/SKILL.md` and dispatching the ten agents as subagents.
The backend never talks to a model: it spawns `claude -p`, reads its event
stream, persists everything to SQLite, relays progress over SSE, and exposes the
artefacts and the instruments.

### 1.2 Scope of v1

**In scope:** everything needed to start a `tiny` (3-chapter) run from an HTTP
call, watch it live, stop it on budget or context breach, and read every artefact
and score afterwards; import the eight existing runs; the three CLI instruments
the orchestrator calls (search, outline audit, sheet validation) and the
measurement instrument; a fake `claude` for $0 tests.

**Out of scope (v1):** the React frontend (separate spec), authentication,
concurrent runs, resuming an interrupted run, PDF output,
populating `character_knowledge`, any call to the Anthropic API. A prose critic
was out of scope when this was drafted; SPEC-006 built one, and the gate has had
six characteristics since.

### 1.3 Definitions

Terms are as in `docs/definitions.md`. Short list used here:

| term | meaning |
|---|---|
| run | one attempt to write one novel from one premise under one config snapshot |
| slug | the run's directory name under `output/`; learned from the stream |
| stage | FLOW-1 … FLOW-6 as in `specs/flow.yaml` |
| attempt | one draft of one chapter; at most three |
| gate | the six-score check (continuity, science, outline, length, chatter, prose — the sixth since SPEC-006), aggregate min, threshold 8 |
| sheet | the feedback document sent to the writer before attempt 2 and 3 |
| event | one line of stream-json emitted by `claude -p` |
| halted | a run stopped by the backend or by the orchestrator, with reason |

### 1.4 References

`docs/architecture.md` · `docs/verification.md` · `specs/flow.yaml` ·
`config/novel.config.json` and `config/profiles/*.json` · `config/pricing.json` ·
`specs/loops/LOOP-003/README.md` · `.claude/agents/*.md` ·
`.claude/skills/novaforge/SKILL.md` · the professor's ontology (definitions,
diagrams) and verification-methodologies sheet.

## 2. Overall description

### 2.1 Product perspective

```
 React (later spec) ──HTTP/SSE──▶ FastAPI backend ──spawn──▶ claude -p (orchestrator)
                                      │  ▲                        │
                                      │  └── stream-json ─────────┘
                                      │                           │ subagents (10)
                                      ▼                           ▼
                                   SQLite                    output/<slug>/*.md, *.json
                                      ▲                           │
                                      └──── importer / readers ───┘
                     orchestrator ──Bash(python *)──▶ CLI instruments (search, outline audit, validate-sheet)
```

The backend is downstream of the orchestrator for generation and upstream of it
for instruments. It owns structured data (SQLite); the orchestrator owns prose and
Bible files (Markdown on disk).

### 2.2 Constraints (hard)

- **C1 — No API key.** No Anthropic SDK dependency; no `ANTHROPIC_API_KEY` read
  anywhere. The only model access is the user's Claude Code session.
- **C2 — 100,000 tokens concurrent.** Enforced in two layers: estimated in
  `SKILL.md` before dispatch; measured by the backend from stream `usage` with
  halt on breach (Addendum C §3).
- **C3 — Single user, local, one run at a time.** Same machine as the `claude`
  CLI; queue of size 1.
- **C4 — Windows-first.** No shell for subprocesses; explicit argv; prompt via
  stdin; UTF-8 without BOM on every write.
- **C5 — No secrets** in repo, argv, logs or DB.
- **C6 — No literals of structure or numbers in code.** Stages from `flow.yaml`;
  numbers from `config/`; rates from `pricing.json`.
- **C7 — One implementation of the pipeline: `SKILL.md`.** The backend never
  re-implements a stage.

### 2.3 Assumptions and dependencies

- `claude` CLI on PATH, authenticated, supports
  `-p --output-format stream-json --verbose --permission-mode acceptEdits --allowedTools …`.
- Python 3.12, `pip` (`uv` is not installed on the build machine — `claude.md`),
  `pytest`; SQLite ≥ 3.41 with extension loading;
  `sqlite-vec`; `sentence-transformers` with a small local model.
- Every dependency above has its skill installed before first use (professor's
  rule).

## 3. System architecture (summary; authoritative text in `docs/architecture.md`)

```
backend/                    (as built, 2026-09-22 — package name `backend`, not `novaforge`)
├── main.py                 the app; `/api/runs` router and `/api/health`
├── checks.py               `python -m backend.checks <stage>`: the per-stage validators the skill calls
├── report.py               a run's report from what was archived
├── commons/
│   ├── runner/             process.py spawns claude -p (stdin prompt, no shell); watch.py: budget + context watchers
│   ├── db/                 connection, numbered SQL migrations 001–008, repository, import_v1, vectors (sqlite-vec)
│   ├── config/             settings + loader for flow.yaml, config and profiles
│   ├── log/                calls.py — one row per subagent call from stream usage
│   └── search.py           embed / index / query over Bible and facts (built; not yet called by the skill — §12)
├── runs/                   router · models · service · repository · archive · conformance
├── bible/  outline/  style/  publish/     domain.py each: what the stage's artefacts must satisfy
├── chapters/               domain (gate, sheets) · decide · promote · prose · score_prose · check_* · names · summary
└── tests/                  pytest; recorded stream (USE_RECORDED_STREAM=true); 449 tests at this date
```

### 3.1 Run lifecycle (state machine)

```
running ──▶ complete
      └──▶ halted { reason: budget | context | gate | process | interrupted }
```

Transitions are persisted on every stream event that changes state; never only at
the end. There is no `queued` state: C3 admits one run at a time and the second
`POST` is answered 409, so nothing ever waits. `interrupted` is the reason the
backend writes when its own reading of the stream raised — distinct from
`process`, which is the orchestrator ending without a `result` event. `user`
(FR-RUN-5) is not built; §12.

### 3.2 The draft against the build, 2026-09-22

This spec was drafted before the backend existed and is being approved after most
of it does. Where the two differ, **the build is what this table says and the
spec text above is amended to match**; what the build lacks is either scheduled
for PLAN-007 or declared as a gap in §12. Nothing here is left implicit.

| item | the draft said | built |
|---|---|---|
| API prefix | `/runs`, `/health` | `/api/runs`, `/api/health` |
| create response | `202 {run_id}` | `201 {id, slug}` |
| lifecycle | `queued → running → …` | `running → complete \| halted`; no queue — 409 is the queue |
| halt reasons | `budget, context, gate, process, user` | `budget, context, gate, process, interrupted`; `user` pending FR-RUN-5 |
| FR-RUN-5 halt endpoint | required | **not built** → PLAN-007; gap in §12 |
| FR-RUN-7 startup sweep | required | **not built** → PLAN-007 |
| FR-RUN-4 `Last-Event-ID` | required | **not built**; stream opens with `snapshot` → gap in §12 |
| FR-RD-1/2 file-backed read endpoints | per artefact | **not built**; artefacts are archived to SQLite at run end (`runs/archive.py`) and read from there; the path-normalisation property is N/A (`verification.md` G17) |
| FR-INS-1 `outline_audit` CLI | a script | a model, `outline-critic` — class D (`verification.md` §8, v2 entry); gap in §12 |
| FR-INS-2 `validate_sheet` | `python -m novaforge.validate_sheet` | the skill runs `node specs/loops/LOOP-003/validate-sheet.mjs`; `backend.chapters.domain.validate_sheet` mirrors it in Python, tested, not yet the one invoked |
| FR-INS-3 `measure` | a Python port | `specs/loops/LOOP-003/measure.mjs` stays in Node, self-tested in CI; it knows five characteristics → gap in §12 |
| FR-SRC search CLI | `python -m novaforge.search` | `backend/commons/search.py` + `db/vectors.py` built and tested; **never invoked by the skill** (`verification.md` §3.15) → gap in §12 |
| per-stage validators | not in the draft | `python -m backend.checks <stage>`, called by the skill after FLOW-2/3/4/6; plus `decide`, `promote`, `score_prose`, `check_prose` as CLIs |
| package names | `novaforge.*` | `backend.*` |
| dependencies | `uv` | `pip` |
| gate | five characteristics | six (SPEC-006 added `prose`) |
| agents | nine | ten |
| FR-RNR-3 `events` table | every raw line persisted before fan-out | **no `events` table**; what is persisted is derived: `runs`, `attempts`, `calls`, `scores`, `gate_decisions`, `findings`, `sheets`, `summary_facts` (`verification.md` G19) — Paso 4 question |
| FR-BUD-1 `--max-budget-usd` | pass it if the CLI has it | the CLI has it (`claude --help`); the runner **does not pass it** → PLAN-007 |
| FR-BUD-1 measure between `result` events | running sum of `calls` cost | tokens priced at the most expensive rate on file, `watch.py` — a ceiling that under-estimates is not a ceiling |
| FR-BUD-2 in-flight sum | `input_tokens + max_tokens` of calls in flight | `input + cache_creation + cache_read` of each `usage` event, measured (`architecture.md` §6.3) |
| FR-RUN-6 import | `POST /api/runs/import` | `import_all()` in `commons/db/import_v1.py`, exercised by `test_import.py`; **no endpoint, no CLI entry point** — Paso 4 question |
| FR-HLT-1 health | DB, migrations, `claude`, `sqlite-vec`, model | `{ok, orchestrator, claude_on_path}` only |
| §6.1 prefix | `/api/v1` | `/api` |
| tests | fake `claude` binary | the runner replays a recorded stream when `USE_RECORDED_STREAM=true`; same effect, no binary |

The draft's `python -m novaforge.*` names are gone from §4; where §8 keeps one
it is marked with the Paso 4 decision that retired it.

## 4. Functional requirements

Numbering: `FR-<feature>-<n>`. Each FR is testable; its verification letter is in
§10.

### 4.1 Runs

- **FR-RUN-1** `POST /api/runs` with `{premise, profile, tone?}` validates the profile
  against `config/profiles/`, writes `prompt.txt` (`premise:`, `profile:`, optional
  `tone:` — nothing else), creates a `runs` row in `running`, and returns
  `201 {id, slug}`. If a run is running, returns 409.
- **FR-RUN-2** `GET /api/runs` lists runs newest first with status, slug, profile,
  chapters, retries, cost, provenance flags.
- **FR-RUN-3** `GET /api/runs/{id}` returns the run's current state: stage, chapter,
  attempt, active agent(s), totals, halt reason.
- **FR-RUN-4** `GET /api/runs/{id}/events` is an SSE stream of run events (§6.2).
  It opens with a `snapshot` of the run's persisted state and then relays live
  events. With `Last-Event-ID: <seq>` it replays from the `events` table
  (FR-RNR-3) before going live. *Not built at 2026-09-22; PLAN-007 (Paso 4, Q3).*
- **FR-RUN-5** `POST /api/runs/{id}/halt` terminates the subprocess and marks
  `halted: user`. **Not built at 2026-09-22** (§3.2); PLAN-007 schedules it and
  §12 carries the gap until then.
- **FR-RUN-6** `python -m backend.commons.db.import_v1` (a CLI entry point over
  the existing `import_all()`; no HTTP endpoint — *Paso 4, Q7*) scans `output/*/`, imports every run found
  (state, log, critiques, sheets, cost.json) into SQLite with
  `source = reconstructed`, normalising the three known critique shapes; an
  unrecognised shape becomes a row with `parse_error` and is never dropped
  silently.
- **FR-RUN-7** On startup, any run left in `running` is marked `halted: process`.
  **Not built at 2026-09-22** (§3.2); PLAN-007 schedules it.

### 4.2 Runner

- **FR-RNR-1** Spawns exactly:
  `claude -p --output-format stream-json --verbose --permission-mode acceptEdits --allowedTools <list>`
  with the allowed-tools list from `config/` (default as in Addendum C §2.1,
  including `Bash(python *)`), no shell, explicit argv, prompt on stdin.
- **FR-RNR-2** Reads stdout line by line; each line is parsed as JSON. A
  malformed line is logged with its raw text and skipped; the parser never
  crashes the run.
- **FR-RNR-3** Persists every event to `events(run_id, seq, ts, type, payload)`
  before fanning out. *Not built at 2026-09-22 — the build persists derived
  state only; PLAN-007 adds the table by migration (Paso 4, Q3): a run is judged
  by the stream it ran, and that needs the stream, not a reconstruction.*
- **FR-RNR-4** Derives run state from events: stage and agent from `Agent` tool
  calls (subagent name), chapter/attempt from `output/<slug>/chapters/chNN*` and
  `critiques/chNN.*.attemptK*` paths in tool inputs, slug from the first write
  under `output/`.
- **FR-RNR-5** Extracts `usage` from assistant messages into `calls` rows (agent,
  stage, chapter, attempt, input/output tokens, cost from `pricing.json`, real
  `ts`, `duration_ms` when derivable, `in_flight_at_dispatch`).
- **FR-RNR-6** On the `result` event writes `output/<slug>/cost.json`
  (`total_cost_usd`, `duration_ms`, `num_turns`, `ts`) and marks `complete`, or
  `halted: gate` if the orchestrator reported `patch_then_halt`.
- **FR-RNR-7** If the process exits without `result`, marks `halted: process` and
  keeps everything written so far readable.

### 4.3 Budget and context watchdogs

- **FR-BUD-1** Maintains running `cost_usd` from `calls`; when it exceeds
  `config.budget.max_cost_usd` for the profile, terminates the process and marks
  `halted: budget`. The CLI offers `--max-budget-usd`; the runner passes the
  profile's ceiling as the first line of defence and the watcher stays the
  second — whether the flag binds under a subscription is learned from the real
  run (AC-15) and written down either way.
- **FR-BUD-2** Maintains the sum of `input_tokens + max_tokens` of calls
  currently in flight (a call is in flight from its dispatch event until its
  `usage` event). When the sum exceeds `config.context.max_concurrent_tokens`
  (100,000), marks `halted: context` and terminates.
- **FR-BUD-3** Records per call `tokens_reserved`, `in_flight_at_dispatch`,
  `wait_ms` when derivable, with `source = measured`.
- **FR-BUD-4** Both thresholds come from `config/`; never literals.

### 4.4 Config and consistency

- **FR-CFG-1** Loads `specs/flow.yaml`, `config/novel.config.json`, the profile,
  and `pricing.json`; computes `config_hash` per run and stores the resolved
  snapshot as `output/<slug>/config.snapshot.json` and in `runs`.
- **FR-CFG-2** Validates `.claude/skills/novaforge/SKILL.md` against `flow.yaml`
  and `config/`: stage order, gate critics list, threshold, max attempts,
  `on_fail`. Any divergence fails a CI test with the exact lines.
- **FR-CFG-3** Validates every `.claude/agents/*.md` front matter: the
  `chapter-writer` `tools:` line must equal `Glob`; only `worldbuilder` and
  `character-architect` may include `Write`. Fails CI otherwise.

### 4.5 Search (vector)

- **FR-SRC-1** Embeds `bible/*.md` sections and rolling-summary facts per run
  with a local `sentence-transformers` model into a `vec0` table keyed to the
  source row. Never embeds chapter prose.
- **FR-SRC-2** `backend/commons/search.py` indexes and queries Bible sections
  and summary facts (built, tested). **The orchestrator does not call it in v1**
  — wiring it into `SKILL.md` before the continuity critic changes the procedure,
  which only a real run verifies, and the one real run of this spec (§10, AC-15)
  validates the backend. Declared in §12; a SPEC of its own. *Paso 4, Q5.*
- **FR-SRC-3** If `sqlite-vec` or the model is unavailable, the CLI exits with a
  distinct code and JSON `{"available": false}`; `SKILL.md` then falls back to
  passing the full Bible. The degradation is logged, never silent.

### 4.6 Instruments (CLI, invoked by the orchestrator)

- **FR-INS-1** The outline is audited against the bullets under `## Rules` in
  `bible/world.md` before FLOW-4, and a violation blocks FLOW-4 for that chapter
  until the outline is revised. **The auditor is a model** (`science-critic` in
  its FLOW-3 role, `architecture.md` §4.6) — class D, `verification.md` G11.
  The draft's `outline_audit` script is **not built by this spec**: matching
  free-text beats against free-text rules in code would be a T in name only.
  A script is its own SPEC, with its own evidence. *Paso 4, Q4.*
- **FR-INS-2** `node specs/loops/LOOP-003/validate-sheet.mjs <path>` — the
  validator the skill already runs — rejects a sheet missing any of the six
  scores, any of the four finding fields, with a template gap, quoting a previous
  chapter, or reaching attempt 3 without literal replacements. Exit code non-zero
  on reject. **Stays in Node**; no Python port. *Paso 4, Q6.*
- **FR-INS-3** `node specs/loops/LOOP-003/measure.mjs <slug> [--self-test]`
  stays in Node and **learns the sixth characteristic, `prose`**, in PLAN-007;
  `--self-test` reproduces the recorded assertions on the fixture run
  (`deep-space-salvage-derelict`), reporting SKIP where the fixture lacks data,
  never hiding it. *Paso 4, Q6.*
- **FR-INS-4** All instruments read files and SQLite only; none calls a model.

### 4.7 Read endpoints (per feature)

- **FR-RD-1** What a run produced is read **from the archive in SQLite**, not
  from `output/<slug>/`: `GET /api/runs/{id}` returns the run with its stages,
  attempts, scores, gate decisions, calls and cost as archived at run end
  (`runs/archive.py`). Per-artefact endpoints (`/bible/{section}`, `/chapters/{n}`
  …) are **not in v1**: no client consumes one. *Paso 4, Q2.*
- **FR-RD-2** The backend serves no file by path. The path-normalisation
  property of the draft is therefore not applicable (`verification.md` G17);
  it returns the day an endpoint reads a file.
- **FR-RD-3** Every numeric field carries
  `source ∈ {measured, reported, reconstructed, estimated, absent}`.

### 4.8 Health

- **FR-HLT-1** `GET /api/health` reports: DB reachable, migrations applied, `claude`
  CLI found on PATH, `sqlite-vec` loadable, embeddings model present. Never
  probes the model.

## 5. Data requirements

SQLite, stdlib `sqlite3`, WAL mode, single writer. Migrations as numbered SQL
files. Every table carries `run_id` (C3 → D6).

| table | key columns |
|---|---|
| `runs` | id, slug, premise, profile, tone, config_hash, status, halt_reason, started_at, finished_at, total_cost_usd, num_turns, duration_ms, source |
| `events` | run_id, seq, ts, type, payload (the raw line) — **added by PLAN-007 6.2**; written from 6.4 |
| `calls` | run_id, seq, agent, stage, chapter, attempt, input_tokens, output_tokens, cost_usd, ts, duration_ms, tokens_reserved, in_flight_at_dispatch, source |
| `gate_decisions` | run_id, chapter, attempt, scores (JSON), aggregate, threshold, verdict |
| `findings` | run_id, chapter, attempt, critic, kind, severity, upheld, quote, fix, reference, ruling, late |
| `sheets` | run_id, chapter, attempt, level, path, validated, validator_version |
| `drafts` | run_id, chapter, attempt, path, words, kept — **built as `attempts`** (+ aggregate, verdict, promoted) |
| `facts` | id, run_id, chapter, kind, text (rolling-summary facts, D15) — **built as `summary_facts`**; never written (§12) |
| `character_knowledge` | run_id, character, fact_id, learned_in_chapter — created, empty in v1 |
| `embeddings` (vec0) | run_id, source_table, source_id, chunk, embedding — **built as `chunks`** + a vec0 index; never populated (§12) |
| `config_snapshots` | run_id, config_hash, json — **built as the `runs.config_snapshot` column**; the hash is computed from it (PLAN-007 6.3) |

Prose and Bible stay on disk under `output/<slug>/`; the DB stores paths.

## 6. External interfaces

### 6.1 REST

All under `/api` (the draft said `/api/v1`; the build has no version segment).
JSON. Errors as FastAPI emits them (`{detail}`); 404 for unknown run; 409 for a
second concurrent run; 422 for invalid input.

### 6.2 SSE event schema

```json
{"id": <seq>, "event": "<type>", "data": {"run_id": "...", "ts": "...", ...}}
```

Types: `state` (stage/chapter/attempt/agent), `call` (a subagent usage row),
`gate` (a decision), `finding`, `sheet`, `halt`, `complete`, `raw` (optional, the
untouched stream line). The stream opens with `snapshot` and closes with
`done`; `id` is the persisted `seq` once FR-RNR-3 lands, and `Last-Event-ID`
resumes from it.

### 6.3 Subprocess contract with `claude -p`

Argv as FR-RNR-1; stdin = `prompt.txt`; stdout = one JSON per line; exit code
recorded. Tool names as observed in the current project: the subagent tool is
`Agent`.

### 6.4 Filesystem contract

`output/<slug>/` as today: `bible/`, `outline.md`, `chapters/chNN.md`,
`chapters/chNN.attemptK.md` (rejected drafts, kept from v1),
`chapters/chNN.final.md`, `chapters/chNN.summary.md`,
`critiques/chNN.<critic>.json`, `logs/agents.jsonl`, `state.json`,
`config.snapshot.json`, `cost.json`, `dist/book.md`, `synopsis.md`. Sheets under
`specs/loops/LOOP-003/sheets/<slug>/`.

## 7. Non-functional requirements

- **NFR-1 Reliability.** No single malformed event, missing file or failed
  extension load crashes the service; each degrades to a logged, visible state.
- **NFR-2 Persistence granularity.** State is queryable mid-run at attempt
  resolution; a crash loses at most the events after the last persisted `seq`.
- **NFR-3 Latency.** An event is relayed over SSE within 500 ms of being read.
- **NFR-4 Security.** C4, C5, FR-RD-2; dependency list pinned; no shell.
- **NFR-5 Observability.** Every call row has real `ts`; every number has
  `source`; logs are structured JSON.
- **NFR-6 Cost honesty.** Live runs: exact cost from `usage` and `result`.
  Imported runs: low / estimate / high with `reconstructed`.
- **NFR-7 Portability.** Runs on Windows 11 and Linux; paths handled with
  `pathlib`; UTF-8 explicit everywhere.
- **NFR-8 Testability.** The whole service is exercisable with the fake `claude`
  (§9) at $0 in CI.

## 8. Constraints on the orchestrator side (changes to `SKILL.md` this spec requires)

The backend cannot work unless `SKILL.md`:

1. Writes rejected drafts as `chapters/chNN.attemptK.md`.
2. Records real `ts` (`date -u`) and, where possible, `duration_ms` per call.
3. ~~Calls `search` before the continuity critic~~ — **not in v1** (Q5); the
   critic receives the full Bible, and this line returns with the spec that wires
   the search.
4. Audits the outline against `## Rules` after FLOW-3 and revises it on
   violations before FLOW-4 — **done today by a model** (Q4), and the skill
   already does it.
5. Runs `node specs/loops/LOOP-003/validate-sheet.mjs` before sending any sheet
   — **the skill already does** (Q6).
6. Estimates packet size (`wc -w × 1.35`, marked `estimated`) before each dispatch
   and staggers parallel critics to stay under 100,000.
7. Emits the rolling summary as structured facts (D15) into
   `chapters/chNN.facts.json` in addition to the text.

These are listed so the plan schedules them; they are changes to the skill, not
to Python, and each is a separate SPEC item if the team prefers.

## 9. Test strategy (summary; full mapping in `docs/verification.md`)

- **Fake claude:** an executable placed first on PATH in tests that replays a
  recorded stream-json from a real `tiny` run (fixture), with switches to inject:
  a malformed line, a missing `result`, a cost overshoot, five parallel critic
  calls exceeding 100,000, an unknown critique shape.
- **Unit:** parser, state derivation, cost arithmetic, path normalisation, config
  hash, consistency validator, front-matter validator, each instrument.
- **Integration:** `POST /api/runs` → SSE → `complete`, against the fake; import of
  the eight fixture runs; halt paths (budget, context, gate, process,
  interrupted; `user` once FR-RUN-5 exists).
- **Contract:** the SSE schema (§6.2) and the CLI JSON outputs are
  snapshot-tested; a change requires a spec change.
- **Property-based:** path normalisation never escapes `output/<slug>/`; min
  aggregation; watchdog sums.
- **Self-tests:** `measure --self-test` and `validate_sheet --self-test`
  reproduce recorded results on the fixture run.

## 10. Acceptance criteria (with T/A/I/D/U)

| id | criterion | letter |
|---|---|---|
| AC-1 | `POST /api/runs` with a valid profile starts one `claude -p` process, no shell, prompt on stdin; a second POST while running returns 409 | T (fake claude) |
| AC-2 | Every stream line is persisted to `events` before any fan-out; a malformed line is logged and skipped | T |
| AC-3 | Run state (stage, chapter, attempt, agent) is correct at every step of the recorded fixture stream | T |
| AC-4 | `cost.json` and `runs.total_cost_usd` equal the `result` event's values | T |
| AC-5 | Cost overshoot in the fake stream → process terminated → `halted: budget` | T |
| AC-6 | Concurrent tokens > 100,000 in the fake stream → `halted: context`; all `calls` rows carry `in_flight_at_dispatch` | T |
| AC-7 | `python -m backend.commons.db.import_v1` imports the eight v1 runs; three critique shapes normalised; an unknown shape yields a `parse_error` row and no silent drop | T |
| AC-8 | `chapter-writer` front matter `tools:` equals `Glob`; only the two Bible writers include `Write`; CI fails otherwise | T |
| AC-9 | `SKILL.md` agrees with `flow.yaml` and `config/` on stage order, critics, threshold, attempts, `on_fail` | T |
| AC-10 | No endpoint reads a file by path (Q2); a test asserts the router has no path-taking file route, so the property returns with the first such endpoint | T |
| AC-11 | `backend.commons.search` returns top-k fragments from Bible and facts only, never from chapter prose, and degrades to `{"available": false}` when the extension or model is missing — at module level; the skill does not call it (Q5, §12) | T |
| AC-12 | The FLOW-3 audit (a model, Q4) flags the impossible beat the `stress` profile commissions; evidenced from the run's critique file, not reproducible | D |
| AC-13 | `validate-sheet.mjs` rejects each of the five defect classes; its self-test passes in CI | T |
| AC-14 | `measure.mjs --self-test` reproduces the fixture's recorded assertions over **six** characteristics, reporting SKIP where data is absent | T |
| AC-18 | `POST /api/runs/{id}/halt` stops the process, marks `halted: user`, keeps the attempt in flight unpromoted and readable | T |
| AC-19 | On startup a run left `running` is marked `halted: process` | T |
| AC-20 | Every stream line lands in `events` before fan-out; `Last-Event-ID: n` replays from `n+1` then goes live | T |
| AC-21 | The spawned argv carries `--max-budget-usd <profile ceiling>`; the prompt is not in argv | T |
| AC-15 | A real `tiny` run completes end to end via the backend with exact cost recorded (last v2 tiny: $18.82); difference vs v1's $7.45 is explained in `docs/domain-knowledge.md` | D |
| AC-15b | A real `stress` run via the backend reaches `patch_then_halt` or explains why it did not; both runs carry `--max-budget-usd` and the profile ceiling; the pair is authorised at Paso 4, Q8 | D |
| AC-16 | The 100k pre-dispatch estimate in `SKILL.md` is present and applied (read the skill; inspect one run's log) | I |
| AC-17 | No dependency on the Anthropic SDK; grep for `anthropic` and `ANTHROPIC_API_KEY` returns nothing outside docs | A |

### 10.1 Results, 2026-09-22 (Paso 10)

Recorded after PLAN-007 6.1–6.12 on `backend-v1`. Letters are the spec's; the
evidence column names the test, the command, or the run. Nothing here was run
by hand except what the letter says is inspection or demonstration.

| id | letter | result | evidence |
|---|---|---|---|
| AC-1 | T | pass | `test_start_a_run_and_follow_it_to_completion`, `test_the_queue_is_one`, `test_the_prompt_is_never_an_argument`; and the real runs below |
| AC-2 | T | pass | `test_a_line_that_is_not_json_is_kept_as_skipped_not_silently_dropped`, `test_a_malformed_line_becomes_a_run_warning` |
| AC-3 | T | pass | `test_runner.py` over the recorded fixture (slug learned, dispatches counted, cost from `result`) |
| AC-4 | T | pass | `test_the_measured_cost_is_stored_and_preferred_over_the_sum`, `test_the_whole_run_cost_comes_from_the_result_event` |
| AC-5 | T | pass | `test_the_budget_stops_the_run_when_the_reported_cost_crosses_it` |
| AC-6 | T (fixture) | pass on an injected packet; **on real streams the packet `usage` reads zero** (P-11, `verification.md` §3.5) | `test_an_oversized_subagent_packet_halts_the_run`, `test_unreported_packets_are_absent_rather_than_zero` |
| AC-7 | T | pass | `test_the_cli_entry_point_imports_the_eight_v1_runs`, `test_an_unknown_critique_shape_is_a_parse_error_row_not_a_drop`; the CLI on a fresh database at Paso 10 (see §3.20 of `verification.md` for what it also did) |
| AC-8 | T | pass | `test_agents_frontmatter.py` |
| AC-9 | T | pass | `test_skill_contract.py`, `test_formulas_agree.py` |
| AC-10 | T | pass | `test_no_route_takes_a_path_and_reads_a_file` (corrected once — it was committed red) |
| AC-11 | T (module) | pass; the skill does not call it (Q5) | `test_vectors.py` |
| AC-12 | D | **pass** — `outline.audit.json` of the stress run: verdict `defects`, one violation (chapter 3, beat 9, rule R4, severity high) found at FLOW-3 and the outline revised before FLOW-4; chapter 3 then needed one redraft, on `prose`, not on the audited beat | `output/cartographer-valley-funding-review/critiques/outline.audit.json` |
| AC-13 | T | pass | `validate-sheet.mjs --self-test`, `test_the_sheet_validator_requires_all_six_scores` |
| AC-14 | T | pass | `measure.mjs --self-test` (six characteristics, two named SKIPs on the fixture), `test_the_measurement_instrument_knows_six_characteristics` |
| AC-15 | D | `night-translator-rewriting-phrasebook` — complete; halted=None (None); cost $16.25 (measured); 3 chapters, 4 attempts, 3 promoted; conformance conformant; warnings 3 | `specs/PLAN-007-results/tiny.json`, `output/<slug>/cost.json`, `docs/domain-knowledge.md` §8 |
| AC-15b | D | `cartographer-valley-funding-review` — complete; halted=None (None); cost $20.15 (measured); 3 chapters, 4 attempts, 3 promoted; conformance conformant; warnings 3 | `specs/PLAN-007-results/stress.json`, `output/<slug>/` |
| AC-16 | I | the skill's 100k estimate is present (`SKILL.md`, `architecture.md` §6.1); `check_log` on the real runs reports the timestamp provenance — see `domain-knowledge.md` §8 | `python -m backend.chapters.check_log output/<slug>` |
| AC-17 | A | pass — `anthropic` / `ANTHROPIC_API_KEY` appear only in three docstrings that say there is none; no network client is imported outside tests | `grep -rn -iE "anthropic|ANTHROPIC_API_KEY" backend frontend/src`; `grep -rn -E "^(import|from) (httpx|requests)" backend` |
| AC-18 | T | pass | `test_halt_stops_the_process_and_marks_halted_user`, `test_halt_keeps_what_was_persisted_readable`, `test_halt_on_an_unknown_or_finished_run_is_404_or_409` |
| AC-19 | T | pass | `test_a_run_left_running_is_marked_halted_process_on_startup` |
| AC-20 | T | pass | `test_every_stream_line_is_in_events_with_a_dense_seq`, `test_sse_id_field_is_the_persisted_seq`, `test_last_event_id_replays_from_the_next_seq_then_goes_live`, `test_last_event_id_beyond_the_end_yields_only_done` |
| AC-21 | T | pass | `test_argv_carries_max_budget_usd_from_the_ceiling_it_is_given`, `test_the_same_figure_reaches_argv_and_the_watcher` |

Suite at this table: **494 backend tests, 19 frontend**, `tsc` clean, both Node
self-tests green. Imported at Paso 10 on a scratch database: the eight v1 runs
(and, uninvited, two v2 runs — `verification.md` §3.20).

## 11. Failure modes considered (full table in `docs/verification.md` §6)

`claude` missing or unauthenticated · malformed stream line · process exits
without `result` · slug never detected · watchdog false positive from `usage`
semantics · budget breach · SQLite lock · `sqlite-vec` fails to load on Windows ·
embeddings model download blocked · unknown critique shape on import · path
traversal · command injection via argv · BOM/mojibake · `SKILL.md` diverging from
`flow.yaml` · orphaned process after restart · SSE client disconnect · impossible
beat reaching FLOW-4.

## 12. Gaps this spec knowingly leaves (per `AGENTS.md` §3, *The gaps a spec leaves*)

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| Pre-dispatch token reservation is an estimate in the skill, not a count | important | no API key → no `count_tokens`; measured post-hoc with halt | `halted: context` rows; estimated vs measured deltas in `calls` |
| The procedure in `SKILL.md` is not testable at $0 | important | only the runner is; the skill needs real runs | `measure` on each real run; LOOP-003 instruments |
| Interrupted runs cannot resume | incidental | v1 scope | `halted: process` count |
| `character_knowledge` is created but never written | incidental | v1 scope; ontology says it matters | table row count stays 0 |
| `POST /api/runs/{id}/halt` (`halted: user`) is not built | important | **closed by PLAN-007 6.7** — `test_halt_stops_the_process_and_marks_halted_user`, `test_halt_keeps_what_was_persisted_readable`, `test_halt_on_an_unknown_or_finished_run_is_404_or_409` | AC-18 |
| The startup sweep (FR-RUN-7) is not built | important | **closed by PLAN-007 6.7** — `test_a_run_left_running_is_marked_halted_process_on_startup` | AC-19 |
| No endpoint serves an artefact by path (FR-RD-1, Q2) | incidental | no client asks for one; the archive answers through `GET /api/runs/{id}` | a frontend feature that needs a file the archive lacks |
| `Last-Event-ID` resume is not built | incidental | **closed by PLAN-007 6.4/6.7 (Q3)** — `test_every_stream_line_is_in_events_with_a_dense_seq`, `test_sse_id_field_is_the_persisted_seq`, `test_last_event_id_*` | AC-20 |
| `SKILL.md` never calls `search` before the continuity critic (§8 point 3) | important | `backend/commons/search.py` and `db/vectors.py` are built and tested and not running (`verification.md` §3.15); the critic gets the full Bible | no `search` call in any run's log |
| `SKILL.md` does not emit `chNN.facts.json` (§8 point 7) | incidental | the rolling summary is text and `check_summary` holds it to its cap | no `facts.json` under `output/<slug>/chapters/` |
| `measure.mjs` measures five characteristics; `prose` is outside its self-test | incidental | **closed by PLAN-007 6.9 (Q6)** — `test_the_measurement_instrument_knows_six_characteristics`, `test_the_sheet_validator_requires_all_six_scores`, `test_the_shipped_template_carries_six_slots` | AC-14 |
| The outline audit is a model (`outline-critic`), not the FR-INS-1 script | important | `verification.md` G11 records it as D; a script would give T and is the next candidate under *code before agent* | the letter stays D until the CLI exists |
| Subagent-level tool calls may not be visible in the stream; the writer's isolation is asserted from the agent file, not observed at runtime | critical → assumed risk | the `tools:` line is the structural guarantee; AC-8 pins it | any change to the agent file fails CI |

## 12a. Decisions taken at Paso 4 (grill, 2026-09-22)

Eight questions, all answered with the recommendation. Each is cited where it
changed a requirement; the list is here so the plan and the report can point at
one place.

| q | decision |
|---|---|
| Q1 | renamed SPEC-007 / PLAN-007: the number collided with SPEC-001-commons |
| Q2 | reads come from the SQLite archive; no file-by-path endpoints in v1 |
| Q3 | an `events` table is added; `Last-Event-ID` replays from it |
| Q4 | the outline audit stays a model (D); a script would be its own spec |
| Q5 | `search` stays built-and-unwired; a declared gap, its own spec |
| Q6 | `validate-sheet.mjs` and `measure.mjs` stay in Node; `measure.mjs` learns `prose` |
| Q7 | import is a CLI, `python -m backend.commons.db.import_v1`; no endpoint |
| Q8 | one real `tiny` run and one real `stress` run, each under `--max-budget-usd` and the profile ceiling |

## 13. How this spec is executed

1. Human sets `status: approved` in the header after review.
2. The building session writes `specs/PLAN-007-backend-v1.md`: tests first, then
   code by feature in `flow.yaml` order (commons before features), then docs
   updates; loop the plan against `docs/architecture.md` and this spec until no
   gap remains.
3. Human sets PLAN-007 to `approved`.
4. Work happens on a new branch cut from the current one; TDD; every merge
   updates this spec if behaviour differs, and `docs/verification.md`.
