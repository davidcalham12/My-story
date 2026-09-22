# PLAN-007 — Backend v1: from the approved spec to a tested branch

status: draft
date: 2026-09-22
implements: SPEC-007-backend-v1 (approved 2026-09-22, commit `16e493b251e3be0878f498a440676aeaeb430302`)
branch: `backend-v1`, cut from `main` at `92b0cad`

The spec was approved after most of the backend existed. This plan therefore
does three different things and says which is which at every phase: it
**verifies** what is built against the spec's criteria, it **builds** what the
spec requires and the repository lacks, and it **retires** what Paso 4 decided
against (SPEC-007 §12a). The runbook's twelve phases are kept, with their
numbers, so the report can be read against it.

Every phase lists its tests before its code (`AGENTS.md` §4). A test named here
is written, watched to fail, and then made to pass; a test named here that
already exists is run and cited, not rewritten. "Built" below means: exists at
`16e493b` and has a test that exercises it.

## Part 1 — Reference

| what | where |
|---|---|
| the spec | `specs/SPEC-007-backend-v1.md`, `status: approved`, 2026-09-22 |
| its commit | `16e493b251e3be0878f498a440676aeaeb430302` |
| the decisions the plan obeys | SPEC-007 §12a (Q1–Q8) |
| the architecture the plan may not contradict | `docs/architecture.md`; where the two disagree, stop (SPEC-007 preamble) |
| the criteria the plan must satisfy | SPEC-007 §10, AC-1 … AC-21 |
| what runs the tests | `USE_RECORDED_STREAM=true python -m pytest backend/tests -q` — 449 at the cut |

## Part 2 — Build order

One commit per phase, message `PLAN-007 6.N: <what>`. A phase whose work is
"verify only" still gets its commit if it adds a test or a docs line; if it adds
nothing it is recorded in Part 6 as verified and gets no commit.

### 6.1 The recorded stream (the runbook's "fake claude")

**State.** Built differently from the draft: there is no fake `claude`
executable. `commons/runner/process.py` has a `RecordedProcess` that replays a
committed stream-json when `USE_RECORDED_STREAM=true`; the app and every test go
through it. Same effect — runner, parser, persistence, SSE and both watchers at
$0 — no binary on PATH.

**Tests first.** Inventory, then fill: the spec's five switches (malformed line,
missing `result`, cost overshoot, five parallel critics over 100,000, unknown
critique shape) against what `test_runner.py`, `test_db_and_tokens.py` and
`test_import.py` already inject.

Inventory done at round 1 of the convergence loop:

| switch | test | criterion | state |
|---|---|---|---|
| malformed line | `test_runner.py::test_a_line_that_is_not_json_is_logged_and_skipped` | AC-2 | **add** — `test_an_unfamiliar_shape_never_raises` covers an unexpected *JSON* shape, not a non-JSON line |
| missing `result` | `test_runner.py::test_a_stream_that_ends_without_result_halts_process` | FR-RNR-7 | **add** |
| cost overshoot | `test_runner.py::test_the_budget_stops_the_run_when_the_reported_cost_crosses_it` | AC-5 | exists |
| context overshoot | `test_runner.py::test_an_oversized_subagent_packet_halts_the_run` | AC-6 | exists |
| unknown critique shape | `test_import.py::test_an_unknown_critique_shape_is_a_parse_error_row_not_a_drop` | AC-7 | **add** — `test_three_critique_shapes_all_read` covers the three known ones |

**Code.** Only what the inventory shows missing: a switch is a modified copy of
the fixture, never a change to `RecordedProcess`.

**Docs.** `architecture.md` §8.3 names the recorded stream as the test double;
SPEC-007 §3.2 already does. Nothing else.

**Effort.** 1.5 h, *estimated*.

### 6.2 `commons/db` — schema and migrations

**State.** Built: migrations 001–008, WAL, one writer, `repository.py`. Tables
at the cut: `runs, attempts, calls, scores, gate_decisions, findings, sheets,
summary_facts, character_knowledge, chunks, run_warnings, run_completeness`.
Missing against SPEC-007 §5: **`events`** (Q3). `drafts` and `facts` of the
draft's table exist under the names `attempts` and `summary_facts`; the spec's
§5 table is amended to the built names at 6.2's docs step rather than the
schema renamed.

