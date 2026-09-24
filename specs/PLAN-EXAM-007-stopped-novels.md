# PLAN-EXAM-007 — stopped novels: continue them or bin them

status: draft — written by the building agent; the coordinating session asked for it to be built in the same pass. Awaiting the owner's approval in this header.
date: 2026-09-24
implements: SPEC-EXAM-007 (approved 2026-09-24), including its §7 precisions from the build review

Tests first, seen red. $0 throughout: fake processes, tmp dirs, no `claude`.

## Tests (red first)

| AC | test | file |
|---|---|---|
| AC-1 | `test_a_continued_run_launches_with_the_profiles_current_orchestrator` — snapshot `models.orchestrator = null`, profile `tiny` says sonnet; the real `RunProcess` argv carries `--model sonnet`; the snapshot row is unchanged; a `changes` row n=2, kind `continue`, names sonnet | `backend/tests/test_stopped_novels.py` |
| AC-1 | `test_the_original_launch_is_segment_one`, `test_the_hand_made_resume_block_becomes_segment_two` | same |
| AC-2 | `test_a_budget_halt_is_not_continued_without_a_figure` (422 at the route), `test_with_a_figure_the_cli_ceiling_is_that_figure` (`--max-budget-usd 40.0`) | same |
| AC-2 | `test_error_max_budget_usd_ends_as_a_budget_halt` (conductor and single-orchestrator paths) | same |
| AC-2 | `test_other_halts_get_the_profile_ceiling_minus_the_measured_spend`, `test_nothing_left_or_unmeasured_asks_for_a_figure` | same |
| AC-3 | `test_promoted_chapters_are_not_redone` — ch01–ch02 on disk, fake runner, first unit launched is chapter 3, ch01 bytes unchanged | same |
| AC-4 | `test_trash_and_restore_are_byte_identical`, `test_the_library_hides_binned_runs_and_the_bin_lists_them`, `test_restore_refuses_when_the_directory_exists_again`, `test_a_locked_directory_is_a_readable_error`, `test_a_new_run_never_takes_a_binned_slug` | same |
| AC-5 | `test_trash_refuses_a_live_run_and_a_complete_novel`, `test_resume_refuses_a_complete_run_and_a_second_live_one` (reasons in `detail`), `test_stopped_means_units_missing_not_stage` (stage `complete` at 8/10 is continuable) | same |
| AC-5 | `test_the_100k_refusal_is_estimated_and_only_for_the_unit_that_halted` | same |
| AC-6 | `LibraryView.test.tsx`: stopped cards show "Continuar" and "Mover a la papelera", complete/live cards do not; the modal shows why, spent (measured or "not measured", never $0) and the stage; budget halt asks for USD and the button is disabled without it; trash asks one confirmation; the Papelera view lists binned runs and "Restaurar" calls restore with the run id | `frontend/src/pages/library/LibraryView.test.tsx` |
| — | route set pinned: add `/trash`, `/restore` | `backend/tests/test_api_contract.py` |
| — | `test_resuming_a_finished_run_is_refused` now puts every unit on disk: §7.1 defines complete by units, not by stage | `backend/tests/test_conductor.py` |

## Code, in order

1. `backend/commons/db/migrations/019_stopped_novels.sql`: `runs.trashed_at`; a `changes` table. Segments are rows of `changes` kind='continue' (the launch is kind='generate'), shared with SPEC-EXAM-008; no run_segments table (coordinating session, 2026-09-24, under §4's "rows in an existing table"). Its SPEC-008 cost columns stay NULL here.
2. `backend/commons/runner/watch.py`: `State.last_subtype`; `conductor.py`: a unit whose result is `error_max_budget_usd` halts `budget`; `Unit.inputs`, `estimate_packet()` (floor 48,800 + bytes/4); `first_missing()`.
3. `backend/commons/db/repository.py`: segment open/close, trash/restore columns. `backend/runs/repository.py`: list filters `trashed_at`.
4. `backend/runs/service.py`: `standing()` (stopped / complete / live, resume-from, spent across segments); `resume(ceiling_usd)` with the overlay and the ceiling rules; segment 1 on `start`; `trash`, `restore`; `unique_slug` looks in `output/_papelera/`; `cost.json` total across segments.
5. `backend/runs/router.py`, `models.py`: `ResumeRun`, `/trash`, `/restore`, `?trashed=true`; refusals as 409/422 with the reason.
6. Frontend: `shared/api` (`resume`, `trash`, `restore`, `bin`, `Run` fields); `pages/library/LibraryView.tsx` (pure, tested) + `ContinueDialog`; `Library.tsx` keeps the state.

## Docs

`docs/handoff/from-build.md` gets the block; the spec is unchanged except for §7 already folded in. AC-7 (real demo) is out of scope here. Screenshot: `docs/screenshots/007-library.png`.
