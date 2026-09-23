---
id: SPEC-009
title: frontend v2 — the panel v1 had, on the API v2 has, with a design
status: draft
created: 2026-09-23
approved: —
depends_on: docs/architecture.md §2.3 (FSD), D27–D29, SPEC-007 (backend v1), the v1 panel (`web/` in the claude-orchestrator branch of the old repo)
---

# SPEC-009 — frontend v2

## What is wanted

**The frontend v1 had, rebuilt on v2's API and FSD structure, with a designed
visual identity, in two tiers: P0 ships in 48 hours, P1 is what the exam adds.**

v1's `web/` had eight screens and the logic that made the project legible:
Library, NewNovel, Configurator, Run, Quality (with *why this chapter was
repeated* and the critic-disagreement panel), Manuscript, Diagram (the pipeline
coloured by live state), Presentation (replay of a recorded run), plus
`ContextChart` (prompt size per chapter), `Provenance` on every figure, and 53
logic checks. v2's `frontend/` has four pages (Library, NewNovel, Run, Quality
without the *why*), the provenance logic ported, and a 2.8 KB stylesheet.
**Six of the eight screens' worth of function is missing, and there is no
design.** This spec restores the function and adds the design.

### P0 — 48 hours, in this order

1. **A design system before any component** — `frontend/DESIGN.md`, produced
   with the `frontend-design` skill: 4–6 named colours, two typefaces and their
   roles, a type scale, spacing, the layout concept as ASCII, and the principles.
   Reviewed against the brief for template tells (§3 of the skill) **before**
   code. Every component reads tokens from it; no literal colours or fonts in
   components.
2. **Manuscript** — read a novel: chapter index, one chapter at a time, the
   Bible sections, synopsis, the assembled book. Markdown rendered; nothing
   parsed from it.
3. **Quality, complete** — the gate table (chapter × attempt × six
   characteristics, the `min` highlighted, threshold 8 marked, reproducible vs
   model critics distinguished); **why this chapter was repeated** (per rejected
   attempt: the headline, each finding with its literal quote, what failed,
   against what, how it should read; what changed; the next attempt's scores);
   the **critic-disagreement / overruled-finding** panel; what a 10 checked
   (`notes`); rejected drafts side by side where the archive has them.
4. **Diagram** — the six stages from `flow.yaml` (never hard-coded) with the
   orchestrator as an explicit lane, coloured by the selected run's state,
   nodes linking into Quality/Manuscript.
5. **Run, complete** — the live SSE view v2 has, plus the agent cards (name,
   stage, model, `tools:` badge with the `chapter-writer: Glob` explanation),
   critics shown in parallel, tokens per agent where `measured`, `absent` where
   the stream gives none (§3.5), and the **orchestrator's own lane** (gate
   decisions, arbitrations, assembly — every event without an `agent`).
6. **NewNovel, complete** — simple mode (premise, chapters, lines per chapter)
   and advanced mode (the config's `novel`, `bible`, `quality_gate`, `budget`
   blocks in base → profile → yours columns); cross-validation of feasibility;
   projected calls and cost **as three figures**; the premise passed as an
   argument, not a config field. Starts the run via `POST /api/runs`.
7. **Presentation** — replay a finished run from its `events` at chosen speed,
   through the same Run view. Zero cost; the demo mode.
8. **ContextChart** — prompt size per chapter, drawn flat when measured and
   drawn as `absent` when the stream reports nothing, with the sentence that
   says why.

### P1 — the exam's reader (not in 48 hours)

- Cover with a personalised dedication.
- Character and place sheet generated from the Bible, each entry linking to
  the chapter where it first appears.
- Reader change: select a fact → the chapters that use it → regenerate →
  new version → diff marks; previous version kept.
- PDF export of the same HTML.

P1 is listed so P0's structure leaves room for it (a `version` on every
manuscript read; entities for `fact` and `character`), not so it gets built now.

## Why

- **The panel is what gets shown.** The backend is sound and documented; a
  demo is a screen. Six functions v1 could show, v2 cannot.
- **The design was a decision (D27) and was skipped.** Phase 4 of the brief
  said *token plan before code*; the plan went straight to code. The skill
  exists for exactly this and is installed.
- **The exam's reader is this panel plus three pages.** Building P0 on FSD with
  `version` in the data model makes P1 an addition, not a rewrite.

## Backend surface this spec requires

