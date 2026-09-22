# Verification

Every guarantee this system claims, the class of evidence that supports it, the
method, and what that method leaves behind for someone else to check.

Produced with the `verification` skill. Classes are **T**est, **A**nalysis,
**I**nspection, **D**emonstration, **U**nverifiable, preferred in that order.

> **Read the letters as claims about evidence, not about effort.** A Test runs
> again tomorrow. An Analysis runs again when the code changes. An Inspection is
> true of the version somebody read. A Demonstration is true of one run that has
> already happened. Nothing here is promoted above what its evidence supports,
> and where a guarantee splits into a strong half and a weak one, both lines are
> written.

**Status, 2026-09-21.** The backend, the panel and the vector layer are built.
**93 backend tests and 9 frontend tests run on the mock engine, in CI, at $0.**
Rows still marked *(planned)* are the ones whose code exists but whose test does
not, and they are named rather than quietly assumed.

The suite that carries these guarantees:

| file | holds |
|---|---|
| `test_context.py` | G1 — the writer's packet, read as a type |
| `test_semaphore.py` | G2 — the ceiling under five parallel reservations |
| `test_gate.py` | G3, G4, G7, G8 — the gate as arithmetic over values |
| `test_end_to_end.py` | all of them, in a whole run, including the halt |
| `test_import.py` | G12, G13 — the eight v1 runs and their recorded gaps |
| `test_outline_audit.py` | G11 — the commission checked before FLOW-4 |
| `test_vectors.py` | what retrieval may and may not be used for |
| `test_api.py` | the HTTP edge and the SSE snapshot |

---

## G1 — The writer never receives a previous chapter's prose

**Class: A.** Evidenced. **Upgraded back from T** by Annex C.

**Method.** `chapter-writer` is a Claude Code subagent whose front matter reads
`tools: Glob`. `Glob` returns paths and cannot return contents. The prose is
therefore **unreachable** — the capability is absent, not merely unused.

**Evidence.** `backend/tests/test_agents_frontmatter.py` reads the front matter
of all nine agents and asserts each tool list exactly. It fails if anyone gives
the writer `Read`, `Grep`, `Bash`, `WebFetch` or `Agent`, and it fails if a
critic gains one, since a critic that could fetch its own context would hold the
very capability the writer is denied.

**Why this row moved twice, and why it matters.** Under D2 the orchestrator was
Python calling an API, so the guarantee became "the `ContextPacket` has no field
for it, and a test says so" — class **T**, true only while the test exists.
Annex C removed the API, and the guarantee went back to being a property of a
capability. **A test can be deleted; a tool that cannot read cannot be talked
into reading.**

**Not covered (U).** That the rolling summary contains no paraphrase of a
previous chapter's prose. It is a judgement about text and nothing here renders
it.

**Also held here:** retrieval. `commons/search` runs in the *orchestrator*
through `Bash(python *)`, and only the Bible, the outline and the summaries are
indexed. Indexing chapter prose would be this guarantee's leak arriving through
the back door, so the indexable list is a constant with a test around it.

## G2 — The 100,000-token ceiling

**Class: I for layer 1, T for layer 2.** Neither is a reservation taken in
advance, and that is the honest consequence of Claude Code assembling the
prompts.

**Layer 1 — a procedure (I).** `SKILL.md` has the orchestrator measure each
packet with `wc -w` before dispatching, convert at ~1.35 tokens per word, trim if
it is over, and decide how many critics can run at once. Evidence: the text of
`SKILL.md`, and a reviewer. It is a procedure a model follows, so it is
Inspection and nothing stronger.

**Layer 2 — a measurement (T).** `commons/runner/watch.py` reads the `usage` on
every stream event and stops the run when a subagent packet exceeds the ceiling.
Evidence: `test_runner.py`, against a real recorded stream.

**What replaying two real runs showed, and it changed this row.**

`input_tokens` alone is nearly always **2** — almost the whole context arrives
cached — so the true size is `input + cache_creation + cache_read`. A watcher
reading the first field only would report two-token calls and never trip. That
was found by replay, not by reading a document, and `test_runner.py` pins it.

