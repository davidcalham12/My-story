# Verification

> **Designing solutions with AI is an exercise in BEST EFFORT. The skill of a
> good AI solutions engineer lies in managing to build systems that are
> *reliable*.**

That epigraph governs this document, and the consequence is the whole point:
**reliability does not come from nothing failing. It comes from knowing exactly
where it can fail, what happens when it does, and how we would find out.**

A system with known, bounded gaps is reliable. A system with "no gaps" is a
system whose gaps nobody has looked for.

The brief already said *what cannot be measured is reported as unmeasurable,
never as zero*. This generalises it: **what is not verified is written down,
never omitted.** §3 is the most important section here, and it is the one
documents like this usually leave out.

---

## 1. How to read this

**Five classes of evidence**, strongest first. Always claim the strongest letter
that is *true*, never the strongest that is flattering:

| letter | class | what it means | how long it stays true |
|---|---|---|---|
| **T** | Test | executed; pass/fail decided by a machine | until someone deletes the test |
| **A** | Analysis | derived without executing: a type, an absent capability | while the code is that shape |
| **I** | Inspection | a person read it and confirmed it | of the version they read |
| **D** | Demonstration | shown working once, under observation | of that one run |
| **U** | Unverifiable | cannot be established by any of the above | — |

**Three levels of criticality**, and the level fixes the **minimum acceptable
letter**:

| level | meaning | minimum |
|---|---|---|
| **critical** | if it breaks, the project's thesis or its safety falls | **T or A.** Weaker is an accepted risk and gets a row in §3 |
| **important** | if it breaks, the result visibly worsens | **I** |
| **incidental** | if it breaks, it is fixed later without damage | anything, **U** included |

**Not everything deserves the same effort.** Knowing what to care about is half
the work, and the level column is where that decision gets written down instead
of implied.

Levels come from Annex D §2.1. A row may move level, but only in writing and
with the reason attached — two have, and they say so.

---

## 2. The guarantees

| # | promise | level | letter | minimum met? |
|---|---|---|---|---|
| G1 | the writer never receives a previous chapter's prose | **critical** | **A** | yes |
| G2 | the 100,000-token ceiling | important | **I** + **T** | yes |
| G3 | five characteristics, all at 8 or above | important | **T** / **D** | yes |
| G4 | `outline` scores 10 − 3·missing − 1·out-of-order | important | **T** / **D** | yes |
| G5 | three attempts, feedback escalating | important | **T** | yes |
| G6 | a failed chapter does not enter the book | **critical** | **D** | **no → §3.1** |
| G7 | the writer changes only what was cited | important | **T** / **D** | yes |
| G8 | a malformed verdict is excluded, never counted as a pass | **critical** | **T** | yes |
| G9 | only two agents write the Story Bible | **critical** | **A** | yes |
| G10 | the manuscript is assembled in code | important | **A** | yes |
| G11 | the outline is audited against `## Rules` before FLOW-4 | important | **D** | **no → §3.2** |
| G12 | every figure carries its provenance | important | **T** *(partial)* | yes |
| G13 | cost is not invented | important | **D** | **no → §3.3** |
| G14 | a run stops when it reaches its budget | **critical** | **T** | yes |
| G15 | no agent declares a genre | incidental | **A** | yes |
| G16 | no prompt asks a quantity without saying how to decide it | incidental | **I** | yes |
| G17 | there is no credential to leak | **critical** | **A** | yes |

**Three rows fail their own minimum**, and applying the criterion is what
exposed them. They are not deleted and they are not promoted — they become §3.1,
§3.2 and §3.3. That is the mechanism working as intended on its first use.

Two levels were moved from Annex D's assignment, in writing:

- **G8 raised to critical.** It is not in the brief's list because it was not
  known yet. A malformed verdict once returned **10** and silently passed a
  draft: that is the gate reporting a pass it never made, which is the thesis
  falling, not the result worsening.
- **G16 kept incidental**, as assigned, despite being Inspection. A bare range in
  a prompt produces a worse novel, not a false claim.

Status, 2026-09-22: **91 backend tests and 9 frontend tests, on the mock engine,
in CI, at $0.** The suite that carries these:

| file | holds |
|---|---|
| `test_agents_frontmatter.py` | G1, G9, G15 — the authority model, read off the front matter |
| `test_runner.py` | G2 layer 2, G13, G14, G17 — the stream, replayed |
| `test_gate.py` | G3, G4, G5, G7, G8 — the gate as arithmetic over values |
| `test_end_to_end.py` | all of them, in a whole run, including the halt |
| `test_import.py` | G12, G13 — the eight v1 runs and their recorded gaps |
| `test_outline_audit.py` | G11 — the commission checked before FLOW-4 |
| `test_vectors.py` | what retrieval may and may not be used for |
| `test_skill_contract.py` | §5 — that `SKILL.md`, `flow.yaml`, the config and the schema still describe one system |
| `test_api.py` | the HTTP edge and the SSE snapshot |

---

### G1 — The writer never receives a previous chapter's prose

**Critical · Class A.** Evidenced. **Upgraded back from T** by Annex C.

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

### G2 — The 100,000-token ceiling

**Important · Class I for layer 1, T for layer 2.** Neither is a reservation
taken in advance, and that is the honest consequence of Claude Code assembling
the prompts.

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

**Gaps: §3.4** (no reservation before the call) **and §3.5** (those packets
report zero, so layer 2 is armed and unexercised on the thing it exists for).

### G3 — A chapter passes only when all five characteristics reach 8

**Important · Class T** for the arithmetic, **D** for the whole.

**Method.** `min` over five scores against a threshold read from config, in
`chapters/domain.py`, which imports only the standard library and is tested
directly with no database, model or HTTP.

**Evidence.** Unit tests over the aggregation and the thresholds; the gate
decision row per attempt in the run record.

**Split, because the two halves are not the same claim:**

- *`length` and `chatter` reproduce* — **T**. Word count against a band; first
  line against `# Chapter`. Same input, same answer, always.
- *`continuity`, `science` and `outline` do not* — **D**. They are model
  judgements. The same draft can score 8 one run and 7 the next. **§3.6.**

So **"this run's gate produced these scores" is D**, evidenced by the recorded
decision. **"This text would pass any run" is U.** Those are different claims and
the system only ever supports the first.

### G4 — `outline` scores 10 − 3 per missing beat − 1 per beat out of order

**Important · Class T** for the arithmetic, **D** for the input.

**Method.** The formula is in `domain.py` and unit-tested. *Which* beats are
missing is a model's reading, and the critic is asked to show its arithmetic in
`notes` so the orchestrator can check the sum against the findings.

**Evidence.** Tests over the formula; the `notes` field, checkable against the
findings count on every scored attempt. Recomputing rather than believing is what
§3.8 rests on.

### G5 — Three attempts, with feedback that escalates

**Important · Class T** for the count and the escalation, evidenced in
`test_gate.py`; **U** for the claim it rests on.

**Method.** The attempt counter and the sheet level are code. Attempt 2 receives
the correction described; attempt 3 receives the critic's literal replacement.
Tested by driving a failing chapter through the mock engine.

**Evidence.** A test asserting no fourth attempt; a test asserting attempt 3's
sheet carries `Replacement:` and attempt 2's does not; every sheet kept at
`specs/loops/LOOP-003/sheets/<slug>/`.

**The guarantee, restated.** LOOP-003 §2 used to claim *a chapter comes out valid
by the third attempt*. That is false and there is a counterexample: a run halted
at chapter 3 having exhausted three attempts and the patch — not because the
writer underperformed, but because the outline commissioned an event the world's
rules did not admit, and the underlying rule read two ways.

It now reads: **a chapter that CAN pass will pass by the third attempt; a chapter
that cannot halts the run rather than entering the book.** The second half is
**D**, demonstrated at G6; the first half is **U**, because "can pass" is not
decidable in advance. Two honest claims where there was one false one.

### G6 — A failed chapter does not enter the book

**Critical · Class D** — demonstrated once, on real data. **Below its minimum:
§3.1.**

**Method.** `patch_then_halt`. Three failed attempts trigger the orchestrator
applying the critics' own replacements, arbitrating each first, then a rescore. A
chapter that still fails halts the run; no `chapters/chNN.md` is promoted.

**Evidence.** `output/night-dispatcher-recovered-climber/`: the run halted, there
is **no `ch03.md`**, the best draft sits unpromoted at `ch03.attempt3.md`, and
FLOW-5 and FLOW-6 never ran. That is the whole path exercised end to end, once.

