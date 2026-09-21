# Architecture

How NovaForge is built: the stack, the rule that governs where code goes, how a
run is orchestrated, the nine agents, how memory is managed, how the 100,000
concurrent tokens are held, and the limits.

`definitions.md` holds the vocabulary. `domain-knowledge.md` holds what the runs
taught. `verification.md` holds every guarantee with the class of evidence behind
it. `AGENTS.md` at the root holds the process the coding agent follows.

---

## 1. The stack

| layer | choice | why |
|---|---|---|
| backend | Python 3.12, FastAPI | the orchestrator itself, not a wrapper around one |
| database | SQLite via the stdlib `sqlite3`, no ORM | small stable schema; `sqlite-vec` is a virtual table and ORMs model those badly |
| vector search | `sqlite-vec` | same file, same transaction, no second service |
| embeddings | `sentence-transformers`, local, `all-MiniLM-L6-v2` (384) | no per-call cost, no network, runs in CI |
| frontend | React + Vite + TypeScript | — |
| frontend structure | Feature-Sliced Design v2.1 | — |
| tooling | uv + pytest; npm + vitest; GitHub Actions | CI runs on the mock engine and costs nothing |

**Context ceiling: 100,000 tokens held concurrently.** Not per call — see §6.

---

## 2. The architecture, and what it is for

The frontend has a named architecture and the backend needed one. Both halves are
governed by the same idea: **slices that do not import each other, and a
dependency direction inside each slice.**

### 2.1 Backend — vertical slices with hexagonal layering

One folder per feature, plus `commons`. Inside each feature:

```
chapters/
├── router.py        HTTP in. Request → arguments, result → response, errors → status.
├── models.py        Pydantic shapes, at the edge only.
├── service.py       The procedure. Imports nothing from FastAPI.
├── domain.py        The rules. Imports nothing but the standard library.
├── repository.py    SQL out, behind a Protocol.
└── prompts/         The agent prompts for this stage.
```

**Rule 1 — dependencies point inward.** `router → service → domain`, and
`service → repository` through a Protocol. `domain.py` imports only the standard
library.

This is not tidiness. It is what makes the gate testable: the `min` of five
scores, `10 − 3` per missing beat, the word band, a sheet's completeness — all
arithmetic over values, testable in `domain.py` with no database, no HTTP and no
model. In v1 those rules were entangled with network calls, so the only way to
exercise them was to write a novel.

**Rule 2 — features do not import each other.** `chapters/` does not import
`bible/`. They compose in `runs/`, or share through `commons/`. This is
Feature-Sliced Design's own rule applied to the backend, so one idea governs both
sides of the app.

### 2.2 What `commons/` is for, precisely

Not "shared code". **What nobody may skip.**

```
commons/
├── llm/       the Anthropic client and its mock; the ONLY path to a model
├── context/   ContextPacket per agent, its builder, the token semaphore
├── budget/    the cost ceiling, checked before every call
├── db/        connection, migrations, sqlite-vec, embeddings
├── config/    flow.yaml, config, profiles
└── log/       one row per call: agent, tokens in/out, cost, duration, real timestamp
```

The semaphore lives in `commons/context` and the client in `commons/llm`, which
is the only way to reach the API. A feature therefore **cannot** send a prompt
without it being counted, reserved and charged. v1 held its central guarantee
structurally, through a subagent's tool list; calling the API directly gives that
up, and routing every call through one module puts a structural guarantee back
where the strongest one was lost.

### 2.3 Frontend — Feature-Sliced Design

Layers, highest to lowest: `app → pages → features → entities → shared`. Imports
go downward only; slices on a layer do not import each other; every slice exports
through its `index.ts`.

- **pages:** `library` · `new-novel` · `run` · `quality` · `manuscript` · `diagram`
- **features:** `start-run` · `watch-progress` · `configure-novel` · `compare-runs`
- **entities:** `run` · `chapter` · `critique` · `agent` · `provenance`
- **shared:** `api` · `ui` · `lib`

