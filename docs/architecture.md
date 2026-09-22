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
| model access | **Claude Code, the user's own session** | there is no API key and no SDK anywhere in this project |
| backend | Python 3.12, FastAPI | launches Claude Code, watches its stream, archives what it says |
| database | SQLite via the stdlib `sqlite3`, no ORM | small stable schema; `sqlite-vec` is a virtual table and ORMs model those badly |
| vector search | `sqlite-vec` | same file, same transaction, no second service |
| embeddings | `sentence-transformers`, local, `all-MiniLM-L6-v2` (384) | no per-call cost, no network, runs in CI |
| frontend | React + Vite + TypeScript | — |
| frontend structure | Feature-Sliced Design v2.1 | — |
| tooling | uv + pytest; npm + vitest; GitHub Actions | CI runs on the mock engine and costs nothing |

**Context ceiling: 100,000 tokens**, held in two layers rather than reserved in
advance — see §6.

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
├── runner/    launches `claude -p`, reads its stream, watches context and budget
├── db/        connection, migrations, repository, sqlite-vec, the v1 importer
├── config/    flow.yaml, config, profiles, pricing
├── log/       one row per call: agent, tokens in/out, cost, duration, real timestamp
└── search.py  retrieval over the Bible, the outline and the summaries — never prose
```

**This tree was wrong until 2026-09-22**, and wrong in the way that matters: it
listed `llm/` ("the Anthropic client and its mock; the ONLY path to a model"),
`context/` (the token semaphore) and `budget/` (a ceiling checked before every
call). None of the three exists. They were the D2 design, and **Annex C deleted
the premise all three rested on** — there is no client, because there is no key.
A map of a codebase that no longer matches it is worse than no map, so
`test_architecture_doc.py` now fails if this tree names a directory that is not
there.

What replaced the guarantee that paragraph was making: every model call goes
through `claude -p`, launched by `commons/runner` with an explicit `--allowedTools`
list, and the agents' authority is their `tools:` front matter. That is the
structural guarantee v1 had, back again — see §3.2
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

**Claude Code, running `.claude/skills/novaforge/SKILL.md`.** Not a Python
service. There is no Anthropic API key and no way to obtain one, so the only
access to a model is the user's own Claude Code session on this machine.

FastAPI is the **launcher, the observer and the archive**. It starts
`claude -p --output-format stream-json --verbose` as a subprocess with the prompt
on stdin, reads the stream line by line, forwards it over SSE, persists state in
SQLite, and writes `cost.json` from the final `result`. That is exactly what v1's
four Vite plugins did, moved to Python with a database behind it.

**This was reversed deliberately**, and §8.4 says what it gains and costs. The
short version: it gains back the strongest guarantee the project has, and it
loses the ability to reserve tokens before a call.

### 3.2 What an agent is

A subagent, dispatched by Claude Code with the `Agent` tool, defined by
`.claude/agents/<name>.md`. **Its `tools:` line is the authority model.**

`chapter-writer` holds `tools: Glob`. `Glob` returns paths and cannot return
contents, so a previous chapter's prose is **unreachable** — not merely not
passed. That is the difference between a capability being absent and a code path
being polite, and it is why `verification.md` G1 is class **A** rather than
**T**.

Only `worldbuilder` and `character-architect` hold `Write`. The other seven
return text and the orchestrator writes the file.

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
   - **five critics, in parallel** — how many at once is the orchestrator's
     estimate, not a reservation (§6.1)
   - `min` of the five scores
   - below 8 → level-1 sheet → attempt 2 → level-2 sheet → attempt 3 →
     `patch_then_halt`
6. **FLOW-5** style — a pass that may not change a word.
7. **FLOW-6** publish — synopsis by an agent, **manuscript assembled in code**.

**State is persisted after every event the stream reveals**, not at the end. The
run's slug is *learned* from the `output/<slug>/` paths the run writes, because
Claude Code derives it from the premise itself and a guessed slug opens the wrong
novel or none.

### 3.4 Concurrency

- **Within a chapter:** the five critics run in parallel. How many fit at once is
  decided by the orchestrator's `wc -w` estimate before dispatch — an estimate,
  not a reservation, and §6 says why that is the honest word.
- **Between chapters:** in series. Chapter *n*'s summary feeds chapter *n+1*, and
  that chain is the only channel between them.
- **Between runs:** a queue of one.

### 3.5 Failure and stopping

Three reasons a run halts, each leaving it readable up to where it reached:

| mark | cause |
|---|---|
| `halted: budget` | the cost ceiling was reached; the attempt in flight is kept, unpromoted |
| `halted: context` | a subagent packet was reported above the ceiling |
| `halted: gate` | `patch_then_halt` exhausted; no chapter file is promoted |
| `halted: process` | the orchestrator ended without a `result` event |
| `halted: interrupted` | the launcher itself failed |

**A `claude -p` process that dies is not resumed.** The run halts, stays readable,
and resuming would be a different run. That is an honest limit of this
arrangement rather than a missing feature.

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

## 6. Managing the 100,000 tokens

**Python no longer assembles the prompts**, so it cannot reserve tokens before a
call. The semaphore Annex B specified is not implementable here, and saying so is
better than shipping something that looks like one. Two layers replace it, and
neither is a reservation taken in advance.

### 6.1 Layer 1 — a procedure, inside `SKILL.md`

Before dispatching an agent, the orchestrator measures the packet with `wc -w`
and converts at roughly **1.35 tokens per word**, marked `estimated`. Over the
limit, it trims — the summary, the number of retrieved fragments — and measures
again. For concurrency it decides how many critics can go at once from those
estimates: if five do not fit, they go in two rounds.

**This is a procedure, not a guarantee.** `verification.md` classifies it
**Inspection**.

### 6.2 Layer 2 — a measurement, in Python

Every message in the stream carries `usage`. `commons/runner/watch.py` reads it
and stops the process when a subagent packet exceeds the ceiling. It is a real
check on real figures — **and it arrives after the call, not before it.**

### 6.3 Two things replaying real runs showed, and they shaped this

**`input_tokens` alone is nearly always 2.** Almost the whole context arrives
cached, so the real size is
`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. A watcher
reading only the first field reports two-token calls and never trips: a ceiling
that cannot be exceeded because it is measuring the wrong thing.