**Tests first** — `backend/tests/test_events.py`:

| test | criterion |
|---|---|
| `test_migration_009_creates_events_with_seq_per_run` | FR-RNR-3 |
| `test_seq_is_dense_and_monotonic_within_a_run` | AC-20 |
| `test_payload_is_the_untouched_line` | AC-20 |
| `test_migrating_twice_applies_009_once` | (existing guarantee, `migrate.py`) |

**Code.**
1. `009_events.sql` — `events(run_id, seq, ts, type, payload)`, primary key
   `(run_id, seq)`, `payload TEXT` holding the raw line. The header comment says
   why the table exists: a run is judged by the stream it ran.
2. `repository.append_event(conn, run_id, seq, ts, type, payload)` and
   `repository.events_after(conn, run_id, seq)`.

**Docs.** SPEC-007 §5: table names as built, `events` marked *added by PLAN-007
6.2*. `verification.md` G19 gains the raw stream; §3.14 ("a run that dies
mid-flight archives nothing") narrows — the stream up to the death is now in
the database even when the archive is not.

**Effort.** 1.5 h, *estimated*.

### 6.3 `commons/config` — loading and the consistency validators

**State.** Built and tested: `loader.resolve(profile)`, `test_skill_contract.py`
(SKILL.md ↔ `flow.yaml` ↔ config: stage order, critics, threshold, attempts,
`on_fail`), `test_agents_frontmatter.py` (`chapter-writer` holds `Glob`; only
the two Bible writers hold `Write`), `test_formulas_agree.py` (gate constants
have one home).

**Tests first.** Existing tests cover AC-8 and AC-9; run and cite. FR-CFG-1's
`config_hash` **does not exist anywhere in `backend/`** (round 1); it is built:

| test | criterion |
|---|---|
| `test_skill_contract.py::*` | AC-9 |
| `test_agents_frontmatter.py::*` | AC-8 |
| `test_config_hash.py::test_the_same_resolved_config_hashes_the_same` | FR-CFG-1 |
| `test_config_hash.py::test_detail_exposes_the_hash_of_the_stored_snapshot` | FR-CFG-1 |

**Code.** `loader.config_hash(snapshot) -> str` (sha256 of the canonical JSON,
16 hex); `runs/repository.get_run` exposes it computed from the stored
`config_snapshot` — no new column, the snapshot is already stored per run.

**Docs.** none beyond SPEC-007 §3.2 (already says the validators exist).

**Effort.** 1 h, *estimated*.

### 6.4 `commons/runner` — spawn, parse, persist, derive

**State.** Built: `RunProcess.for_run` (explicit argv, no shell, prompt on
stdin), `events()` line parser, `watch.apply` state derivation, `cost.json` on
`result`. Missing: **`--max-budget-usd`** in argv (AC-21) and **persisting each
raw line to `events` before fan-out** (AC-20, table from 6.2).

**Tests first** — additions to `test_runner.py` and `test_api.py`:

| test | criterion |
|---|---|
| `test_runner.py::test_argv_carries_max_budget_usd_from_the_profile` | AC-21 |
| `test_runner.py::test_the_prompt_is_on_stdin_and_absent_from_argv` | AC-1, AC-21 (exists as the argv half of G17 — verify) |
| `test_api.py::test_every_stream_line_is_in_events_before_the_stage_changes` | AC-20 |
| `test_api.py::test_events_count_equals_recorded_stream_lines` | AC-20 |
| `test_api.py::test_cost_json_and_conformance_are_utf8_without_bom` | NFR-7 |

**Code.**
1. `RunProcess.for_run(..., max_budget_usd: float)` appends
   `"--max-budget-usd", str(ceiling)`; the value is the one 6.5 resolves.
2. `RunService._execute`: `append_event` is the **first** statement in the loop
   body, before `apply` and before `_record`; `seq` is a per-run counter held on
   `Live`.
3. `service.py` lines 342 and 369 call `write_text` **without an encoding**
   (round 1): on Windows that is cp1252. Both get `encoding="utf-8"`; NFR-7 says
   explicit everywhere.

**Docs.** `architecture.md` §3.6 *Observation*: the raw stream is persisted, then
derived. `claude.md` guarantee 2 unchanged (the watchers are unchanged).

**Effort.** 2 h, *estimated*.

### 6.5 Budget and context watchers

**State.** Built and tested: `BudgetWatcher` (measured on the stream, worst-rate
priced between `result` events), `ContextWatcher`
(`input + cache_creation + cache_read`, per `usage`). Two things the spec
requires that the build does not do:

- **FR-BUD-4** — the budget ceiling comes from `settings.budget_ceiling_usd`
  (`NOVAFORGE_BUDGET`, default 25), **not from the profile**. `tiny.json` says
  `max_cost_usd: 5.0`; the last real tiny run cost $18.82. Honouring the profile
  as written would halt every tiny run at chapter 1.
- **FR-BUD-1** — the CLI flag (6.4) needs the same figure.

**Tests first** — `test_budget_source.py`:

| test | criterion |
|---|---|
| `test_the_ceiling_is_the_profile_figure_when_the_env_is_unset` | FR-BUD-4 |
| `test_the_env_only_lowers_the_ceiling_never_raises_it` | FR-BUD-4 |
| `test_the_same_figure_reaches_argv_and_the_watcher` | AC-21, FR-BUD-1 |

**Code.** `RunService._execute`: `ceiling = min(cfg["budget"]["max_cost_usd"],
settings.budget_ceiling_usd)` when the env is set, else the profile's figure;
passed to both `BudgetWatcher` and `RunProcess.for_run`.

**Decision the plan cannot take** (Part 5, gap P-1): `tiny.json`'s `5.0` is a
value `AGENTS.md` §6 protects. This plan proposes `25.0` for `tiny` (measured
cost ×1.3) and leaves `stress` at `40.0`; the change is made at 6.5 **only if
the user writes the new figure into this plan's approval**. Without it, 6.5
ships with the profile figure and the real tiny run of Part 6 will halt on
budget — which is also a result, and is recorded as one.

**Docs.** `architecture.md` §3.5 (`halted: budget` row cites the profile);
`claude.md` guarantee 8 (rule 10 before renumbering) unchanged in wording;
`config/novel.config.json` `_comment_budget` rewritten — it says "advisory only
on this branch", which stops being true.

**Effort.** 1.5 h, *estimated*.

### 6.6 `commons/log` — one row per subagent call

**State.** Built and tested: `calls.py` writes a `CallRow` per `task_progress`
usage event with stage, chapter, attempt, tokens, `in_flight_at_dispatch` and
provenance (`test_db_and_tokens.py`, `test_absent_is_not_zero.py`).

**Tests first.** Existing; run and cite for AC-6 (`in_flight_at_dispatch` on
every row) and FR-RNR-5.

**Code.** none.

**Docs.** none.

**Effort.** 0.25 h, *estimated* (running and citing).

### 6.7 `runs` — endpoints, SSE, halt, import, orphans

**State.** Built: `POST/GET /api/runs`, `GET /api/runs/{id}`,
`GET /api/runs/{id}/events` (snapshot, live, done), archive on finish,
conformance. To build: **halt** (FR-RUN-5, AC-18), **startup sweep** (FR-RUN-7,
AC-19), **`Last-Event-ID` replay** (FR-RUN-4, AC-20), **import CLI** (FR-RUN-6,
Q7, AC-7).

**Tests first** — `test_api.py` additions and `test_import.py`:

| test | criterion |
|---|---|
| `test_halt_stops_the_process_and_marks_halted_user` | AC-18 |
| `test_halt_keeps_the_attempt_in_flight_unpromoted_and_readable` | AC-18 |
| `test_halt_on_a_finished_run_is_409_not_a_second_halt` | AC-18 |
| `test_a_run_left_running_is_marked_halted_process_on_startup` | AC-19 |
| `test_last_event_id_replays_from_the_next_seq_then_goes_live` | AC-20 |
| `test_last_event_id_beyond_the_end_yields_only_done` | AC-20 |
| `test_sse_id_field_is_the_persisted_seq` | AC-20 |
| `test_import.py::test_the_cli_entry_point_imports_the_eight_v1_runs` | AC-7 |
| `test_import.py::test_the_cli_skips_runs_already_in_the_database` | AC-7 |

**Code.**
1. `router.py`: `POST /{run_id}/halt` → `service.halt(run_id)`; 404 unknown,
   409 not live.
2. `service.halt`: `live.process.stop()`, `halted = ("user", "halted by the
   user")`, through the same `_finish` path the watchers use — the archive and
   the `None` sentinel are not special-cased.
3. `service.sweep_orphans()` called from `main.build_service()`: every `runs`
   row with `stage != complete` and no `halted` → `halt(kind="process",
   detail="found running at startup; the process is gone")`.
4. `service.follow(run_id, after_seq: int | None)`: `events_after` first, then
   live; `router.events` reads the `Last-Event-ID` header and writes `id:` on
   each frame.
5. `commons/db/import_v1.py` gains `if __name__ == "__main__":` over
   `import_all()` with `--output` and `--db` arguments; the eight v1 slugs are
   the default list `test_import.py` already holds.

**Docs.** `architecture.md` §3.5 gains the `halted: user` row (and its "Three
reasons" becomes the count the table has — that sentence is wrong today,
reported by coherencia-docs and left for this phase); §3.6 the replay.
`verification.md` G19 T for the stream; §3.14 narrowed as in 6.2; SPEC-007 §12
rows for halt, sweep and `Last-Event-ID` marked **closed by 6.7** with the
tests as evidence — the rows stay, per `AGENTS.md` §3.

**Effort.** 4 h, *estimated*.

### 6.8 `commons/search` — local embeddings, `vec0`, degradation

**State.** Built and tested (`test_vectors.py`, `search.py`): embeds Bible
sections and facts, never chapter prose; `{"available": false}` when
`sqlite-vec` or the model is missing. **Not wired into the skill — Q5**, and
this plan does not wire it.

**Tests first.** Existing; run and cite for AC-11 at module level.

**Code.** none.

**Docs.** none — `verification.md` §3.15 and SPEC-007 §12 already carry the gap.

**Effort.** 0.25 h, *estimated*.

### 6.9 Instruments — `validate-sheet.mjs`, `measure.mjs`

**State.** Both in Node, both self-tested in CI (`ci.yml` lines 49–52). **Q6:
they stay.** `measure.mjs` has `FEATURES = ['continuity', 'science', 'outline',
'length', 'chatter']` — five; SPEC-007 FR-INS-3 requires six. `validate-sheet.mjs`
holds `FIVE = ['Continuity', 'Science', 'Outline', 'Length', 'Heading']` (round
1): it accepts a sheet with no `Prose` line, so FR-INS-2's "six scores" is
unmet today and both instruments change.

**Tests first.** The instruments' self-tests are their tests. Additions:

| test | criterion |
|---|---|
| `measure.mjs --self-test` names `prose` as SKIP on the five-characteristic fixture, not as absent | AC-14 |
| `measure.mjs <slug>` on `output/lighthouse-keeper-ledger` (a six-characteristic run) reports six scores per chapter | AC-14 |
| `validate-sheet.mjs --self-test` rejects a sheet missing `prose` | AC-13 |
| `test_instruments.py::*` (both self-tests from pytest) | AC-13, AC-14 |

**Code.** `measure.mjs`: `FEATURES` gains `'prose'`; the self-test's fixture
assertions gain a named SKIP for it (the fixture predates SPEC-006 — absent, not
zero). `validate-sheet.mjs`: `FIVE` becomes the six with `Prose`, and its
self-test's good sheet carries a `Prose` score. `sheet_template/v01.md` is
checked for the line; if the template lacks it the template changes too, and
`SKILL.md` says the template does not vary — so that is a one-line skill edit,
listed at 6.12.

**Docs.** SPEC-007 §12 `measure.mjs` row → **closed by 6.9**; `verification.md`
G21 note rewritten to say the instrument now knows six.

**Effort.** 1.5 h, *estimated*.

### 6.10 Read endpoints by feature — retired

**State.** **Q2: not built.** Reads come from the archive through
`GET /api/runs/{id}`. The phase keeps its number and becomes one negative test.

**Tests first.**

| test | criterion |
|---|---|
| `test_api_contract.py::test_no_route_takes_a_path_and_reads_a_file` | AC-10 |

**Code.** none.

**Docs.** none beyond SPEC-007 (done at Paso 4).

**Effort.** 0.5 h, *estimated*.

### 6.11 `/api/health`

**State.** Built: `{ok, orchestrator, claude_on_path}`. FR-HLT-1 asks also for:
DB reachable, migrations applied, `sqlite-vec` loadable, embeddings model
present — never probing the model.

**Tests first** — `test_api.py`:

| test | criterion |
|---|---|
| `test_health_reports_db_and_the_number_of_migrations_applied` | FR-HLT-1 |
| `test_health_reports_sqlite_vec_and_model_availability_without_loading_the_model` | FR-HLT-1 |
| `test_health_says_whether_it_is_replaying_or_orchestrating` (exists) | FR-HLT-1 |

**Code.** `main.health` adds `db: bool`, `migrations: int`, `sqlite_vec: bool`,
`embeddings_model: "present" | "absent" | "unchecked"` — the last from the
model cache directory's existence, not from importing the model.

**Docs.** SPEC-007 §3.2 health row → as built after 6.11.

**Effort.** 1 h, *estimated*.

### 6.12 `SKILL.md` — what SPEC-007 §8 requires of the procedure

**State**, point by point:

| §8 | requirement | state |
|---|---|---|
| 1 | rejected drafts as `chapters/chNN.attemptK.md` | **done** — the archive reads them (`test_archive.py`) |
| 2 | real `ts` (`date -u`) and `duration_ms` per call | **unknown at $0**; the backend takes `ts` from the stream (`calls.py`), so the skill's own timestamps are secondary — verified on the real run (AC-16's method) |
| 3 | `search` before the continuity critic | **retired, Q5** |
| 4 | outline audit after FLOW-3 | **done by a model, Q4** |
| 5 | `validate-sheet.mjs` before any sheet | **done** (`SKILL.md` §"The sheet") |
| 6 | packet estimate `wc -w × 1.35` before dispatch | **done** (`architecture.md` §6.1; `claude.md` guarantee 2) |
| 7 | `chNN.facts.json` | **retired**, SPEC-007 §12 |