**Why D and not T.** A test can prove the halt fires, and one should exist — that
is §3.1's remedy. Whether the arbitration refuses a *bad* replacement is a
judgement: in that run it refused two on arithmetic, which is the encouraging
case and not a general one.

### G7 — The writer changes only what was cited

**Important · Class T** for the mechanism, **D** for the outcome.

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
and the instrument reported *not measurable* rather than zero.
`keep_attempt_drafts` is now true and FLOW-4 writes `chNN.attemptK.md`.

### G8 — A malformed critic verdict is excluded, never counted as a pass

**Critical** (raised; see §2) **· Class T.** Evidenced in `test_gate.py`.

**Method.** An unparseable reply yields no score. It is excluded from the `min`,
recorded as unscored, and named in the gate row's note.

**Evidence.** A unit test feeding malformed JSON, asserting exclusion and not a
10. This once returned 10 — a malformed reply *silently passed* a draft — which
is why it has its own row rather than living inside G3, and why it is critical.

### G9 — The Story Bible is written by two agents only

**Critical · Class A.** Restored by Annex C, for the same reason as G1.

**Method.** Only `worldbuilder` and `character-architect` hold `Write` in their
front matter. The other seven cannot write a file at all — the capability is
absent, not merely unexercised.

**Evidence.** `test_agents_frontmatter.py::test_only_two_agents_can_write`
asserts exactly that set.

**It had dropped to I under D2**, when a Python service could have written to
`bible/` and nothing structural stopped it. Getting it back was not the point of
Annex C, but it is a second thing the reversal bought.

### G10 — The manuscript is assembled in code

**Important · Class A**

**Method.** Concatenation in `publish/domain.py`. No model call on that path.

**Evidence.** The absence of an LLM call in that module, checkable by reading it
and by a test that the publish path makes exactly one model call — the synopsis.

**Why it matters.** A model asked to concatenate approved chapters rewrote a
sentence in the middle of text the gate had already passed. It is the founding
case of §4.

### G11 — The outline is audited against `## Rules` before FLOW-4

**Important · Class D. Below its minimum: §3.2.**

**Method.** At FLOW-3, `science-critic` receives the outline entries and the
whole of `## Rules`, and reports beats that commission what the rules forbid —
and rules that read two ways.

**Evidence.** Run against a real outline with three different methods, scoring 4
or 5 and costing **$0.07–$0.13**, finding two defects the full five-critic gate
missed across three attempts and a patch.

**Second demonstration, on v2's own first real run** —
`output/lighthouse-keeper-ledger/critiques/outline.audit.json`. It reported two
defects and five ambiguous rules; the orchestrator upheld the two defects and
four of the ambiguities and **overruled the fifth**, which is the row that makes
the other six credible. One of them was load-bearing: under the rejected reading
of R5, a chapter's central act became impossible before it began. `world.md` was
amended by the only agent allowed to write it, the outline was reissued against
the amended rules, and **FLOW-4 did not start until both had landed** — the
failure mode this exists to prevent, prevented, in the run where it appeared.

**Not covered (U).** That it finds *every* impossible beat. On the outline that
halted a run, none of the three methods flagged the beat the run blamed — and
that turned out to be right, because the defect was an ambiguous rule rather than
an impossible beat. The audit is worth its cents and is not a proof of
possibility.

### G12 — Every figure carries its provenance

**Important · Class T** *(partial — the render half is untested)*

**Method.** Each number is typed with `measured` / `reported` / `reconstructed` /
`estimated` / `absent`. A `CHECK` constraint on the `calls` table refuses a row
without a grade. The interface renders the grade beside the figure.

**Evidence.** The schema, and tests that a figure cannot be persisted without a
grade. The render assertion is not written; the `(partial)` stays until it is.

**The rule this exists to hold: what cannot be measured is reported as
unmeasurable, never as zero.** A run that destroyed its evidence and a run where
nothing changed are identical in a number and must not be identical in a report.

### G13 — Cost is not invented

**Important · Class D**, and better than it was. **Below its minimum: §3.3.**

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
zero. The run total is solid; the split by agent is not yet. **§3.3.**

**Imported runs stay bounded**, `low / estimate / high`, graded `reconstructed`.
Any bounded figure of that shape is a **floor, not a range**, and the interface
says so where it shows one.

