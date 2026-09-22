# PLAN-003 — Archiving a finished run

status: approved
date: 2026-09-22
implements: SPEC-003-archive (approved 2026-09-22)

## 1. The tests, first

`backend/tests/test_archive.py`, against the real
`output/lighthouse-keeper-ledger/` directory — v2's first run, and the only one
that has ever carried five characteristics. Costs $0: it reads files.

| test | criterion |
|---|---|
| `test_every_attempt_on_disk_becomes_a_row` | A1 |
| `test_each_attempt_carries_five_scores` | A2 |
| `test_an_unusable_verdict_stores_null_not_zero` | A2 |
| `test_exactly_one_attempt_per_chapter_is_promoted` | A3 |
| `test_the_promoted_attempt_is_the_one_that_passed` | A3 |
| `test_a_gate_row_per_attempt_with_a_verdict_the_schema_admits` | A4 |
| `test_every_sheet_on_disk_becomes_a_row` | A5 |
| `test_an_overruled_finding_is_stored_as_overruled` | A6 |
| `test_the_measured_cost_is_stored_and_preferred_over_the_sum` | A7 |
| `test_archiving_twice_does_not_duplicate` | A8 |
| `test_a_halted_run_archives_what_exists` | A9 |

## 2. The code

1. **Migration `005_run_cost.sql`** — `runs.cost_usd REAL`,
   `runs.cost_provenance TEXT CHECK (...)`, `runs.turns INTEGER`,
   `runs.duration_ms INTEGER`. Nullable, because a run that produced no `result`
   has no cost and must not read as $0.
2. **`backend/runs/archive.py`** — `archive_run(conn, run_id, run_dir, sheets_dir)`.
   Reads `critiques/chNN.<critic>.json`, `chapters/`, `cost.json` and the sheets
   directory; writes through the existing `repository.save_*` functions, which
   exist and have never been called.
3. **`repository.save_cost`** — the measured figure onto the run.
4. **`runs/repository.cost`** — prefer the run's measured total; fall back to the
   sum over `calls`, and **say which** in the payload's provenance.
5. **`runs/service.py`** — archive on completion and on halt, inside the same
   transaction that sets the final stage.

## 3. Docs

- `verification.md`: G13 gains the stored figure; §3 gains the two gaps SPEC-003
  leaves; §5 gains the archiver's row.
- `domain-knowledge.md`: the finding — a complete run with an empty archive.
- `AGENTS.md`: nothing.
