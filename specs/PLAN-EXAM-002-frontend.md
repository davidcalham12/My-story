# PLAN-EXAM-002 — the storyMaker frontend, technically

status: draft
date: 2026-09-23
implements: SPEC-EXAM-002 (approved 2026-09-23)
approved_by: —
executes: novaforge-05 · reviews: the coordinating session · decides: the owner

SPEC-EXAM-002 describes the frontend in plain language and, by the owner's
instruction, contains no code. This plan holds everything technical that the
spec deliberately leaves out: priorities mapped to modules, rules, the screens
as components and calls, the backend surface, and the tests. It was Part B of
the spec's first draft, moved here unchanged except for this header.

## The technical plan

### B.1 Priorities, given the Friday deadline

| tier | screens | why |
|---|---|---|
| **P0 — today** | 2 Interview · 5 Ask for a change · 4 Read · 1 Library (existing, adapted) | these are the exam's configuration and reader-change requirements and the live demo |
| **P1 — Thursday** | 6 Quality (existing Quality page extended with judge + validators + evals table) · 3 Writing (existing Run page, relabelled stages) | evidence for the presentation; mostly reuse |
| **P2 — if time** | a design pass with the Qaracter tokens on every screen; ContextChart | presentation polish |

### B.2 Rules (inherited from SPEC-009, decisions of 2026-09-23)

- **Only the API.** The browser reads nothing from disk; the PDF is served by the backend from the archive, resolved by `run_id`, never by a client path.
- **Zero new dependencies.** React + Vite + TypeScript as today. The PDF is shown with the browser's own viewer (`<iframe src=…/pdf>` / `<object>`); no PDF library. Charts are inline SVG. Navigation is state, as today.
- **Feature-Sliced Design**, imports downward only: `pages/` {library, interview, run, read, change, quality}; `features/` {submit-brief, watch-progress, request-change}; `entities/` {run, brief, fact, version, critique, provenance}; `shared/` {api, ui, lib}. The existing `pages/run → pages/quality` import is fixed by moving the gate table to `entities/critique` (SPEC-010 §2).
- **Every number through `Provenance`** (`measured ● · reported ◐ · reconstructed ◌ · estimated ≈ · absent —`).
- **Tokens, not literals.** Colours and fonts come from `frontend/src/shared/ui/tokens.css`, generated from the Qaracter design FRM tokens (`ui_kits/deck-ndod/tokens.json`); a test greps components for hex colours and font names.
- **Language.** The interface is in English (repository rule, SPEC-009 Q8); the buyer's own words (memories, dedication) are shown as typed.
- **Accessible floor.** Visible keyboard focus, `prefers-reduced-motion` honoured, colour never the only signal, 375 px width works.

### B.3 Screens in detail

**1 Library** — `GET /api/runs` (exists) plus `recipient_alias`, `occasion`, `current_version` from the brief and versions tables. A card per novel: alias, occasion, status (`writing · complete · halted: <why>`), version *n*, cost with provenance. Actions: *Read*, *Quality*, *New novel*. Empty state invites the first order.

**2 Interview** — a form in four groups (recipient · memories · story · limits) that mirrors the `Brief` model exactly: `occasion`, `recipient{alias, age, pronouns, traits[], relationship_to_buyer}`, `memories[{text, date?}]`, `genre`, `tone`, `length_chapters` (fixed at 10, shown, not editable), `forbidden_terms[]`, `mandatory_facts[]`, `dedication`, `free_text`.
- On every blur, `POST /api/briefs/check` returns `{status: complete | incomplete | contradiction, questions[], contradictions[]}`; questions render under their field, contradictions as an orange callout naming both fields.
- `free_text` has a visible label: *treated as material, never as instructions*.
- *Load an example* fills the form from `evals/briefs/01-hijo.json` (served by `GET /api/briefs/examples`).
- *Write it* (`POST /api/briefs` then `POST /api/runs {brief_id}`) is enabled only on `complete`; the projected cost is shown as three figures (min · median · max from measured Haiku runs, `estimated`).

**3 Writing** — the existing Run page: SSE `snapshot → progress → done`, the orchestrator lane, halt button (`POST /api/runs/{id}/halt`). Stage names shown as the buyer's words: *World · Characters · Outline · Chapters · Polish · Book*, with the FLOW id small beside each.

