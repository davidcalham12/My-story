# Trade-offs

Each design decision as a decision: the options, the criterion that chose, and the choice. Evidence is cited where a run decided it.

| # | decision | options | criterion | choice |
|---|---|---|---|---|
| 1 | Single agent or many | one model writes the novel · specialised agents with a gate | a chapter must be judged by something that did not write it; context must not grow with the book | **12 agents**: planner, writer, six-characteristic editor gate, judge, interviewer |
| 2 | Who orchestrates | Python calling an API · Claude Code running a skill | there is no API key; the only model access is the owner's Claude Code session | **Claude Code** runs the procedure; FastAPI launches, observes and archives |
| 3 | How the writer is kept from earlier prose | a rule in the prompt · a capability it lacks | a test can be deleted; a tool that cannot read cannot be talked into reading | the chapter writer holds only Glob (paths, never contents) |
| 4 | Story bible format | Markdown only · SQLite only · both | agents write prose-shaped canon; validators need queryable facts | agents write Markdown; a **script** ingests it into SQLite (facts, fact usage, characters, chronology) — script before agent |
| 5 | Pass rule | average · minimum | a chapter is as good as its worst failing | **minimum of six at 8 or above**, three escalating attempts, then patch-then-halt |
| 6 | Reading format | web with fact selection · interactive PDF | what can be finished by Friday while meeting the exam | **PDF** with index, character sheet, cover, and a "what changed" page on regeneration |
| 7 | Generation model | Opus/Sonnet · Haiku everywhere · Haiku for agents only | cost, and keeping the guarantees | **agents on Haiku, orchestrator on the session model**: with the orchestrator on Haiku a real run dispatched 58 generic subagents and none of the project's agents, so the writer held every tool (spec §8) |
| 8 | Budget | advisory · enforced | a ceiling that warns is not a ceiling | the profile's ceiling passed to the CLI; measured to bind (a 1.00 USD ceiling stopped a run in 6.6 s) |
| 9 | Evals size | five full novels · five short novels | cost (about 250 USD) and time against exercising every validator | **3-chapter evals**, full 10-chapter example novel; declared |
| 10 | Observability | live sink · post-hoc export | the harness has no hook into the orchestrator's turns; the run total is exact from Claude Code's result event | **post-hoc export** to Langfuse after each version; said so |
| 11 | Formal methods | full proofs · checks over concrete data · not at all | two days; the exam asks for checks over the real chronology | Lean over the concrete chronology and TLA+ on a 5-chapter model, **only if the tooling installs** |
| 12 | How to build in two days | one session in sequence · five subagents in parallel worktrees | wall clock | **parallel**; the cost was paid at integration (see iterations) |