The `widgets` layer is discouraged by FSD v2.1 and is not used. v1's
`presentation` and `configurator` screens fold into `run` and `new-novel`.

The logic is ported — types, derivations, and the provenance semantics, which are
the part that took longest to learn. The visual layer is rebuilt.

---

## 3. Orchestration — how we intend to do it

### 3.1 Who orchestrates

**A Python service inside FastAPI. Not a model.** The orchestrator does not
reason: it executes `specs/flow.yaml` stage by stage and applies the gate's
rules. Every turn that Claude Code spent orchestrating in v1 disappears from the
bill — and that was most of it: a measured run priced its agents at $6.21 and
actually cost $49.33.

### 3.2 What an agent is

A Python function. It receives a typed `ContextPacket`, loads its prompt from
`backend/<feature>/prompts/<agent>.md`, calls the engine (real or mock) with its
assigned model, and returns text plus token usage.

**Nothing else. An agent does not read disk and does not write disk** — the
orchestrator does both on its behalf. That is what makes the writer's isolation a
property of a type rather than of anyone's discipline.

### 3.3 The sequence of a run

1. `runs` creates the run and persists its state.
2. **FLOW-1** worldbuild → the orchestrator writes `bible/world.md`.
3. **FLOW-2** characters → the orchestrator writes the other three Bible files.
   These two stages are the only ones that produce canon.
4. **FLOW-3** outline → the orchestrator writes `outline.md`, **then audits the
   commission against `## Rules`** before any chapter exists.
5. **FLOW-4**, per chapter:
   - build the writer's packet — **no prior prose, by type**
   - draft
   - **five critics, in parallel, under the semaphore**
   - `min` of the five scores
   - below 8 → level-1 sheet → attempt 2 → level-2 sheet → attempt 3 →
     `patch_then_halt`
6. **FLOW-5** style — a pass that may not change a word.
7. **FLOW-6** publish — synopsis by an agent, **manuscript assembled in code**.

**State is persisted to SQLite after every stage and every attempt.**

### 3.4 Concurrency

- **Within a chapter:** the five critics run in parallel, bounded by the
  semaphore.
- **Between chapters:** in series. Chapter *n*'s summary feeds chapter *n+1*, and
  that chain is the only channel between them.
- **Between runs:** a queue of one.

### 3.5 Failure and stopping

Three reasons a run halts, each leaving it readable up to where it reached:

| mark | cause |
|---|---|
| `halted: budget` | the cost ceiling was reached; the attempt in flight is kept, unpromoted |
| `halted: context` | a single reservation exceeded the semaphore's total capacity |
| `halted: gate` | `patch_then_halt` exhausted; no chapter file is promoted |

A fourth, `halted: interrupted`, marks a run whose process died. Resume is not
implemented in v1; the persisted state is sufficient to add it without migration.

### 3.6 Observation

**Server-Sent Events, one stream per run.** The frontend listens; it does not
poll. On connect it receives a `snapshot` built from the database, then live
events — so a reconnection cannot leave half a state.

**The stream is a view. The database is the record.**

---

## 4. The nine agents and their skills

The catalogue. `AGENTS.md` describes the process the *coding* agent follows;
these are the agents that write the novel.

**The `ContextPacket` is the boundary.** In v1 each was a Claude Code subagent
whose tool list decided what it could reach — the chapter writer had `Glob`,
which returns paths and cannot return contents, so prior prose was *unreachable*.
In v2 they are prompts plus a typed context, and the boundary is the packet's
type: **what an agent cannot be handed, it cannot read.** That is a weaker class
of evidence and `verification.md` G1 says so rather than inheriting the old
language.

Skills are for *building* this system, not for the agents inside it: an agent
writing a chapter needs a Story Bible, not a SQLite reference. Where that
changes, the row says so.

