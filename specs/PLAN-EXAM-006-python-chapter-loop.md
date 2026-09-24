# PLAN-EXAM-006 — the chapter loop in Python

status: draft for review
date: 2026-09-24
implements: SPEC-EXAM-006 (approved 2026-09-24, "apruebo el SPEC-EXAM-006, techo 3 USD para la prueba")
scope: AC-1 to AC-5d at $0. AC-6 and AC-7 (the real spike) are out of this plan: they are run later, by someone else, with the owner's go.

Tests first, seen red, then code. No real `claude` process and no network in any
test: every agent is a fake process returned by an injected runner.

## 1. Tests — `backend/tests/test_chapter_loop.py`

A fixture run directory (four Bible files, an outline with three chapters, a
`config.snapshot.json`, `ch01.summary.md`, and `ch01.md`/`ch01.attempt1.md`
carrying a SENTINEL string), a migrated in-memory db with a `runs` row, and a
fake runner that answers per agent name from a script of canned replies.

| AC | test(s) |
|---|---|
| AC-1 | the whole suite, run unchanged with the default `"claude"`; plus `test_the_switch_defaults_to_claude` (config) and `test_the_conductor_path_is_unchanged_by_default` |
| AC-2 | `test_accept_first_attempt_promotes_and_summarises`, `test_retry_then_accept_writes_a_valid_sheet`, `test_third_attempt_patch_then_accept_is_patched`, `test_patch_that_still_fails_halts_without_summary`, `test_chatter_zero_skips_the_critics`; each asserts the loop's action equals `decide` on the same scores, and that `promote` accepted the same draft |
| AC-3 | `test_no_packet_carries_another_chapters_prose` (sentinel in ch01.md / ch01.attempt1.md; every packet of every agent checked, including redraft and summary packets) |
| AC-4 | `test_packet_over_the_ceiling_is_not_dispatched` (Bible inflated past 100,000 estimated tokens: runner never called, halt names the figure) |
| AC-5 | `test_every_call_row_has_four_figures_and_measured_cost` |
| AC-5b | `test_parallel_critics_share_the_remaining_budget` (sum of handed-out `--max-budget-usd` ≤ ceiling − spent, per round); `test_no_budget_left_halts_before_dispatch` |
| AC-5c | `test_an_exception_kills_every_sibling` and `test_a_halt_kills_every_sibling` (slow fake critics that block until stopped; none alive afterwards) |
| AC-5d | `test_single_and_python_is_refused_at_start` (service raises with the sentence; no run row, no thread) |
| wiring | `test_conductor_hands_chapter_units_to_the_loop`, `test_change_dispatch_uses_the_loop_when_switched` |

## 2. Code

1. `backend/chapters/loop.py` — the loop (service layer). Imports
   `chapters.domain`, `chapters.names`, `chapters.prose`, `chapters.promote`,
   `chapters.check_summary`, `policy.forbidden`, `commons.runner`,
   `commons.log.calls`. Pieces: packet builders (writer, critic, summary),
   `measure` (words × 1.35, SKILL.md §7's estimate), `real_runner`
   (`claude -p --agent <name> … --max-budget-usd`, packet on stdin via
   `RunProcess`), `_dispatch_all` (threads, one share of the remaining budget
   each, every sibling stopped in `finally`), critique envelopes in the shape of
   `critiques/chNN.<c>.json`, `build_sheet`/`validate_sheet`, `apply_patches`,
   `promote.main` and `check_summary.main` called through their `main(argv)`.
   `main(argv)`: `python -m backend.chapters.loop <run_dir> <n> [--change <fact_id>]`.
2. `config/novel.config.json` — `orchestration: {"chapter_loop": "claude",
   "bible_critic": false}`. Profiles untouched.
3. `backend/runs/conductor.py` — `Conductor.chapter_loop` (injected callable);
   used for chapter units only when `cfg.orchestration.chapter_loop == "python"`.
   `refusal(cfg, single)` returns the sentence for `single` + `python`.
4. `backend/runs/service.py` — `start`/`resume` refuse with that sentence;
   `_conduct` passes the loop when switched.
5. `backend/versions/change.py` — in `dispatch`, when the run's snapshot says
   `python`, each chapter goes through the loop on the workspace instead of a unit
   process; nothing else changes.

## 3. Docs and spec (after the code, before approval of the result)

`docs/architecture.md` §8 (the rule change), `docs/verification.md` §3 (the
spec's §7 gaps). Not done in this change: listed for the reviewer.