**The orchestrator's own turns are far above 100,000 and always will be.**

| run | median | p90 | peak |
|---|---|---|---|
| a 3-chapter stress run | 147,086 | 263,285 | 299,678 |
| an 8-chapter run | 254,448 | 554,937 | 642,667 |

That is not a defect. An orchestrator accumulates — it carries the Bible, the
drafts, the findings and the sheets turn after turn, which is the same fact that
made a $6.21 estimate stand in for $49.33. **Halting on those figures would halt
every run inside a minute.** The ceiling was never the orchestrator's budget: it
is about the packets the *agents* receive, the quantity the architecture claims
stays flat as a book grows.

Those packets have a slot in the stream — `task_progress` carries `subagent_type`
and `usage` — and **in both recordings that `usage` reads zero**. So the one
quantity the ceiling is actually about is, from the stream, **not measurable
today**. The watcher therefore reports `packet_series_provenance: absent` rather
than claiming every packet was small. Zero and unmeasured are different
statements, and this one says which.

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
of 30,000 satisfy a per-call limit and put 150,000 in the air.

*Annex B specified a semaphore for this, and Annex C made it unbuildable.* The
reading survives — concurrency is what the ceiling is about — but the mechanism
is now an estimate the orchestrator makes before dispatching and a measured stop
after the fact. §6 and `verification.md` §3.4 say what that costs.

**Spec → plan → code, with human approval written into the file** (D31). States
live in the artefact, not in a conversation. TDD, with the test seen failing
before the code exists.

---

## 8.3 What is built, 2026-09-22

| phase | state |
|---|---|
| 0 — skills | ten installed, each read in full, sources and licences at §7 |
| 1 — documents | six written; fifteen open decisions closed in a grilling round |
| 2 — backend | **done.** A novel runs end to end in CI at $0, on a recorded stream |
| 3 — the real orchestrator | **done, and run for real.** See below |
| 4 — the panel | six pages, FSD, reading one backend; typecheck and build clean |
| 5 — retrieval | `sqlite-vec` with the dimension pinned and the limits tested |
| 6 — the outline audit | at FLOW-3, with its own tests, and it earned its place on the first real run |

**230 backend tests and 18 frontend tests**, one second, no network and no
credential.

**The first real run happened.** `lighthouse-keeper-ledger` — three chapters,
seven drafts, four feedback sheets, a book, **$18.82 measured** from Claude
Code's own `result` event, 136 turns, 56 minutes. Against v1's **$7.45** for a
run of the same shape, judged by two characteristics instead of five and with no
outline audit. `domain-knowledge.md` §5 has the comparison and why it is not like
for like.

That sentence used to read *what has not happened is a single real model call in
v2*, and said the next step needed a credential in the environment. Annex C
removed the credential from the question entirely.

### 8.4 Annex C — Claude Code orchestrates, and there is no API key

D2 reversed. There is no Anthropic key and no way to get one, so the only access
to a model is the user's Claude Code session.

**What it gains.**

- It works, with the session that already exists.
- **The writer's isolation goes back to being structural** — `tools: Glob`, which
  cannot return contents. That is the strongest thing the project has and it was
  about to be traded for a type and a test.
- **The real cost of the whole run, orchestrator included, arrives measured** in
  the `result` event. v1's factor of eight stops being a hole and becomes a
  number.
- **One implementation of the pipeline**, `SKILL.md`. Python validates that it
  does not contradict `flow.yaml` or `config/`; it does not duplicate it.

**What it costs, plainly.**

- **No reservation before a call.** The ceiling is a procedure plus a measured
  stop; §6 has the detail.
- **The procedure cannot be tested at $0.** The runner, the parser, the
  persistence, the SSE and both watchers are covered by a recorded stream.
  `SKILL.md` is covered by real runs, each of which costs the subscription.
- **No resume.** A dead `claude -p` halts the run; resuming would be a different
  run.

### 8.5 What the first real run cost to fix, 2026-09-22

A finished run is a better reviewer than any reading of the code. Four defects it
exposed, each with its own spec or commit:

| what | how it was found |
|---|---|
| `SKILL.md` taught a gate verdict the database rejects | writing the `SKILL.md` ↔ contract validator §5 had claimed to have |
| the run finished with an **empty archive** — every gate fact on disk, none in the database | looking at the database after it finished (SPEC-003) |
| `.gitignore`'s `dist/` was excluding every generated manuscript | listing what was tracked |
| the after-attempt decision was a paragraph a model applied | applying Annex D's criticality rule, which said G6 was below its minimum (SPEC-004) |

And two things built because the gap table named them: the mechanical prose check
(SPEC-005) and the canonical-name check, both **script before agent**, both $0,
both measured over everything that has ever shipped before being believed.

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