**Tests first.** None at $0 can hold the procedure (`verification.md` §3.12).
The check for point 2 is a script over the real run's `logs/agents.jsonl`:

| check | criterion |
|---|---|
| `backend/checks.py` gains `procedure-log`: every call row has a `ts` that parses and is monotonic | AC-16 (I) |

**Code.** No change to `SKILL.md` is required by this plan. If the real run
shows point 2 unmet, the change is a one-line `date -u` in the skill and is
made **after** the run, recorded in Part 6 as a finding — not before, so the
run measures the procedure as it was.

**Docs.** `domain-knowledge.md` after the runs (Part 6).

**Effort.** 1 h, *estimated*.

## Part 3 — Tests by phase, summary

| phase | new tests | existing tests cited | criteria |
|---|---|---|---|
| 6.1 | 0–5 (inventory) | `test_runner`, `test_import` | AC-2, AC-5, AC-6, AC-7 |
| 6.2 | 4 | — | FR-RNR-3, AC-20 |
| 6.3 | 2 | `test_skill_contract`, `test_agents_frontmatter` | AC-8, AC-9, FR-CFG-1 |
| 6.4 | 3–4 | — | AC-1, AC-20, AC-21 |
| 6.5 | 3 | — | FR-BUD-1, FR-BUD-4, AC-21 |
| 6.6 | 0 | `test_db_and_tokens`, `test_absent_is_not_zero` | AC-6 |
| 6.7 | 9 | — | AC-7, AC-18, AC-19, AC-20 |
| 6.8 | 0 | `test_vectors` | AC-11 |
| 6.9 | 3 (Node) + `test_instruments` | — | AC-13, AC-14 |
| 6.10 | 1 | — | AC-10 |
| 6.11 | 2 | 1 | FR-HLT-1 |
| 6.12 | 1 check | — | AC-16 |

