# Iterations — cause and effect

A log of decisions that changed after something was measured. Not a diary.

| when | what was observed | what changed | where |
|---|---|---|---|
| v1 | a critic's malformed reply scored 10 and passed a draft | an unusable verdict is excluded from the minimum, never counted | gate rule 3 |
| v1 | redrafts came back worse than the draft they replaced | the writer receives its own draft and returns literal find/replace substitutions; best draft kept, not last | gate rules 1, 2, 4 |
| v1 | a chapter failing three times entered the book "with warnings" | that exit removed; patch-then-halt | LOOP-003 |
| v1 stress run | a chapter could not pass: the outline commissioned what the rules forbade — root cause a rule that read two ways | the outline is audited against the rules before any chapter, and ambiguity is a finding | FLOW-3 audit |
| v2 | three visible prose defects shipped because no check read prose | a mechanical prose check (script) and a sixth characteristic, prose | SPEC-005, SPEC-006 |
| v2, 8-chapter run | a chapter was promoted at 5; the decision was a paragraph a model applied | the decision is code, promotion refuses unless it passes, and a conformance audit recomputes it after every run | SPEC-004 |
| 2026-09-23 audit | the context watcher reported "no data" for every subagent packet | the parser read the wrong key; the stream carried the figure all along — fixed, and the wrong claim kept as history | SPEC-010 W2 |
| 2026-09-23 | opening a finished run broke the panel | the stream ends with the run's detail | SPEC-010 W1 |
| 2026-09-23 | novels cost too much for the exam budget | the ten agents moved to Haiku | SPEC-011 |
| 2026-09-23 | the orchestrator on Haiku dispatched only generic subagents: the authority model vanished and no critique reached disk | the orchestrator stays on the session model; the finding is a red-team entry | spec §8 |
| 2026-09-23 | one orchestrator turn costs about 1 USD; a 15 USD ceiling would stop the example novel near chapter 3 | exam ceiling 60 USD; evals on 3 chapters | spec §8 |
| 2026-09-23 | five phases built in parallel worktrees wrote against the documented shape of the story-bible tables; the real ones differed in three places (fact id type, a matched column, places described by a note) | reconciled at integration; lesson: parallel work fails exactly where no phase can see the other — the contract between phases must be code, not prose | commit 854df0f |
| 2026-09-23 | TLC's first run of the harness spec reported a deadlock after 4 states: a rejected brief leads to Halted, which had no successor, and TLC stopped there — it was checking only that a brief can be rejected | an explicit terminal action; re-run: 18,253 distinct states, no error, four safety properties and termination hold | tla/README.md |
| pending | results of the example novel and the four evals | recorded here with numbers when they finish | evals/results.md |
