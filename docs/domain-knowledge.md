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

### 3.5 No critic grades prose, and it shows

Three visible defects shipped: a sentence duplicated verbatim, a timeline error
on screen, a paragraph stating the same fact twice. Each was **kept in by rule 2**
— "change only what was cited" forbids touching what no finding names, and no
finding named them because none of the five characteristics reads prose quality.

The guardrail and the goal are in tension, and there is a receipt.

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