Criteria with no test in this table, and why: **AC-3** (state at every step of
the fixture) — `test_runner.py` holds it today, cited at 6.1; **AC-4** —
`test_archive.py::test_the_measured_cost_is_stored_and_preferred_over_the_sum`;
**AC-12**, **AC-15**, **AC-15b** — class D, the real runs of Part 6; **AC-17**
— `grep` in CI, verified at Part 6 by hand and recorded.

## Part 3a — Coverage matrix: every requirement, its phase, its evidence

Built at round 2 of the convergence loop and kept: it is how the loop knows a
requirement has a step and a step has a requirement.

| requirement | phase | evidence |
|---|---|---|
| C1 no API key | Part 6 | AC-17 grep; `main.health` has no API fallback |
| C2 100,000 concurrent | 6.5, 6.12 | layer 2 `ContextWatcher` (built); layer 1 `SKILL.md` estimate (I) |
| C3 one run at a time | built | `test_api.py::test_the_queue_is_one` |
| C4 Windows-first | 6.4 | `test_the_prompt_is_never_an_argument` (built); UTF-8 fix (6.4 code 3) |
| C5 no secrets | 6.4, Part 6 | prompt on stdin (built); AC-17 grep extended to `httpx|requests` outside tests |
| C6 no literals | built | `test_the_ceiling_is_config_not_a_literal`, `test_formulas_agree.py` |
| C7 one implementation | 6.12 | no phase re-implements a stage; `_check_procedure_held` fingerprints `SKILL.md` |
| FR-RUN-1 | built | `test_start_a_run_and_follow_it_to_completion`, `test_a_premise_that_is_too_short_is_refused_at_the_edge`, `test_the_queue_is_one` |
| FR-RUN-2 | built | `test_the_run_list_includes_what_was_imported` |
| FR-RUN-3 | built | `test_the_snapshot_is_built_from_the_database_not_from_memory` |
| FR-RUN-4 | 6.7 | `Last-Event-ID` tests |
| FR-RUN-5 | 6.7 | halt tests |
| FR-RUN-6 | 6.7 | CLI tests; `test_the_named_v1_runs_import` (built) |
| FR-RUN-7 | 6.7 | sweep test |
| FR-RNR-1 | 6.4 | `test_the_command_carries_the_flags_that_were_learned_the_hard_way` (built) + the flag test |
| FR-RNR-2 | 6.1 | non-JSON line test (add) |
| FR-RNR-3 | 6.2, 6.4 | `events` tests |
| FR-RNR-4 | built | `test_the_slug_is_learned_from_the_paths_the_run_writes`, `test_subagent_dispatches_are_counted_by_name` |
| FR-RNR-5 | 6.6 | `CallRow` carries `ts`, `duration_ms`, `in_flight_at_dispatch`; `test_db_and_tokens.py` |
| FR-RNR-6 | built | `test_the_whole_run_cost_comes_from_the_result_event`; `halted: gate` at `service.py:163` |
| FR-RNR-7 | 6.1 | missing-`result` test (add) |
| FR-BUD-1 | 6.4, 6.5 | flag in argv; watcher |
| FR-BUD-2 | built, formula as §3.2 | `test_an_oversized_subagent_packet_halts_the_run`, `test_context_size_counts_the_cache_not_just_the_input` |
| FR-BUD-3 | built | `CallRow.tokens_reserved / in_flight_at_dispatch / wait_ms`; `test_unreported_packets_are_absent_rather_than_zero` |
| FR-BUD-4 | 6.5 | budget-source tests |
| FR-CFG-1 | 6.3 | hash tests (build) |
| FR-CFG-2 | built | `test_skill_contract.py` |
| FR-CFG-3 | built | `test_agents_frontmatter.py` |
| FR-SRC-1, -3 | built, 6.8 | `test_vectors.py` |
| FR-SRC-2 | retired Q5 | P-3 |
| FR-INS-1 | retired Q4 | P-4 |
| FR-INS-2, -3 | 6.9 | self-tests, six characteristics |
| FR-INS-4 | Part 6 | the grep of C5, extended: no network client outside tests |
| FR-RD-1 | built | detail payload; `test_api_contract.py::test_the_run_detail_keys_are_the_ones_the_service_serves` |
| FR-RD-2 | 6.10 | negative route test |
| FR-RD-3 | built | `test_absent_is_not_zero.py`; `test_the_cost_payload_has_exactly_the_fields_the_panel_declares` |
| FR-HLT-1 | 6.11 | health tests |
| NFR-1 | 6.1 | the three added switches; `test_a_failure_in_the_post_run_bookkeeping_still_ends_the_stream` (built) |
| NFR-2 | 6.2, 6.4 | `events` before fan-out |
| NFR-3 latency | declared | P-10 |
| NFR-4 | 6.4, Part 6 | as C4, C5 |
| NFR-5 | built / declared | real `ts` and `source` (built); structured JSON logs → P-8 |
| NFR-6 | built / declared | live exact (built); imported low/estimate/high → P-9 |
| NFR-7 | 6.4 | UTF-8 fix; `pathlib` throughout (built) |
| NFR-8 | 6.1 | the recorded stream |
| §8 points 1–7 | 6.12 | table there |