| agent | stage | model | skills |
|---|---|---|---|
| `worldbuilder` | FLOW-1 | opus | — |
| `character-architect` | FLOW-2 | opus | — |
| `plot-architect` | FLOW-3 | opus | — |
| `chapter-writer` | FLOW-4 | opus | — |
| `continuity-critic` | FLOW-4 gate | sonnet | — |
| `science-critic` | FLOW-4 gate + FLOW-3 audit | sonnet | — |
| `outline-critic` | FLOW-4 gate | sonnet | — |
| `style-editor` | FLOW-5 | sonnet | — |
| `publisher` | FLOW-6 | sonnet | — |

### 4.1 worldbuilder — FLOW-1, opus

**Receives:** the premise verbatim · the genre and tone, read off the premise ·
the chapter count · counts for factions, means entries, world rules and the
world's word band.
**Returns:** the Markdown document.
**Writes:** nothing — the orchestrator writes `bible/world.md`.
**Never sees:** any character. Naming one here fixes a spelling nobody agreed to.

The `## Rules` heading is load-bearing: the world critic reads bullets from under
it and nowhere else, so a constraint written elsewhere is never enforced. Rules
must be falsifiable by a scene, and a rule whose main effect is to make someone
check a division is worse than one about who is allowed in the room.

### 4.2 character-architect — FLOW-2, opus

**Receives:** the premise · genre and tone · the full text of `world.md` · counts
for characters, timeline rows and mysteries · the `names` instruction, default
`familiar`.
**Returns:** three documents.
**Writes:** nothing — the orchestrator writes them.
**Never sees:** any prose.

It fixes canonical spelling for the whole novel; those names travel in every
later packet. `familiar` means names a reader can pronounce on sight and tell
apart at a glance. A real person named in the premise keeps their real name.

### 4.3 plot-architect — FLOW-3, opus

**Receives:** all four Bible files in full · the chapter count · the canonical
names · the promise and beat counts.
**Returns:** the outline as text.
**Writes:** nothing.
**Never sees:** any prose.

`### Chapter N — Title` exactly, em dash included. **Beats numbered `1.` `2.`
`3.`** so the outline critic can name which one is missing. The last agent that
sees the whole book at once.

### 4.4 chapter-writer — FLOW-4, opus

**Receives:** the four Bible files · **this chapter's outline entry only** · the
rolling summary, projected from facts · the canonical names · the chapter number,
title and target. On a redraft, **its own rejected draft** and the feedback sheet.
**Returns:** the chapter, or on a redraft substitutions `{find, replace, why}`.
**Writes:** nothing.

**NEVER SEES: the prose of any other chapter.** The project's central claim. Its
packet has no field that can carry it and a test fails if the builder gains one.

Its own rejected draft is not an exception: the policy forbids a *previous
chapter's* prose. Handing back findings without the text they quote is what once
made redrafts come back worse than what they replaced.

### 4.5 continuity-critic — FLOW-4 gate, sonnet

**Receives:** the draft · Bible fragments retrieved by vector search.
**Returns:** JSON — a score 0–10 and findings, each quoting the draft exactly.
**Never sees:** another chapter's prose.

### 4.6 science-critic — FLOW-4 gate and the FLOW-3 audit, sonnet

**Receives:** the draft · **the whole of `## Rules`, never a retrieved subset**.
**Returns:** JSON — score and findings.

It audits against *this book's* rules, whatever kind they are; the name is
historical. Its rules are passed whole because **a rule not retrieved is a
violation nobody looked for.**

At FLOW-3 it runs again against the outline, before any chapter exists. That
check costs $0.07–$0.13 and has found defects the full gate missed across three
attempts and a patch. It is also asked to report **ambiguity** as a finding in
its own right: a rule that reads two ways does not fail loudly — it fails as a
disagreement nothing can arbitrate, and it cost one run three attempts, a patch
and a halt to discover.

### 4.7 outline-critic — FLOW-4 gate, sonnet

