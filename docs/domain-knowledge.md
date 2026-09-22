# Domain knowledge

What is known about generating a novel this way. Two kinds of thing: what the
domain is like, and what eight runs of the previous implementation actually
showed. The second kind carries numbers, because a lesson without one is an
opinion.

`definitions.md` holds the vocabulary. This holds the findings.

---

## 1. The problem the architecture is for

A novel is longer than a context window, and the naive fix — feed the model
everything written so far — fails in three ways at once. Cost grows with the
square of the book. Quality degrades as the prompt fills. And the model begins to
imitate its own earlier prose rather than the outline, so chapter thirty reads
like a pastiche of chapter one.

NovaForge's answer: **the writer of a chapter never receives the prose of a
previous chapter.** It receives the Story Bible, its own outline entry, and a
bounded rolling summary. Chapter thirty-four's prompt is the same size as chapter
one's.

What that buys is a flat cost curve and a book that does not drift. What it costs
is that every fact a later chapter needs must have been written down somewhere
structured — and **anything nobody wrote down is gone**. The whole system is
built around that trade.

---

## 2. What eight runs showed

Eight novels across seven premises, three to eight chapters each. Every figure
below is measured.

### 2.1 The critics are the expensive half

Not the writing. Of one run's spend, the gate's critics accounted for roughly
half, and a chapter that needs a third attempt costs about as much in critics as
the first two attempts together. **Every chapter that passes earlier is real
money**, which is why the feedback sheet exists at all.

### 2.2 Cost is not what the token log says

| run | tokens priced (subagents) | what it actually cost |
|---|---|---|
| 8 chapters | **$6.21** | **$49.33** |
| 3 chapters | $1.09 | $8.24 |
| 3 chapters (halted) | — | $19.00 |

The log records what the agents consumed. It knows nothing about the
orchestrator's own turns, which carry the Bible, the drafts, the findings and the
sheets over and over — **and those are most of the bill**. A factor of eight,
consistently.

Two consequences, both in the v2 design. Cost is recorded **per call, with input
and output separated**, so it is exact rather than bounded. And the orchestrator
being Python rather than a model session is partly *why*: its turns stop being
billable tokens and become code.

### 2.3 Half the wall clock was the orchestrator working alone

One run logged `duration_ms` on every call: **nineteen subagent calls totalling
twelve and a half minutes, inside twenty-five minutes of wall clock.** The other
half was the orchestrator between them — reading a file back, counting words,
writing a critique, appending a log row, one turn at a time.

So the wall clock is a count of *rounds*, not of model time, and the cheap wins
are all about doing more per round: both critics in one message, all style passes
together, a chapter's bookkeeping alongside the next chapter's dispatch. In
Python these stop being a discipline and become a loop.

The Bible stages are the slowest calls (101s, 135s, 77s) and everything
downstream is written from them. They are the last place to economise.

### 2.4 The gate works, and here is the evidence

Of 24 chapters gated, **one never passed** — and it failed for a reason worth
knowing (§3.2). The rest passed by the third attempt, most by the second.

A run of eight chapters: all valid, seven on the first or second attempt, the
writer touching only what was cited in 7 of 7 measurable attempts, zero late
findings out of 22.

### 2.5 A model asked to concatenate will paraphrase

The manuscript is assembled in code. This is not caution: a model asked to join
approved chapters rewrote a sentence in the middle of text the gate had already
passed. Mechanical transformations go in code, always.

### 2.6 A model's report about itself is not evidence

A worldbuilder said it had written ~870 words; `wc -w` counted 948. A log claimed
a 72-minute run took 24, because the orchestrator estimated its timestamps rather
than reading a clock.

**Measure with a tool, and record where each figure came from.** This is the
origin of the provenance grades.

---

## 3. What the quality gate taught

The gate is the most developed part of the system and almost everything in it was
learned by getting it wrong first.

### 3.1 The four redraft rules

Each one made the gate weaker in a way that looked like it was working.

1. **Hand back the draft, not only the findings.** A redraft prompt carrying
   findings without the text they quote asks for "repair these and change nothing
   else" when there is nothing to change — so the writer starts a fresh chapter
   against findings quoting text no longer in it, and the rewrite can come back
   worse than what it replaced.
2. **Ask for substitutions, not a chapter.** `{find, replace, why}`, applied
   literally. Anything no finding names **cannot** change, and "was this
   addressed?" stops being a judgement: the quoted text is either still there or
   it is not.
3. **A critic that returns no usable verdict is excluded, never counted as a
   pass.** This once returned 10, which meant a malformed reply *silently passed*
   the draft — the one failure a quality gate must not have.
4. **Keep the best draft, not the last.** A chapter scoring 7 then 4 must ship
   the 7. A rewrite is not guaranteed to improve.

