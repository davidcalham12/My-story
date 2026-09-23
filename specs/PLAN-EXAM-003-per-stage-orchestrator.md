# PLAN-EXAM-003 — the per-stage orchestrator

status: approved
date: 2026-09-23
implements: SPEC-EXAM-003 (approved 2026-09-23)
approved_by: David Calderon — same sentence as the spec; written at his instruction
executes: novaforge-05 · reviews: the coordinating session

Tests first, seen red. One commit per phase.

## B1 — unit procedures (docs, no code)
Split the skill into `.claude/skills/storymaker/units/{world,cast,outline,chapter,finish}.md`: each is the slice of today's SKILL.md for its stages, plus "read only the files named in your prompt; write your outputs; end your turn". SKILL.md keeps the shared rules and points at the unit files.

## B2 — the conductor
Tests (`test_conductor.py`, fake process per unit): the unit order from `flow.yaml` and the chapter count; a unit whose accepted outputs exist is skipped (resume, AC-3); a unit's halt stops the sequence and marks the run; no unit starts while the previous process is alive; every stream line lands in `events` with its unit (migration 015 adds `events.unit`).
Code: `backend/runs/conductor.py` — builds each unit's short prompt (slug, unit, chapter, paths, the unit file to follow), launches `RunProcess` for it, feeds the same watchers, checks the unit's output contract, persists, next. `RunService._execute` calls the conductor instead of one process.

## B3 — the ceiling on the orchestrator
Tests (`test_runner.py`): an orchestrator turn over the ceiling raises `WatchTripped("context", "<unit>: N tokens")`; under it, nothing; the largest turn per unit is persisted and exposed in the run detail (provenance measured).
Code: `ContextWatcher` halts on orchestrator turns too (the per-subagent check unchanged); per-unit maxima stored.

## B4 — orphans
Tests: stopping the service stops the live child; a launch refuses while a process of the same run is alive.
Code: `RunService` shutdown hook calls `process.stop()`; the conductor records the child's pid and checks it before launching.

## B5 — the real run (AC-5, AC-6)
Brief 01, profile `exam`, ceiling 60. Record the largest orchestrator turn per unit, cost, minutes, gate. Compare with the single-orchestrator example novel in `docs/iterations.md` — this is also the exam's before/after iteration.

## Cuts, if Thursday runs short
B4's refusal check (keep the shutdown stop) → B3's per-unit persistence (keep the halt) → nothing else: B1–B3 and B5 are the requirement.
