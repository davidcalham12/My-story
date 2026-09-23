# PLAN-010 — Audit fixes

status: approved
date: 2026-09-23
implements: SPEC-010-audit-fixes (approved 2026-09-23, commit `3b8e818`)
approved_by: David Calderon, in chat to the session "Novaforge continuación con repositorios", 2026-09-23 — "apruebo PLAN-010 y ratifico las specs, sigue con todo"; written at his instruction
approved_on: 2026-09-23
written_by: the session "Novaforge continuación con repositorios", which found the four defects

Four small phases, one commit each, tests seen red before the code that makes
them green (`AGENTS.md` §5). Nothing here touches the gate's constants, any
agent's `tools:` line, the ceiling or the budget (`AGENTS.md` §6). The two
corrections to the record (SPEC-010 §1, last paragraph) are docs work owned by
`novaforge-05` and are scheduled after phase 2 lands, not before.

## Part 1 — Reference

| what | where |
|---|---|
| the spec | `specs/SPEC-010-audit-fixes.md`, approved 2026-09-23 |
| the code it touches | `backend/runs/service.py` (`follow`, `_record`, `start`), `backend/commons/runner/watch.py` (`context_size`, `ContextWatcher`), `backend/tests/test_promises.py`, `frontend/src/features/watch-progress/useRun.ts` |
| what runs the tests | `USE_RECORDED_STREAM=true python -m pytest backend/tests -q` — 509 at the cut; `cd frontend && npx tsc --noEmit && npx vitest run` — 19 |
| the fixture's one packet | the recorded stream carries exactly one `task_progress` event, `usage: {total_tokens: 13921, tool_uses: 1, duration_ms: 93451}`, agent `worldbuilder` |

## Part 2 — Build order

### 10.1 W1 — a finished run's stream ends with the run

**Tests first** — `backend/tests/test_api.py`:

| test | criterion |
|---|---|
| `test_a_finished_run_stream_ends_with_its_detail_not_two_words` — start a run, drain it, open the stream again: the last frame is `done`, its data has every required `RunDetail` key (via `test_api_contract.interface("RunDetail")`) and `result == "complete"` | AC-1 |
| `test_a_halted_run_stream_reports_the_halt_as_its_result` — a run that ended without `result` (the existing missing-`result` switch): `done.data.result == "halted: process"` | AC-1 |

**Code.**
1. `RunService.follow`, not-live branch: `{"event": "done", "data": {"result": self._result_of(run_id), **self.detail(run_id)}}`. `_result_of` reads the run row: `"complete"` when `stage == "complete"`, `f"halted: {halted}"` when `halted` is set, else `"not live"` (a row that is neither — only reachable between creation and the sweep — keeps the old word, with the detail beside it).
2. `useRun.ts`, `done` handler: `setDetail` only when `data.run` is present; otherwise keep the snapshot already held and log. Class **A** (a guard, no hook test without a DOM), noted in the commit.

**Docs.** none — SPEC-010 AC-1 is the record.

**Effort.** 0.75 h, *estimated*.

### 10.2 W2 — the context watcher reads the figure the stream carries

**Tests first** — `backend/tests/test_runner.py` and `test_api.py`:

| test | criterion |
|---|---|
| `test_context_size_reads_total_tokens_when_the_input_fields_are_absent` — `context_size({"total_tokens": 13921, "tool_uses": 1, "duration_ms": 93451}) == 13921` | AC-2 |
| `test_context_size_prefers_the_input_fields_when_they_exist` — the three-field sum wins over `total_tokens` when both are present (the orchestrator's own turns carry both kinds) | AC-2 |
| `test_the_fixture_packet_is_measured_not_absent` — **replaces** `test_unreported_packets_are_absent_rather_than_zero`: over the fixture, `packets_measured == 1`, `largest_packet == 13921`, `by_agent["worldbuilder"] == 13921`, `packet_series_provenance == "measured"` | AC-2 |
| `test_an_empty_usage_is_still_absent_never_zero` — a `task_progress` with `usage: {}` leaves `packets_measured` at 0 and provenance `absent` (the old test's claim, kept for the case it was really about) | AC-2 |
| `test_api.py::test_a_task_progress_call_row_carries_the_subagent_total_with_a_note` — after a replayed run, the `calls` row for the packet has `input_tokens == 13921`, `provenance == "measured"`, `output_tokens IS NULL`, and `note` says the figure is the subagent's total (input and output together) | AC-2 |

**Code.**
1. `watch.context_size`: return the three-field sum when any of the three is present; else `int(usage.get("total_tokens") or 0)`.
2. `ContextWatcher` docstring: the paragraph claiming the packets "read zero" is rewritten to what the data shows; the halt on a packet above the ceiling is unchanged and now reachable.
3. `service._record`: `note="total_tokens: the subagent's whole usage, input and output together, as the CLI reports it; an upper bound on the packet"` when the size came from `total_tokens`; `output_tokens` stays `None` (the CLI does not split it).
4. `CallRow` gains `note` if it lacks one (the `calls` table has the column).

**Docs** (`novaforge-05`, after this phase is green): `verification.md` §3.5 rewritten — what the stream carries, that it is a total not a packet, the history of the wrong claim; `domain-knowledge.md` §8.4; `architecture.md` §6.3; G2 layer 2 stops being "armed and never fired". Test count in the three places that state it.

**Effort.** 1 h, *estimated*.

### 10.3 W3 — two premises with the same first six words

**Tests first** — `backend/tests/test_api.py`:

| test | criterion |
|---|---|
| `test_a_taken_fallback_slug_gets_a_suffix_instead_of_a_500` — insert a run whose slug is `slugify(PREMISE)` (through `create_run`, `stage=complete`), then `POST /api/runs` with `PREMISE`: 201, `slug == slugify(PREMISE) + "-2"`, and a third gets `-3` | AC-3 |
| `test_the_learned_slug_still_overwrites_the_suffixed_fallback` — the replayed run ends with `slug == "night-dispatcher-recovered-climber"` regardless of the suffix it started with | AC-3 |

**Code.** `service.start`: `slug = unique_slug(self.conn, slugify(premise))`; `unique_slug` appends `-2`, `-3`, … while `SELECT 1 FROM runs WHERE slug = ?` finds a row. The 40-character cap of `slugify` is respected before the suffix is added.

**Docs.** none.

**Effort.** 0.5 h, *estimated*.

### 10.4 W4 — the promises check is a property of finished runs

**Tests first** — `backend/tests/test_promises.py`:

| test | criterion |
|---|---|
| `test_no_existing_run_has_an_incoherent_promise[<slug>]` — gains, before the assertion: `if not (OUTPUT / slug / "dist" / "book.md").exists(): pytest.skip(f"{slug}: no dist/book.md — a run that did not finish cannot keep promises it never reached")` | AC-4 |
| `test_an_unfinished_run_is_skipped_with_its_reason` — a temporary `output`-shaped directory with `bible/mysteries.md` and no `dist/book.md`; the same predicate returns the skip reason (the predicate is a small function so it can be tested without re-parametrising the glob) | AC-4 |

**Demonstration, recorded in the commit message:** with `novaforge-v2-dead-runs/salvage-crew-derelict-remembers-them` copied back under `output/` for one run of the suite, the suite is green with one `skipped`, then the copy is removed. That is AC-4's second clause, executed once.

**Code.** the predicate `finished(run_dir) -> bool` in `test_promises.py`; `check_promises` itself unchanged (SPEC-010 W4).

**Docs.** none.

**Effort.** 0.5 h, *estimated*.

## Part 3 — Tests by phase

| phase | new tests | replaced | criteria |
|---|---|---|---|
| 10.1 | 2 | — | AC-1 |
| 10.2 | 5 | 1 (`test_unreported_packets_are_absent_rather_than_zero`) | AC-2 |
| 10.3 | 2 | — | AC-3 |
| 10.4 | 1 (+ the skip inside the parametrised one) | — | AC-4 |

AC-5 is **I** and is the docs step of 10.2, reviewed by David.

## Part 4 — Docs by phase

| phase | `verification.md` | `domain-knowledge.md` | `architecture.md` |
|---|---|---|---|
| 10.2 | §3.5 rewritten; G2 layer 2; history row 5 | §8.4 corrected, the wrong claim kept as history | §6.3 corrected |
| all | test count where stated | — | — |

## Part 5 — Gaps this plan leaves

| id | gap | level | why | how we would notice |
|---|---|---|---|---|
| P-1 | `total_tokens` is the subagent's whole usage, not the packet it was handed | important | the only per-subagent figure the CLI emits; labelled in `calls.note` and in §3.5 | a packet under the ceiling whose total trips the watcher — early, the correct direction |
| P-2 | the fixture carries one packet, so the measured series in CI is a sample of one | incidental | the real runs carry 7 and more; the test pins the mechanism, not the distribution | `packets_measured` on the next real run |
| P-3 | the `useRun` guard has no test | incidental | a hook needs a DOM to test; the backend now never sends the shape the guard defends against | a `done` frame without `run` reaching the panel |
| P-4 | gate constants read from Python, not the run's snapshot (SPEC-010 §2) | important | declared to `verification.md` §3 by `novaforge-05`; its own spec | a run archived after a constant change |

## Part 6 — Effort

| phase | hours, *estimated* |
|---|---|
| 10.1 | 0.75 |
| 10.2 | 1 |
| 10.3 | 0.5 |
| 10.4 | 0.5 |
| **total** | **2.75, estimated** |

Stop rule (`AGENTS.md` §5, runbook Paso 9): three red commits in a row and this
plan returns to `draft` with the reason written in.
