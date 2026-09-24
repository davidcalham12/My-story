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
| bible-critic | continuity, science and outline in one reading (SPEC-EXAM-004): two model critics per attempt instead of four, for runs after 2026-09-24 | Glob | haiku |
| style-editor | presentation only; may not change a word | Glob | haiku |
| publisher | back-cover synopsis | Glob | haiku |
| judge | six-criterion rubric on the finished book | Glob | haiku |

The orchestrator is Claude Code. The example novel ran it on the session model; from 2026-09-24 the `exam` and `eval` profiles run it on Sonnet (spec §8). Never Haiku: on Haiku it stopped dispatching these agents (iterations). The table has thirteen rows because `bible-critic` joined the twelve.

## Subagents used to build it
| subagent | purpose | result |
|---|---|---|
| Explore, code audit | read the backend and frontend against the docs | four defects, SPEC-010, all fixed with tests |
| general-purpose, transcript digest | summarise the build session's 3,253 turns | decisions and open items recovered between sessions |
| five general-purpose subagents in isolated worktrees (E2–E6) | brief, story bible, policy and hooks, judge, PDF and versions in parallel | integrated in 854df0f; three contract mismatches found at merge |


## Custom commands (`.claude/commands/`)

Four slash commands, each a procedure that was run by hand often enough to be
worth writing down. **Three of them spend nothing; the one that does says so and
waits for the owner.**

| command | purpose | result it exists for |
|---|---|---|
| `/status` | what is running, what it spent, whether another run is safe | red-team cases 9 and 13: orphan orchestrators billing, and a stale `halted` row on a live run |
| `/reader-change <slug> <fact> "<wording>"` | the reader-change demo: impact first, then only the impacted chapters through the gate, as a new version | exam evidence 3; pins the procedure the book was written with, so v3 reads like v2 |
| `/publish <run-dir> [--next "<reason>"]` | personalise, ingest, print, record every validator, ask the judge | the three published novels that had no characters and no judge row until this was one step |
| `/run-eval` | rebuild `evals/results.md` from code and `validations` | the eval table stays a view of the database, never a document typed by hand |