### G14 — A run stops when it reaches its budget

**Critical · Class T.** Evidenced in `test_runner.py`.

**Method.** `BudgetWatcher` adds up what the stream reports and stops the process
when the total crosses the ceiling. Tokens between `result` events are priced at
the **worst rate on file**, because a ceiling that under-estimates is not a
ceiling.

**Evidence.** A test that a run with a low ceiling halts and that its artefacts
remain queryable.

**Weaker than what it replaces, and the difference has a name.** A projection
refuses the call that would exceed; this lets that call finish and stops the
next. **The overshoot is bounded by one call rather than by zero** — §3.4, the
same gap as the ceiling, for the same reason.

**Why it halts rather than warns.** A ceiling that warns and continues is not a
ceiling. One v1 run reached $49.33 with nothing to stop it.

### G15 — No agent declares a genre

**Incidental · Class A**

**Method.** No agent prompt names a genre; `novel.tone` is null until the
orchestrator reads it off the premise and writes it into the run's config
snapshot.

**Evidence.** A grep over `backend/*/prompts/` for genre declarations, as a test.
The recorded tone in each run's snapshot, which shows what was decided rather
than what was assumed.

### G16 — No prompt asks for a quantity without saying how to decide it

**Incidental · Class I**

**Method.** Review. A range in a prompt must be accompanied by the rule that
picks a value within it.

**Evidence.** A reviewer, a date, the prompts read. This is Inspection because no
machine here can tell a justified range from a bare one, and claiming otherwise
would be the exact failure this document is written to avoid. Incidental is the
right level: a bare range makes a worse novel, not a false claim.

### G17 — There is no credential to leak

**Critical · Class A.** The strongest form this row has ever had, and by
subtraction.

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

---

## 3. Known gaps and accepted risks

**A gap listed here is an engineering decision. A gap not listed here is a
defect.** That is the whole distinction, and it is why this section is reviewed
on every spec rather than written once: `AGENTS.md` §3 requires each SPEC to list
the gaps it leaves, and they arrive here from there.

The first three rows exist because a guarantee sits below the minimum its level
demands. **They were generated by the rule, not noticed by a person.**

### 3.1 `patch_then_halt` is demonstrated, not tested — and G6 is critical

**What is not verified:** that the halt fires on every exhausted chapter, rather
than on the one where it was watched.
**Why accepted:** because **the decision is not in Python.** `patch_then_halt`
is a paragraph in `SKILL.md`; `chapters/domain.py` scores and aggregates but
never decides what happens after the third attempt. So this is §3.10 wearing a
different name, and it cannot be closed by writing a test — only by moving the
decision into code, which is a spec, not an afternoon.

*This row said the opposite when it was first written* — that the mock engine
could drive a chapter to three failures and close it. That was wrong: there is
no such loop in v2's Python, and checking before claiming is the point of the
document.
**Scope of damage:** the project's central safety claim. A chapter that failed
the gate entering the book is the one outcome the system exists to prevent.
**How we would find out:** by reading a book with a bad chapter in it — that is,
**too late**. There is no earlier signal.
**Reviewed by:** the next spec that touches `chapters/`, which should ask whether
the after-third-attempt decision belongs in `domain.py`. Until then this row
stands.

### 3.2 The outline audit is a judgement, and G11 is important

**What is not verified:** that the audit catches every impossible beat.
**Why accepted:** it is a model reading an outline against rules written in
prose. There is no stronger letter available at this price, and the price is
$0.07–$0.13.
**Scope of damage:** an impossible beat reaches FLOW-4 and kills the run three
attempts later — exactly what happened once, and what the audit exists to reduce.
It reduces; it does not prevent.
**How we would find out:** `halted: gate` on a chapter whose finding names a rule
the outline should never have commissioned against.
**Reviewed by:** every run that halts at the gate, by reading why.

### 3.3 Cost is measured per run and absent per agent, and G13 is important

**What is not verified:** the split of cost by agent. The run total is measured
and solid.
**Why accepted:** `task_progress.usage` reads zero in both recordings; the
quantity is not in the stream today.
**Scope of damage:** we cannot say which agent is expensive, only what the run
cost. No decision currently depends on the split.
**How we would find out:** the provenance grade reads `absent` on every per-agent
figure, on the screen, where the decision would be made.
**Reviewed by:** whoever first needs the split, and finds it labelled absent
rather than zero.