The orchestrator's own turns run at a **median of 147,000 and a peak of 642,000**
tokens. **Halting on those would halt every run**, and the ceiling was never the
orchestrator's budget: it is about the packets the agents receive.

**Not covered, and this is the important line.** Those packets have a slot in the
stream — `task_progress.usage` — and in both recordings it reads **zero**. So the
quantity this guarantee is about is **not measurable from the stream today**. The
watcher reports `packet_series_provenance: absent` rather than treating zero as a
measurement. The check is in place and will fire the day those figures populate;
until then **layer 2 is armed and unexercised on the thing it is for**, which is
a weaker claim than it looks and is written down as such.

## G3 — A chapter passes only when all five characteristics reach 8

**Class: T** for the arithmetic, **D** for the whole. Evidenced.

**Method.** `min` over five scores against a threshold read from config, in
`chapters/domain.py`, which imports only the standard library and is tested
directly with no database, model or HTTP.

**Evidence.** Unit tests over the aggregation and the thresholds; the gate
decision row per attempt in the run record.

**Split, because the two halves are not the same claim:**

- *`length` and `chatter` reproduce* — **T**. Word count against a band; first
  line against `# Chapter`. Same input, same answer, always.
- *`continuity`, `science` and `outline` do not* — **D**. They are model
  judgements. The same draft can score 8 one run and 7 the next.

So **"this run's gate produced these scores" is D**, evidenced by the recorded
decision. **"This text would pass any run" is U.** Those are different claims and
the system only ever supports the first.

---

## G4 — `outline` scores 10 − 3 per missing beat − 1 per beat out of order

**Class: T** for the arithmetic, **D** for the input.

**Method.** The formula is in `domain.py` and unit-tested. *Which* beats are
missing is a model's reading, and the critic is asked to show its arithmetic in
`notes` so the orchestrator can check the sum against the findings.

**Evidence.** Tests over the formula; the `notes` field, checkable against the
findings count on every scored attempt.

---

## G5 — Three attempts, with feedback that escalates

**Class: T** for the count and the escalation, evidenced in `test_gate.py`;
**U** for the claim it rests on.

**Method.** The attempt counter and the sheet level are code. Attempt 2 receives
the correction described; attempt 3 receives the critic's literal replacement.
Tested by driving a failing chapter through the mock engine.

**Evidence.** A test asserting no fourth attempt; a test asserting attempt 3's
sheet carries `Replacement:` and attempt 2's does not; every sheet kept at
`specs/loops/LOOP-003/sheets/<slug>/`.

**The guarantee, restated.** LOOP-003 §2 used to claim *a chapter comes out
valid by the third attempt*. That is false and there is a counterexample: a run
halted at chapter 3 having exhausted three attempts and the patch — not because
the writer underperformed, but because the outline commissioned an event the
world's rules did not admit, and the underlying rule read two ways.

It now reads: **a chapter that CAN pass will pass by the third attempt; a chapter
that cannot halts the run rather than entering the book.** The second half is
**D**, demonstrated at G6 and testable; the first half is **U**, because "can
pass" is not decidable in advance. Two honest claims where there was one false
one, and it no longer rests on the FLOW-3 audit being exhaustive — which it
measurably is not.

---

## G6 — A failed chapter does not enter the book

**Class: D** — demonstrated once, on real data.

**Method.** `patch_then_halt`. Three failed attempts trigger the orchestrator
applying the critics' own replacements, arbitrating each first, then a rescore. A
chapter that still fails halts the run; no `chapters/chNN.md` is promoted.

**Evidence.** `output/night-dispatcher-recovered-climber/`: the run halted, there
is **no `ch03.md`**, the best draft sits unpromoted at `ch03.attempt3.md`, and
FLOW-5 and FLOW-6 never ran. That is the whole path exercised end to end, once.

**Why D and not T.** A test can prove the halt fires *(planned, and it should)*.
Whether the arbitration refuses a bad replacement is a judgement — in that run it
refused two on arithmetic, which is the encouraging case and not a general one.

