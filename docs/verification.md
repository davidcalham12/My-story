---
title: NovaForge — Verification
version: 3
status: draft
last_reviewed: 2026-09-22
applies_to: SPEC-007 (backend v1, approved) as built by PLAN-007 6.1–6.12, and the current orchestrator (SKILL.md, LOOP-003)
---

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

**Version 2 is a merge.** Two documents existed on 2026-09-22: one written
against SPEC-001 before the backend was built, and one grown alongside the build
and two real runs. They are unioned here. Where both classified the same
guarantee and disagreed, **the lower letter that is true of the built system
stands** — a merge never raises a letter — and §8 lists every row where the
spec-side document claimed more than the code can show, so a person can decide.

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

*The spec-side document called the third level "accessory". `definitions.md` §9
says `incidental`, and definitions win on vocabulary; the two mean the same.*

**Not everything deserves the same effort.** Knowing what to care about is half
the work, and the level column is where that decision gets written down instead
of implied.

Levels come from Annex D §2.1. A row may move level, but only in writing and
with the reason attached — two have, and they say so.

---

## 2. The guarantees

| # | promise | level | letter | minimum met? |
|---|---|---|---|---|
| G1 | the writer never receives a previous chapter's prose | **critical** | **A** + **T** | yes — but see §3.17 |
| G2 | the 100,000-token ceiling | important | **I** + **T** | yes |
| G3 | six characteristics, all at 8 or above | important | **T** / **D** | yes |
| G4 | `outline` scores 10 − 3·missing − 1·out-of-order | important | **T** / **D** | yes |
| G5 | three attempts, feedback escalating | important | **T** | yes |
| G6 | a failed chapter does not enter the book | **critical** | **T** for the rule, **D** for obeying it | **partly → §3.1** |
| G7 | the writer changes only what was cited | important | **T** / **D** | yes |
| G8 | a malformed verdict is excluded, never counted as a pass | **critical** | **T** | yes |
| G9 | only two agents write the Story Bible | **critical** | **A** + **T** | yes |
| G10 | the manuscript is assembled in code | important | **A** | yes |
| G11 | the outline is audited against `## Rules` before FLOW-4 | important | **D** | **no → §3.2** |
| G12 | every figure carries its provenance | important | **T** + **A** | yes |
| G13 | cost is not invented | important | **T** for the run, **absent** per agent | yes |
| G14 | a run stops when it reaches its budget | **critical** | **T** | yes |
| G15 | no agent declares a genre | incidental | **A** | yes |
| G16 | no prompt asks a quantity without saying how to decide it | incidental | **I** | yes |
| G17 | there is no credential to leak; nothing reaches a subprocess through argv | **critical** | **A** + **T** | yes |
| G18 | the pipeline has one implementation, `SKILL.md`; the backend re-implements no stage | important | **A** + **I** | yes |
| G19 | state is persisted as the stream reveals it, not at the end | important | **T** for every stream line (`events`), the stage and the calls; **not held** for the gate record until the archive | **partly → §3.14**, narrowed |
| G22 | the budget ceiling is the profile's figure, and one figure reaches both `--max-budget-usd` and the watcher | important | **T** | yes |
| G23 | a halt asked for by the user is recorded as the user's, through the same finish as a watcher trip | incidental | **T** | yes |
| G20 | a feedback sheet is complete and never quotes a previous chapter | important | **T** for the validator, **I** for its being run | yes |
| G21 | LOOP-003 §8.3's prohibitions hold: the threshold is 8, the attempts are three, the characteristics are the listed ones | incidental | **T** | yes |

**Three rows failed their own minimum** when the criterion was first applied, and
that is how they were found — not by a reader. They were neither deleted nor
promoted: they became §3.1, §3.2 and §3.3.

**One of the three has since been half repaired.** G6's *rule* is now code with an
exhaustive test (SPEC-004); obeying it is still a procedure. That is what a gap
row is for — it named the work, the work happened, and the row shrank to what is
actually left instead of disappearing.

Two levels were moved from Annex D's assignment, in writing:

- **G8 raised to critical.** It is not in the brief's list because it was not
  known yet. A malformed verdict once returned **10** and silently passed a
  draft: that is the gate reporting a pass it never made, which is the thesis
  falling, not the result worsening.
- **G16 kept incidental**, as assigned, despite being Inspection. A bare range in
  a prompt produces a worse novel, not a false claim.

Status, 2026-09-22 (after PLAN-007): **509 backend tests and 19 frontend tests, on a
recorded stream, in CI, at $0.** The suite that carries these:

| file | holds |
|---|---|
| `test_agents_frontmatter.py` | G1, G9, G15 — the authority model, read off the front matter |
| `test_runner.py` | G2 layer 2, G13, G14, G17 — the stream, replayed |
| `test_gate.py` | G3, G4, G5, G7, G8 — the gate as arithmetic over values |
| `test_decision.py` | G6's rule — what follows an attempt, exhaustively |
| `test_conformance.py` | G6's obedience, checked after the fact against the archive |
| `test_six_end_to_end.py` | a chapter stopped by `prose` alone, through the real archive path |
| `test_promote.py` | that a failing chapter cannot be promoted by the script that promotes |
| `test_summary_cap.py` | the rolling summary against its cap — the flat cost curve, measured |
| `test_rules_resolve.py` | that a cited rule is one the Bible declares |
| `test_promises.py` | that every promise names a chapter the book actually reaches |
| `test_checks.py` | that every instrument is reachable from a stage, and the procedure calls it |
| `test_report.py` | that an unarchived run reads as *unchecked*, never as sound |
| `test_prose.py` | §3.9's mechanical floor, measured over the nine shipped books |
| `test_names.py` | canonical names against the Bible — and the measurement that it has never fired |
| `test_api.py` | the HTTP edge, the SSE snapshot, and a whole run followed to completion |
| `test_import.py` | G12, G13 — the eight v1 runs and their recorded gaps |
| `test_vectors.py` | what retrieval may and may not be used for |
| `test_absent_is_not_zero.py` | G12's rule as a structural guard, not a memory |
| `test_instruments.py` | LOOP-003's two `--self-test`s, which ran nowhere automatic |
| `test_api_contract.py` | the payload the backend serves against the types the panel declares |
| `test_figures_in_docs.py` | every run cost quoted in the docs against the `cost.json` it came from |
| `test_formulas_agree.py` | the scoring formulas, wherever they are written, executed against the code |
| `test_verification_doc.py` | this document — that it still refers to things that exist |
| `test_architecture_doc.py` | `architecture.md` against reality: the `commons/` map, and §4's agent catalogue against their front matter |
| `test_skill_contract.py` | §5 — that `SKILL.md`, `flow.yaml`, the config and the schema still describe one system |
| `test_archive.py` | SPEC-003 — that a finished run's own record reaches the database |
| `Provenance.test.tsx`, `figures.test.ts` | G12's other half — the grade reaches the screen |

