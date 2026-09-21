---
id: PLAN-001
spec: SPEC-001
status: draft
created: 2026-09-21
approved: null
---

# PLAN-001 — implementing `commons`

Implements SPEC-001. Tests first, then code, then docs.

## 1. Tests, written and seen failing first

| test | covers |
|---|---|
| `test_context.py::test_writer_packet_has_no_prose_field` | A1 |
| `test_context.py::test_builder_rejects_prose` | A1 |
| `test_semaphore.py::test_five_critics_never_exceed_capacity` | A2 |
| `test_semaphore.py::test_oversized_reservation_raises` | A3 |
| `test_semaphore.py::test_waiting_is_not_failure` | A2 |
| `test_tokens.py::test_counting_is_deterministic` | A4 |
| `test_mock.py::test_plan_drives_named_failures` | A5 |
| `test_mock.py::test_can_emit_out_of_band_and_headingless` | A5 |
| `test_db.py::test_migrations_run_once_and_in_order` | A6 |
| `test_budget.py::test_halts_before_the_call_that_would_exceed` | A7 |
| `test_log.py::test_row_carries_every_field` | A8 |
| `test_import.py::test_all_eight_runs_import` | A9 |
| `test_import.py::test_completeness_records_what_was_missing` | A9 |
| `test_import.py::test_imported_runs_excluded_from_statistics` | A10 |

## 2. Code, in dependency order

1. `commons/config/` — load `flow.yaml`, base config, profile overlay.
2. `commons/db/` — connection with the four pragmas, `migrate()`, migrations
   `001`–`004`.
3. `commons/context/tokens.py` — the counter (deterministic for the mock).
4. `commons/context/semaphore.py` — acquire / wait / release, with the log fields.
5. `commons/context/packets.py` — one frozen dataclass per agent. The writer's is
   written first, because A1 is the guarantee this module exists for.
6. `commons/llm/engine.py` — the `Engine` protocol, `MockEngine` with its plan,
   `AnthropicEngine` behind the flag.
7. `commons/budget/` — worst-case projection and the ceiling.
8. `commons/log/` — the call row.
9. `commons/db/import_v1.py` — the importer and its completeness record.

## 3. Docs

- `docs/verification.md`: mark G1, G2, G13, G14 as evidenced rather than
  *(planned)* once their tests are green.
- `docs/architecture.md` §6.4: replace the estimated reservation table with
  measured figures **only after Phase 3**, not from mock runs.
- `docs/domain-knowledge.md`: anything the importer discovers about the eight
  runs that is not already recorded.

## 4. Order of work

`config` → `db` → `tokens` → `semaphore` → `packets` → `llm` → `budget` → `log`
→ `import`. Each with its tests green before the next begins.
