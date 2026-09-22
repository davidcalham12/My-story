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

## 2. What the eight v1 runs showed

Eight v1 novels across seven premises, three to eight chapters each. Every figure
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
critic — `verification.md` §3.8 — and the first time refusing one saved six chapters rather than
one paragraph.

**And the file came back in a different shape from the last run's.** One wrote
`ambiguities`, the other `ambiguous_rules` with a `violations_note` beside an
empty `violations`. Nobody had said which, so both are correct and neither is
queryable — v1 wrote its critiques in three shapes for exactly this reason.
`SKILL.md` now states the shape.

### 3.3a What actually blocks a chapter, measured over two v2 runs

Eleven chapters, 22 scored attempts, **12 below the threshold**. What was worst
each time:

| characteristic | times it was the minimum on a failing attempt |
|---|---|
| `continuity` | **9** |
| `science` | 3 |
| `outline`, `length`, `chatter` | **0** |

**The gate is, in practice, a continuity gate.** Three of its five
characteristics have never once been the thing that stopped a chapter. That is
not an argument for removing them — `outline` exists because a beautifully
consistent chapter about something else used to pass cleanly, and `chatter`
catches a failure mode no rubric anticipates. It is an argument for knowing where
the work is: **the writer's isolation is paid for in continuity, and that is the
bill arriving.**

### 3.3b Does a later chapter get harder? The data says yes and no

The eight-chapter run looks like a clean answer. Chapters 1 and 2 passed on the
first attempt; **chapters 3 through 8 all failed it, every one on `continuity`,
and every one needed exactly two attempts.** A step, not a slope, and it lands
exactly where the rolling summary first has to compress rather than restate.

**The three-chapter run does not reproduce it.** Its first-attempt `continuity`
went 7, 3, **10** — the last chapter was its best.

So the honest statement is the one this document has always made about chapter
thirty-four, now for a better reason: **there is data and the data does not settle
it.** One run of eight is one run. What the two agree on is §3.3a — where the
failures are — and not that they worsen with position.

Two things worth doing before believing either shape: a second eight-chapter run,
and per-chapter packet sizes, which the stream does not currently report
(`verification.md` §3.5).

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

### 3.4a A sentence repeated across chapters, and why it had to happen

The eight-chapter book repeats a line word for word in **chapters 2 and 7**:

> "That's what's in your hand, sir," Fowler said. "I'll not say it for you."

**It is not the writer copying itself — it cannot be.** The writer never receives
a previous chapter's prose; that is the architecture. The line is in
`bible/characters.md`, verbatim, as Nat Fowler's `Speaks.` example. Two chapters
five apart were each handed the Bible, each wanted that character's voice, and
each used the sentence they were given.

**So the isolation that prevents drift is exactly what prevents noticing.** The
Bible is the only shared channel, which means *a quoted line in canon is a line
the book will repeat*, and no chapter can see that another already did.

**Nothing caught it, including the checks written to catch it.** The gate reads
one chapter at a time. So did `check_prose` — it found nothing in all eight
chapters. The repeat is only visible in the assembled book, and it took pointing
the same script at `dist/book.md` to see it. *A per-chapter check cannot find a
between-chapter defect*, which sounds obvious written down and was not.

Two fixes, at the two ends: `character-architect` is told that a quoted line is a
sample of register rather than a line to use — describe the voice, let each
chapter find its own words — and `backend.checks FLOW-6` reads the book.

### 3.5 No critic grades prose, and it shows

Three visible defects shipped: a sentence duplicated verbatim, a timeline error
on screen, a paragraph stating the same fact twice. Each was **kept in by rule 2**
— "change only what was cited" forbids touching what no finding names, and no
finding named them because none of the five characteristics read prose quality.
**SPEC-006 added a sixth that does**, after SPEC-005 took the mechanical part of
it off the model's plate.

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
- **The eight-chapter comparison, both sides measured — and it inverts the
  three-chapter one.**

  | | v1 `ice-station` | v2 `cartographer` |
  |---|---|---|
  | chapters | 8 | 8 |
  | words in the book | 10,723 | **11,133** |
  | characteristics | 2–3 | **5** |
  | rejected drafts kept | 0 | **6** |
  | outline audited first | no | **yes** |
  | orchestrator turns | 329 | **275** |
  | **cost** | **$49.33** | **$54.87** |

  **Eleven per cent more money, for roughly twice the judging and fewer turns.**
  At three chapters the same comparison was 2.5× ($7.45 → $18.82). The overhead
  does not scale with the book: it is mostly fixed — the Bible, the outline, the
  audit — and a longer book amortises it. Per thousand words the two runs are
  $4.60 and $4.93.

  That is the single most useful number this project has, because it is the one a
  person deciding whether to run it would ask for.

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