---

### G1 — The writer never receives a previous chapter's prose

**Critical · Class A.** Evidenced. **Upgraded back from T** by Annex C.

**Method.** `chapter-writer` is a Claude Code subagent whose front matter reads
`tools: Glob`. `Glob` returns paths and cannot return contents. The prose is
therefore **unreachable** — the capability is absent, not merely unused.

**Evidence.** `backend/tests/test_agents_frontmatter.py` reads the front matter
of **every agent file present** and asserts each tool list exactly — in both
directions, so a tenth agent cannot appear unnoticed. It fails if anyone gives
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

**Asserted from the file, not observed at runtime — §3.17.** The stream Claude
Code emits does not show a subagent's individual tool calls. So the guarantee is
that the *file* says `Glob`; that Claude Code honours it is a property of the
CLI, and if it ever stopped, nothing here would see it from the stream.

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

### G3 — A chapter passes only when all six characteristics reach 8

**Important · Class T** for the arithmetic, **D** for the whole.

**Method.** `min` over six scores against a threshold read from config, in
`chapters/domain.py`, which imports only the standard library and is tested
directly with no database, model or HTTP.

**Evidence.** Unit tests over the aggregation and the thresholds; the gate
decision row per attempt in the run record.

**Split, because the two halves are not the same claim:**

- *`length` and `chatter` reproduce* — **T**. Word count against a band; first
  line against `# Chapter`. Same input, same answer, always.
- *`prose`'s mechanical term reproduces* — **T**. It is a script's count, and
  it is weighted highest for exactly that reason.
- *`continuity`, `science`, `outline` and the judged half of `prose` do not* —
  **D**. They are model judgements. The same draft can score 8 one run and 7 the
  next. **§3.6.**

**SPEC-006 made this row weaker on purpose**, and the spec says so: three of five
were model judgements, and it is now four of six, the newest being the most
subjective.

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

**Critical · Class T for the rule, D for obeying it.** Split by SPEC-004, and
the split is the honest form of this row.

**Method.** `patch_then_halt`. Three failed attempts trigger the orchestrator
applying the critics' own replacements, arbitrating each first, then a rescore. A
chapter that still fails halts the run; no `chapters/chNN.md` is promoted.

**What changed, and why it is the most important thing in this document.** The
decision used to be a paragraph in `SKILL.md` that a model read and applied.
`chapters/domain.py::decide()` now answers `accept | retry | patch | halt` as
arithmetic, and `python -m backend.chapters.decide` makes it a script the
orchestrator runs. **The rule is no longer a judgement.**

`test_decision.py` asserts it **exhaustively**: every aggregate 0–9 at every
attempt number, patched and unpatched, never decides `accept` — 63 cases, because
at this size exhaustive is cheaper than clever. `None` — no usable verdict — never
accepts either; it is the absence of a score, not a low one, and it returned 10
once.

It was read at the worst possible moment: an hour spent, a run about to be thrown
away. That is exactly when *it is only just below* gets rationalised, and
`accept_with_warnings` is what rationalising looked like when it won.

**Evidence.** `output/night-dispatcher-recovered-climber/`: the run halted, there
is **no `ch03.md`**, the best draft sits unpromoted at `ch03.attempt3.md`, and
FLOW-5 and FLOW-6 never ran. That is the whole path exercised end to end, once.

**Why the second half is still D — and what now backs it.** The script decides;
the orchestrator acts. Whether it calls the script and does what it says is a
procedure, §3.12's limit, not a missing test.

**But disobedience is no longer invisible.** `conformance.audit()` recomputes the
decision at every archived attempt and reports the contradictions: a draft
promoted below the threshold, a verdict the rule would not give, a fourth
attempt, a chapter that failed without halting, two promotions for one chapter.
It ran clean over the first real run — **7 attempts, no breaches** — and that is a
measurement, not an assurance. `test_skill_contract.py` asserts `SKILL.md` instructs
the call and names all four answers, which is the strongest thing readable from
here.

And whether the arbitration refuses a *bad* replacement remains judgement: in the
halted run it refused two on arithmetic, which is the encouraging case and not a
general one.

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

**A second reason, measured afterwards and never anticipated.** `check_prose`
over the nine assembled books found **20 headings glued to the previous
chapter's last sentence — in six v1 books, and none in v2's.** v1 concatenated in
the shell with a single newline; `publish/domain.py` joins with a blank line.
Assembling in code was adopted because a model paraphrased. It also happens to
concatenate *correctly*, which nobody had claimed and nothing had checked.

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

**No test file, and that is correct rather than missing.** This table used to
name `test_outline_audit.py`. There is no such file and there should not be: the
audit is a model reading an outline against rules written in prose, so there is
nothing in Python to assert. The row promised evidence of a kind this guarantee
cannot have — which is the failure the document exists to prevent, committed by
the document.

**Not covered (U).** That it finds *every* impossible beat. On the outline that
halted a run, none of the three methods flagged the beat the run blamed — and
that turned out to be right, because the defect was an ambiguous rule rather than
an impossible beat. The audit is worth its cents and is not a proof of
possibility.

### G12 — Every figure carries its provenance

**Important · Class T** for storing it, **A** for showing it. **No longer
partial.**

**Method.** Each number is typed with `measured` / `reported` / `reconstructed` /
`estimated` / `absent`. A `CHECK` constraint on the `calls` table refuses a row
without a grade. The interface renders the grade beside the figure.

**Evidence, both halves.** The schema, and tests that a figure cannot be
persisted without a grade — **T**. `Provenance.test.tsx` renders all five grades
and asserts each mark, its name and its meaning reach the output, including that
`absent` reads *not the same as zero* — **T**. And `figures.test.ts` reads the
pages through Vite's glob and fails if any line rendering `money()` is not
accompanied by a `<Provenance>` — **A**, true while the source is that shape.

**What the pair still does not cover.** A figure printed by some future helper
that is not `money()`. That is the limit of reading source as text, and it is why
`money()` is the only sanctioned way a cost reaches the screen rather than one
way among several.

**The rule this exists to hold: what cannot be measured is reported as
unmeasurable, never as zero.** A run that destroyed its evidence and a run where
nothing changed are identical in a number and must not be identical in a report.

**And the rule was broken here, on this system's own main screen.** Every `calls`
row of the first real run stored `input_tokens` as `NULL` — correctly, because
the stream's per-agent packets report nothing. The reader wrapped the sum in
`COALESCE(..., 0)`, and the panel printed **"0 / 0 tokens" for a run that spent
$18.82**. The database told the truth, the query threw it away, and the screen
stated a measurement nobody made.

It was found by grepping the frontend for `.toLocaleString()` on a figure that
can be absent — not by a test, and not by anyone reading the page. `total_usd`
had already been fixed the same way an hour earlier and the token pair beside it
had been missed, which is the honest shape of this class of bug: **it is never
fixed once.**

