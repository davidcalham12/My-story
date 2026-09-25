---
id: PLAN-EXAM-008
spec: SPEC-EXAM-008 (approved 2026-09-24, "apruebo el SPEC-EXAM-008")
status: draft — written and built in one pass at the coordinating session's request, as PLAN-EXAM-007 was; needs the owner's approval in this header
date: 2026-09-24
---

# PLAN-EXAM-008 — the cost of every change

## 1. Tests first (each seen red before its code)

| AC | test | file |
|---|---|---|
| AC-1 | a `result` with `modelUsage` splits by role (main model = orchestrator) and the parts sum to `total_cost_usd`; minutes = Σ `duration_ms` | `test_change_costs.py::test_split_*`, `::test_the_service_writes_each_result_as_it_arrives` |
| AC-1 | the python loop's processes are agents: `orchestrator_model` NULL with the note "no orchestrator (python loop)" | `test_change_costs.py::test_the_loop_*` |
| AC-1 | `change.py` opens a `reader_change` row, `--workspace/--only` a `redo` row on the same version; each chapter process's `result` adds to it | `test_change_costs.py::test_a_reader_change_*`, `::test_a_redo_*` |
| AC-2 | a process with no `result`: figures NULL (never 0), note "incomplete: N processes without a result" | `test_change_costs.py::test_*_without_a_result_*` |
| AC-3 | the export: one trace per change with two generations carrying measured `cost_details`; no per-call `cost_details`; the estimate in metadata `estimated_cost_usd` | `test_langfuse_export.py::test_*change*`, `::test_a_call_ships_its_four_usage_figures_and_its_estimate_in_metadata` |
| AC-4 | `/costs` from a fake Langfuse; Langfuse down → local rows "unconfirmed in Langfuse"; disagreement → both figures; credentials never in the body | `test_costs_api.py` |
| AC-5 | the backfill gives 53.17 (Opus 48.79 / Haiku 4.38) and, from the real `logs/resume.stream.jsonl`, 21.03 (Opus 19.34 / Haiku 1.69); v3, `_aborted-change-*`, `_redo-*` in tmp fixtures | `test_backfill_changes.py` |
| AC-6 | Costs section rows, total, "absent" never "$0", source ✓/local; card total with provenance | `CostsSection.test.tsx`, `LibraryView.test.tsx` (one case) |
| AC-7 | D, after merge — not in this plan's tests | — |

## 2. Code, in order

1. `backend/commons/db/migrations/020_change_costs.sql` — `changes` gains `results`, `unresulted`, `sources` (JSON). Still one table (§8.1).
2. `backend/costs/measure.py` — pure: `split(result, main_model)`, `Meter` (the main model from `system/init`, else `--model`, else the first top-level assistant message; counts processes and results).
3. `backend/costs/repository.py` — `open_change`, `add_result`, `add_missing`, `add_note`, `finish`, `rows`, `card_total`. `commons/db/repository.close_change` stops overwriting `minutes` and a measured total.
4. Wiring (additive): `runs/service.py` (`Live.meter`; `_record` folds each event; `_finish` counts the processes left without a result; the loop gets `change=`), `chapters/loop.py` (`change=`; each `Reply` keeps its `result`), `versions/change.py` (`main` opens the row, passes `change=` to `regenerate`; `dispatch` records per chapter; `_set_aside` also keeps the chapter's old stream so a redo no longer overwrites the evidence).
5. `backend/costs/backfill.py` — `python -m backend.costs.backfill output/<slug> [--dry-run]`: events (first run), `logs/resume.stream.jsonl`, `dist/vN/logs`, `dist/_aborted-change-*/logs`, streams set aside in `_redo-*`. Idempotent (matched by kind and sources).
6. `tools/export_to_langfuse.py` — change traces (`trace_id(run|change n)`, tags kind/version/chapters, metadata provenance + sources), generations `orchestrator` and `agents`; per-call estimate to metadata.
7. `backend/costs/langfuse_read.py` + `router.py` — `GET /api/runs/{id}/costs`: `observations.get_many(session_id=slug, type=GENERATION)`, 4 s timeout, 60 s cache; merge with local; `trace_url` from the observation's project id.
8. `backend/runs/service.py::list/get` add `cost_total` (local, all kinds, with provenance) for the card.
9. Frontend: `entities/cost` (types, `lib.ts`), `pages/run/CostsSection.tsx` on the novel page, one line on the Library card.

## 3. Docs and spec

- `docs/verification.md`: AC-1..6 rows (T), AC-7 (D); gap: a stream overwritten before this change (v3 ch03 first pass, 4.24 USD) is absent to the backfill.
- `docs/architecture.md`: `backend/costs/`. `docs/definitions.md`: *change*.
- The spec is not changed; conflicts found are reported to the coordinating session.

## 4. What is measured and what is not

`total_usd`, `minutes` (Σ `result.duration_ms`, measured by Claude Code, not a wall clock), `orchestrator_usd`, `agents_usd` are `modelUsage` figures: measured. A process with no `result` contributes nothing and is counted in `unresulted`: absent, never 0.