### 7.1 The procedure is a file, and a file can change under a run

`SKILL.md` **is** the pipeline — Annex C left exactly one implementation of it —
and it is a file anyone can edit while a run is in flight. **That happened.** A
sixth characteristic was added during an eight-chapter run: chapters 1 and 2 were
judged by five, and everything after could be judged by six.

Nothing noticed. The config has been snapshotted per run since the first
migration, for precisely this reason; **the procedure was not**, and the
procedure is the larger half of what a run does.

The result is not a broken run — it is worse in a quieter way. It is **a run that
is not a clean sample of either gate**, whose cost cannot be compared with a
five-characteristic run's and whose pass rate cannot be compared with a
six's. That is the same contamination `source: pre-loop003` exists to prevent
between implementations, appearing inside one run.

Runs now carry a SHA of `SKILL.md` at start and at end, and a mismatch writes a
`procedure-changed` warning. **A missing fingerprint is absent, not "unchanged"** —
runs that finished before this existed say nothing rather than claiming the
procedure held.

**And then the run itself corrected the alarm.** Chapters 1, 2 **and 3** all came
back with five critiques, after the edit. The orchestrator appears to hold the
procedure it read when its session began rather than re-reading the file each
turn — so the file changing mid-run is a smaller hazard than it looked, for that
run.

That does not retire the warning; it calibrates it. The warning says the early
and late chapters were *not necessarily* produced by the same procedure, which is
exactly the claim the evidence supports: **we can detect that the file moved, and
we cannot detect what the orchestrator was still holding.** A warning hedged that
way is useful; one that asserted contamination would have been wrong here.

The unhedged consequence stands and is the more important one: **the next run
picks up the change**, and a run's own config snapshot will say five while its
procedure says six unless the snapshot is taken from the same place.

### 7.2 The pass rule, written twice, was wrong the second time

The archive decided a verdict with `aggregate >= THRESHOLD`. The gate decides it
with `domain.aggregate`, which also requires **every** characteristic to have
answered. Two copies of the most important rule in the project, and the second
one was missing half of it.

It was invisible while every critic always answered. The sixth characteristic
made it reachable: a chapter whose `prose` critic returns something unparseable
has an aggregate of 10 over the five that did answer, and the archive recorded
**`accept`** for a chapter the gate had not passed. *A gate short a critic is a
weaker gate, not a passing one* — the rule that already returned 10 once and let
a malformed reply ship a draft, rediscovered in a second implementation of it.

Found by a test written to exercise the new characteristic, not by reading the
code. The fix is not a better second copy; it is having one: the archive now asks
`domain.aggregate`.

**A second door in the same wall.** The conformance audit exempted any attempt
whose verdict was `patched` from "promoted below the threshold". But `patched`
means *the patch brought this to the threshold*, so a `patched` row still under
it is incoherent and `decide` cannot produce one. The exemption was the widest
possible hole, under the one label nobody would think to question.

### 7.3 The gate was disobeyed on a live run, and the instrument caught it

**The most important thing this project has measured.**

On the eight-chapter run, chapter 3 scored `continuity` **2**, then **5** on its
second draft. It was **promoted**. `ch03.md` is byte-identical to
`ch03.attempt2.md` — no third attempt was made, no patch was applied, and the run
did not halt. It carried on and wrote chapters 4 and 5.

That is G6 violated: *a chapter that failed the gate does not enter the book*.
The one outcome the whole system exists to prevent, on a real run, with the
threshold at 8 and the chapter at 5.

**And it was detected within minutes, by the audit written that morning.**
Before it existed, §3.1 said the only signal was *reading a book with a bad
chapter in it* — which would have meant nobody ever noticing, because nobody
reads a test novel closely. The audit reports it twice, from two independent
rules: promoted below the threshold, and a verdict the rule would not give.

**What it says about the architecture, which is the uncomfortable part.**
SPEC-004 moved the decision into code precisely so a model could not reason its
way past it at the moment a run is about to be thrown away. This run shows the
remaining half of §3.1 is not theoretical: **the rule being arithmetic does not
make it obeyed.** Detection is not prevention, and the gap says so.

**And it was not one chapter. A second violation on the same run, which the audit
missed at first.**
Chapter 7 was promoted with `continuity` returning nothing usable. Its aggregate
was **10** — a minimum over the four critics that answered — so every rule that
read the aggregate saw a perfect chapter. *A gate short a critic is a weaker
gate, not a passing one*: the rule that once returned 10 and let a malformed
reply ship a draft, shipping one again, **through the audit built to catch
exactly this.**