So it is guarded rather than remembered. `test_absent_is_not_zero.py` fails on
any `COALESCE(SUM(...), 0)` in a read query, and on any `toFixed` or
`toLocaleString` outside `shared/lib/provenance.ts`, where the null check lives.
A rule everybody agrees with is exactly the kind that erodes one `COALESCE` at a
time.

### G13 — Cost is not invented

**Important · Class T** for the run's total, **absent** for the split by agent.
**Raised from D on 2026-09-22**, when the figure stopped living only in a file.

**Method.** Claude Code's final `result` event carries `total_cost_usd` for the
**whole run, orchestrator turns included**. It is written to
`output/<slug>/cost.json` and graded `measured`.

**Evidence.** `test_runner.py` asserts the figure is read from a real recorded
`result` ($19.00 on the run in the fixture). Three v1 runs carry their own
`cost.json` from the same source. **Two v2 runs are measured.** Three chapters, **$18.82** (136 turns, 56
minutes), against v1's **$7.45** for the same shape. Eight chapters, **$54.87**
(275 turns, 131 minutes, 11,133 words), against v1's **$49.33** for a comparable
book — **eleven per cent**, for roughly twice the judging and *fewer* turns. The
overhead is mostly fixed and a longer book amortises it. `domain-knowledge.md` §5 has the comparison and
why it is not like for like.

**It is now stored, not only written to disk** (SPEC-003). It sat in
`cost.json` while the API reported the sum over nine `calls` rows — a
reconstructed figure standing where a measured one existed, which is this row's
own rule inverted. `runs.cost_usd` carries it with its grade, and
`test_archive.py` asserts the reader prefers it.

**Why this is the row Annex C improves most.** v1 priced the subagents' tokens
and knew nothing of the orchestrator's turns: **$6.21 estimated against $49.33
actual** on the same run. The difference was never a modelling error — it was a
quantity nobody could see. Now it arrives measured, from the only party that
knows it.

**Why T now.** The figure is read from the `result` event, stored on the run with
its grade, and preferred over the sum of `calls` — and `test_archive.py` asserts
each of those against a real recorded run. It is no longer "a file exists with a
number in it".

**What T does not cover, and cannot.** That Claude Code's own accounting is
correct. It counted, we record what it counted, and the grade `measured` means
*counted by something that was there* — which is true and is not the same as
*audited*. Nothing here can check a bill against the meter that wrote it.

**Per-agent breakdown is `absent`.** It comes from `task_progress.usage`, which
reads zero in every recording, so those rows are graded `absent` rather than
zero. The run total is solid; the split by agent does not exist. **§3.3.**

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

**What still applies, and is T.** Anything reaching a subprocess goes on
**stdin**, never in argv: in v1 a task was passed as a command-line argument with
`shell=True` on Windows, which was command injection and shipped for about an
hour. `test_runner.py` asserts a hostile premise appears in the prompt and in no
element of the command, and that `shell` is never true.

**What the spec-side document claimed and the built system has no surface for.**
SPEC-001 requires every file-backed read endpoint to reject `..`, absolute paths
and symlinks outside `output/<slug>/`, with a property test. **The built backend
has no file-backed read endpoints** — four routes, all reading the database — so
the guarantee is true by absence. That is a conditional invariant of exactly the
kind §3 warns about: it stops being true the day the first such endpoint is
added, and it is written here so that day is noticed.

---

### G18 — The pipeline has one implementation, and the backend re-implements no stage

**Important · Class A + I.**

**Method.** `SKILL.md` is the procedure; Python launches it, watches it and
archives what it wrote. `backend/` holds no prompt files and no stage logic — the
stages are read from `flow.yaml` to *validate* the skill, never to execute
anything. `test_skill_contract.py` asserts the skill runs exactly the stages the
contract declares, which is the half of this a test can reach.

**Evidence.** The absence of a prompt directory and of any stage code under
`backend/`, checkable by reading; a reviewer, at each change.

**Why it matters.** Two implementations of one pipeline disagree within a month,
and the one that runs is not always the one that was reviewed.

### G19 — State is persisted as the stream reveals it, not at the end

**Important · Class T** for the stage, the slug and the `calls` rows, written on
every event; **not held** for the gate record, which is archived when the run
ends.

**Method.** `runs/service.py::_record` writes after every stream event, and
`test_api.py` asserts the SSE snapshot is built from the database, not from
memory. But attempts, scores, findings and sheets reach the database through
`archive_run`, at completion — so **a run that dies mid-flight leaves its stage
and its calls and none of its gate record.** That is §3.14, and it is the
difference between this row and the one the spec-side document wrote.

**What the spec asked for, and where it stands.** An `events` table holding every
raw stream line under a sequence number, and `Last-Event-ID` resume over it.
**Built, PLAN-007 6.2–6.7 — T.** `009_events.sql`; every parsed line lands in
`events` before anything is derived from it (`test_every_stream_line_is_in_events_with_a_dense_seq`);
every live SSE frame carries its `seq` as `id:` and `Last-Event-ID` replays the
rows after it, then goes live or ends (`test_last_event_id_replays_from_the_next_seq_then_goes_live`,
`test_last_event_id_beyond_the_end_yields_only_done`). The snapshot on connect
stays, so a client that sends no id still gets the whole state.

### G20 — A feedback sheet is complete and never quotes a previous chapter

**Important · Class T** for the validator, **I** for its being run before every
send.

**Method.** `validate-sheet` refuses a sheet missing a score, missing a finding
field, carrying an unfilled template slot, quoting a previous chapter, or reaching
attempt 3 without a literal replacement. Its `--self-test` runs in CI
(`test_instruments.py`). Whether the orchestrator runs it before every send is a
procedure in `SKILL.md`, which is §3.12's limit.

**Evidence.** The self-test, in CI; the `sheets.validated` column, which the
archive fills from the fact that the sheet reached the writer at all.

### G21 — LOOP-003 §8.3's prohibitions hold

**Incidental · Class T.**

**Method.** `test_skill_contract.py` pins the threshold at 8 against the config,
the attempts at three against the config's two revisions, the characteristic list
across `flow.yaml`, the config and `domain.py`, and `on_fail` at
`patch_then_halt` in all three. `test_formulas_agree.py` pins the gate constants
to one home in Python. Changing any of them without a spec turns CI red.

**Why incidental.** Breaking one of these is caught before anything runs. The
damage would be a wrong gate, which is visible; the row exists because
`AGENTS.md` §6 lists them as untouchable, and a rule that is only a rule is a
reminder.

**Note, SPEC-007 §12 — closed at PLAN-007 6.9.** The pin on the characteristic
*list* is Python-side; the Node instruments used to know five. `measure.mjs`
and `validate-sheet.mjs` now carry the six, the sheet template has a `Prose`
slot, and `test_instruments.py` holds all three to it.