**Receives:** the draft · **this chapter's outline entry entire, beats numbered,
never retrieved**.
**Returns:** JSON — score, findings, and the arithmetic in `notes`.
**Scoring:** `10 − 3 per beat that does not happen − 1 per beat out of order`,
floor 0.

It answers the one question the other four do not: *did the writer write the
chapter the outline commissioned?* Without it, a draft consistent with the Bible,
obeying the world, in the word band and about something else entirely passes
cleanly. A beat delivered differently is delivered: penalise absence and
sequence, never phrasing.

### 4.8 style-editor — FLOW-5, sonnet

**Receives:** one approved chapter, and the word count it must return.
**Returns:** the chapter with punctuation and spacing normalised. **No word may
change.**

The orchestrator counts words before and after and **discards the pass** if they
differ. Arithmetic, not judgement — and it has fired on a pass that changed no
word at all, when closing a space merged two tokens into one. That is the rule
working, and the discard is recorded.

### 4.9 publisher — FLOW-6, sonnet

**Receives:** the Bible, the outline and the chapter summaries — **not the
chapters**. A synopsis is written from canon.
**Returns:** the synopsis.

The manuscript is concatenated **in code**. A model asked to concatenate
paraphrases a sentence in the middle of text the gate already approved.

---

## 5. Memory management — short and long term

Four layers, from the most ephemeral to the most persistent. **The rule that
joins them: what enters a prompt is a *projection* of memory, never memory
itself — and that projection is what counts against the 100,000.**

| layer | what it is | where it lives | how long | who writes it |
|---|---|---|---|---|
| **Call memory** | one agent's `ContextPacket` | process memory | one call; the model retains nothing after | the context builder |
| **Run working memory** (short term) | the rolling summary as structured facts `{fact, chapter, kind}` with a cap by count; the feedback sheets; the per-attempt drafts; stage state | SQLite, by `run_id` | the run | the orchestrator |
| **Canon** (long term within a run) | the Bible — world, characters, timeline, mysteries — and the audited outline | Markdown in `output/<slug>/` + a vector index in SQLite | the whole run; immutable after FLOW-3 | only `worldbuilder` and `character-architect`, through the orchestrator; the outline, `plot-architect` |
| **Between-run memory** (long term, system) | runs, calls, exact costs, findings by kind, scores by characteristic; `character_knowledge` (empty in v1) | SQLite | permanent | the orchestrator and the importer |

Three consequences worth writing down:

**The rolling summary is working memory, not canon.** It is rebuilt for each
chapter from the facts; the writer receives the projection as text. Facts carry
four closed kinds — `event`, `state-change`, `knowledge`, `open-question` — and
`who` on the `knowledge` ones, which is what fills `character_knowledge` in the
same transaction that writes the chapter. When the cap bites, every
`open-question` survives first, and dropping one warns at run level rather than
halting: an abandoned promise is the ontology's foreshadowing failure arriving
quietly, so it has to be visible.

**Vector retrieval is how canon is projected without entering whole.** The
continuity critic receives the fragments nearest the draft. The science critic
receives `## Rules` entire, because it is small and a rule not retrieved is a
violation nobody looked for. The outline critic receives its entry entire, for
the same reason.

**Between-run memory is where the system could learn**, and it is where
LOOP-002's idea would live — a fixed-size list of lessons that forgets on
purpose, carrying no prose quotations — **if v2 decides to switch it on. In v1 it
is recorded and never injected.** Recording without injecting is the cheap half,
and it is the half that cannot go wrong.

---

## 6. Managing the 100,000 concurrent tokens

**The ceiling applies to the sum of all model calls in flight at the same
instant**, not to each call separately. The distinction is not pedantic: the five
critics run in parallel, and five calls of 30,000 tokens each satisfy a per-call
limit while putting 150,000 in the air. A per-call limit is a *consequence* — no
single call can reserve more than the total capacity.

### 6.1 The mechanism: a token semaphore in `commons/context/`