SPEC-007 retired file-by-path reads: *the archive answers*. The archive
answers over HTTP through endpoints that do not yet exist. This spec requires
them, read-only, archive-backed, every number with `source`:

| endpoint | returns |
|---|---|
| `GET /api/runs/{id}/chapters` | list: n, title, words, attempts, promoted attempt, status |
| `GET /api/runs/{id}/chapters/{n}` | promoted text + every archived attempt's text where present |
| `GET /api/runs/{id}/chapters/{n}/gate` | scores per attempt, aggregate, verdict, findings (with `upheld`, `ruling`, `late`), sheets |
| `GET /api/runs/{id}/bible` | world, characters, timeline, mysteries |
| `GET /api/runs/{id}/outline` | outline entries with numbered beats |
| `GET /api/runs/{id}/book` | `dist/book.md`, synopsis |
| `GET /api/runs/{id}/cost` | measured cost, or `absent`; imported runs: low/estimate/high |
| `GET /api/runs/{id}/calls` | one row per subagent call: agent, stage, chapter, attempt, tokens or `absent`, ts, provenance |
| `GET /api/runs/{id}/replay` | the persisted `events` in order, for Presentation |
| `GET /api/flow` | `specs/flow.yaml` as JSON |
| `GET /api/agents` | the ten agents' front matter: name, stage, model, tools |
| `GET /api/profiles` | base config + profiles, for NewNovel |

Paths never leave the archive's own records; nothing reads a client-supplied
path (the retirement in SPEC-007 stands). **Where the text lives on disk**
(`/chapters/{n}`, `/bible`, `/outline`, `/book`), the backend resolves
`output/<slug>/` from `runs.slug` in the database for the given `run_id` —
never from anything the client sends — and the pin
`test_no_route_takes_a_path_and_reads_a_file` widens to "no route accepts a
file-path parameter" and keeps its name (Q2). No text is migrated into SQLite.
`/replay` for a run imported from v1 answers *not available: this run predates
the events table* (Q9). The twelve endpoints are phase 1 of PLAN-009, tests
first (Q3). This is a short spec of its own if the
team prefers; it is listed here because P0 cannot ship without it.

## Decisions from the grill, 2026-09-23