Catching it needed the scores, not the minimum — and then needed one more thing.
A five-characteristic run has `prose` NULL on every attempt because it did not
exist, so reading NULL as *the critic said nothing* reports every one of those
chapters as a breach. **"The critic did not exist" and "the critic answered
nothing" are opposite facts that look identical in a NULL**, and only the archive
can tell them apart, because only it sees which critique files exist. So the gate
a run ran is now recorded, and a run archived before that column says *nothing*
rather than guessing.

**What it does not say.** Nothing here shows the orchestrator ignored the script:
this run began before `SKILL.md` told it to call `decide` at all. The honest
conclusion is narrower and worse — *the procedure as written when this run
started was not enough*, and the run is evidence for the change rather than
against it.

### 7.4 The one number the flat cost curve rests on was not being checked

The project's central architectural claim is that **chapter thirty-four's prompt
is the same size as chapter one's**. The Bible is fixed; the outline entry is one
chapter's. **The rolling summary is the only part that can grow with the book**,
and `context.max_summary_words` is the only thing stopping it.

Nothing measured it. Measured now:

| profile | cap | summaries, in order |
|---|---|---|
| `tiny` | 120 | 108, 116, **122** |
| `small` | 200 | 192, **204**, **211**, **246**, **220**, **222** |

Five of six over on the longer run, by 2% to 23%. **A number nobody measures
becomes a target rather than a limit.**

**What it is not.** It is not a runaway. The figures plateau around 220 instead of
climbing with the chapter count, and the cap scales by profile — 120, 200, 260,
300 — so the flat curve holds with roughly a tenth of one component's slack. The
distinction is the whole finding: *bounded overshoot* and *unbounded growth* look
the same in a single number and are not the same claim.

**And the check reports rather than truncates**, deliberately. Truncating a
written summary to fit is worse than a long one: the cap protects a budget, and a
dropped sentence loses the only channel between chapters.

### 7.5 The rule identifiers in the arbitration record referred to nothing

The critics and the outline audit cite a world's rules by number — *"R1 says only
the keeper on watch may write in the Register"*, *"R5 rewritten to name the
keeper as the writer"*. Those arbitrations are the evidence behind G11, and they
are quoted in this document.

`bible/world.md` writes its rules as **unnumbered bullets**. The numbers were the
critic counting the list and inventing an identifier. Across the two v2 runs
there are **76 such references and not one of them resolves to anything.**

Why it matters beyond tidiness: a positional reference points at a different rule
the moment one is inserted or reordered, and **two critics can number the same
list differently** — so `science` and the audit can hold confident, contradictory
views about which rule is at issue, and nothing would show it. The arbitration
record decays silently, which is the failure mode this whole document is about.

`worldbuilder` now writes `- **R1.** …`, and `check_rules` resolves the citations.
**A Bible with no numbers reports `unnumbered`, never `clean`** — saying "no
dangling references" about a file with no reference system is the same mistake as
reporting an unmeasured figure as zero.

### 7.6 The promises to the reader were unverifiable in ten runs of eleven

`bible/mysteries.md` holds the questions the book undertakes to answer. The
ontology calls a promise made and never paid a **foreshadowing failure**, and
`verification.md` has always listed it under what nothing checks.

It turns out to be *almost* checkable. One run wrote each mystery with two extra
lines — `Planted: Chapter 1` and `Lands: Chapter 3` — and those make the promise
a commitment a script can hold: landing before planting, landing past the last
chapter, landing in a chapter the run never reached.

**One run of eleven had them.** The other ten wrote mysteries in four different
shapes — bullets with prose answers, numbered `## 1.` headings, bullets with a
`True:` line — because **nobody had said which**. It is v1's three critique
shapes again, and the outline audit's two, in a third place.

So the format is now stated in `character-architect`, and `check_promises` holds
it. **A file whose promises name no chapters reports `unstated`, never
`coherent`** — that is not a book that kept its promises, it is one where the
question cannot be asked.

**What it still cannot do is most of the question.** It reads a commitment; it
does not read the chapter. A chapter that says nothing about the mystery it was
supposed to land passes this and fails a reader — which is the part that stays
**U**, and the part a sixth characteristic does not reach either.

### 7.7 Two memory layers were built, tested, documented as live — and never ran

`architecture.md` §5 described memory in four layers. Two of them do not run.

**Structured summary facts.** `chapters/summary.py` projects the rolling summary
from typed facts and drops the lowest priority first, so that every
`open-question` survives the cap — because an abandoned promise is the
foreshadowing failure arriving quietly. It is written and tested. `save_facts`
has **no caller**; `summary_facts` and `character_knowledge` are empty in every
run; the summary that reaches the next chapter is prose the orchestrator writes
freehand.

**Vector retrieval.** `commons/search` indexes canon into `chunks` and serves the
nearest fragments, with the dimension pinned and the `vec0` limits tested. **No
run has ever populated `chunks`.**