- **Capacity: 100,000, read from config.** Never a literal in the code.
- Before each call the orchestrator computes the **reservation**: prompt tokens +
  `max_tokens` for the reply.
- **Prompt tokens are counted, never estimated** — with Anthropic's token-counting
  API for the real engine, and the equivalent tokenizer in the mock.
- The call **acquires** that amount. If capacity is short it **waits**; waiting is
  never a failure. When the call finishes it **releases**.
- **A reservation larger than total capacity is rejected before waiting** — that
  is `halted: context`, an error of the run, not an infinite wait.

Note the shape: the reservation is worst case, since `max_tokens` bounds a reply
nobody can predict. A semaphore sized by an *assumed* reply is one a single long
answer walks through, and a ceiling that can be exceeded is not a ceiling.

### 6.2 What the log records, per call

| field | why |
|---|---|
| `tokens_reserved` | what this call held |
| `in_flight_at_dispatch` | what everything else held when it started |
| `wait_ms` | how long it waited for room |

With those three, two series can be drawn that were previously assertions:
**"chapter 34 weighs what chapter 1 weighed"**, and **"how long the critics spent
waiting"** — which is the cost of the ceiling, made visible rather than argued
about.

### 6.3 The test

Five critics dispatched in parallel, 30,000 tokens each. The test asserts, over
every row in the log, that `in_flight_at_dispatch + tokens_reserved ≤ 100,000`,
and that all five completed. It is a **Test**-class guarantee in
`verification.md`.

### 6.4 What a `tiny` run reserves

Estimated from the current runs and **marked estimated until Phase 3 measures
it**.

| call | reservation, estimated |
|---|---|
| worldbuilder | ~6,000 |
| character-architect | ~8,000 |
| plot-architect | ~12,000 |
| chapter-writer | ~14,000 |
| continuity-critic | ~15,000 |
| science-critic | ~9,000 |
| outline-critic | ~8,000 |
| style-editor | ~7,000 |
| publisher | ~7,000 |

The three model critics together come to roughly 32,000, which fits — so on
`tiny` the semaphore should rarely block, and a `wait_ms` that is consistently
non-zero there means one of these estimates is wrong. That is the point of
recording it.

---

## 7. Skills installed for building this

Phase 0. Every skill was read in full before installing — a skill is text with
instructions, and one carrying executable code, a downloader, or a request for
credentials is not installed. Installed under `~/.claude/skills/<name>/SKILL.md`.

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

### 7.1 Why `SecureSkills-io/sqlite-skill` was rejected

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

### 7.2 The verification skill's missing source

The brief says to build it from the professor's verification-methodologies
artifact (`c71637b1`). That artifact is not shared with this account. It was built
from the summary in the brief instead, says so inside itself, and asks whoever
obtains the artifact to correct it and state what changed. The brief's summary
names eleven agent-process methods and lists ten; the skill records the gap rather
than inventing the eleventh.

The two ontology artifacts *are* available and were used for `definitions.md`.

---

## 8. Decisions taken while building

Recorded here as the brief's §0 requires, for decisions it did not settle.

**The backend needed an architecture and did not have one.** "A folder per
feature plus commons" is a layout, not an architecture: it says where files go,
not what may import what. §2.1 adopts vertical slices with hexagonal layering —
the mirror of the frontend's FSD — because the guarantees have to live somewhere
that cannot be bypassed, and a layout alone cannot provide that.

**The repository is at `Desktop/novaforge-v2`, and is named `novaforge`.** The v1
tree stays in place, working and readable: its eight novels are imported from it
and its procedure is translated stage by stage, and overwriting the reference
while still reading from it would be an avoidable risk.

**`npx skills add` was not used** for `feature-sliced-design`. It installs before
the skill can be read, which the brief's own security rule forbids. The
repository was cloned, read, and copied by hand.