Architecture decisions, the other direction:

| decision | phase |
|---|---|
| §3.4 queue of one | built |
| §3.5 halt marks | 6.7 adds `user` |
| §3.6 snapshot then live; the database is the record | built; 6.7 replay |
| §5.1 two memory layers built and not running | 6.8 leaves them so (P-3); §8 point 7 retired |
| §6 two layers, neither a reservation | 6.5; P-11 |
| §8.1 "the budget projects worst case — input plus `max_tokens`" | **superseded** by §6.2 and §8.4 (measured on the stream); the plan follows the newer section and the spec; the older paragraph is a coherencia-docs OBS for the user |
| §8.1 "the mock engine takes an explicit plan" | **superseded**: the recorded stream replaced the mock; coherencia-docs EDO |
| §9 "the writer's isolation is now typed, `ContextPacket`" | **contradicts §3.2** (structural, `Glob`); coherencia-docs FAC — no plan step depends on it |

## Part 4 — Docs by phase

| phase | `architecture.md` | `verification.md` | `domain-knowledge.md` | spec |
|---|---|---|---|---|
| 6.1 | §8.3: the recorded stream is the double | — | — | — |
| 6.2 | §2.1 tree (`events`) | G19 raw stream; §3.14 narrowed | — | §5 names as built |
| 6.4 | §3.6 persisted then derived | — | — | — |
| 6.5 | §3.5 budget row cites the profile | — | — | — (config comment) |
| 6.7 | §3.5 `halted: user`, count fixed; §3.6 replay | G19; §3.14; §3 rows closed with evidence | — | §12 rows → closed by 6.7 |
| 6.9 | — | G21 note: six | — | §12 row → closed by 6.9 |
| 6.11 | — | — | — | §3.2 health row |
| Part 6 | §8.6 what the runs cost | v2 of the document (runbook Paso 11) | the two real runs, with numbers | §10 results table |