Neither is broken and neither is deleted: each is a working implementation of a
decided design. **What was broken is the document**, which described both as
live, so a reader planning against §5 was planning against a system that does not
exist.

**The pattern, which is the day's pattern one more time.** `save_attempt`,
`save_gate` and `save_sheet` were written and called by nothing. So were these.
Code that implements a documented guarantee and has no caller is the quietest
defect there is: **every test of it passes**, because tests call it directly. The
only thing that finds it is asking *who calls this* — and the only thing that
keeps it found is a test that fails when the answer changes.

### 7.8 The sentinel that ends a stream must come last, and in a `finally`

Everything a run does after it halts is bookkeeping — the cost, the fingerprint,
the archive, the conformance audit — and **every line of it was added after the
SSE follower was written.** The sentinel that ends the stream came last.

So a failure in any of them hung every follower forever. Not an error: a wait. **A
reader on a finished run that never returns looks exactly like a run still
going**, which is the worst way for a system to fail in front of someone.

It was found by adding one more bookkeeping step and watching the entire test
suite stop at its 300-second limit — a defect that had been reachable since the
first one of those steps was written, and that no test covered because no test
made any of them fail.

The `finally` is the fix. The second lesson is smaller and worth as much: the
underlying error was a `NameError` from an edit that moved a block into the wrong
method, and **`_archive`'s own `except` had been swallowing it into a warning row
nobody reads.** A handler that turns a programming error into a log line is a
handler that hides it.

### 7.9 A rule lives in one place, and the count is the tell

Finding the pass rule written twice was worth searching for the others. The
threshold — 8 — turned out to be written in **four**:

| where | now |
|---|---|
| `config/novel.config.json` | the source |
| `chapters/domain.py` | the default, from the config |
| `runs/archive.py` | **a literal `8`**, four lines from the module that owns it — and `commons/config/loader.py` opens by saying exactly why that is wrong |
| `frontend/.../lib.ts` | a literal, in a language that cannot import it — so a test compares it |

The panel also said *"All five must reach 8"* after the gate had six, and its
column-label map was `Record<string, string>`, so the missing `prose` entry
returned `undefined` and **the column would have shipped with no name**. Typed
against `Characteristic`, the compiler refuses an incomplete map — which is the
difference between a rule and a reminder.

**The pattern worth keeping:** when a defect turns out to be two copies of one
fact, the next move is not to fix that pair. It is to count the copies.

### 7.10 Zero is a value, and this is the family the bugs come in

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

### 7.11 The procedure records the time it can compute, and says so

SPEC-007 §8 point 2 asks `SKILL.md` to record a real `ts` per call. What the
first real v2 run recorded, read by `check_log` at PLAN-007 6.12: **3 rows
`measured`, 47 `derived_from_duration`.** The orchestrator computed most
timestamps from durations and labelled them — which is the difference between a
figure and a guess, and the label is why the check reports rather than refuses.
The backend's own `calls.ts` comes from the stream and does not depend on it.

### 7.12 A second follower of a finished run waited forever

`follow()` yielded the snapshot, then blocked on the live queue. The queue's
sentinel had been consumed by the first follower; a second one — a reconnecting
panel, a test with `Last-Event-ID` — never returned. Found by the first test that
followed a run twice (PLAN-007 6.7). The fix is one branch: `live.done` answers
`done`. The lesson is the one §7.8 already drew, from the other side: **the
sentinel that ends a stream is consumed once**, and every reader after the first
needs a different signal.

### 7.13 The watcher knew nine agents

`watch.AGENTS` listed "the nine" — the set the file was written against — and
`prose-critic` had existed for a day. Nothing used the set except a comment, so
nothing failed; it was a count that had gone stale in a place no test read.
`test_the_watcher_knows_every_agent_file` pins it to `.claude/agents/*.md` now.
§7.9's rule, again: **a count written in prose is a count that will be wrong.**

### 7.14 A pin that was committed red

The route pin of PLAN-007 6.10 read `app.routes`, saw one route, and was
committed as passing because the commit chain did not stop on a red test.
FastAPI wraps an included router, so the test believed the app served only
`/api/health`. **A test that has never been seen green is not a pin**; it was
corrected in the next commit to read the OpenAPI paths, and the chain that
commits after a test now stops on its exit code.

### 7.15 The import's default sees every `state.json`, and v2 writes one too

On a fresh scratch database, `import_v1` without slugs imported two v2 runs as
`pre-loop003` history — they have a `state.json`, which was the only criterion.
In the deployed database they are already rows and are skipped; on an empty one
they are not. `verification.md` §3.20; the fix belongs to the next spec that
touches the importer.