### 3.4 The ceiling cannot be reserved before a call

**What is not verified:** that no single call exceeds 100,000 tokens, or that no
run exceeds its budget by a cent.
**Why accepted:** without an API key Python does not assemble the prompts, so
there is nothing to count in advance (Annex C §3). The `wc -w` estimate in
`SKILL.md` is the first line, and it is Inspection.
**Scope of damage:** **bounded by one call, not by zero** — the call that crosses
finishes; the next does not start. Both the ceiling and the budget behave this
way.
**How we would find out:** `halted: context` or `halted: budget` in the log, with
the figure that crossed.
**Reviewed by:** nobody routinely, and that is accepted.

### 3.5 The packets the ceiling is about report zero

**What is not verified:** that any given agent packet was under the ceiling.
`task_progress.usage` reads **zero** in both recorded runs.
**Why accepted:** it is a property of the stream, not of our code. The watcher
reports `packet_series_provenance: absent` rather than reading zero as small.
**Scope of damage:** **layer 2 of G2 is armed and has never fired on the thing it
exists for.** It is a check in waiting, and calling it a working check would be
the exact dishonesty this document is against.
**How we would find out:** the provenance flips from `absent` to `measured` the
day those figures populate, and the halt becomes possible.
**Reviewed by:** every new recorded stream, automatically, by that flag.

### 3.6 Three of the five gate scores are a model's judgement

**What is not verified:** that a passing chapter passes again.
**Why accepted:** it is the nature of literary judgement. An arithmetic critic
for continuity would be a worse critic, not a more reliable one.
**Scope of damage:** a chapter accepted today might not be tomorrow. "It passed
the gate" is a statement about one run, never a property of the text.
**How we would find out:** the LOOP-003 instruments measure the spread between
runs.
**Reviewed by:** LOOP-003, on every run.

### 3.7 An agent cannot measure its own work

**What is not verified:** any figure an agent states about itself.
**Why accepted:** it cannot be fixed, only neutralised.
**Scope of damage:** a worldbuilder reported ~870 words where `wc -w` counted
948. Any self-declared quantity is that unreliable.
**How we would find out:** we do not rely on finding out — **no self-declaration
enters a decision.** The orchestrator measures with a tool, always.
**Reviewed by:** the rule in §4, permanently.

### 3.8 A critic can raise a false finding

**What is not verified:** that a finding describes a real defect.
**Why accepted:** it happened — a 3/10 from an arithmetic error the critic made
itself. The mitigation is cheaper than the cure.
**Scope of damage:** an unnecessary correction that damages correct text.
**How we would find out:** the orchestrator's arbitration, and
`late_findings.jsonl`. **Numeric findings are recomputed rather than believed.**
**Reviewed by:** the orchestrator, per finding.

### 3.9 Nobody measures the quality of the prose

**What is not verified:** whether the prose is any good. **Unverifiable with the
means available.** None of the five characteristics reads prose.
**Why accepted:** there is no instrument. Inventing a score would be worse than
the gap, because it would close the question.
**Scope of damage:** real and observed — a duplicated sentence, a timeline error
on screen, a paragraph stating the same fact twice. Three shipped defects, and
rule 2 is what kept them in, because no finding named them.
**How we would find out:** **no automatic signal. A reader, or nothing.**
**Reviewed by:** deferred to v2 as a possible sixth characteristic.

### 3.10 The procedure in `SKILL.md` cannot be tested at $0

**What is not verified:** that a change to the orchestration procedure is
correct, before a real run.
**Why accepted:** it is the price of having no API key. Everything Python does is
covered by a recorded stream; what Claude Code does is not.
**Scope of damage:** a broken procedure is found by spending money on a run.
**How we would find out:** the instruments' `--self-test`, and a real `tiny` run.
**Reviewed by:** whoever changes `SKILL.md`, before merging.

### 3.11 An interrupted run is not resumed

**What is not verified:** nothing — this one is absent by decision, and is here
because absent by decision is not the same as forgotten.
**Why accepted:** resume has its own failure modes and buys less than it costs.
**Scope of damage:** what was spent is lost. What was written stays readable.
**How we would find out:** `halted: process`.
**Reviewed by:** accepted for v1; the schema does not preclude adding it.

