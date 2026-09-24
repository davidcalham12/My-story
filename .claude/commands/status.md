---
description: What is running, what it has spent, and whether it is safe to launch another run
---

Report the state of storyMaker before anything else is launched. Read, do not
change anything.

1. **Is an orchestrator alive?** List processes whose command line contains
   `claude -p`. A stopped server once left three running, billing for novels
   nobody asked for (`docs/red-team-log.md`, case 9). If one is alive, say which
   run it belongs to and stop here: the queue is one.
2. **The runs:** `GET http://localhost:8000/api/runs` — for each, its title,
   stage and `halted`. A `halted: process` on a run whose orchestrator is alive
   is the stale row of red-team case 13, not a stopped run.
3. **What each finished run cost:** `output/<slug>/cost.json`, with its
   provenance. `absent` is said as absent, never as zero.
4. **What was published:** `GET /api/runs/{id}/versions` — versions, and
   whether each has its PDF and its HTML.

End with one line: safe to launch, or why not.