### 3.2 A chapter can be impossible as commissioned

The single most important finding. A run halted at chapter 3 after three attempts
and the patch — and the writer had done nothing wrong.

The chapter's beat 7 commissioned an event the world's rules did not admit. A
missing beat costs 3, so `outline` floors at 7 and `min` can never reach 8. The
science critic demanded one thing and the outline critic demanded its opposite,
each correct under its own reading, and no amount of redrafting could satisfy
both.

**Root cause, one layer further down than it first appeared:** the rule itself
read two ways. *"The line is permanent, and a correction is a new line"* — does a
correction line need its own confirmations, or carry the original's? Three
independent audits took one reading; the run's critic took the other. Both
defensible.

**An ambiguous rule does not fail loudly.** It fails as a disagreement nobody can
arbitrate, and it cost three attempts, a patch and a halted run to find. Hence
the FLOW-3 audit, which is asked to report *ambiguity* as a finding in its own
right — the only cheap moment to catch it.

### 3.3 Nothing audits the outline, and it is wrong often

In one eight-chapter run the outline was wrong on arithmetic **four times** —
"fourteen left" against a ledger giving thirteen, "six cycles left" where twelve
minus two minus two is eight. The writer's numbers overruled it each time.

The FLOW-3 audit costs **$0.07–$0.13** and found two defects the full five-critic
gate missed across three attempts and a patch: a beat having a field-team member
set a record reserved to a duty controller, and a callout firing at exactly
twenty minutes where the rule required *more than* twenty.

Cheap in an outline, expensive in a chapter.

**On a longer book it finds a different thing, and that changes what it is for.**
Run against an eight-chapter outline it reported **zero impossible beats and
three ambiguous rules**, all three load-bearing:

- *whose measurement is it* — the hand on the chain or the hand in the field
  book. Under one reading two figures three chapters apart must be identical,
  which the outline contradicts.
- *do repeats stabilise or never repeat again* — the critic proposed the first,
  and the orchestrator **OVERRULED it**: that reading contradicts a later beat
  and the chapter-4 plant, and *a replacement built on it would have written the
  error into six chapters by hand*.
- a third about what a constant guarantees.

So the audit was built to catch beats that break a rule, and what it actually
catches on a real book is **rules that read two ways**. That is the failure that
deadlocked a run, it cannot be found by re-reading a chapter, and it is the one
thing here that gets cheaper the earlier it is asked.

It is also the second time the arbitration has earned its place by refusing a
critic — §3.8 — and the first time refusing one saved six chapters rather than
one paragraph.

**And the file came back in a different shape from the last run's.** One wrote
`ambiguities`, the other `ambiguous_rules` with a `violations_note` beside an
empty `violations`. Nobody had said which, so both are correct and neither is
queryable — v1 wrote its critiques in three shapes for exactly this reason.
`SKILL.md` now states the shape.

### 3.4 Repairing one characteristic breaks another

Confirmed twice. In the halted run, the repair prompted by `science` took
`outline` from 10 to 7, `continuity` from 5 to 4, and **`science` itself** from 5
to 4 — the critic that commissioned the repair scored the result worse than what
it replaced.

The escalation in LOOP-003 §2 does not address this: the literal replacement
handed to attempt 3 is written by **one** critic, and applying it can break a
characteristic that was already passing. **Open. Not solved by the obvious fix**
— cross-checking with the other critics would not have saved that chapter,
because `outline` *did* review the replacement and reject it. That rejection is
the 10 → 7.

**A third case, on v2's first real run — and reading its own notes cuts it
down.** Chapter 1 of `lighthouse-keeper-ledger` scored `continuity` 7 then 10,
and `science` 10, then 4, then 10. It looks like a repair breaking a passing
characteristic, and the run's own record says it was **not only** that:

- the `continuity` repair was a four-word literal substitution, *stands twice in
  your hand* → *stands twice in that book*, confirmed applied by grep;
- the `science` 4 arrived on an iteration whose prompt the orchestrator had
  **enriched** — it added a canon note on who wrote each existing entry and asked
  the critic pointedly about the count. The critique says so in its `note`;
- the 10 that followed is a **rescore of the identical draft** against an amended
  R5. **No prose changed between the 4 and the 10.**

So the honest reading is *an ambiguity in the rules, surfaced by a sharper
prompt, closed in canon* — not a repair that damaged the text. The two are easy
to confuse from the score column alone, and only the notes tell them apart.

**What it does settle**, and this survives the correction: **re-scoring all five
characteristics every iteration is what made any of this visible.** `science` had
passed at 10 and would never have been asked again under a scheme that re-runs
only the failing critic; the ambiguity would have reached chapters 2 and 3
unnoticed. Five critic calls per iteration instead of one is what that costs.

