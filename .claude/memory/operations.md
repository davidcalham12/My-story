---
name: operations
description: operating rules each learned from a run that went wrong
type: feedback
---

- **One server per database.** A second server's startup sweep marked a live run
  `halted=process` (red-team 13). Check no orchestrator is alive before a real run
  (red-team 9).
- **The prompt goes on stdin, never in argv** (command injection, 2026-09-21).
- **The whole suite green, alone, before every push** — not while another agent runs
  tests in the same checkout; use a git worktree for parallel work.
- **`pytest -v -p no:cacheprovider`** when `-q` crashes; a test that left a thread
  writing after the database closed was the cause of the segfaults (fixed in SPEC-007).
- **A run started outside the server** (a resume by hand) writes its stream to
  `logs/`; backfill it (`python -m backend.costs.backfill`) so its cost reaches `changes`.

**Why:** each line cost a run, a paid process or a broken push. See [[approvals]].
