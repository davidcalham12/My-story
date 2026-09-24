---
id: SPEC-EXAM-005
title: Four optional items, added beside the system and never inside it
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-24: "te acuerdas de lo que era opcional si ya se puede empezar a trabajar hazlo pero no quiero que afecte el resultado que ya tenemos", then "ni que sea contraproducente"
approved_on: 2026-09-24
names_protected_value: none — nothing here touches the gate, an agent's tools line, the budget or the token ceiling
depends_on: the exam statement's "Opcional (suma nota)" list
---

# SPEC-EXAM-005 — The optionals, added without risk

## 1. What is wanted, and why

The mandatory work is done or in the owner's hands. The exam gives extra
credit for optional items. **The owner's condition is absolute:** nothing may
change the results already obtained, and nothing may be counterproductive.

So only items that are **purely additive** are taken:
- each lives in its own new files;
- none costs a model call;
- none changes a module the novel, the gate, the panel or the evals run
  through.

## 2. The four items

| item | the exam's optional | what it is | why it is safe |
|---|---|---|---|
| O1 | new prose linters | `backend/linters/repetition.py`: a sentence restated within a few sentences (the defect the judge found in ch05), and verbal tics repeated across a chapter. Report-only, run on the published book | stdlib, read-only, not wired into the gate; running it changes no score |
| O2 | MCP server to query and download novels | `mcp_server/`: FastMCP, read-only tools (list novels, a novel's versions, validators and cost, the PDF path) over the SQLite database opened read-only | own virtual environment, so the backend's dependencies are untouched; opens the database with `mode=ro`, so it cannot write |
| O3 | security analysis with agents | `docs/security-review.md`: an agent reviews the repository for prompt injection, secrets, path traversal and unsafe subprocess use, with each finding checked | documentation only |
| O4 | TLA+ of concurrency | `tla/TwoServers.tla`: two servers sharing one database, each sweeping "orphans" at start-up. TLC should find red-team case 13 (a live run marked halted) as a counterexample, then verify the fix of checking the process before sweeping | a new spec beside `Harness.tla`, which is untouched |

## 3. Out of scope

- Login.
- Write tools on the MCP server: a reader change spends money.
- The manual-editing linter.
- Further Lean invariants: elan is not installed.
- Wiring O1 into the gate. That would change how chapters are judged, which is
  a protected value and not an optional.

## 4. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | the backend and frontend suites pass unchanged after all four land | T |
| AC-2 | O1 flags the repeated sentence in ch05 of the example novel, and reports nothing on a clean fixture | T, D |
| AC-3 | O2's tools answer from the real database; a write through its connection fails | T |
| AC-4 | O3 lists each finding with its file, severity and whether it was confirmed | I |
| AC-5 | O4: TLC reports the counterexample for the unguarded sweep and passes with the guard | D |

## 5. Gaps this spec leaves

| gap | level | why accepted |
|---|---|---|
| O1 does not act on what it finds | incidental | acting would change the gate; that is a separate decision for the owner |
| O2 is local (stdio) and read-only | incidental | the exam asks to query and download; writing costs money |
| O4's guard is specified and model-checked, not implemented in `sweep_orphans` | important | implementing it touches the running backend the night before delivery; red-team case 13 stays declared |