---

## G7 — The writer changes only what was cited

**Class: T** for the mechanism, evidenced; **D** for the outcome.

**Method.** Redrafts return substitutions `{find, replace, why}` applied by
literal match. Anything no finding names is not touched, because the orchestrator
does not touch it. A `find` that does not match is skipped and counted, never
applied approximately.

**Evidence.** Unit tests over the patch applier, including the non-matching case.
Measured per attempt as lines touched against lines the sheet cited: **7/7 within
2× on one run, 3/3 on another** — the second under deliberately impossible
pressure, which is the more informative of the two.

**Prerequisite, and it was missing once.** This needs every attempt's draft kept
on disk. A run that overwrote its rejected drafts made the measure impossible,
and the instrument reported *not measurable* rather than zero. `keep_attempt_drafts`
is now true and FLOW-4 writes `chNN.attemptK.md`.

---

## G8 — A malformed critic verdict is excluded, never counted as a pass

**Class: T.** Evidenced in `test_gate.py`.

**Method.** An unparseable reply yields no score. It is excluded from the `min`,
recorded as unscored, and named in the gate row's note.

**Evidence.** A unit test feeding malformed JSON, asserting exclusion and not a
10. This once returned 10 — a malformed reply *silently passed* a draft — which
is why it has its own row rather than living inside G3.

---

## G9 — The Story Bible is written by two agents only

**Class: A.** Restored by Annex C, for the same reason as G1.

**Method.** Only `worldbuilder` and `character-architect` hold `Write` in their
front matter. The other seven cannot write a file at all — the capability is
absent, not merely unexercised.

**Evidence.** `test_agents_frontmatter.py::test_only_two_agents_can_write`
asserts exactly that set.

**It had dropped to I under D2**, when a Python service could have written to
`bible/` and nothing structural stopped it. Getting it back was not the point of
Annex C, but it is a second thing the reversal bought.

---

## G10 — The manuscript is assembled in code

**Class: A**

**Method.** Concatenation in `publish/domain.py`. No model call on that path.

**Evidence.** The absence of an LLM call in that module, checkable by reading it
and by a test that the publish path makes exactly one model call — the synopsis.

**Why it matters.** A model asked to concatenate approved chapters rewrote a
sentence in the middle of text the gate had already passed.

---

## G11 — The outline is audited against `## Rules` before FLOW-4

**Class: D**

**Method.** At FLOW-3, `science-critic` receives the outline entries and the
whole of `## Rules`, and reports beats that commission what the rules forbid —
and rules that read two ways.

**Evidence.** Run against a real outline with three different methods, scoring 4
or 5 and costing **$0.07–$0.13**, finding two defects the full five-critic gate
missed across three attempts and a patch.

**Not covered (U).** That it finds *every* impossible beat. On the outline that
halted a run, none of the three methods flagged the beat the run blamed — and
that turned out to be right, because the defect was an ambiguous rule rather than
an impossible beat. The audit is worth its cents and is not a proof of
possibility.

---

## G12 — Every figure carries its provenance

**Class: T** *(planned)*

**Method.** Each number is typed with `measured` / `reported` / `reconstructed` /
`estimated` / `absent`. The interface renders the grade beside the figure.

**Evidence.** Type tests that a figure cannot be constructed without a grade;
render tests that the grade appears.

**The rule this exists to hold: what cannot be measured is reported as
unmeasurable, never as zero.** A run that destroyed its evidence and a run where
nothing changed are identical in a number and must not be identical in a report.

---

## G13 — Cost is not invented

**Class: D**, and better than it was.

**Method.** Claude Code's final `result` event carries `total_cost_usd` for the
**whole run, orchestrator turns included**. It is written to
`output/<slug>/cost.json` and graded `measured`.

**Evidence.** `test_runner.py` asserts the figure is read from a real recorded
`result` ($19.00 on the run in the fixture). Three v1 runs carry their own
`cost.json` from the same source.

