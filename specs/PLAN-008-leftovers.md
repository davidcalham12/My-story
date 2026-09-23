# PLAN-008 — Two leftovers

status: approved
date: 2026-09-23
implements: SPEC-008-leftovers (approved 2026-09-23, standing approval)
approved_by: David Calderon (standing approval given in chat, 2026-09-22; written by the building session)

## 1. The tests, first

| test | criterion |
|---|---|
| `test_import.py::test_a_fresh_database_import_skips_v2_runs_by_their_marker` | AC-1 |
| `test_import.py::test_the_named_v1_runs_import` (exists) | AC-2 |
| `test_archive.py::test_the_prose_check_file_is_known_and_not_warned_about` | AC-3 |
| `test_archive.py::test_a_genuinely_unknown_critique_file_is_still_noted` | AC-4 |

## 2. The code

1. `import_v1.import_all_with_skipped`: when `slugs is None`, skip any directory
   with `conformance.json` and return the skipped names beside the reports;
   `import_all` keeps its signature over it; the CLI prints the skipped names.
2. `runs/archive.py`: `prose_check` is a known companion file; it is skipped
   silently, with one note per run naming how many were seen.

## 3. Docs

- `verification.md` §3.20 → closed, with the test named; history row 4.
- `domain-knowledge.md` §8.6 → the fix and its spec.
- SPEC-007 §12: no row changes (the gaps were verification.md's, not the spec's).

Effort: 1 h, *estimated*.
