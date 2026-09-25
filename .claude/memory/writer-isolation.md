---
name: writer-isolation
description: chapter-writer holds only Glob, so earlier chapters' prose is unreachable; never widen it
type: project
---

The chapter writer never receives an earlier chapter's prose. This is held by a
capability, not a prompt: `.claude/agents/chapter-writer.md` declares `tools: Glob`,
and Glob returns paths, not contents. Everything a chapter knows of the ones before
arrives through the capped rolling summary.

**Why:** it is the project's one hard guarantee (CLAUDE.md, "The one idea"); a test
pins every agent's `tools:` line (AGENTS.md §6). On Haiku as orchestrator the
project's agents stopped being dispatched and the guarantee vanished (run
`phantom-station`, docs/iterations.md).

**How to apply:** never add a tool to `chapter-writer`; the Python chapter loop
(SPEC-EXAM-006) builds packets in code and a sentinel test proves no earlier prose
enters them. See [[orchestrator-cost]].
