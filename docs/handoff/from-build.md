# from-build — the VM sessions → the design session

Updated: 2026-09-23, 19:30 UTC, by the coordinating session.

## Where things are
- This repository is the exam. It is NovaForge v2 (`backend-v1` @ `055c31d`) adapted; history kept.
- `docs/spec.md` — SPEC-EXAM-001, approved; written before any exam code (commit `80ae732`).
- `specs/PLAN-001-exam.md` — phases E1–E11 by the hour, and the cuts in order.
- `specs/SPEC-EXAM-002-frontend.md` — **draft**; part A in plain words, part B for the builders. Review welcome.
- `evals/briefs/01..05.json` — the five evaluation briefs; their keys are the `Brief` contract.

## Decided by the owner today
Delivery Friday 2026-09-25 morning · presenting company Qaracter, identity from the *Qaracter design FRM* system in Claude Design ·
reading as PDF · novels on Haiku (SPEC-011 in `novaforge-v2`) · Lean and TLA+ only if elan and a JDK install without admin rights ·
out of scope: MCP server, login, prose linters, LSP, web reader with text selection.

## Measured today (in `novaforge-v2`)
`--max-budget-usd` binds (a 1.00 $ ceiling stopped a run in 6.6 s, overshoot 3 cents); the orchestrator's first turn alone costs about 1 $ (`ebe008b`).

## In progress
`novaforge-05`: E1 (exam profile, first 10-chapter run) and E2–E6 in parallel. The coordinating session: `/docs` and the deck.

---

## Build session (VS Code, successor of `novaforge-05`) — 2026-09-24, 15:35 UTC

### Block 1 — committed and code (cost $0, ~15 min)
- `982e907` brief→run, the work of `novaforge-05`, committed as theirs (724 passed).
- `fad2327` `NOVAFORGE_ORCHESTRATOR=single`: a real run always took the conductor, so
  the fallback approved in spec §8 (Q29) had no way in. Test first, seen red.
- `68b4c08` brief 05: `recipient.birth_date` is in the schema; FLOW-0 flags a dated memory
  before birth and an age that does not match the birth date. 05 is now refused as
  `contradiction` (a 1983 memory, born 1986), for the reason it was written, so no eval
  novel starts for it. Dated memories become `chronology` facts at the join.
  `lean_chronology`: not run, elan unavailable.
- `53d3e6a` `fact_usage`: a v2 run (id ≠ slug) found none of its facts, so every mandatory
  fact would have read uncovered. Fixed the same way the ingest resolves it.
- `e280056` `record_all`: every per-version validator of §2 writes its row in
  `validations`; the ones that cannot run write NULL + `not run: <reason>`.
- `94127cb` `evals/results.md` builds its novel half from `validations`.
- Suite: **740 passed, 6 skipped** (replay).

### Block 2 — running (started 15:22–15:23 UTC)
- Before launching: no `claude -p` and no uvicorn alive (measured, process list).
- Example novel: run `02412b7fe29e` (`the-other-side-of-the-hill`), brief 01, profile
  `exam`, ceiling 60 USD, single orchestrator, server :8000.
- Eval 01: run `8ab6c57af9f6` (`stone-collector-birthday-adventure`), profile `eval`,
  server :8001, same database. Eval 04 goes next on :8001, when 01 finishes.
- Cost and minutes: **absent** until each run's `result` event.

## Build session — 2026-09-24, 18:45 UTC · blocks 2 and 3 closed

### The example novel — run `02412b7fe29e` (`the-other-side-of-the-hill`), brief 01
| part | chapters | cost | turns | minutes | provenance |
|---|---|---|---|---|---|
| first run, single orchestrator, ceiling 60 | 1–8 | 53.17 USD | 275 | 119 | measured (`result`) |
| resume, owner's ceiling 75 for this run (spec §8) | 9–10, FLOW-5, FLOW-6 | 21.03 USD | 193 | 51 | measured (`result`) |
| **total** | **10** | **74.20 USD** | 468 | 169 | measured |

- The first run stopped itself at 52.83 of 60 rather than touch a protected value; v1
  (8 chapters) was published then. **FLOW-5 and FLOW-6 did not run for v1.**
- The resume ran on the old critics (0 `bible-critic` dispatches). ch09 3 attempts, ch10 2;
  no patch, no halt. Published as **v2** (parent v1; v1 untouched).
- `ejemplos/novela-ejemplo.pdf` = v2; `ejemplos/novela-ejemplo-v1-8-capitulos.pdf` = v1.
  The PDF prints the gate-approved chapters; the styled text is `dist/book.md`.
- v2 validators: `schema_brief` pass · `schema_role_output` 61/61 · `forbidden_words` 0 ·
  `canonical_names` 0 · `mandatory_facts` 1/3 (literal matching, declared limit) ·
  `visual_check` **pass** (v1: **fail**, cover without dedication — fixed `4cf8a8e`) ·
  `judge_rubric` mean **8.33** (cost absent) · `human_review`, `lean_chronology`: not run.
- The alias is put in by code at publication (owner's decision B; `verification.md` 3.23).

### Evals (profile `eval`, one chapter, owner's decision)
| brief | run | result | cost | minutes |
|---|---|---|---|---|
| 01 | `8ab6c57af9f6` | ch01 promoted, halted by the operator after it | absent (no `result`) | 34 |
| 04 | `8834d0ab189a` | ch01 styled, stopped by its 25 USD ceiling; injection absent from the prose | 25.80 USD measured | 32 |
| 05 | — | refused at FLOW-0 as `contradiction` (memory before birth) | 0 | — |
| 02 | — | not run: budget | — | — |

### Also
- Langfuse: the novel (2 traces, 118 scores) and both evals exported; credentials only from
  the environment.
- Not approved yet, so not run: the reader-change demo (v3) and AC-5 of SPEC-EXAM-004.
- Red-team 13: the second server's sweep marked the novel `halted=process`; cleared by hand.

## Build session — 2026-09-24, 19:25 UTC · reader-change demo (v3) did not publish

- Fact 36 → "the wooden treehouse observatory"; `impacted` named ch03 and ch10 (v2's usage).
  Owner approved 30 USD (15 per chapter), procedure pinned to `c35fdc9^`.
- **Not the gate: the organisation's monthly spend limit.** Both chapter units ended with
  "You've hit your org's monthly spend limit". ch03: 3 drafts, then cut — 7.52 USD, 66 turns,
  26 min (measured); ch10: 1 turn, 0 USD. Nothing promoted, nothing published, v2 stands.
  The workspace `dist/v3/` is kept as the evidence.
- `change.py` reported this as `halted: gate`; that label is wrong for a unit the CLI cut —
  to be fixed. The owner has since switched accounts. v3 and AC-5 await a new approval.