### G22 — The budget ceiling is the profile's, and it is one figure

**Important · Class T.**

**Method.** `test_budget_source.py`: `ceiling_for` returns the profile's
`budget.max_cost_usd` when `NOVAFORGE_BUDGET` is unset and the smaller of the
two when it is set — the env is a brake, never a raise; the same number is in the
spawned argv as `--max-budget-usd` and in `BudgetWatcher.ceiling_usd`; an unset
env is `None`, not 25. `tiny` is pinned at 25.0 (PLAN-007 P-1).

**Why it exists.** Until PLAN-007 6.5 the watcher read `NOVAFORGE_BUDGET`
(default 25) and never looked at the profile, whose figure for `tiny` was 5.0 —
below the measured cost of a tiny run. Two numbers for one concept, and the run
obeyed neither knowingly. Whether the CLI flag *binds* under a subscription is
learned from the real runs and written at §3.19.

### G23 — A user's halt is the user's

**Incidental · Class T.**

**Method.** `test_halt_stops_the_process_and_marks_halted_user`,
`test_halt_keeps_what_was_persisted_readable`,
`test_halt_on_an_unknown_or_finished_run_is_404_or_409`. The halt sets the
reason before stopping the process, so a stream that ends because it was ended
is not filed as `process` (the orchestrator's death); the run goes through the
same `_finish` as a watcher trip — archive, warnings, the sentinel — so nothing
a `budget` halt does is skipped for a `user` one.

## 3. Known gaps and accepted risks

**A gap listed here is an engineering decision. A gap not listed here is a
defect.** That is the whole distinction, and it is why this section is reviewed
on every spec rather than written once: `AGENTS.md` §3 requires each SPEC to list
the gaps it leaves, and they arrive here from there.

The first three rows exist because a guarantee sits below the minimum its level
demands. **They were generated by the rule, not noticed by a person.**

### 3.1 `patch_then_halt` is demonstrated, not tested — and G6 is critical

**Narrowed by SPEC-004, not closed.** It used to read *the whole decision is a
paragraph a model applies*. The decision is now arithmetic with 63 exhaustive
cases behind it. What is left is smaller and still real.

**What is not verified:** that the orchestrator calls
`python -m backend.chapters.decide` and obeys the answer, on every chapter of
every run.
**Why accepted:** it is §3.12 — the procedure in `SKILL.md` cannot be tested at
$0, and there is no way to make a model's obedience a unit test. What could be
moved into code has been.
**Scope of damage:** the project's central safety claim, but **bounded by what
disobeying would take**: a chapter entering the book now needs the orchestrator
to ignore a script that printed `halt` and its reason, rather than to reason its
way through a paragraph. That is a sharper thing to do wrong.
**It has happened, and this row is no longer hypothetical.** On the
eight-chapter run, chapter 3 scored `continuity` 5 and was promoted: no third
attempt, no patch, no halt, and `ch03.md` byte-identical to the failing draft.
G6's central claim, violated on a real run. `domain-knowledge.md` §7.3 has it in
full.

**How we would find out:** `runs/conformance.py`, which recomputes what
`decide()` would have answered at every archived attempt and reports where the
record and the rule disagree. It found that chapter within minutes, twice, from
two independent rules — **and missed a second breach on the same run**, a chapter
promoted while `continuity` returned nothing usable, because its aggregate was 10
over the four critics that answered. Reading the minimum is not reading the
gate. **It runs the moment a run ends**, writes a
`gate-breach` warning per contradiction, and the run's page leads with the
answer.

*That line used to read "by reading a book with a bad chapter in it — too late,
and there is no earlier signal".* There is one now. It does not prevent a
disobeyed halt; it makes one visible in seconds instead of never, which is the
difference between an accepted risk and an undetectable one. **The row stays
critical** because detecting is not preventing.
**And the correct path is now the shorter one.** `backend/chapters/promote.py`
re-reads a chapter's critiques, recomputes the aggregate, asks `decide` and
copies the draft **only on `accept`** — refusing, non-zero, file untouched,
otherwise. Run against the chapter that actually shipped it answers
`promoted: false`.

It is not a guarantee and is not claimed as one: the orchestrator holds `Write`
and always will, because it writes every other file in the run. What it removes
is the version where nothing says no.

**Reviewed by:** every run, automatically, and `test_conformance.py` and
`test_promote.py` on every commit.

*This row claimed the opposite when first written* — that the mock engine could
close it in an afternoon. It could not: the decision was not in Python at all.
Checking before claiming is the point of the document.

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

### 3.3 Cost has no split by agent

**What is not verified:** the split of cost by agent. **The run total is now T**
— read from the `result` event, stored with its grade, preferred over the sum,
each asserted by a test — so this row has shrunk to the half that is genuinely
missing.
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

### 3.6 Four of the six gate scores are a model's judgement

**What is not verified:** that a passing chapter passes again.
**Why accepted:** it is the nature of literary judgement. An arithmetic critic
for continuity would be a worse critic, not a more reliable one. **SPEC-006 made
this worse deliberately** — four of six now, up from three of five — in exchange
for a gate that can stop a chapter for being badly written.
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

**Narrowed twice — by SPEC-005 with a script, then by SPEC-006 with a critic.**

**What is not verified:** whether the prose is any good. Still **U** for the
claim as stated, and the reason is now different: there *is* a judge, and its
judgement does not reproduce.
**Why accepted:** there is no instrument for judgement. Inventing a score would
be worse than the gap, because it would close the question.
**Scope of damage:** real and observed — a duplicated sentence, a timeline error
on screen, a paragraph stating the same fact twice. Three shipped defects, and
rule 2 is what kept them in, because no finding named them. **A fourth shipped on
2026-09-22**: a line quoted verbatim in the Bible, used word for word in chapters
2 and 7. Not the writer copying itself — it cannot see its own earlier prose — but
the Bible handing the same sentence to both. The isolation that prevents drift is
what prevents noticing.
**How we would find out:** **for the judgement, still a reader or nothing.** For
the mechanical part there is now a signal: `backend/chapters/prose.py` finds a
sentence repeated verbatim, a heading glued to the previous line and a paragraph
echoing another's opening — two of those three shipped defects, at $0, **T**, and
deterministic. A sixth critic would have cost $0.07 a chapter and been **D**
forever.
**And SPEC-006 put a judge on the rest.** `prose` is the sixth characteristic:
`prose-critic` returns quoted `major` and `minor` findings and **no score**, and
the orchestrator computes `10 − 3·mechanical − 2·major − 1·minor`. A `prose`
below 8 blocks a chapter through `min`, like any other.

**What that changes, and what it does not.** A chapter can now be stopped for
being badly written, which was the hole. What it cannot do is establish that a
chapter scoring 10 *is* well written — a 10 is the absence of named defects, and
absence of a finding is not a finding of quality. That is why this row stays
**U** rather than moving to D.

**What it cost, stated where it can be checked:** four of six characteristics are
now model judgements, up from three of five, and the new one is the most
subjective. `verification.md` G3 and §3.6 both say so, and SPEC-006's own "what
this costs" section was written before the code.
**Reviewed by:** the script, per chapter, before promotion — and its output is
written to `critiques/chNN.prose.json` and archived as warnings, **clean or
not**, because a check whose result exists only in a transcript cannot be read
afterwards and *"we ran it and it was fine"* is not a record. The judgement half
remains a decision nobody has taken.

### 3.10 A false `prose` finding damages a correct chapter

**What is not verified:** that a `prose` finding describes a real defect.
**Why accepted:** it is §3.8 with a larger blast radius, and SPEC-006 accepted it
in writing before the code was written.
**Scope of damage:** larger than any other critic's. Theirs correct a clause;
`prose`'s level-2 replacement is **a rewritten sentence**, handed to a writer
told to integrate it without judging it. Arbitration has already refused two such
replacements on arithmetic in one run, and one this week that would have written
an error into six chapters.
**How we would find out:** the orchestrator's arbitration, `late_findings.jsonl`,
and the quote rule — a finding that cannot be quoted is not counted, which is the
cheapest filter available.
**Reviewed by:** the orchestrator, per finding, with more care than before.

### 3.11 A run's procedure can change while it is running

**What is not verified:** that the `SKILL.md` a run finished under is the one it
started under.
**Why accepted:** it cannot be prevented without locking a file someone may
legitimately need to fix mid-run, and a lock that stops a repair is worse than a
warning that names a contamination.
**Scope of damage:** **it has already happened.** SPEC-006 added a sixth
characteristic during an eight-chapter run, so chapters 1–2 were judged by five
and the rest could be judged by six. Not a broken run — a run that is **not a
clean sample of either gate**, whose cost and pass rate compare to neither.
**How we would find out:** a SHA of `SKILL.md` is recorded at start and at end,
and a mismatch writes a `procedure-changed` warning on the run. A missing
fingerprint reads as absent, never as "unchanged".
**Reviewed by:** whoever reads the run, on the run's own page.

### 3.12 The procedure in `SKILL.md` cannot be tested at $0

**What is not verified:** that a change to the orchestration procedure produces
the right behaviour, before a real run.
**Why accepted:** it is the price of having no API key. Everything Python does is
covered by a recorded stream; what a model does with a paragraph is not.

**Smaller than it was, which is the only honest way to narrow it.** Seven
instruments now stand between a run and a defect, and remembering which at what
moment is exactly what failed: a chapter promoted at 5, a summary cap exceeded
five times, a verdict in a vocabulary the database rejects. `backend/checks.py`
maps stage → checks, so the procedure holds **one command per stage instead of
seven**, and `test_checks.py` fails if an instrument exists that no stage calls
or a stage the procedure never invokes.

**Narrower too, and worth saying how.** `test_skill_contract.py` now
checks statically that `SKILL.md`:

- runs exactly the stages `flow.yaml` declares, in that order;
- dispatches only agents that exist, and names each one;
- teaches the verdict vocabulary the database admits, and never the abolished
  one;
- defers the after-attempt decision to `decide` rather than restating it;
- agrees with the config on the threshold, the aggregate, the five
  characteristics, and three attempts being two revisions.

**What that leaves is the part that was always the real gap: whether a model
follows a procedure it can read.** No test reaches it. Every static check
above removes a way for the procedure to be *wrong on paper*; none of them
removes a way for it to be *ignored*.
**Scope of damage:** a procedure that is right on paper and not followed is
found by reading a run's artefacts, or by §3.1's conformance audit where the
gate is concerned.
**How we would find out:** the conformance audit, the instruments' `--self-test`,
and a real run.
**Reviewed by:** whoever changes `SKILL.md`, before merging.

### 3.13 The archive is as complete as the orchestrator's writing was

**What is not verified:** that every attempt the run made has a file. The
archiver reads `output/<slug>/`; it cannot see an attempt whose critique was
never written.
**Why accepted:** the alternative is the orchestrator calling Python per
attempt, which is a change to `SKILL.md` and therefore untestable at $0 (§3.12).
**Scope of damage:** a chapter whose files are missing is indistinguishable from
a chapter that was never attempted. **Bounded by being visible:** an attempt with
no critique on file is stored with `NULL` scores and a `run_warnings` row, never
as a pass.
**How we would find out:** `run_warnings` with `kind = 'archive'`, and the
`completeness` block on the run's page.
**Reviewed by:** whoever reads a run whose warnings list is not empty.

### 3.14 A run that dies mid-flight archives nothing

**What is not verified:** anything about a run whose process died before
`_finish` ran.
**Why accepted:** archiving at completion is what made SPEC-003 testable at all.
**Scope of damage:** the database has the run's row, its stage, its calls and —
since PLAN-007 6.4 — **every stream line it read** in `events`; what it lacks is
the archive (attempts, scores, sheets). **The files are all still there**, and
`archive_run` can be pointed at the directory by hand.
**How we would find out:** a run at `halted: process` with zero attempts.
**A restart used to make it worse.** SPEC-007 FR-RUN-7 asks that a run left
`running` be marked `halted: process` when the server starts. **Built at
PLAN-007 6.7** (`sweep_orphans`, called from `build_service`;
`test_a_run_left_running_is_marked_halted_process_on_startup`). Before it, a
server restarted mid-run left the row `running` forever.
**Reviewed by:** nobody routinely. It is a recovery, not a loss, and the
restart case no longer lies.

### 3.15 Two memory layers are built, tested, and not running

**What is not verified:** nothing about them is wrong — they are simply not
exercised by any run, so every claim about their behaviour is **A** from reading
the code and **T** from tests that call them directly. No run's behaviour
depends on either.

- **Structured summary facts.** `chapters/summary.py` projects the rolling
  summary from typed facts, dropping the lowest priority first so every
  `open-question` survives the cap. `save_facts` has **no caller**,
  `summary_facts` and `character_knowledge` are empty in every run, and the
  summary that reaches the next chapter is prose the orchestrator writes. What
  bounds it is `check_summary`, a word count — **not the survival ordering**.
- **Vector retrieval.** `commons/search` indexes the Bible, the outline and the
  summaries. **No run has ever populated `chunks`.** The critics receive whole
  inputs.

**Why accepted:** the conservative behaviour is the one running. Whole inputs to
a critic cost tokens and lose nothing; a prose summary the orchestrator wrote is
a worse projection than a typed one but not a wrong one. Switching either on is a
spec, not an afternoon.
**Scope of damage:** the architecture document described both as live until
2026-09-22, so **a reader planning against it was planning against a system that
does not exist**. That is the damage, and it has been done: the section is
rewritten and this row is why.
**How we would find out:** `SELECT COUNT(*) FROM summary_facts` and
`FROM chunks`. Both zero, on every run, today.
**Reviewed by:** whoever writes the spec that switches one on, and nobody until
then.

### 3.16 An interrupted run is not resumed

**What is not verified:** nothing — this one is absent by decision, and is here
because absent by decision is not the same as forgotten.
**Why accepted:** resume has its own failure modes and buys less than it costs.
**Scope of damage:** what was spent is lost. What was written stays readable.
**How we would find out:** `halted: process`.
**Reviewed by:** accepted for v1; the schema does not preclude adding it.

---

### 3.17 The writer's isolation is asserted from a file, not observed at runtime

**What is not verified:** that Claude Code actually denies `chapter-writer` every
tool but `Glob` during a run. The stream does not show a subagent's individual
tool calls, so the guarantee is that the *agent file* says `Glob` — G1 pins that
file with a test — and that the CLI honours it.
**Why accepted:** there is no runtime signal to read. `--allowedTools` and the
`tools:` line are the only structural controls this arrangement offers, and they
are the strongest thing the project has.
**Scope of damage:** the project's central claim. If the CLI ever ignored
`tools:`, prior prose would be reachable and **nothing here would see it from
the stream**.
**How we would find out:** any change to an agent file fails CI; a manual read of
one run's transcript, on every CLI upgrade, is the only check on the runtime.
**Reviewed by:** whoever upgrades the `claude` CLI, and nobody between upgrades.

### 3.18 Repairing one characteristic can break another

**What is not verified:** that a fix to one characteristic leaves the others
where they were.
**Why accepted:** the gate's design — five independent judges over one text —
makes it possible by construction, and preventing it would need a loop of its own.
**Scope of damage:** extra attempts, and occasionally `patch_then_halt`.
**Recorded twice**, in the halted v1 run, where a `science` repair took `outline`
from 10 to 7 and `science` itself from 5 to 4. A third case on v2's first run
looked identical in the score column and was not: the critique notes showed a
rule ambiguity closed in canon, with no prose changed. **A score series is not a
finding**; only the notes tell the two apart.
**How we would find out:** `gate_decisions` score deltas between attempts; the
critiques' `note` fields.
**Reviewed by:** LOOP-003, per run. A LOOP-004 candidate.

### 3.19 The backend writes no log file; the database is the log

**What is not verified:** SPEC-007 NFR-5's "logs are structured JSON". Nothing in
`backend/` imports `logging`; a malformed stream line becomes a `run_warnings`
row, every stream line an `events` row, every subagent call a `calls` row.
**Why accepted:** an operator asking "what happened" is answered by the database
and the artefacts beside the book (`cost.json`, `conformance.json`); a second
record in a log file would be a second place for the two to disagree
(PLAN-007 P-8).
**Scope of damage:** a failure *before* the database is reachable — a bad
`NOVAFORGE_DB` path, a migration error — is reported only on uvicorn's stderr.
**How we would find out:** `/api/health` says `db: false`; the process log says
why.
**Reviewed by:** whoever adds the first `logging` call, who should read this row
first.

### 3.21 Whether `--max-budget-usd` binds under a subscription is unknown

**What is not verified:** that the CLI flag the runner passes (G22) stops a
`claude -p` run at the figure, when the session is a subscription rather than
API credit.
**Why accepted:** the only way to learn it is a run that reaches its ceiling,
and the two Paso 10 runs ended at 65% and 50% of theirs; provoking it costs a
run. The watcher on the stream is the second line and is tested (G22).
**Scope of damage:** none while the watcher holds; the flag is the cheaper stop,
not the only one.
**How we would find out:** a run halted `budget` by the watcher whose `result`
shows the CLI let it past the figure — or the opposite.
**Reviewed by:** whoever first sees a `halted: budget` on a real run.

### 3.20 The import CLI on a fresh database labels v2 runs as v1 history

**What is not verified:** that `python -m backend.commons.db.import_v1` run
without slugs on an *empty* database imports only v1 runs. It imports every
`output/*/` with a `state.json` — and v2 runs write one too — as
`source = pre-loop003`. Found at Paso 10 on a scratch database: two v2 runs came
in as history.
**Why accepted:** in the deployed database the v2 runs are already rows, and
`test_a_live_v2_run_is_not_imported_as_history` holds that path; the fresh-DB
path is a one-time operation whose default the operator can override by naming
the eight slugs, as `test_import.py` does.
**Scope of damage:** a v2 run excluded from LOOP-003 statistics it belongs in,
and read as pre-loop history in the panel.
**How we would find out:** a `pre-loop003` row whose directory has
`conformance.json`, which only v2 writes.
**Closed by SPEC-008 / PLAN-008, 2026-09-23** —
`test_a_fresh_database_import_skips_v2_runs_by_their_marker`: a directory with
`conformance.json` (written by v2 and only by v2) is skipped and named on
stderr. Left: a v2 run that died before writing the marker (SPEC-008 §4).

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
| **what happens after an attempt** | **a paragraph the orchestrator applied** | **`decide()`, a script it runs and obeys (SPEC-004)** |
| **promoting a chapter into the book** | **a copy the orchestrator made** | **`promote`, which refuses unless the gate passed** |
| critics' arithmetic findings | believed | recomputed |
| **mechanical prose defects** | **nothing, and three shipped** | **`check_prose`, before promotion (SPEC-005)** |
| the `prose` score | three numbers copied by hand into a formula | `score_prose`, which runs the mechanical check itself |

| a heading glued to the previous line | nothing, and it is in every v1 book | `check_prose` (SPEC-005) |
| a name one letter off the Bible's | `continuity`, which reads for contradiction, not for typos | `names.check`, folded into the same script |
| the run's cost | estimated from the subagents' tokens — $6.21 against $49.33 | read from Claude Code's own `result`; exact |

**Next candidate:** counting the summary's facts — the one of the spec-side
document's three candidates not yet built. The other two on this list are
done — and the name check, **measured over nine books and 32 chapters, has never
fired.** That is written down rather than quietly deleted: it cost nothing, and
the alternative was believing the defect was out there because it sounded likely.

**Standing rule, also in `AGENTS.md` §5:** before proposing an agent for a task,
say why a script will not do. If one will, it is a script.

---

## 5. What each validator stops propagating

A validator does not "check" something. It stops a failure reaching the next
step, and that is the sentence worth writing for each one.

| validator | stops |
|---|---|
| `validate-sheet` | an incomplete sheet, or one quoting prior prose, reaching the writer — and its own `--self-test` now runs in CI, which it did not |
| the outline audit | an impossible beat reaching FLOW-4 and killing the run three attempts later |
| `measure` | an unmeasured claim reaching the documentation |
| the front-matter test | a change of tools reaching a run |
| `BudgetWatcher` | a run reaching $49 without anyone deciding it |
| `test_skill_contract.py` | the procedure and the contract diverging in silence |
| `archive_run` | a finished run leaving no record anyone can query |
| `decide` | a chapter below the threshold being talked into the book at the moment a run is about to be thrown away |
| `promote` | a failing draft reaching `chNN.md` by a one-line copy, which is how one did |
| `check_summary` | the one component that can grow with the book growing unwatched |
| `check_rules` | an arbitration record citing rules that do not exist |
| `check_promises` | a book ending before the chapter that owed the reader an answer |
| `test_api_contract.py` | the panel and the backend describing the same JSON differently, each passing its own checks |
| `test_formulas_agree.py` | a chapter being scored by one copy of a formula and judged by another |
| `conformance.audit` | a run disobeying its own gate and nobody finding out until someone reads the book |
| `check_prose` | a sentence the gate cannot see appearing twice in a chapter that passed — and, at FLOW-6, twice in a book |
| `ContextWatcher` | a subagent packet above 100,000 tokens reaching the next call — **armed and never fired**, because the packets report zero (§3.5) |
| stdin-only task passing | argv injection reaching the shell — recorded, ~1 h in production, in v1 |
| the import normaliser | an unknown critique shape becoming a blank screen — recorded in v1; it becomes a `run_completeness` gap instead |

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

## 6. Failure modes

Per component: what fails, its likely cause, how it is detected, what it does,
what mitigates it — and **the letter the mitigation has actually earned in the
built system**, which is not always the letter the spec assumed it would.

| # | failure | cause | detection | effect | mitigation | letter |
|---|---|---|---|---|---|---|
| F1 | `claude` not on PATH or not signed in | environment | `/health` reports `claude_on_path` | the run never starts | preflight in `/health`; no retry loop | **T** (`test_api.py`) |
| F2 | a malformed stream line | CLI change, partial write | `JSONDecodeError` | one event lost | logged and skipped in `runner/process.py`; the run continues | **A** — handled in code, no test injects one |
| F3 | the process ends without a `result` | crash, kill, network | EOF before `result` | no cost, incomplete run | `halted: process`; everything persisted stays readable | **A** — handled in `service.py`, no test drives it |
| F4 | the slug is never learned | the skill wrote elsewhere | no `output/<slug>/` path in the stream | artefacts unlinked from the run | the fallback slug from the premise, set at creation | **A** — the spec's `output/` scan and `slug_source = inferred` flag are **not built** |
| F5 | the context watcher trips on healthy runs | orchestrator turns run at 147k–642k tokens | it would have halted every run | wasted runs | halts only on *subagent* packets; calibrated on two recorded streams | **T** (`test_runner.py`) |
| F6 | the budget is exceeded | a long run, retries | summed cost crosses the ceiling | overspend | `BudgetWatcher` halts; overshoot bounded by one call (§3.4) | **T** |
| F7 | SQLite is locked | three critics writing at once | `database is locked` | lost rows | one connection, `check_same_thread=False`, a lock | **A** — no test provokes contention |
| F8 | `sqlite-vec` fails to load | Windows build, path | extension load error | no retrieval | `search` prints *retrieval unavailable* and exits distinctly; the critics receive whole inputs — which they do today regardless (§3.15) | **A** |
| F9 | the embedding model is unavailable | offline, blocked download | import error | as F8 | as F8 | **A** |
| F10 | an unknown critique shape on import | a run wrote its own | the normaliser finds no iterations | data loss | recorded as a `run_completeness` gap, never dropped; STRICT tables refused a string `iteration` on the first import | **T** (`test_import.py`) |
| F11 | path traversal on a read endpoint | crafted path | — | file disclosure | **not applicable: the backend has no file-backed read endpoints.** A conditional invariant (G17); the day one is added, this row needs a test | **A** by absence |
| F12 | command injection | a task in argv with a shell | `test_runner.py` | arbitrary command | no shell, explicit argv, prompt on stdin | **T** |
| F13 | BOM or mojibake in an agent file | PowerShell defaults | — | corrupted prompts | **unmitigated.** No check for a BOM exists anywhere | **U** |
| F14 | `SKILL.md` diverges from `flow.yaml` | an edit in one place | `test_skill_contract.py` | the gate rules differ from the contract | CI fails naming the lines — and it did, on its first run | **T** |
| F15 | a run orphaned by a server restart | restart | — | a row `running` forever; the panel shows a run still going | **unmitigated.** SPEC-001 FR-RUN-7 is not built (§3.14) | **U** |
| F16 | the SSE client disconnects | network | connection drop | missed events | a reconnect receives a fresh snapshot from the database | **T** for the snapshot; `Last-Event-ID` resume is **not built** |
| F17 | an impossible beat reaches FLOW-4 | outline contradicts `## Rules` | recorded: v1 stress ch3 beat 7 | `patch_then_halt`, run dies | the outline audit, a model, before FLOW-4 | **D** (§3.2) |
| F18 | two critics disagree about one passage | model variance | scores far apart | wrong fix or wrong halt | the orchestrator's arbitration; `late_findings` | **D** (§3.8) |
| F19 | a self-reported number used in a decision | convenience | code review | wrong gate outcome | no self-declaration enters a decision; `reported` provenance | **A** (§3.7) |
| F20 | prompt growth across chapters | feedback accumulating | `calls.input_tokens` per chapter not flat | the thesis broken silently | **cannot be detected today**: the per-agent packets report zero (§3.5). The spec's alert waits on the stream | **U** |

Three of twenty are **U** and two of those are unmitigated. They are here because
the spec-side document marked all twenty **T** before any of it was built, and a
table of twenty T's is what a reader believes.

## 7. Mapping to the methodology catalogue

Which of the catalogue's methods this project uses — **as built**, not as
planned — and which it does not, with why.

### 7.1 Artefact level (code)

| method | used? | how, here |
|---|---|---|
| type checking | **frontend yes, backend no** | `tsc --strict` in CI; Python is annotated but no `mypy` runs |
| static analysis / SAST | no | no `ruff`, no `bandit` configured. The spec-side document said both were in use; neither was |
| symbolic execution | no | disproportionate |
| formal verification | no | disproportionate |
| unit and integration testing | yes | 509 backend tests and 19 frontend (2026-09-22, after PLAN-007), over a recorded stream, at $0, on every push |
| property-based testing | **no library** | where the space is small it is enumerated instead: every aggregate at every attempt for `decide` (63 cases), every coefficient combination for the prose formula (64) |
| mutation testing | no | not yet |
| contract testing | yes | `test_api_contract.py` (backend payload ↔ panel types), `test_skill_contract.py` (procedure ↔ contract), `test_formulas_agree.py` (formula ↔ code) |

### 7.2 Process level (agents)

| method | used? | how, here |
|---|---|---|
| runtime observability | **partly** | one `calls` row per subagent dispatch; the whole run's cost from `result`, measured. Per-agent token usage is **absent** — the stream reports zero (§3.5). No Langfuse |
| evals | narrow | LOOP-003's `measure --self-test` over a committed run, in CI |
| sandboxed execution | partial | `--allowedTools`, no shell, each agent's `tools:` line — **asserted from files, not observed at runtime** (§3.17) |
| guardrails | yes | the gate, `decide`, `promote`, both watchers, `validate-sheet`, the four `check_*` instruments |
| human-in-the-loop | yes | spec and plan approval written into file headers; every **I** row |
| multi-agent verification | yes | four model critics over one draft, and an orchestrator that has overruled them on arithmetic |
| CI/CD gates | yes | three jobs: backend, frontend, instruments |
| progressive rollout | no | one user, one machine |
| red-teaming | small | a hostile premise against argv injection; a stress profile built to force `patch_then_halt` |
| model checking | no | the run state machine is small enough to enumerate |

## 8. History

| version | date | what changed |
|---|---|---|
| 4 | 2026-09-23 | **SPEC-008.** §3.20 closed with its test; the archive knows `prose_check.json` (`test_the_prose_check_file_is_known_and_not_warned_about`), so a run archives with no noise warnings. Tests 506 → 509. |
| 3 | 2026-09-22 | **After PLAN-007 6.1–6.12** (SPEC-007 approved, built on `backend-v1`). G19 raised to **T for the stream** on the evidence of `test_events.py` and the SSE tests; G22 and G23 added; §3.14 narrowed (the restart case is closed, the mid-flight archive is not); G21's note closed (the Node instruments carry six); §3.19, §3.20 and §3.21 opened. **No letter was raised without a test named beside it.** Tests 449 → 506. What the two real runs of Paso 10 showed is in §3.19's neighbour rows and in `domain-knowledge.md` §8. |
| 2 | 2026-09-22 | **Merged.** The spec-side v1 (18 guarantees, 10 gaps, 20 failure modes) unioned with the build-side document (17 guarantees, 16 gaps). Added G18–G21, §3.17, §3.18, §6 failure modes, §7 catalogue, this header. **No letter was raised.** Kept lower where the two disagreed: v1 G4 "T" → **D for obedience** (disobeyed twice on a real run); v1 G9 "T" → **A** (the byte-for-byte fixture test does not exist); v1 G10 "T" → **D** (the `outline_audit` CLI was never built; the audit is a model); v1 G18 "T" → **split** (no `events` table; the gate record is archived at the end); v1 G16's path property test → **not applicable** (no file-backed endpoints). §7 rewritten to what runs: no `mypy`, `ruff`, `bandit` or `hypothesis`. **Candidates for a person to raise**, with their evidence: G1 and G9 also have tests (`test_agents_frontmatter.py`); G17's argv half has one (`test_runner.py`). |
| 1 | 2026-09-22 | the spec-side draft: 18 guarantees, 10 gaps, 20 failure modes, catalogue mapping; and, separately, the build-side document that grew with SPEC-001…006 and two real runs |

### 8.1 What changed on the build side, before the merge

- **Annex D.** The epigraph, the criticality level on every row, §3, §4 and §5.
  The document had the mechanics and not the criterion. Applying the criterion
  immediately produced **three gaps nobody had written down** — G6, G11 and G13
  sit below the minimum their level demands — which is §3 earning its place on
  the day it was added.
- **Annex C.** G1 and G9 go back up to **A**: the guarantee is an absent
  capability again, not a type plus a test. G17 becomes **A by subtraction** —
  there is no credential to leak. G2 is rewritten as two layers, neither a
  reservation. G13 improves, because the whole run's cost now arrives measured.
- **SPEC-003.** v2's first real run finished with a complete novel and an
  **empty archive** — three chapters, seven drafts, four sheets on disk and zero
  rows in `attempts`, `scores`, `findings`, `gate_decisions` and `sheets`.
  `save_attempt`, `save_gate` and `save_sheet` existed and were called by
  nothing. G13 gains the stored measured total; §3 gains two rows.
- **SPEC-006.** A sixth characteristic, `prose`, which can stop a chapter for
  being badly written — the hole three shipped defects went through. It is the
  first change that makes this document's claims **weaker on purpose**: four of
  six characteristics are now model judgements, up from three of five. The spec
  wrote down what that costs before the code existed, and §3.10 is the new gap it
  opens.
- **SPEC-005.** The mechanical floor under §3.9, built first, because
  `AGENTS.md` §5 requires answering why a script will not do before proposing an
  agent. It answered for two of the three defects; SPEC-006 is what was left.
- **SPEC-004.** The decision after an attempt moved from a paragraph in
  `SKILL.md` into `decide()`, with an exhaustive test and a script the
  orchestrator runs. **G6, the only critical guarantee below its minimum, is
  now T for the rule** — and honestly still D for obeying it, which is what §3.1
  has been narrowed to say.
- **§5 stopped being a list of intentions.** Writing the `SKILL.md` ↔ contract
  validator as a test found a live divergence in the verdict vocabulary the same
  hour — see §5. §3.1 was also corrected: it had claimed the halt was testable
  with the mock engine, and the decision is not in Python at all.
- **G12 lost its `(partial)`.** The grade was refused by the database and
  unchecked on the screen; both halves now have tests, and the one that reads
  source as text is marked **A** rather than dressed up as **T**.
- **Four rows** lost a `(planned)` marker when their tests were written. No row
  carries one now — which is a fact about this date, not a property of the
  document.

---

## 9. What is not verified at all

Listed apart from §3 because these have no remedy to schedule — they are the edge
of what this arrangement can know. A document covering only what it verifies
reads as complete.

| claim | class | why |
|---|---|---|
| the prose is any good | **U** | §3.9 |
| voice, pacing, dialogue, originality hold | **U** | four of the ontology's ten dimensions, unchecked |
| repairing one characteristic does not break another | **U** | §3.18 — confirmed twice; a third case looked identical in the score column and was a rule ambiguity closed in canon |
| the book is worth reading | **U** | the ontology puts a human at this gate and is right to |
| chapter 34 reads like chapter 1 | **U** | and now for a better reason: **there is data and it does not settle it.** On the eight-chapter run, chapters 3–8 all failed their first attempt on `continuity` and chapters 1–2 did not; the three-chapter run scored its *last* chapter best. `domain-knowledge.md` §3.3b |
| the feedback sheet's wording matters | **U** | the loop's premise. One chapter has reached attempt 3; there is almost no signal |
| the log resists tampering | **U** | a record the orchestrator writes, not a hash chain |
| it runs unattended | **U** | one user, one run, a subprocess on this machine |
