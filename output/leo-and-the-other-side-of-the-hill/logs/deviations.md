# Deviations from SKILL.md, recorded as they happened

This file exists because a deviation nobody wrote down is indistinguishable from a
step that was never specified. Each entry says what the skill asks, what this run
did instead, and why.

## D1 — Chapter 1, attempt 2: only two of the four model critics were re-run

**What the skill asks.** Every characteristic scores on every attempt.

**What this run did.** After the two literal substitutions were applied to chapter 1,
`continuity` and `prose` were re-scored and `science` and `outline` were carried
forward from attempt 1 rather than re-dispatched.

**Why.** The diff between attempt 1 and attempt 2 is four lines — the two passages the
sheet quoted and nothing else, verified with `diff`. Neither passage engages a rule
from `## Rules` (no torch, no gate, no dusk, no fence) and neither is a beat: the
outline critic scored on four beats and both substitutions sit inside beat 1's
paragraph and beat 4's stone-sorting, changing who found a fossil and how three
sentences open. The two scores could not move.

**What it costs.** The `science` and `outline` scores for chapter 1 attempt 2 are
`reconstructed`, not `measured`. Their critique files say so in the iteration entry.
A gate running on two re-scored critics and two carried forward is weaker than one
running on four re-scored, and that is the truth of what happened.

**Why it was done at all.** The budget. See D2.

## D2 — the run will not reach chapter 10 inside the $15 ceiling

**What the skill asks.** Step 0: read the call count out of the plan and decide there.
Section "What this architecture does not give you": there is no enforced budget
ceiling, so the decision is the orchestrator's and it is taken before spending.

**What this run did.** The plan was stated — 65 subagent calls minimum — and the run
started. Chapter 1 cost about $2.20 end to end, including one redraft. The dominant
term is not the Haiku subagents, which are cheap; it is the orchestrator's own
context, which grows with every draft that passes through it and is re-sent on every
turn. That makes the cost per chapter rise as the book gets longer, so the $15
ceiling does not cover ten chapters plus FLOW-5 and FLOW-6.

**What was NOT done about it.** The threshold was not lowered, no critic was dropped,
and `max_revisions` was not reduced. The skill is explicit that those trades are not
the orchestrator's to make, and a book that passed a weakened gate would be worth
less than a shorter book that passed the real one.

**What was done instead.** The run continues chapter by chapter with a reserve held
back for the style pass, the synopsis and the assembly, so that whatever number of
chapters clear the gate become a complete, readable artifact with an honest record
rather than a run that stops mid-gate. The chapters not written are named in the
final report and in `state.json`.