## Part 5 — Gaps this plan leaves

| id | gap | level | why | how we would notice |
|---|---|---|---|---|
| P-1 | `tiny.json` budget is $5.0 against a measured $18.82; the plan proposes $25.0 but cannot change a protected value | important | `AGENTS.md` §6; the figure is the user's at Paso 8 | the real tiny run halts on budget at chapter 1 |
| P-2 | Whether `--max-budget-usd` binds under a subscription is unknown | incidental | no way to learn it at $0; the watcher is the second line either way | the real run's `result` and the flag's behaviour, recorded in Part 6 |
| P-3 | `search` built and unwired | important | Q5; its own spec | `verification.md` §3.15 |
| P-4 | The outline audit stays a model, D | important | Q4 | `verification.md` G11 / §3.2 |
| P-5 | §8 point 2 (skill timestamps) is checked only on a real run | incidental | the backend's `ts` comes from the stream and does not depend on it | `checks.py procedure-log` on the run |
| P-6 | The stress run may not reach `patch_then_halt` | incidental | it is built to fail, but a model can pass what was built to fail | AC-15b says "or explains why it did not" |
| P-7 | `events` stores every line; no retention | incidental | one machine, MBs per run | disk, eventually; a `VACUUM` note in §5 |
| P-8 | NFR-5 "logs are structured JSON": the backend writes no log at all; the database is the record | incidental | adding a logger is scope the spec did not size; the stream is in `events` after 6.2 | an operator asking for a log file |
| P-9 | NFR-6 "imported runs: low / estimate / high": the importer records *completeness* (what was missing) and one `reconstructed` figure, not a range | incidental | the v1 logs do not split tokens into halves that could bound a range (`test_v1_token_totals_are_not_split_into_invented_halves`); inventing bounds would be worse than one marked figure | the panel's cost provenance says `reconstructed` |
| P-10 | NFR-3 "relayed within 500 ms": no test measures it | incidental | the relay is a queue `put` on the reading thread; a timing test on CI runners flakes | a viewer noticing lag |
| P-11 | AC-6 is T against an injected packet only; on both real recordings the subagent `usage` reads zero, so the watcher never sees a real packet (`architecture.md` §6.3, `verification.md` §3.5) | important | the stream does not carry the figure; the watcher says `packet_series_provenance: absent` rather than pretending | the real runs of Part 6 either carry `usage` or record `absent` again |

