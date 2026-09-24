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