Thirteen questions, asked by the design session against `frontend/src` and v1's
`web/src`; the owner accepted every recommendation ("yo acepto tus
sugerencias"). Each is cited where it changed the spec.

| q | decision |
|---|---|
| Q1 | the owner writes the approval header by hand; no dictated approval for this spec unless he says so explicitly |
| Q2 | texts are read from `output/<slug>/`, the directory resolved from `runs.slug` by `run_id`; never a client path; the route pin widens and keeps its name; no migration of texts into SQLite |
| Q3 | the twelve endpoints are phase 1 of PLAN-009, tests first; no separate spec (SPEC-010 is taken) |
| Q4 | if 48 hours do not suffice, cut from the end of the P0 order; the 48 hours count from PLAN-009's approval |
| Q5 | zero new frontend dependencies (see Rules) |
| Q6 | screens are tested with `renderToStaticMarkup`, no jsdom (AC-3…AC-9); AC-11 becomes I plus a text-level CSS test |
| Q7 | one design identity, named now, serving the panel and the exam deck — **slot pending: the owner has not given the name** |
| Q8 | the UI is in English |
| Q9 | replay of a v1-imported run is *not available*; synthesising it from `agents.jsonl` would be P1 and `reconstructed` |
| Q10 | cost projection from the four measured v2 runs (lighthouse 18.82 · cartographer-inconstant 54.87 · night-translator 16.25 · cartographer-valley 20.15): min, median, max per chapter × chapters, `estimated`, with the sentence that a long run amortises the fixed cost |
| Q11 | `version: 1` constant; `entities/fact` and `entities/character` exist, empty |
| Q12 | the orphaned `output/salvage-crew-…` was moved out of the repo as evidence of a dead run; the promises test skips unfinished runs — SPEC-010 W4 |
| Q13 | the Run page breaking on a finished run is fixed under SPEC-010 W1 / PLAN-010, tests first |

## Out of scope

Authentication; multiple concurrent runs; editing prose in the browser;
starting anything other than `POST /api/runs`; a second implementation of any
pipeline logic (derivations only — `min`, cost bounds, feasibility arithmetic —
all with tests); P1 unless P0 is accepted.

## Rules

- **Only the API.** No file reads from the browser. The v1 dev-server plugins
  are not brought back.
- **Zero new dependencies** (Q5): the Markdown renderer is v1's
  `web/src/data/markdown.ts`, ported (it escapes everything); charts are inline
  SVG; the diagram is CSS; navigation is state.
- **The interface is in English** (Q8); the repository's language.
- **Every number carries `source`** and renders through the `Provenance`
  component: `measured ● · reported ◐ · reconstructed ◌ · estimated ≈ · absent —`.
  Absent is a word, never a zero.
- **Structure from data**: stages from `/api/flow`, agents from `/api/agents`,
  critic columns from the gate data (six today; the table adapts if a run has
  five).
- **Quotes are literal.** The *why repeated* view shows findings' quotes and
  fixes exactly as archived, untranslated, unparaphrased.
- **Tone**: a rewrite is the system working, never "failed"; copy in the
  interface's voice; errors say what happened and what to do.
- **FSD** as D28/D29: `pages/` {library, new-novel, run, quality, manuscript,
  diagram}; `features/` {start-run, watch-progress, configure-novel,
  compare-runs, replay-run}; `entities/` {run, chapter, critique, agent,
  provenance}; `shared/` {api, ui, lib}. Imports only downward.
- **Accessible floor**: keyboard focus visible, reduced motion respected,
  colour never the only signal, phone width works.

## Acceptance criteria

| id | criterion | tier | letter |
|---|---|---|---|
| AC-1 | `frontend/DESIGN.md` exists, produced with `frontend-design`, with the 4–6 colours, two typefaces, scale, layout and principles; the review-against-tells paragraph is present | P0 | **I** |
| AC-2 | No component contains a literal colour or font; all read tokens (lint rule or grep in CI) | P0 | **T** |
| AC-3 | Manuscript renders every chapter, Bible section, synopsis and book of the fixture run from the API | P0 | **T** (render test) |
| AC-4 | Quality shows the gate table with `min` highlighted and reproducible/model critics distinguished for every archived run | P0 | **T** |
| AC-5 | For `deep-space-salvage-derelict` ch02 attempt 1, the *why repeated* view shows three findings with their literal quotes and the repair text; ch03 shows one upheld and one overruled with the ruling | P0 | **T** |
| AC-6 | Diagram's stages come from `/api/flow`; changing the YAML changes the diagram with no frontend change | P0 | **T** |
| AC-7 | Run shows every event without an `agent` in the orchestrator's lane; none dropped | P0 | **T** |
| AC-8 | Tokens render `absent` (not 0) for calls whose stream had no usage; the fixture has such rows | P0 | **T** |
| AC-9 | NewNovel rejects an infeasible configuration before enabling Start, and shows cost as three figures — minimum, median and maximum per chapter over the **four measured v2 runs**, scaled by chapter count, every one labelled `estimated` (Q10) | P0 | **T** |
| AC-10 | Presentation replays a finished run from `/replay` at 1×/4×/16× through the Run view | P0 | **D** |
| AC-11 | Every P0 page renders at 375 px width without horizontal scroll; focus visible; `prefers-reduced-motion` honoured | P0 | **I** (the built-in browser) + **T** for the CSS rules by text (Q6) |
| AC-12 | `tsc --noEmit`, `vitest`, `vite build` green in CI | P0 | **T** |
| AC-13 | Manuscript reads carry `version: 1` (a constant; no migration until P1) and `entities/fact`, `entities/character` exist, empty (Q11) | P0 | **A** |
| AC-14 | Cover, character sheet, reader change, PDF | P1 | — |

## Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| The ContextChart cannot draw the thesis because the stream carries no per-subagent tokens (§3.5) | important | not a frontend problem; the chart shows `absent` and says why | the chart stays empty until the stream changes |
| Design quality is Inspection, not Test | accessory | taste is not testable; the tells checklist is | AC-1 review |
| Presentation replays the persisted events, not the wall clock | accessory | events have `seq`; derived `ts` are labelled | replay speed is nominal |
| P1 features unbuilt | important | 48-hour scope | the exam rubric |

## How this spec is executed

Per `AGENTS.md`: grill (the repository answers first — read `frontend/src` and
the v1 `web/src` for what exists), approve in the header, `PLAN-009` with tests
first, P0 in the order above, one commit per page.
