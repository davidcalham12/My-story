# Subagents and custom commands

## The twelve agents of the product
| agent | role | tools | model |
|---|---|---|---|
| interviewer | turns the buyer's answers into a brief; asks for what is missing | Glob | haiku |
| worldbuilder | world rules (writes the world file of the bible) | Read, Write | haiku |
| character-architect | cast, timeline, promises (writes the other bible files) | Read, Write | haiku |
| plot-architect | the outline (planner) | Glob | haiku |
| chapter-writer | one chapter, never seeing earlier prose (writer) | Glob | haiku |
| continuity, science, outline and prose critics | four model characteristics of the gate (editor) | Glob | haiku |
| style-editor | presentation only; may not change a word | Glob | haiku |
| publisher | back-cover synopsis | Glob | haiku |
| judge | six-criterion rubric on the finished book | Glob | haiku |

The orchestrator is Claude Code on the session model: a cheaper orchestrator stopped dispatching these agents (iterations).

## Subagents used to build it
| subagent | purpose | result |
|---|---|---|
| Explore, code audit | read the backend and frontend against the docs | four defects, SPEC-010, all fixed with tests |
| general-purpose, transcript digest | summarise the build session's 3,253 turns | decisions and open items recovered between sessions |
| five general-purpose subagents in isolated worktrees (E2–E6) | brief, story bible, policy and hooks, judge, PDF and versions in parallel | integrated in 854df0f; three contract mismatches found at merge |