**Why this is the row Annex C improves most.** v1 priced the subagents' tokens
and knew nothing of the orchestrator's turns: **$6.21 estimated against $49.33
actual** on the same run. The difference was never a modelling error — it was a
quantity nobody could see. Now it arrives measured, from the only party that
knows it.

**Per-agent breakdown is weaker.** It comes from `task_progress.usage`, which
reads zero in both recordings, so those rows are graded `absent` rather than
zero. The run total is solid; the split by agent is not yet.

**Imported runs stay bounded**, `low / estimate / high`, graded `reconstructed`.
Any bounded figure of that shape is a **floor, not a range**, and the interface
says so where it shows one.

## G14 — A run stops when it reaches its budget

**Class: T.** Evidenced in `test_runner.py`.

**Method.** `BudgetWatcher` adds up what the stream reports and stops the
process when the total crosses the ceiling. Tokens between `result` events are
priced at the **worst rate on file**, because a ceiling that under-estimates is
not a ceiling.

**Weaker than what it replaces, and the difference has a name.** A projection
refuses the call that would exceed; this lets that call finish and stops the
next. **The overshoot is bounded by one call rather than by zero.**

**Evidence.** A test that a run with a low ceiling halts and that its artefacts
remain queryable.

**Why it halts rather than warns.** A ceiling that warns and continues is not a
ceiling. One v1 run reached $49.33 with nothing to stop it.

---

## G15 — No agent declares a genre

**Class: A**

**Method.** No agent prompt names a genre; `novel.tone` is null until the
orchestrator reads it off the premise and writes it into the run's config
snapshot.

**Evidence.** A grep over `backend/*/prompts/` for genre declarations, as a test.
The recorded tone in each run's snapshot, which shows what was decided rather
than what was assumed.

---

## G16 — No prompt asks for a quantity without saying how to decide it

**Class: I**

**Method.** Review. A range in a prompt must be accompanied by the rule that
picks a value within it.

**Evidence.** A reviewer, a date, the prompts read. This is Inspection because no
machine here can tell a justified range from a bare one, and claiming otherwise
would be the exact failure this document is written to avoid.

---

## G17 — There is no credential to leak

**Class: A.** The strongest form this row has ever had, and by subtraction.

**Method.** There is no Anthropic SDK in this project and nothing reads
`ANTHROPIC_API_KEY`. The only access to a model is the user's Claude Code session
on this machine. **A key that does not exist cannot be committed, logged or
pasted into a chat.**

**Evidence.** A grep over the tree for `anthropic` and `ANTHROPIC_API_KEY`
returns only the comments saying they are absent. `pyproject.toml` has no
Anthropic dependency.

**What still applies.** Anything reaching a subprocess goes on **stdin**, never
in argv: in v1 a task was passed as a command-line argument with `shell=True` on
Windows, which was command injection and shipped for about an hour.
`test_runner.py` asserts a hostile premise appears in the prompt and in no
element of the command.

## What is not verified at all

Listed because a verification document covering only what it verifies reads as
complete.

| claim | class | why |
|---|---|---|
| Prose is any good | **U** | No characteristic reads prose quality. Three visible defects shipped and rule 2 kept them in, because no finding named them. |
| Voice, pacing, dialogue, originality hold | **U** | Four of the ontology's ten quality dimensions, unchecked. |
| Repairing one characteristic does not break another | **U** | Confirmed to happen twice. The obvious fix — cross-checking the replacement — is known not to have saved the case on record. |
| The book is worth reading | **U** | The ontology puts a human at this gate and is right to. |
| Chapter 34 reads like chapter 1 | **U** | Architecture, not evidence. The longest run is eight chapters. |
| The feedback sheet's wording matters | **U** | The loop's premise. One chapter has reached attempt 3; there is almost no signal. |
| The log is trustworthy against tampering | **U** | A record the orchestrator writes, not a hash chain. Anyone who can edit it can edit it undetectably. |
| It runs unattended | **U** | Single user, queue of one, background task in one process. Not designed for it. |