**And the second lesson is about this document.** The cross-break was written up
here from the score column before the notes were read, and the notes changed what
it meant. **A score series is not a finding.** The critique's `note` field is the
evidence; the numbers are an index into it.

### 3.5 No critic grades prose, and it shows

Three visible defects shipped: a sentence duplicated verbatim, a timeline error
on screen, a paragraph stating the same fact twice. Each was **kept in by rule 2**
— "change only what was cited" forbids touching what no finding names, and no
finding named them because none of the five characteristics reads prose quality.

The guardrail and the goal are in tension, and there is a receipt.

**Two of those three are arithmetic, and nobody had tried.** A sentence repeated
word for word is equality; a paragraph echoing another's opening is a prefix.
Only the timeline error needs judgement. `check_prose` finds the first two at $0
and deterministically, where a sixth critic would have cost ~$0.07 a chapter and
never reproduced.

Run over the nine assembled books it found **23 defects in six of them**, and the
distribution is the interesting part:

| | v1 books | v2 book |
|---|---|---|
| heading with no blank line before it | **20**, across six books | **0** |
| paragraph echoing another's opening | 3, all in one degenerate early run | 0 |
| sentence repeated verbatim | 0 | 0 |

Every v1 book glues each chapter's heading to the previous chapter's last
sentence — the shell concatenated with a single newline. v2 assembles in
`publish/domain.py`, which joins with a blank line.

**So "assemble in code" bought a second thing nobody claimed.** It was adopted
because a model asked to concatenate paraphrased a sentence. It also happens to
concatenate correctly, and the difference sat in nine published files for weeks
with nothing looking at it.

### 3.6 Arithmetic cannot tell presentation from editing

Two style passes were discarded because the editor closed the space in `± 0.30`
→ `±0.30`, merging two tokens into one. `wc -w` sees a changed word count. The
rule fired correctly on a change that altered no word.

---

## 4. What writing the prose taught

### 4.1 The genre must come from the premise

Every agent once opened by declaring itself hard science fiction, and
`novel.tone` was fixed at `hard-scifi`. The premise was one line against nine
instructions saying otherwise, and it lost: a cyberpunk premise came back as an
engineering document with a bandwidth budget; a premise about a pop star trying
quesadillas came back unrecognisable, because the worldbuilder is obliged to
produce factions and a technology section whatever it is handed.

**No agent declares a genre.** It is read off the premise and recorded.

### 4.2 Rules should be story-shaped, not arithmetic-shaped

A world bible full of numbers gets the book *audited* rather than *read*. One run
spent an entire redraft cycle on whether 8,640 MB at 4 Mb/s takes twenty minutes
or four hours forty-eight — inside a chapter of 476 words.

A constraint whose main effect is to make someone check a division is a worse
rule than one about who is allowed in the room.

### 4.3 Canon must be sized to the book

No profile scaled the Story Bible: a three-chapter run of 1,400 words received
the same four factions, six technologies, eight rules, seven characters, twelve
timeline rows and five mysteries as a twelve-chapter novel. It then spent every
chapter introducing canon it had no room to use.

**That is what an incoherent short run is made of.** Every profile now states its
own counts: `tiny` gets two factions and three characters, `full` gets six and
ten.

### 4.4 Names are for the reader

A 1,400-word story introduced Nayla Wiryawan, Ilham Basri, Oskar Maas, Ratri
Sundoro and Juno Halim — a cast list a reader cannot hold. `names` defaults to
`familiar`: names pronounceable on sight and distinguishable at a glance. A real
person named in the premise keeps their real name.

### 4.5 A prompt asking for a quantity must say how to decide it

"Write three to five beats" invites a coin flip. Say what makes it three and what
makes it five. This applies to every range in every prompt.

---

## 5. What the tooling taught

- **Persist after every stage and every attempt.** State kept in memory is lost
  to a restart, and a run measured in hours will meet one.
- **Keep the rejected drafts.** "The writer changed only what was cited" can only
  be measured by diffing attempts. A run that overwrote them destroyed the
  evidence, and the instrument correctly reported *not measurable* rather than
  zero.
- **An unmeasurable field is not zero.** A run that destroyed its evidence and a
  run where nothing changed look identical in a number.
- **What the gate costs, measured on both sides.** Two three-chapter `tiny` runs
  on the same profile, each figure from Claude Code's own `result`:

  | | v1, `the-beginning-after-the-end` | v2, `lighthouse-keeper-ledger` |
  |---|---|---|
  | characteristics | 2 — `continuity`, `science` | **5** |
  | critic iterations | 6 | **36** |
  | rejected drafts kept | **0** | 7 |
  | outline audit before FLOW-4 | no | yes, with the rules amended |
  | orchestrator turns | 102 | 136 |
  | **cost** | **$7.45** | **$18.82** |

  **2.5× the money for 6× the judging**, and it is not the same test: the v1 run
  was judged by two characteristics, audited nothing before writing, and kept
  none of its rejected drafts — which is why "the writer changed only what was
  cited" could not be measured on it at all. That is what `source: pre-loop003`
  exists to say, and why those runs stay out of LOOP-003's statistics.

  **The cheap thing to notice: the price is sublinear in the judging.** Six times
  the critic iterations cost two and a half times the money, because the
  expensive part is the context every call carries, not the call.
