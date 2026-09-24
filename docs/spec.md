---
id: SPEC-EXAM-001
title: storyMaker — personalised novels as a gift, built on the NovaForge harness
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "acepto y apruebo tus recomendaciones y todo"; written at his instruction
approved_on: 2026-09-23
written_before_code: yes — this file exists in the first commit of storyMaker that adds exam code
delivery: Friday 2026-09-25, morning
depends_on: the NovaForge v2 harness this repository is cloned from (branch backend-v1 at 055c31d), AGENTS.md, docs/architecture.md, docs/verification.md, specs/SPEC-007 … SPEC-011
---

# storyMaker — what is being built, and why

The final exam of *Harness Engineering* asks for an agentic system that writes
**personalised novels to give as a gift**: ten chapters of 1,000–1,500 words in
which the recipient recognises their own name, history and details, and which a
reader can read end to end without stumbling. It is graded on the reasoning in
`/docs` and on **evals with numbers**, not on the prose.

**Decision one, and the one everything else follows from:** storyMaker is
**NovaForge v2, adapted**, not a new system. NovaForge already writes a novel
end to end with a bounded context, a six-characteristic quality gate with three
escalating attempts, a Story Bible, a per-run archive in SQLite, provenance on
every figure, and 524 tests at $0. The exam's roles map onto its agents; the
exam's validators map onto its instruments; the exam's memory is its Bible and
archive, moved into SQLite tables the exam names. What is genuinely new is
listed in §3 and is small enough for two days. Everything the exam asks that
does not fit is named in §5 as **out of scope, declared**, never omitted.

**Decision two:** the novels are generated with **Haiku** (SPEC-011 of the
harness, 2026-09-23). Cheaper runs mean the five evaluation briefs can actually
run before Friday; the gate stays exactly as it was, so quality is *measured*
under Haiku rather than assumed.

**Decision three:** the reading format is **PDF**, not web. The exam admits
either. With two days, an interactive PDF (navigable index, character and place
sheet with links, personalised cover, a "what changed" page on regeneration)
is deliverable and the reader-change demo is a regenerated PDF; a web reader
with fact selection is not deliverable in the time and is P1 of a later spec.

## 1. What the client asked for, mapped

