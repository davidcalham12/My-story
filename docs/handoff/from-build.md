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