**The embedding model is `all-MiniLM-L6-v2`, 384 dimensions.** Permanent, because
a `vec0` table fixes its dimension at creation and changing it means a re-index.
Taken as the simplest option rather than asked, per §0. The model name is recorded
beside every vector table: two different models of the same dimension are accepted
by the store and return confident nonsense, and nothing but that record catches it.

**The unit of drafting stays the chapter, not the scene.** The ontology models
scenes; changing to them would restructure `flow.yaml` and all nine packets. The
brief asks for the same project, improved.

### 8.1 Settled in the grilling round

Fifteen decisions the brief left open, closed before Phase 2.

**The rolling summary is structured facts.** The call that already writes
`chNN.summary.md` returns JSON instead of prose: `{fact, chapter, kind}` with four
closed kinds and `who` on `knowledge` facts only. No extra model call; one already
paid for now returns something queryable, and `who` is what fills
`character_knowledge` in the same transaction that writes the chapter.

**The cap drops by kind, never by age alone.** Survival order: every
`open-question`, then recent `state-change`, then `event`. Dropping an
`open-question` **warns and is recorded at run level, and does not halt**. Halting
because a novel opened many threads is the wrong trade; the cap exists to hold the
context flat, not to govern the story. Widening it silently would make the
flat-context claim unverifiable.

**The importer imports what is common and records what was missing, per run.** The
eight runs carry three critique shapes, eight chapter schemas and five critic sets;
three wrote no gate rows at all. Each gets a completeness record, and the interface
says "not recorded" rather than zero. They are marked `pre-loop003` and **excluded
from LOOP-003's statistics**: a pass rate over runs judged by three critics does
not measure what it claims. The importer does **not** backfill `knowledge` facts
from their prose summaries; that would be invented data wearing the appearance of
measurement.

**The mock engine takes an explicit plan**, `{chapter, attempt, fail: [...]}`, not
a seed. The tests that matter are specific, and random failure tests nothing in
particular. The split falls out of a boundary that already exists: `length` and
`chatter` are real code and always compute over the text the mock produced — so
the mock must emit out-of-band and heading-less text on demand — while the three
model critics have their scores scripted. Scripting the two that reproduce would
be not testing them.

**Three halts, each with its mark and its readable artefacts.** See §3.5.

**SSE sends a `snapshot` on connect, then live events.** See §3.6.

**The budget projects worst case** — exact input tokens plus `max_tokens`. A
ceiling computed from an assumed output is broken by one long reply. Worst case
stops slightly early, which is the correct direction to be wrong in, and the real
cost is recorded afterwards so the gap stays visible.

### 8.2 From Annex B

**`AGENTS.md` is the standard file: the process the coding agent follows**, not a
catalogue of the novel's agents. That catalogue is §4 of this document, which is
where the brief asked for "the list of agents and their skills, the process".
`claude.md` opens by pointing at `AGENTS.md`.

**The 100,000-token ceiling is concurrent, not per call** (§6). The brief said
"counted before sending, per call"; the requirement is *concurrent*. Five critics
of 30,000 satisfy a per-call limit and put 150,000 in the air. The mechanism is a
semaphore, and the per-call limit survives only as a consequence.

**Spec → plan → code, with human approval written into the file** (D31). States
live in the artefact, not in a conversation. TDD, with the test seen failing
before the code exists.

---

## 9. Limits

Stated here and classified in `verification.md`.

- **The gate does not reproduce.** Three of its five characteristics are model
  judgements. "It passed the gate" is a statement about one run.
- **No tamper-evident audit.** The log is a record the orchestrator writes.
- **One writer at a time**, one user, no authentication. A local tool.
- **Retrieval is not exhaustive.** Where a check must see everything — every rule,
  every beat — the whole thing is passed and nothing is retrieved.
- **The writer's isolation is now typed, not structural.** In v1 the chapter
  writer held a tool list that could not return file contents; the prose was
  unreachable. In v2 it is a `ContextPacket` with no field for prose, plus a test.
  A real downgrade in the class of evidence, and `verification.md` says so rather
  than inheriting v1's language.