| exam requirement | what storyMaker does | new or reused |
|---|---|---|
| interviewer collects recipient data, detects missing data and one contradiction, treats free text as untrusted, emits a schema-validated brief | stage **FLOW-0** dispatches the `interviewer` agent with the buyer's answers and free text; the reply is validated by the `Brief` Pydantic model; **missing fields and the age/tone contradiction are decided in code** (`backend/brief/domain.py`), the agent only extracts and asks | new |
| three roles minimum: planner, writer, editor/critic | `plot-architect` (planner), `chapter-writer` (writer), the four critics + `style-editor` (editor); plus `worldbuilder`, `character-architect`, `publisher`, and two new roles: `interviewer`, `judge` | reused + 2 new |
| `CLAUDE.md`, a reusable skill, two hooks (chapter validation, policy) | `CLAUDE.md` rewritten for the exam; the skill is the harness procedure `.claude/skills/storymaker/SKILL.md`; hooks in `.claude/hooks/`: `validate-chapter` (length, canonical names, schema of the critique files) and `policy` (forbidden words + audit log), wired as `PostToolUse` on writes under `output/*/chapters/` | new hooks, reused procedure |
| tools with validated schema | every CLI instrument the orchestrator calls prints JSON validated by a Pydantic model in `backend/*/models.py`; the brief and each role's output have a schema | partly reused |
| retries with a limit | three attempts, `patch_then_halt`, `decide` and `promote` unchanged | reused |
| tokens and cost per novel in Langfuse | `tools/export_to_langfuse.py` (from NovaForge v1) rewritten for v2's `logs/agents.jsonl` + `calls` + `validations`: one **session per novel**, one **trace per version**, one **span per agent call and per tool**, **scores** per validator, prompts registered as versions from `.claude/agents/*.md`; the run's exact total from Claude Code's `result`. Exported after each version, not live — said so in `/docs` | adapted |
| story bible in SQLite with fact → chapters, and a chronology table | migration `010_story_bible.sql`: `facts(id, run_id, kind, text, source)`, `fact_usage(fact_id, version_id, chapter)`, `characters(run_id, canonical_name, role, birth_date, first_chapter)`, `places`, `chronology(run_id, event, moment, place, excludes_after)`, `chronology_participants`; filled by `python -m backend.bible.ingest` from the Markdown Bible the agents already write, and by `python -m backend.chapters.fact_usage` after each accepted chapter | new tables, script before agent |
| chapter summaries for later context | the rolling summary, unchanged | reused |
| checkpoint per chapter, resume from the last complete one | `state.json` + attempts on disk already; `SKILL.md` §0 gains the resume rule and `python -m backend.runs.resume <slug>` prints where to continue; demonstrated by killing one run mid-chapter | mostly reused |
| validators of four kinds, each named, with an execution point and a Langfuse score | §2 | mixed |
| forbidden-words guardrail, three levels, normalised, with retries, audit log, tests | `backend/policy/`: table `forbidden_words(level ∈ global/client/novel, term, normalised)`, seed of global terms in the migration, normalisation = casefold + NFKD strip accents + simple plural; a hit returns the chapter through the feedback sheet; attempts exhausted → `halted: policy`; every hit → `audit_log` + Langfuse score; tests per level plus accent and plural | new |
| audit log of policy decisions | `audit_log(run_id, ts, actor, decision, detail, langfuse_trace_id)` | new |
| 100,000 concurrent tokens | the two layers of the harness (`SKILL.md` estimate + `ContextWatcher` on `total_tokens`, SPEC-010 W2) | reused |
| reading: index, character/place sheet with links, personalised cover; PDF regenerated with a "what changed" page; previous version kept | `backend/publish/pdf.py`: HTML from the archive → Playwright Chromium print → `dist/v<N>/novel.pdf`; `versions(run_id, n, parent, reason)`; a reader change is `python -m backend.versions.change <slug> --fact <id> --to "<text>"` | new |
| five briefs, one adversarial, one temporal-incoherence; a table brief × validator; one tuning iteration | `evals/briefs/01..05.json`, `python -m backend.evals.run`, `evals/results.md` generated from `validations`; tuning = one prompt change on `chapter-writer` (personalisation), brief 01 before/after | new |
| Lean 4 chronology validator | `python -m backend.formal.lean_export <slug>` writes `lean/Chronology.lean` with the events and two invariants (order; age ≥ 0 and ≤ 120 at every event) as `decide` theorems over the concrete lists; `lake build` in the publish gate **if elan installs on the VM** (§5) | new, conditional |
| TLA+ harness specification | `tla/Harness.tla` + `Harness.cfg` (Configuring → Planning → Writing(ch) → Validating(ch) → Published(v) \| Halted; retries, checkpoint, ReaderChange; 3 safety invariants + 1 liveness); TLC **if Java installs** (§5); the README maps each action to `backend/runs/` | new, conditional |
| browser MCP configured and its use documented | `.claude/mcp.json` with Playwright MCP; one real session opening `dist/v1/novel.html` to check index, sheet and cover; `docs/browser-mcp.md` | new |
| `/docs` inventory | §6 | new |
| presentation with corporate identity, budget slide, video | Claude Design on the organisation's **Qaracter design FRM** system; `presentacion/` with PDF + PPTX + annexes + README; the video is recorded by the owner | new |

## 2. The validators — name, point of execution, score