## Part 6 — Effort, and the runbook steps after the code

| phase | hours, *estimated* |
|---|---|
| 6.1 | 1.5 |
| 6.2 | 1.5 |
| 6.3 | 1 |
| 6.4 | 2 |
| 6.5 | 1.5 |
| 6.6 | 0.25 |
| 6.7 | 4 |
| 6.8 | 0.25 |
| 6.9 | 1.5 |
| 6.10 | 0.5 |
| 6.11 | 1 |
| 6.12 | 1 |
| **code total** | **16, estimated** |
| Paso 10 real runs | tiny ≈ 1 h wall, ≈ $19 measured last time; stress ≈ 1–2 h, ≤ $40 by profile — *estimated* |
| Paso 11 verification.md v2, coherencia-docs | 2 |
| Paso 12 report | 1 |

Paso 9's stop rule applies: three red commits in a row and the plan returns
here as `draft` with the reason written in.

## Convergence loop

Stop rule (runbook Paso 7): a full round with no new gap in either direction, or
five rounds. **Stopped at round 2.**

**Round 1** — plan against `architecture.md` §2–§9, SPEC-007 §2–§12 and
`verification.md` §3. Eight gaps, all fixed in the plan:

1. 6.1 named five tests "verify exists; add if not" — the inventory showed two
   exist and three do not; named as such.
