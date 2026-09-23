---
id: SPEC-EXAM-003
title: A fresh orchestrator per stage and per chapter, so that nothing in a run holds more than 100,000 tokens
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "entonces sí haz la opción b ya que necesito que el máximo sea de 100000 tokens concurrentes"; written at his instruction, after the risk was explained to him (spec §8, Q27)
approved_on: 2026-09-23
names_protected_value: the 100,000-token ceiling (AGENTS.md §6) — its figure is unchanged; its scope widens from the agents' packets to the orchestrator's own context
depends_on: docs/spec.md §8, backend/commons/runner, backend/runs/service.py, .claude/skills/storymaker/SKILL.md, specs/flow.yaml
---

# SPEC-EXAM-003 — The per-stage orchestrator

## 1. What is wanted, and why

**Today one Claude Code process orchestrates the whole novel.** It is one
conversation that accumulates the Bible, every draft, every critique and every
feedback sheet, so its context grows with the book: measured median 147,000
tokens and peaks of 642,000. The agents it dispatches stay under 100,000; the
orchestrator does not, and a ceiling applied to it would halt every novel.

**The owner requires that no part of a run exceed 100,000 concurrent tokens.**
The way to satisfy that without halting every novel is to stop the orchestrator
from accumulating: **Python becomes the conductor** and launches a *fresh*
Claude Code process for each unit of work, handing it only what that unit needs
and reading its results from disk. Each process starts clean and ends when its
unit is done, so its context is bounded by the unit, not by the book.

The units, in `flow.yaml` order:

| unit | one process does | reads from disk | writes to disk |
|---|---|---|---|
| U1 world | FLOW-1 | brief | `bible/world.md` |
| U2 cast | FLOW-2 + ingest | brief, world | characters, timeline, mysteries; story-bible rows |
| U3 outline | FLOW-3 + audit | the Bible | `outline.md`, audit file |
| U4.n chapter n | FLOW-4 for chapter n: draft, the gate, up to three attempts, patch-then-halt, promotion, summary, fact usage | Bible, outline entry n, rolling summary | `chNN.md`, attempts, critiques, summary |
| U5 finish | FLOW-5 + FLOW-6: style, synopsis, judge, mandatory facts, PDF | chapters, Bible, summaries | finals, synopsis, PDF, validations |

**What this buys beyond the ceiling:**
- **Checkpoint and resume come for free** (an exam requirement): the conductor skips every unit whose outputs already exist and are accepted, so a run that dies resumes at the first unfinished unit.
- **The TLA+ state machine maps one-to-one** onto the conductor's loop.
- **Cost stops growing with the square of the book**: each process pays for its own unit, not for everything before it. Each process also pays a fixed start-up cost (about one orchestrator turn), which is measured, not assumed.

## 2. Rules

- **The ceiling is enforced on every orchestrator turn**: a turn whose context exceeds 100,000 tokens halts the run with `halted: context`, naming the unit. The agents' packets keep their existing check.
- **Concurrency.** Within a unit, the four model critics run in parallel only if the orchestrator's last measured context plus four critic packets (estimated as in the skill, words × 1.35) fits under 100,000; otherwise in two rounds. The conductor never runs two units at once.
- **One conductor, one process at a time.** Before launching a unit the conductor checks that no other orchestrator of this run is alive; on stopping, the conductor stops its child (closes the orphan hole found on 2026-09-23, red-team log case 9).
- **The procedure stays written, not coded.** Each unit gets its own short procedure file (a slice of today's skill); Python chooses which one and passes paths, never re-implements a stage.
- **Nothing is carried in memory between units.** Everything a unit needs is on disk or in the database; a unit's prompt names files, not contents.

## 3. Out of scope

Running units in parallel (chapters stay sequential: chapter n needs summary
n−1). Changing the gate, the agents' tools, or the budget ceiling. Resuming a
unit halfway (a unit restarts from its beginning).

## 4. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | the conductor launches the units in `flow.yaml` order, one process each, and a chapter unit per chapter | T (fake process) |
| AC-2 | an orchestrator turn over 100,000 tokens halts the run as `context`, naming the unit | T |
| AC-3 | a run killed after unit U4.3 resumes at U4.4 with no chapter duplicated or lost | T |
| AC-4 | stopping the server stops the live orchestrator; launching refuses while another orchestrator of the run is alive | T |
| AC-5 | a real 10-chapter run completes with **every orchestrator turn under 100,000**, the largest turn reported with provenance `measured` | D |
| AC-6 | the same run's cost and wall time are compared with the single-orchestrator example novel, both measured | D |
| AC-7 | the conductor holds no stage logic: each unit's procedure is a file read by Claude Code | I |

## 5. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| a single chapter unit (three attempts with all critiques) could still exceed 100,000 on a very long chapter | important | measured on the first real run; the halt makes it visible, never silent | `halted: context` naming a chapter unit |
| the concurrency sum is estimated before dispatch and measured after, never reserved | important | no API key: Python does not assemble the prompts | a context halt during parallel critics |
| each unit re-pays the orchestrator's start-up (about one turn) | incidental | measured in AC-6; bounded by the number of units | cost per unit in the run's calls |
| built two days before delivery | important | the owner's decision with the risk stated; the single-orchestrator novel runs in parallel as a fallback | AC-5 not reached by Thursday evening |
