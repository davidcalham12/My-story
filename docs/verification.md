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
| G3 | six characteristics, all at 8 or above | important | **T** / **D** | yes |
| G4 | `outline` scores 10 − 3·missing − 1·out-of-order | important | **T** / **D** | yes |
| G5 | three attempts, feedback escalating | important | **T** | yes |
| G6 | a failed chapter does not enter the book | **critical** | **T** for the rule, **D** for obeying it | **partly → §3.1** |
| G7 | the writer changes only what was cited | important | **T** / **D** | yes |
| G8 | a malformed verdict is excluded, never counted as a pass | **critical** | **T** | yes |
| G9 | only two agents write the Story Bible | **critical** | **A** | yes |
| G10 | the manuscript is assembled in code | important | **A** | yes |
| G11 | the outline is audited against `## Rules` before FLOW-4 | important | **D** | **no → §3.2** |
| G12 | every figure carries its provenance | important | **T** + **A** | yes |
| G13 | cost is not invented | important | **D** | **no → §3.3** |
| G14 | a run stops when it reaches its budget | **critical** | **T** | yes |
| G15 | no agent declares a genre | incidental | **A** | yes |
| G16 | no prompt asks a quantity without saying how to decide it | incidental | **I** | yes |
| G17 | there is no credential to leak | **critical** | **A** | yes |

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

Status, 2026-09-22: **342 backend tests and 19 frontend tests, on the mock engine,
in CI, at $0.** The suite that carries these:

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

**Method.** `min` over five scores against a threshold read from config, in
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

**Important · Class D**, and better than it was. **Below its minimum: §3.3.**

**Method.** Claude Code's final `result` event carries `total_cost_usd` for the
**whole run, orchestrator turns included**. It is written to
`output/<slug>/cost.json` and graded `measured`.

**Evidence.** `test_runner.py` asserts the figure is read from a real recorded
`result` ($19.00 on the run in the fixture). Three v1 runs carry their own
`cost.json` from the same source. **v2's first real run measured $18.82** —
136 turns, 41 subagent dispatches, 56 minutes — against **$7.45** for v1's
three-chapter `tiny` run, which judged by two characteristics instead of five and
audited nothing before writing. `domain-knowledge.md` §5 has the comparison and
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
two independent rules. **It runs the moment a run ends**, writes a
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
rule 2 is what kept them in, because no finding named them.
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

**Narrower than it was, and worth saying how.** `test_skill_contract.py` now
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
**Scope of damage:** the database has the run's row and nothing else. **The files
are all still there**, and `archive_run` can be pointed at the directory by hand.
**How we would find out:** a run at `halted: process` with zero attempts.
**Reviewed by:** nobody routinely. It is a recovery, not a loss.

### 3.15 An interrupted run is not resumed

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
| **what happens after an attempt** | **a paragraph the orchestrator applied** | **`decide()`, a script it runs and obeys (SPEC-004)** |
| **promoting a chapter into the book** | **a copy the orchestrator made** | **`promote`, which refuses unless the gate passed** |
| critics' arithmetic findings | believed | recomputed |
| **mechanical prose defects** | **nothing, and three shipped** | **`check_prose`, before promotion (SPEC-005)** |
| the `prose` score | three numbers copied by hand into a formula | `score_prose`, which runs the mechanical check itself |

| a heading glued to the previous line | nothing, and it is in every v1 book | `check_prose` (SPEC-005) |
| a name one letter off the Bible's | `continuity`, which reads for contradiction, not for typos | `names.check`, folded into the same script |

**Next candidate:** counting the summary's facts. The other two on this list are
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
| `test_api_contract.py` | the panel and the backend describing the same JSON differently, each passing its own checks |
| `test_formulas_agree.py` | a chapter being scored by one copy of a formula and judged by another |
| `conformance.audit` | a run disobeying its own gate and nobody finding out until someone reads the book |
| `check_prose` | a sentence the gate cannot see appearing twice in a chapter that passed |

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

## 7. What is not verified at all

Listed apart from §3 because these have no remedy to schedule — they are the edge
of what this arrangement can know. A document covering only what it verifies
reads as complete.

| claim | class | why |
|---|---|---|
| the prose is any good | **U** | §3.9 |
| voice, pacing, dialogue, originality hold | **U** | four of the ontology's ten dimensions, unchecked |
| repairing one characteristic does not break another | **U** | confirmed twice. A third case on v2's first run turned out, on reading the critique notes, to be a rule ambiguity surfaced by a sharper prompt and closed in canon — the score column alone could not tell the two apart |
| the book is worth reading | **U** | the ontology puts a human at this gate and is right to |
| chapter 34 reads like chapter 1 | **U** | architecture, not evidence. The longest run is eight chapters |
| the feedback sheet's wording matters | **U** | the loop's premise. One chapter has reached attempt 3; there is almost no signal |
| the log resists tampering | **U** | a record the orchestrator writes, not a hash chain |
| it runs unattended | **U** | one user, one run, a subprocess on this machine |