---

## 4. Code before agent

**When a check can be done by a script, it is done by a script.** An agent judges
only where judgement is needed. Every move from agent to code improves
reliability and cost at the same time, so each one is recorded here.

| check | was | is |
|---|---|---|
| chapter length | — | `wc -w`, by the orchestrator |
| chapter heading | — | a script |
| feedback-sheet validity | the orchestrator's judgement | `validate-sheet`, refusing before it is sent |
| assembling the book | an agent, which paraphrased | concatenation in the shell |
| applying corrections | the writer rewrote | literal `{find, replace}` substitutions |
| beats against the world's rules | nothing | a script audit before FLOW-4 (D25) |
| critics' arithmetic findings | believed | recomputed |

**Next candidates:** counting the summary's facts; detecting a `##` at the start
of a paragraph; checking canonical names.

**Standing rule, also in `AGENTS.md` §5:** before proposing an agent for a task,
say why a script will not do. If one will, it is a script.

---

## 5. What each validator stops propagating

A validator does not "check" something. It stops a failure reaching the next
step, and that is the sentence worth writing for each one.

| validator | stops |
|---|---|
| `validate-sheet` | an incomplete sheet, or one quoting prior prose, reaching the writer |
| the outline audit | an impossible beat reaching FLOW-4 and killing the run three attempts later |
| `measure` | an unmeasured claim reaching the documentation |
| the front-matter test | a change of tools reaching a run |
| `BudgetWatcher` | a run reaching $49 without anyone deciding it |
| `test_skill_contract.py` | the procedure and the contract diverging in silence |

**The last row was an aspiration until it was written, and it caught something on
its first run.** `SKILL.md` told the orchestrator that a verdict is `accept`,
`retry` or `accept_with_warnings`. The `attempts` table admits
`accept | retry | patched | halt` and **not** `accept_with_warnings`, which is
the exit `patch_then_halt` exists to abolish. An orchestrator obeying that
paragraph would have crashed on the insert, or — worse, if the insert had been
loose — filed a failed chapter as kept-with-warnings, which is the one outcome
G6 promises cannot happen. A second copy survived in §7's report line, in prose,
after the first had been corrected.

Nobody had read the two files side by side, and nothing made them. That is what
a validator is: not a check, a thing that makes the reading happen.

---

## 6. What changed since the last version

- **Annex D.** The epigraph, the criticality level on every row, §3, §4 and §5.
  The document had the mechanics and not the criterion. Applying the criterion
  immediately produced **three gaps nobody had written down** — G6, G11 and G13
  sit below the minimum their level demands — which is §3 earning its place on
  the day it was added.
- **Annex C.** G1 and G9 go back up to **A**: the guarantee is an absent
  capability again, not a type plus a test. G17 becomes **A by subtraction** —
  there is no credential to leak. G2 is rewritten as two layers, neither a
  reservation. G13 improves, because the whole run's cost now arrives measured.
- **§5 stopped being a list of intentions.** Writing the `SKILL.md` ↔ contract
  validator as a test found a live divergence in the verdict vocabulary the same
  hour — see §5. §3.1 was also corrected: it had claimed the halt was testable
  with the mock engine, and the decision is not in Python at all.
- **Four rows** lost a `(planned)` marker when their tests were written. **G12
  keeps a partial one**, and keeping it is the point.

---

## 7. What is not verified at all

Listed apart from §3 because these have no remedy to schedule — they are the edge
of what this arrangement can know. A document covering only what it verifies
reads as complete.

| claim | class | why |
|---|---|---|
| the prose is any good | **U** | §3.9 |
| voice, pacing, dialogue, originality hold | **U** | four of the ontology's ten dimensions, unchecked |
| repairing one characteristic does not break another | **U** | confirmed to happen twice; the obvious fix is known not to have saved the case on record |
| the book is worth reading | **U** | the ontology puts a human at this gate and is right to |
| chapter 34 reads like chapter 1 | **U** | architecture, not evidence. The longest run is eight chapters |
| the feedback sheet's wording matters | **U** | the loop's premise. One chapter has reached attempt 3; there is almost no signal |
| the log resists tampering | **U** | a record the orchestrator writes, not a hash chain |
| it runs unattended | **U** | one user, one run, a subprocess on this machine |