2. 6.3 hedged on `config_hash` — it does not exist; the phase builds it.
3. NFR-7: two `write_text` calls without an encoding (`service.py` 342, 369) —
   added to 6.4.
4. 6.9 hedged on `validate-sheet.mjs` — it holds five; both instruments change,
   and the sheet template is checked.
5. NFR-5 structured logs — no step, no logger anywhere: declared P-8.
6. NFR-6 imported cost range — the importer does completeness, not bounds:
   declared P-9.
7. NFR-3 latency — no step: declared P-10.
8. `architecture.md` §6.3: subagent `usage` reads zero on real streams, so AC-6's
   T holds on the fixture only — declared P-11.

Three places where the architecture disagrees with itself or with the spec
were found; none needs a plan step, all go to the coherencia-docs report of
this Paso: §8.1 budget worst-case (superseded by §6.2/§8.4), §8.1 mock engine
(superseded by the recorded stream), §9 `ContextPacket` bullet (contradicts
§3.2). Also §2.1's slice tree lists `prompts/`, which no feature has; §8.3's
"230 backend tests and 18 frontend" is 449 and 19.

**Round 2** — built Part 3a and walked it: every `C`, `FR` and `NFR` of the spec
has a phase, a "built" citation or a declared gap; every step in 6.1–6.12
answers a row. No new gap in either direction. Stopped.

**What stayed declared:** P-1 … P-11, Part 5.
