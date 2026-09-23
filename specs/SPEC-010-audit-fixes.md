---
id: SPEC-010
title: What the 2026-09-23 code audit found — four fixes and two corrections to the record
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "apruebo PLAN-010 y ratifico las specs, sigue con todo"; this line written at his instruction
approved_on: 2026-09-23
approval_history: first written `approved` on a standing chat approval; returned to `draft` by novaforge-05 (5a80fda) when the design session pointed at `AGENTS.md` §1 — a state written in a file is a human act; approved again the same afternoon on the owner's explicit sentence above. A hand edit by the owner remains the stronger act and is still welcome.
depends_on: specs/SPEC-007-backend-v1.md, docs/verification.md §3.5, docs/domain-knowledge.md §8.4, docs/architecture.md §6.3
found_by: the session "Novaforge continuación con repositorios", auditing backend/ and frontend/ against the docs; verified by novaforge-05 against the fixture and the events table
---

# SPEC-010 — Audit fixes

Four defects found by reading the code against the documents, each verified
against the repository before being written here, and two places where the
documents said something the data contradicts. `AGENTS.md` §5: a fix gets a
short spec first. This is it. It is deliberately narrow so PLAN-010 can be one
afternoon; everything larger it names goes to SPEC-009 or to `verification.md`.

## 1. What is wanted, and why

**W1 — a finished run's stream ends with the run, not with two words.**
`RunService.follow()` for a run that is not the live one yields
`{"event": "done", "data": {"result": "not live"}}`. The panel's `useRun`
does `setDetail(done.data)` and renders `RunDetail` fields that are not there;
the error boundary catches it. **Opening any finished run in the panel breaks
the Run page.** The `live.done` branch (PLAN-007 6.7) already sends
`{"result": …, **detail}`; the not-live branch must send the same shape with
`result` taken from the record (`complete`, or `halted: <kind>`).

**W2 — the context watcher reads the token figure the stream actually carries.**
`verification.md` §3.5, `domain-knowledge.md` §8.4 and `architecture.md` §6.3
say the subagent packets "read zero" and the one quantity the ceiling is about
is not measurable from the stream. **That is false.** Every `task_progress`
event carries `usage: {total_tokens, tool_uses, duration_ms}` — 13,921 on the
fixture, 7 of 7 on the run `night-translator-rewriting-phrasebook` (10,226 …
25,004). `context_size()` sums `input_tokens + cache_creation + cache_read`,
none of which that event has, and reports 0 → "absent". The datum is there
under another key; the parser ignored it. `context_size` reads `total_tokens`
when the three input fields are absent, the watcher measures real packets, and
`calls` rows carry the figure with provenance `measured` and a note that it is
the subagent's *total* tokens (input and output together), which is what the
CLI reports.

**W3 — two premises with the same first six words do not 500.** `runs.slug`
is `UNIQUE`; `slugify` takes the first six words. The fallback slug gets a
short suffix (`-2`, `-3`, …) when taken; the real slug is still learned from the
stream and overwrites it.

**W4 — the promises check is a property of finished runs.**
`test_promises.py::test_no_existing_run_has_an_incoherent_promise` parametrises
over every `output/*/bible/mysteries.md`; a run that died in FLOW-4 has
promises that land past its last written chapter, which is not a defect of the
run. Runs without `dist/book.md` are skipped with a reason in the test output.
(`check_promises` itself keeps its behaviour: on a live run FLOW-6 is the
moment it is asked.)

**The two corrections to the record** are docs work under this spec (not code):
`verification.md` §3.5 and `domain-knowledge.md` §8.4, `architecture.md` §6.3
rewritten to what the data says once W2 lands, with the history of the wrong
claim kept — three runs were read as "no packet data" because of a key name.

## 2. Out of scope, named

- `BudgetWatcher` prices `input + output` at the worst rate between `result`
  events and so trips in practice only on `result`; `--max-budget-usd` is the
  first line. Consistent with §3.21; not changed here.
- `conformance`, `archive`, `promote` read the gate constants from Python, not
  from the run's snapshot. A run judged after a threshold change would be
  judged by today's rule. Goes to `verification.md` §3 as a declared gap; a fix
  is its own spec.
- `pages/run` imports `pages/quality` (FSD forbids it): SPEC-009 P0.
- Stale "five characteristics / four-critic" wording in `config/*.json`
  comments, `prose.py`, `check_prose.py`, `report.py`, `build_sheet`,
  `Quality.tsx`: `coherencia-docs` Lote A, separate docs commit.

## 3. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | `GET /api/runs/{id}/events` on a finished run ends with a `done` frame whose data has every `RunDetail` key and `result ∈ {complete, halted: <kind>}` (test with `client_for`, and `test_api_contract` against `RunDetail`) | T |
| AC-2 | `context_size({"total_tokens": 13921, …})` is 13,921; the fixture replay reports `packets_measured == 7`-ish (the fixture's count) and `packet_series_provenance == "measured"`; `calls` rows for `task_progress` events carry `input_tokens` = total with `note` saying so | T |
| AC-3 | Two `POST /api/runs` with premises sharing their first six words both return 201 with different slugs | T |
| AC-4 | `test_promises` skips a run directory without `dist/book.md` and says why; the full suite is green with a half-written run present in `output/` | T |
| AC-5 | `verification.md` §3.5 no longer says the stream carries no per-subagent figure; it says what it carries and what that figure is | I |

## 4. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| `total_tokens` is the subagent's whole usage, not the packet handed to it; the ceiling is about the packet | important | it is the only per-subagent figure the CLI emits; an upper bound on the packet, labelled as such | a packet under 100k whose total exceeds it trips the watcher early — the correct direction to be wrong in |
| The gate constants come from Python at judgement time, not from the run's snapshot | important | changing them needs a spec (`AGENTS.md` §6), so drift is deliberate and dated | a run archived after a constant change |