- **A test that counts what is on disk is measuring the filesystem.** The v1
  importer's test asserted `len(reports) == 8` and held for weeks — until v2
  wrote its first novel into the same `output/` directory and it read nine. The
  count was never the claim; *those eight historical runs, by name* was. Worse
  than the red test: the importer had quietly filed a live v2 run as
  `pre-loop003`, contaminating exactly the statistics the `source` column exists
  to keep clean. **Found by a real run, not by review** — the first defect v2's
  own first run produced, and it was in the test suite.
- **Name artefacts by run.** Feedback sheets written to a flat path were silently
  overwritten by the next run. Recoverable from git that time, which is luck.
- **A contract nobody stated cannot be enforced.** A run wrote its critiques as a
  bare array instead of an object; the reader called `.iterations` on it and took
  the whole interface down. The shape had never been written down, so being
  strict about it was not rigour.
- **The instrument finds its own bugs when it is used.** A goal read 2/7 on a run
  that was 7/7, because it compared an attempt's diff against that attempt's own
  citations rather than the sheet's. The run reported the artefact instead of the
  number, which is the behaviour an instrument exists to make possible.

---

## 6. What remains unknown

Stated because a document that lists only findings reads as complete.

- **Whether the feedback sheet's wording matters.** The loop's premise is that
  some phrasings of "how it should read" produce a correction first time and
  others need the literal sentence. With one chapter reaching attempt 3, there is
  almost no signal. The format was promoted by the letter of the rule, on thin
  evidence, and that is recorded as thin.
- **Whether retrieval degrades the critics.** Passing the whole Bible is known to
  work. Retrieving fragments is cheaper and untested; the design keeps `science`
  and `outline` on whole inputs, because a rule not retrieved is a violation
  nobody looked for.
- **Whether a long book holds.** The longest run is eight chapters. The claim
  that chapter thirty-four reads like chapter one is architecture, not evidence.
- **What the knowledge-state tier is worth.** The ontology calls it the most
  common source of continuity errors. The table exists, empty. Nothing has
  measured what filling it would prevent.

---

## 7. What the checks taught about writing checks

Three defects found by instruments on the day they were written, each in the
instrument's own first run.

- **A check that answers when the record cannot is inventing its subject.** The
  gate-conformance audit reported six of the eight v1 runs as having promoted
  chapters below the threshold. Those runs had recorded no usable scores at all:
  the aggregate was `NULL`, and the check read absent as failure — **the exact
  mirror of reading absent as zero**, and no better. An unjudgeable attempt is
  counted apart now, and `unchecked` is a verdict distinct from `conformant`.
- **A rule cannot judge what predates it.** The same audit flagged v1 chapters
  that scored 10 as ones that should not have been retried. They were scored on
  two or three characteristics with `accept_with_warnings` available — a rule
  that no longer exists. Applying today's produces a confident answer about
  nothing, which is the category error the `source` column was added to prevent
  and which it then failed to prevent because nobody consulted it.
- **A test that counts files is measuring the filesystem.** `len(reports) == 8`
  held until v2 wrote its first novel into the same directory.

The pattern behind all three: **an instrument is most wrong in the direction of
having an opinion.** Each one preferred a confident answer to none, and in each
case none was correct.

### 7.1 Zero is a value, and this is the family the bugs come in

Four in one day, in four languages and four places, all the same mistake:

| where | what it said | what was true |
|---|---|---|
| `COALESCE(SUM(input_tokens),0)` | 0 tokens | **nobody reported any** |
| `COALESCE(SUM(cost_usd),0)` | $0.00 | nobody reported a cost |
| the conformance audit | six v1 runs breached the gate | their scores were **absent**, so the question has no answer |
| `warning.chapter ? … : ''` | this warning is about no chapter | **chapter 0**, which is the outline audit's slot |

The first two turn "unmeasured" into "measured as nothing". The third turns it
into "measured as wrong". The fourth is the same reflex in a language where `0`
is falsy. **The rule is not "report absent figures honestly" — it is that zero,
empty and absent are three different claims, and every language offers a cheap
way to collapse them.**

Two of the four were found an hour apart, in adjacent fields of the same payload.
That is why `test_absent_is_not_zero.py` exists: a rule everybody agrees with
erodes one `COALESCE` at a time.