| kind | name | checks | runs at | Langfuse score |
|---|---|---|---|---|
| a | `schema_brief` | the brief conforms to `Brief` | FLOW-0, before anything is spent | pass/fail |
| a | `schema_role_output` | each critic's JSON and the outline audit conform to their models | `validate-chapter` hook | pass/fail |
| a | `canonical_names` | recipient and characters spelled exactly as `characters.canonical_name` (`backend/chapters/names.py`, exists) | `validate-chapter` hook | number of deviations |
| a | `chapter_length` | 1,000–1,500 words (`length` characteristic, exists) | gate, every attempt | words |
| a | `mandatory_facts` | every fact with `source = brief` and `mandatory = 1` has a `fact_usage` row | publish gate, per version | fraction covered |
| a | `forbidden_words` | §1 guardrail | `policy` hook, every attempt | hits |
| a | `visual_check` | the PDF's HTML renders index, sheet and cover — Playwright MCP session, documented | publish gate, once per version, manual + documented | pass/fail |
| b | `judge_rubric` | continuity, tone, narrative arc, character coherence, pacing, **natural personalisation** — a score 0–10 and a justification per criterion, from the `judge` agent on the assembled book | publish gate, per version | 6 scores + mean |
| b | `human_review` | the owner reads one complete novel with the same rubric | once, Thursday night | 6 scores; delta with the judge |
| c | `lean_chronology` | two invariants over the exported chronology | publish gate, `lake build` | pass/fail, or `not run: elan unavailable` |
| d | `tla_harness` | 3 safety + 1 liveness with TLC on 5 chapters / 2 retries | development, not per generation | — |

Plus the six characteristics of the existing gate (`continuity`, `science`,
`outline`, `length`, `chatter`, `prose`), which are the editor role, unchanged.

## 3. What is genuinely new, in one list

1. `interviewer` and `judge` agents (`.claude/agents/`), both `model: haiku`, `tools: Glob`.
2. `backend/brief/` (Pydantic `Brief`, missing-data and contradiction rules, `POST /api/briefs`).
3. Migration `010_story_bible.sql` and `backend/bible/ingest.py`, `backend/chapters/fact_usage.py`.
4. `backend/policy/` (forbidden words, audit log) and the two hooks.
5. `backend/publish/pdf.py` (HTML + Playwright print) and `backend/versions/` (versions, reader change).
6. `backend/evals/` (five briefs, runner, results table).
7. `tools/export_to_langfuse.py` adapted to v2 with sessions, spans, scores and prompt versions.
8. `backend/formal/lean_export.py`, `lean/`, `tla/` — conditional on tooling.
9. `config/profiles/exam.json`; `CLAUDE.md`; `/docs` per §6; `presentacion/`.

## 4. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | a brief with a missing field returns `incomplete` with the questions; a brief with age 8 and an adult tone returns the contradiction; both decided in code with tests | T |
| AC-2 | free text containing an injection ("ignore your instructions…") ends up as a `facts.source = freetext` row and in no prompt as an instruction; the adversarial brief (04) shows it | T + D |
| AC-3 | after FLOW-2, `facts`, `characters`, `chronology` are populated from the Bible of the run; after each accepted chapter, `fact_usage` has rows | T |
| AC-4 | the guardrail catches a global term, a client term and a novel term, plus an accented variant and a plural, in tests; a hit writes `audit_log` and a sheet finding | T |
| AC-5 | the two hooks fire on a write under `output/*/chapters/` and their output is JSON | T (hook script) + D (Claude Code firing it) |
| AC-6 | `dist/v1/novel.pdf` exists for the example brief with cover, dedication, linked index, character/place sheet linking each to its first chapter | D + I |
| AC-7 | a reader change on one fact regenerates only the chapters `fact_usage` names, writes `dist/v2/novel.pdf` with a "what changed" page linking to them, and `dist/v1/` is untouched | D + T (versions table) |
| AC-8 | the five briefs run; `evals/results.md` shows, per brief, each validator's result; the tuning iteration shows brief 01 before and after with the prompt version named | D (the runs) + T (the table is generated from `validations`) |
| AC-9 | `judge_rubric` writes six scores with justifications per version; the human review of one novel is in `docs/iterations.md` beside the judge's | D + I |
| AC-10 | every novel has a Langfuse session with a trace per version, spans per agent call, the validators' scores, the run's measured cost, and the prompts as versions | D |
| AC-11 | `lean/Chronology.lean` is generated from the chronology of a real run and `lake build` passes or the reason it did not run is written | D or declared |
| AC-12 | `tla/Harness.tla` model-checks with TLC on 5 chapters / 2 retries, or the reason it did not run is written; the README maps actions to code | D or declared |
| AC-13 | `/docs` has every file of §6; `presentacion/` has the deck in PDF and PPTX with the Qaracter identity, the budget slide from the measured costs, and the video or its link | I |
| AC-14 | no API key anywhere; `.env.example` lists `LANGFUSE_*` with no values | A + T (grep in CI) |
| AC-15 | the 524 tests of the harness still pass, plus the new ones | T |