**4 Read** — `GET /api/runs/{id}/versions` → the version picker; `GET /api/runs/{id}/versions/{n}/pdf` in the viewer; beside it the index (`GET …/chapters`) and the character/place sheet (`GET …/bible/characters`, `…/places`), each entry linking to `pdf#chapter-N`. A banner on version > 1: *chapters 3, 5 and 7 changed in this version* with links.

**5 Ask for a change** — `GET /api/runs/{id}/facts` lists facts (text, kind, source, chapters that use it). The person picks one, types the new value, and the page shows `GET …/facts/{fid}/impact` → chapters to rewrite. *Request change* → `POST /api/runs/{id}/changes {fact_id, new_text}` → `202 {version: n+1}`; the page follows the regeneration through the Writing view and returns to Read on the new version. If the regeneration halts at the gate, the page says so and keeps the previous version as current.

**6 Quality** — the existing gate table and "why repeated" (SPEC-009 P0), plus: the judge rubric per version (six criteria, score + justification, `GET …/versions/{n}/judge`), the validators table (name, where it runs, result, Langfuse score id, `GET …/versions/{n}/validations`), and, on an evaluation run, a link to the evals table (`GET /api/evals`).

### B.4 Backend surface this frontend needs

| endpoint | returns | built in |
|---|---|---|
| `POST /api/briefs/check` | status, questions, contradictions | PLAN-001-exam E2 |
| `POST /api/briefs` / `GET /api/briefs/examples` | brief id / the five example briefs | E2 |
| `POST /api/runs {brief_id}` | run id (existing route, new body field) | E2 |
| `GET /api/runs/{id}/facts`, `…/facts/{fid}/impact` | facts with usage / chapters affected | E3 |
| `GET /api/runs/{id}/versions`, `…/versions/{n}/pdf` | versions / the PDF bytes | E6 |
| `POST /api/runs/{id}/changes` | new version number | E6 |
| `GET /api/runs/{id}/chapters`, `…/bible/characters`, `…/places` | index and sheet | E3 / E6 |
| `GET /api/runs/{id}/versions/{n}/judge`, `…/validations` | rubric / validators | E5 |
| `GET /api/evals` | the brief × validator table | E7 |

The route pin (`test_no_route_takes_a_path_and_reads_a_file`) widens to this list; no route takes a filesystem path.

### B.5 Acceptance criteria

| id | criterion | tier | letter |
|---|---|---|---|
| AC-1 | the interview renders every `Brief` field and nothing else (a test compares the form's field names with the model's JSON schema) | P0 | T |
| AC-2 | brief 03 shows the missing-data questions and the age/genre contradiction and keeps *Write it* disabled; brief 01 enables it | P0 | T (render with mocked API) + D |
| AC-3 | brief 04's free text appears labelled *untrusted* and is never shown inside an instruction field | P0 | T |
| AC-4 | Read shows the PDF of the chosen version, a working index, and a character sheet whose links point at `#chapter-N` anchors present in the HTML the PDF is printed from | P0 | T + D |
| AC-5 | Ask for a change shows the impacted chapters before submission, and after it Read opens on version n+1 with the changed chapters listed; version n remains selectable | P0 | D (the demo) + T (impact list rendering) |
| AC-6 | Library lists every run with alias, occasion, status, version and cost with provenance; zero runs shows the empty state | P0 | T |
| AC-7 | Quality shows the judge's six criteria with justifications and the validators table for a version | P1 | T |
| AC-8 | no component contains a hex colour or a font name outside `tokens.css` | P1 | T |
| AC-9 | every P0 screen works at 375 px with visible focus | P1 | I (built-in browser) |
| AC-10 | `tsc --noEmit`, `vitest`, `vite build` green | all | T |

### B.6 Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| the change is picked from a fact list, not by selecting text in the PDF | incidental | the exam allows a form for the PDF route; text selection inside a PDF needs a PDF library | a reader asking to click the text |
| the projected cost rests on few Haiku runs | important | only today's runs exist; shown as `estimated` with three figures | the evals' measured costs diverging |
| design quality is Inspection | incidental | taste is not testable; the tokens rule is | AC-9 review |
| one novel at a time | incidental | the backend's queue of one | a 409 on a second order |