## 5. Out of scope, declared

MCP server, write tools over MCP, prose linters beyond the mechanical check the
harness has, an LSP or manual-edit linter, user login, security agent, web
reader with fact selection (P1). **Lean and TLA+ run only if `elan` and a JDK
install on the VM without administrator rights**; if either does not, the export
and the specification are still written and their verification is recorded as
*not run, with the reason*, which the exam admits for Lean. Live Langfuse
tracing (the export is post-hoc). A second eight-chapter NovaForge run. A
video recorded by the sessions — the owner records it.

## 6. `/docs` inventory

`spec.md` (this), `trade-offs.md`, `explainers/` (harness, story bible,
LLM-as-judge, hooks, guardrails, TLA+, Lean, observability, T/A/I/D/U, best
effort), `diagrams/` (harness, TLA+ state machine, SQLite schema, validators
table), `iterations.md`, `red-team-log.md`, `verification.md` (the harness's,
extended with the exam's validators), `browser-mcp.md`, `skills.md`,
`subagents.md`. The harness's own `architecture.md`, `definitions.md`,
`domain-knowledge.md` stay and are cited.

## 7. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| Haiku's gate pass rate is unknown; all measured figures before 2026-09-23 are Opus/Sonnet | important | the evals measure it; the budget slide uses Haiku figures only | `evals/results.md` |
| Langfuse is post-hoc, not live | important | the harness has no hook into the orchestrator's turns; the run total is exact from `result` | the trace's timestamps are the export's, labelled |
| `fact_usage` is string matching of canonical names and fact text against chapter prose, not semantic | important | script before agent; a fact paraphrased is missed and reported as uncovered, never invented as covered | `mandatory_facts` reporting uncovered facts a reader can see in the text |
| the reader change regenerates chapters through the same gate and may fail it | important | `patch_then_halt`; a halted regeneration leaves v1 intact | `halted: gate` on a version > 1 |
| `visual_check` is a documented manual session, not a test | incidental | two days | `docs/browser-mcp.md` |
| Lean and TLA+ conditional on tooling | important | admin rights on the VM unknown | the reason line in `/docs` |

## 8. Decisions taken after approval

| date | decision | why | owner's words |
|---|---|---|---|
| 2026-09-23 | **The orchestrator stays on the session's model** (`models.orchestrator: null`); only the ten agents run on Haiku | a real run with the orchestrator on Haiku dispatched 58 subagents, all `general-purpose`, none of the project's ten: the chapter writer held every tool, the central guarantee (no prior prose) did not exist, and no critique reached disk (`novaforge-v2`, run `phantom-station`) | — (measured; SPEC-011 already said `null`) |
| 2026-09-23 | **The exam profile's budget ceiling is 60.0 USD** (was 15.0) — `AGENTS.md` §6 protects this figure, and this row is the recorded decision | one turn of the orchestrator costs about 1 USD (`novaforge-v2` `ebe008b`); the last 8-chapter novel with a session orchestrator cost 54.87 USD; a ceiling of 15 would stop the example novel near chapter 3 and spend it for nothing | "si", answering Q25: raise the ceiling to 60 |
| 2026-09-23 | **The five evaluation briefs run with 3 chapters each** (profile `eval` = `exam` with `novel.chapters` 3 and the `tiny` word band); the example novel is the full 10 chapters | five full novels would cost about 250 USD and do not fit before Friday; every validator (brief, forbidden words, mandatory facts, judge, chronology) is exercised the same on 3 chapters; stated in `evals/results.md` and in the presentation | "si", answering Q26 |
| 2026-09-23 | **The orchestrator's context is measured against the 100,000-token ceiling, warned and shown, not halted**; a per-stage orchestrator (a fresh Claude Code process per stage and per chapter, state on disk) is the declared next step that would bring it under | the orchestrator is one conversation for the whole novel and accumulates the Bible, drafts, critiques and sheets: measured median 147,000 and peaks of 642,000 tokens; halting at 100,000 would stop every novel within a minute. The ceiling itself is unchanged (AGENTS.md §6); what changes is that the orchestrator's excess stops being invisible | "uso tu recomendación", answering Q27 (option C) |
| 2026-09-23 | **The per-stage conductor stays, the 100,000 ceiling stays, and the gap is declared**; large units are split (outline into writing and audit; cast into characters and timeline/mysteries) | each Claude Code process starts at about 49,000-50,800 tokens before reading anything, whatever its tool list (measured with 15, 5 and 2 tools), so a unit has about 51,000 tokens of work; world fitted (82,686), cast and outline did not (100,669 and 109,722) | the owner chose "bajar el suelo y seguir con el conductor" and "el techo se queda y se declara el hueco" in the build session |
| 2026-09-23 | **Fallback deadline: Thursday 2026-09-24 12:00 Mexico time (18:00 UTC).** If by then the conductor has not produced the 10-chapter example novel, the single-orchestrator path runs it with the 60 USD ceiling (about 2.5 hours), and the conductor is presented as built and measured | the example novel is mandatory; the afternoon is needed for evals, the PDF, the reader-change demo and the deck | "va", answering Q29 |
| 2026-09-24 | **The evaluation briefs run with 1 chapter, not 3** (supersedes the 3-chapter row above); the example novel stays at 10 chapters. The full test suite is no longer re-run after every change, only the tests of the file touched | time before delivery: the suite already passes (740) and three chapters per eval tripled the wait for what one chapter already shows about the gate, the facts and the guardrails | the owner, in chat to the coordinating session: "super si eso me gusta", answering the recommendation to cut the evals to one chapter and stop re-running the suite |
| 2026-09-24 | **The recipient's name is inserted by code at publication, not written by the model.** The orchestrator, under the organisation's data-protection policy, wrote the placeholder `[NOMBRE_ANONIMIZADO]` in place of the brief's recipient alias (Bible, outline, chapters); at publication a script replaces it with the alias read from the brief's JSON, and `canonical_names`, `mandatory_facts` and the PDF run on the substituted text | privacy by design: no model ever holds the recipient's name, and the personalisation is deterministic; relaunching would have lost the spend with no guarantee the model would not anonymise again | the owner, in chat to the coordinating session: "la b", choosing mechanical substitution over relaunching |
| 2026-09-24 | **The buyer chooses the length: any number of chapters from 1 to 10** (default 10), on the `exam` profile. Supersedes SPEC-EXAM-002's "shown, never editable" length field. The count travels as `chapters` in `POST /api/runs` into the run's config snapshot, which every stage reads; the route refuses more chapters than the profile's budget was priced for. Without `chapters` the profile decides, as the eval harness needs | the owner could not try the product without paying for ten chapters, and asked for the number to be his, not a choice between two | the owner, in chat to the coordinating session: "no me deja cambiar la longitud", then "no solo quiero la opcion de entre 10 y 1 quiero yo ponerle cuando quiero" |
