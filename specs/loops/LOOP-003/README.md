# LOOP-003 — The validation: five scores, three attempts, and feedback that escalates

A loop over a single problem: how a chapter is validated, and what the writer is
told when it does not pass. Supersedes LOOP-002.

| | |
|---|---|
| **id** | LOOP-003 |
| **problem** | chapters that miss the minimum score, and the feedback they get |
| **rule** | five characteristics, each 0–10; all ≥ 8; three attempts at most; by the third the chapter comes out valid |
| **status** | **run twice** (§9, §10); candidate 1 tested and adopted, and it corrected §10.2's root cause (§11) |
| **date** | 2026-09-18 |

## In five lines

A loop on the writer's validation.

- **Trigger** — when a chapter scores under 8 on any of the five characteristics.
- **Goal** — 100% of chapters valid, all five scores ≥ 8, by the third attempt at
  the latest, and more of them passing on the first or second over time.
- **Verify** — a script records which attempt each chapter passed on, the five
  scores per attempt, which findings were resolved and how many lines the writer
  touched; and checks that every sheet has the full format before it is sent.
- **Stop** — (1) eight consecutive chapters valid without needing the third
  attempt's patch → the format is promoted; (2) two consecutive chapters needing
  the patch after a change to the sheet → revert and stop automatically.
- **Memory** — every sheet sent with its outcome, so the sheet learns what to
  say; and which critic raises findings late.

## 1. The five characteristics

There were four. The fifth covers the largest hole: nobody checked that the
writer wrote the chapter the outline commissioned.

| # | characteristic | what it measures | who scores | how |
|---|---|---|---|---|
| 1 | Continuity | does not contradict the Bible or the timeline | critic (model) | as before |
| 2 | Science | does not break the world's rules | critic (model) | as before |
| 3 | **Outline** (new) | covers the beats the outline assigned this chapter, in order | critic (model) | 10 − 3 per missing beat − 1 per beat out of order; floor 0 |
| 4 | Length | words inside the profile's band | script | as before |
| 5 | Heading | first line is `# Chapter N`, no model chatter | script | as before |

The chapter's score is the lowest of the five. A chapter is worth what its worst
characteristic is worth. It passes when all five are at 8 or above.

Two of the five are pure arithmetic and cannot be wrong. Three are a model's
judgement and can be; that is what the orchestrator's arbitration is for, and it
has already overruled one false finding in the saved run.

## 2. The three attempts — and why the third is different

**Each failed attempt must make the next one easier, not merely better
informed.** The feedback escalates in concreteness until, by the third attempt,
there is nothing left to interpret.

| attempt | what the writer gets | what it is asked to do | if it fails |
|---|---|---|---|
| 1st | the Bible, its outline entry, the summary | write the chapter | → level-1 sheet |
| 2nd | the above + level-1 sheet: per finding, the exact quote, what is wrong, against which rule, and how it should read, described in one sentence | correct only what is marked, touching the fewest lines | → level-2 sheet |
| 3rd | the above + level-2 sheet: per open finding, **the literal replacement sentence, written by the critic** | integrate those sentences, do not rewrite | → patch: the orchestrator applies the sentences itself and rescores |

On the second attempt the writer interprets a description. On the third it does
not interpret — it integrates a given text. And if not even that, the patch is
applied by something that does not need to interpret anything. For the two
arithmetic characteristics the patch is trivial: trim words, fix the first line.
For the three model ones it is the sentence the critic itself proposed. The only
way a chapter fails to come out valid by the third is that the critic's sentence
was also wrong — which is what the orchestrator's arbitration exists to catch
before it is applied.

**Honest limit.** Outline is the hardest to patch, because a missing beat is not
a sentence but a paragraph. Its level 2 is the beat fully specified — what
happens, between which paragraphs, in how many sentences — and its patch is that
paragraph, written by the critic. It is the weakest point of the guarantee and
it is said here rather than discovered later.

## 3. The feedback sheet

The object this loop improves. Always the same format, always complete.
`validate-sheet.mjs` checks it before it is sent; an incomplete sheet is not
sent. The template is `sheet_template/v01.md`.

The five rules of the sheet:

1. **All five scores, always, including the passing ones.** The writer has to
   know what is right in order not to touch it.
2. **An explicit DO NOT TOUCH list.** In the saved run the writer changed
   exactly two lines and then one — that is what there is to preserve. A writer
   that takes the opportunity to improve an approved paragraph is the commonest
   way a passing score stops passing.
3. **Four fields per finding** — quote, what is wrong, against what, how it
   should read — or it is not sent. The quote is literal. "Against what" points
   at the Bible or the outline, never at a previous chapter.
4. **A RESOLVED list.** The writer knows what worked. And the script knows which
   form of "how it should read" produced the fix (§7).
5. **Findings worst first, and all of them.** They are not trimmed: a finding
   held back is a finding that fails again next time.

### 3.1 The late-finding rule

A critic that raises on the third attempt something that was equally present in
the first and went unmentioned is moving the goalposts. That finding is marked
**late**: recorded, patched if possible, and it does not block validation. It
counts against the critic in memory (§7), because a critic that accumulates late
findings is one that does not read the same way twice. Without this rule the
third-attempt guarantee does not exist, because something new can always appear.

## 4. TRIGGER — entry conditions

What is needed:

- The five characteristics scoring from the first attempt, Outline included.
- The chapter's outline entry with its beats **numbered**, so Outline has
  something to measure against.
- The sheet format script running: no sheet goes out without passing it.
- The per-attempt line counter — **which requires the rejected drafts on disk**.

When it fires:

- At the end of any attempt with a score under 8. Generates the sheet at the
  right level and sends it.
- On the third attempt failing. Fires the orchestrator's patch and the rescore.
- On detecting a late finding. Marks and records it without blocking.

## 5. GOAL

**G1 — 100% of chapters valid by the third attempt at the latest**, all five
scores ≥ 8, zero chapters accepted with warnings. *Why:* today the system, if
the third attempt does not pass, accepts "with warnings" and carries on. That is
a defective chapter inside the book with a note in the margin. This loop removes
that exit: it passes, or it is patched until it passes.

**G2 — the share passing on the 1st or 2nd attempt rises against the baseline.**
*Why:* the third attempt guarantees the outcome but costs about as much in
critics as the first two together. Every chapter that passes earlier is roughly
27,000 tokens saved. G1 is the guarantee; G2 is the saving.

**G3 — the writer touches only what was marked**: lines changed ≤ lines quoted ×
2, in 95% of attempts. *Why:* it is the guardrail on the DO NOT TOUCH list. If
it breaks, the approved scores start falling and the guarantee is lost from the
other end.

**G4 — late findings under 10% of all findings.** *Why:* above that, the problem
is neither the writer nor the sheet — it is that the critics do not read the
same way twice, and that is fixed somewhere else.

## 6. VERIFY

A script measures. Never the writer, never the critics. `measure.mjs`.

### 6.1 Recorded per attempt

| measure | from |
|---|---|
| the five scores | the attempt's critique files |
| passed? (all five ≥ 8) | computed from the scores |
| which attempt it passed on (1, 2, 3 or patch) | the log |
| findings open / resolved / new / late | comparing findings between attempts **by their quote** |
| lines the writer touched | diff between drafts |
| lines quoted in the sheet | the sheet sent |
| did the sheet have the full format? | the validator, before sending |
| the attempt's tokens, writer and critics | the log |

### 6.2 Self-test of the instrument — and what it found

Before anything else the script runs over the saved run and must reproduce it.
`node measure.mjs --self-test`:

```
PASS  chapter 1 passes on the first attempt
PASS  chapter 2 passes on the second
PASS  chapter 2 resolved 3 findings
PASS  chapter 3 passes on the second
PASS  chapter 3 resolved 1 finding
PASS  chapter 3 had 1 overruled
SKIP  chapter 2 touched 2 lines — the rejected draft was not kept
SKIP  chapter 3 touched 1 line — the rejected draft was not kept
```

**Six of the eight assertions reproduce. Two cannot, and that is the first thing
this loop found.** The saved run keeps only its accepted drafts, so there is no
diff and the line counts cannot be recovered from disk — the numbers 2 and 1
survive only as prose in a `repair` note. G3 therefore had no instrument at all
until this was fixed: `config.feedback.keep_attempt_drafts` is now true and
FLOW-4 writes `chapters/ch0N.attemptK.md` for every attempt.

The script reports an unmeasurable field as *not measurable*, never as zero. A
run that destroyed its evidence and a run where the writer changed nothing look
identical in a number and must not look identical in a report.

### 6.3 Honest baseline

In the three saved chapters all passed by the second at the latest: 1st, 2nd,
2nd. The G1 baseline is already 100% on that sample, so three chapters are not
enough to watch this loop work. An eight-chapter novel is needed. **The first
known case of a chapter that did not validate is from the second book, whose
record is not in this document and has to be added when it is available** — it is
the datum that motivates the loop and it is still missing.

A second gap found while building the instrument: the runs after the saved one
stopped writing `length` and `chatter` critique files, folding both into
`chNN.gate.json` instead. The measurement script cannot see five scores in those
runs and reports every chapter as never having passed, which is correct and
useless. SKILL.md now requires all five files.

### 6.4 Design

An eight-chapter novel with the five characteristics and the escalating sheet
from chapter 1. Each change to the sheet format is tried on the chapters that
follow and compared with those before (§7, stop condition 2). No control arm is
needed: the metric is absolute — 100% valid by the third — and each chapter's
own history is the comparison.

Cost of an eight-chapter novel with five critics instead of four, at the
project's rates and extrapolating from the real run: **$3.90 low / $6.25
estimated / $19.50 high.**

## 7. STOP — the two conditions

**Condition 1 — the metric is reached.** Eight consecutive chapters valid with
all five ≥ 8, none by patch, and G3 and G4 in range. The current sheet format is
promoted to final and the loop ends.

**Condition 2 — two consecutive chapters need the patch after a change to the
sheet.** The change is reverted to the previous version and the loop stops
automatically. Two in a row is already a signal; a third costs what two full
attempts cost.

**Safety cut** (a brake, not a stop condition): if a chapter still does not
validate after the patch, the run halts. By construction it should not happen;
if it does, the critic's sentence was wrong and arbitration did not catch it,
and that needs looking at before going on.

## 8. MEMORY

### 8.1 What it remembers

- **Every sheet sent, with its outcome**: which findings the writer resolved next
  attempt and which it did not. This is the only thing this loop genuinely
  learns — which form of "how it should read" produces a correction first time
  and which needs the literal sentence. Over time the level-1 descriptions get
  written like the ones that worked.
- **The distribution by attempt**: how many chapters pass on the 1st, 2nd, 3rd
  and by patch. That is the curve that has to move left.
- **Late findings by critic and characteristic.** If one accumulates, the problem
  is that critic's.
- **Lines touched against lines quoted, per attempt.** If it grows, the DO NOT
  TOUCH list is not working.

### 8.2 Allowed

- Rewording any field of the sheet.
- Reordering the sheet's blocks.
- Changing how level 1's "how it should read" is phrased — where the learning
  lives.
- Adjusting the Outline scoring formula, which is new and has no history.

### 8.3 Not allowed

- Lowering the 8. The threshold is not a variable of this loop.
- Fewer than five characteristics, or scoring two as one.
- A fourth attempt. The third is the last because the third is the one that
  guarantees.
- Trimming findings from the sheet to make it look shorter.
- Sending a sheet that does not pass the format validator.
- Quoting text from a previous chapter in the sheet. "Against what" points at the
  Bible or the outline. The writer still never sees prior prose.
- Changing the sheet and the Outline formula in the same chapter. One at a time.

### 8.4 Where

```
specs/loops/LOOP-003/
├── README.md                    this document; conclusion in one paragraph when it ends
├── measure.mjs                  §6, the instrument, with --self-test
├── validate-sheet.mjs           §3, the format gate, with --self-test
├── sheet_template/vNN.md        each version of the sheet format
├── sheets/chNN.attemptK.md      each sheet sent, verbatim
├── attempts.jsonl               one row per attempt: scores, findings, lines, tokens
└── late_findings.jsonl          late findings, by critic
```

Both `attempts.jsonl` and `late_findings.jsonl` now exist, written by the run in
§9.

---

## 9. First run — `ice-station-water-recycler-surplus`

Eight chapters, 10,723 words, 2026-09-18. 44 subagents, 0 failed. **$49.33, 99
minutes**, from Claude Code's own result event.

### What the instrument says

```
G1 valid by the third attempt: 8/8
G2 passed on the 1st or 2nd:   7/8
G3 touched vs cited:           7/7 within 2x
G4 late findings:              0/22
```

| ch | attempts | continuity · science · outline · length · chatter (final) |
|---|---|---|
| 1 | 2 | 10 · 10 · 9 · 10 · 10 |
| 2 | 2 | 10 · 10 · 10 · 10 · 10 |
| 3 | **3** | 10 · 10 · 10 · 10 · 10 |
| 4 | 2 | 10 · 10 · 9 · 10 · 10 |
| 5 | 1 | 10 · 9 · 10 · 10 · 10 |
| 6 | 2 | 10 · 10 · 10 · 10 · 10 |
| 7 | 1 | 10 · 10 · 10 · 10 · 10 |
| 8 | 2 | 10 · 10 · 10 · 10 · 10 |

15 attempt drafts kept, 40 critique files (five characteristics × eight
chapters), 7 sheets, every one validated before sending — and **one refused
first time**, for chapter 3, where a quote containing nested double quotes
parsed as a single character. The validator did the job it exists for on its
first outing.

### §7 condition 1 is met, and thinly

Eight consecutive chapters valid, none by patch, G3 and G4 in range. By the
letter the sheet format v01 is promoted. **Say what that is worth:** the loop
never had to work. `patch_then_halt` was never reached, seven of eight chapters
passed by the second attempt, and §8.1 says what this loop learns is which
phrasing of "how it should read" produces a correction first time. With one
chapter reaching attempt 3 there is almost no signal to learn from. The format
is promoted because the rule says so, not because it has been tested.

### The datum §6.3 asks for was still missing here — see §10, which went and got it

**No chapter has ever failed to validate.** Twenty-four chapters now across
seven runs, and the worst case remains a chapter that needed all three attempts
and passed — chapter 3 here, and chapter 1 of
`last-lighthouse-keeper-on-titan` before it. So the whole `patch_then_halt`
path — the orchestrator applying replacements, arbitrating them first, the
safety cut — **has never executed**. It is specified, implemented and unexercised.

The sentence in §6.3 stands unchanged: the record that motivates this loop is
not in this document.

### What the run found that this document did not predict

**1. The instrument's G3 was wrong, and the run said so rather than reporting
the number.** `measure.mjs` compared attempt *k*'s diff against attempt *k*'s own
citations, so a final attempt that passed clean cited nothing and any repair
failed against zero. It read 2/7 on a run that is 7/7. Fixed: G3 now pairs the
diff with what the sheet that commissioned it cited, which is attempt *k−1*'s
findings. This is the behaviour the instrument exists to make possible — an
orchestrator that reported a bad number instead would have been believed.

**2. Nothing audits the outline.** The outline was wrong four times on
arithmetic — "fourteen left" against a ledger giving thirteen, "six cycles left"
where twelve minus two minus two is eight — and the writer's numbers overruled
it each time, declared to the outline critic before it scored. The `outline`
critic holds the draft to the outline and nobody holds the outline to anything.
Both chapters scoring 9 on outline are that shape.

**3. `wc -w` cannot tell presentation from editing.** Two style passes were
discarded because the editor closed the space in `± 0.30` → `±0.30`, merging two
tokens into one. `style.word_count_tolerance_pct` is 0, so the gate-approved
text shipped instead — correct under the rule, and the rule fired on a change
that altered no word.

**4. Arbitration ran in both directions.** On chapter 3 the orchestrator offered
the science critic a reading to justify a repair and the critic **rejected the
orchestrator's arithmetic**, grounding the fix in a different rule instead. On
chapter 8 the orchestrator overruled the critic. The run's only overruled
finding is recorded in `late_findings.jsonl` as `overruled_not_late`.

**5. The cost estimate in §6.4 is right about the wrong thing.** It projected
$3.90 / $6.25 / $19.50 and the subagent tokens came to $3.88 / $6.21 / $19.42 —
almost exact. The run cost **$49.33**. The estimate prices what the eight
subagents consumed and knows nothing about the orchestrator's 329 turns, which
carry the Bible, the drafts, the findings and the sheets over and over. Read
that range as a floor, not a range.

### Carried in from `last-lighthouse-keeper-on-titan`

Two defects this document does not cover, from the only other chapter that ever
needed three attempts. Its `critiques/ch01.gate.json` recorded both.

**The critics pulled opposite ways on the same sentence.** The science repair at
attempt 2 — which took science from 4 to 10 — introduced the continuity failure
that made attempt 3 necessary. §2's escalation does not address this: the literal
replacement handed to attempt 3 is written by **one** critic, and applying it can
break a characteristic that was already passing. That is a larger hole in "it
will pass by the third" than the missing-beat paragraph §2 admits to, and it is
not fixed here — it is recorded.

**A duplicated sentence shipped, and rule 2 is what kept it in.** The attempt-3
patch replaced only the sentence its `find` named and left the one before it, so
a paragraph states the same fact twice. No critic flagged it: none of the five
grades prose quality. It stayed because "change only what was cited" forbids
touching text no finding names, and no attempts remained. §5's G3 guardrail and
§5's G1 goal are in tension, and this is the receipt.

### What to do next, in order

1. **Get the missing datum.** Everything that has never run needs a chapter that
   fails three times. It has not happened in twenty-four chapters, so waiting for
   one is not a plan.
2. **Decide what a cross-characteristic repair does** (finding 1 above). Until
   then the third-attempt guarantee is weaker than §2 claims.
3. **Do not promote v01 on this evidence** despite §7 condition 1 firing. One
   chapter at attempt 3 is not a test of a feedback format.

---

## 10. The stress test — `night-dispatcher-recovered-climber`

Waiting for a natural failure was not working: twenty-four chapters and none had
ever failed. So one was built. `config/profiles/stress.json` puts **nine to ten
mandatory beats inside a hard 300–550 word band at tolerance 0**, so satisfying
`outline` costs words and satisfying `length` costs beats. Nothing about the gate
was weakened — threshold 8, five characteristics, three attempts, §8.3 intact.

**$19.00, 42 minutes, 3 chapters. It halted.**

| ch | attempts | final: cont · sci · out · len · chat | verdict |
|---|---|---|---|
| 1 | 2 | 10 · 10 · 10 · 10 · 10 | accept |
| 2 | 1 | 10 · 10 · 10 · 10 · 10 | accept |
| 3 | 3 + patch | **8 · 10 · 7 · 10 · 10** | **halt** |

Chapter 3 went 5 → **4** → 7. The second attempt came back worse than the first.

**`patch_then_halt` executed for the first time, and it did the thing it exists
to do: there is no `chapters/ch03.md`.** The failed chapter did not enter the
book with a note in the margin; the best draft sits at `ch03.attempt3.md`,
unpromoted, and FLOW-5 and FLOW-6 never ran. The sentence "no chapter has ever
failed to validate" is no longer true, and the machinery specified in §2 is no
longer unexercised.

### 10.1 The patch applied nothing, and that is the finding

Three literal replacements were offered. Arbitration admitted one and **refused
two on arithmetic, not taste**:

- **Science's** added 22 words to a draft with **5 words of headroom** against a
  hard 550 ceiling. 567 words scores `length` 0 — trading a 10 for a 0 to raise
  something already at 10.
- **Continuity's** was byte-identical to text `science` had already scored 5 in a
  measured pass. A known regression, not a repair.
- **Outline's** was applied at attempt 3. Its rescore moved science 4 → 10 and
  continuity 4 → 8, and **outline stayed at 7** — the outline critic scored its
  own replacement text, was told not to inflate it because it was its own, and
  returned 7 anyway, marking beat 7 still missing. It had predicted exactly that.

At the patch step the same three candidates were the only ones available, so
nothing was applied and no rescore was run. A rescore of unchanged text produces
a number that looks like evidence and is not.

### 10.2 The cross-characteristic hole, confirmed and worse than recorded

§9 carried one instance in from another run: a repair for one characteristic
breaking another. Here it is again, three ways worse.

> **Science, attempt 1:** "Line 0471 is instead validated on a voice transmission
> from the subject himself and a tag-reconciliation analysis — neither of which
> is a field-team callsign report."
>
> **Outline, attempt 2:** "beat 7 … does not happen; the patched line has him
> explicitly reject the tape as a confirmation … **which is the opposite event**."

Outline fell 10 → 7. It was **on the sheet's DO NOT TOUCH list and the writer
never touched it** — the sentence that broke it was a sentence the sheet ordered
changed. Beyond the earlier precedent, the same repair also took continuity 5 → 4
and **science itself 5 → 4**: the critic that commissioned the repair scored the
result worse than what it replaced.

And the conflict is **unresolvable, not merely unlucky**. Asked directly, outline
returned `beat_7_and_the_rule_are_compatible: false`; science returned *"There is
no wording in which the 03:14 voice tape is Bauer's literal first confirmation
and the RECOVERED bullet survives."* Continuity dissented, 2–1.

**Root cause, as the run reported it:** §9 finding 2 recurring — nothing audits
the outline against the rules. Beat 7 commissions a voice tape as a confirmation;
`world.md` admits only a field-team callsign and a beacon tag. A missing beat
costs 3, so outline floors at 7 and `min` can never reach 8, and the chapter was
impossible as commissioned.

**That root cause did not survive being checked — see §11.** Three independent
audits of the same outline, by three different methods, all decline to flag beat
7, and two of them reason explicitly that line 0471 inherits line 0447's valid
confirmations. What they find instead is a rule that reads two ways. The
deadlock is real and the chapter genuinely could not pass; the reason is one
layer further down than the run concluded.

### 10.3 The DO NOT TOUCH list held, completely

Under maximum pressure the writer never exceeded its brief. Every attempt
returned substitutions, never prose: **9 patches offered, 9 matched literally, 0
skipped**, quoted text verified absent every time. G3 is 3/3 within 2×. At
attempt 2 it fitted four repairs into 31 of its 36 available words.

The guardrail worked and the guarantee it protects still failed. Those are
separate facts and both belong in the record.

### 10.4 Two instrument bugs, found by being used

- **Sheets collided across runs.** `sheets/chNN.attemptK.md` had no run
  dimension, so this run overwrote the previous one's chapter 1 and chapter 3
  sheets. They were restored byte-exact from `ce517ab` — verified 7/7 — which is
  luck, not design. Sheets now live under `sheets/<slug>/`, in SKILL.md and in
  `measure.mjs`, which still reads the flat path as a fallback.
- **`measure.mjs` bucketed unattributed tokens into attempt 1.** Arbitration
  calls are logged with no `iteration`, and `?? 1` treated "not stated" as "the
  first", so chapter 3's attempt 1 read 91,489 tokens — large enough to be
  believed and wrong. Now only a stated iteration counts, and the remainder is
  reported as `tokens logged with no attempt named` (41,383 here).

### 10.5 Recorded against the run itself

- Science's attempt-1 fix offered **two branches** and the orchestrator silently
  wrote one into the sheet. Branch two was never tried. **The sheet template has
  no field for a fix with alternatives**, and it should: §8.2 permits changing
  how "how it should read" is phrased, which is where that belongs.
- **A gate miss in chapter 2**, recorded not patched: a character reads queued
  bursts on screen at ~02:55 when canon holds them until the 03:05 flush. Both
  critics were handed the maintenance window and both returned 10. No finding
  named it, so rule 2 forbade touching it — the same disposition as the
  duplicated sentence in the lighthouse run, and the third instance of the same
  shape.

### 10.6 What this changes

**Answered:** `patch_then_halt` works. The halt is real, the failed chapter stays
out of the book, arbitration refuses bad replacements on arithmetic, and the DO
NOT TOUCH list survives pressure.

**Not answered, and now urgent:** §2's claim that a chapter comes out valid by
the third attempt is **false as written**, and the counterexample is not a writer
that underperformed. It is a commission that contradicts canon, which no
characteristic checks. Two candidates, neither adopted here because §8.3 is not
mine to amend:

1. Audit the outline against `## Rules` before FLOW-4 begins — the cheapest fix
   and it addresses the root cause of both §9 finding 2 and §10.2.
2. Give the level-2 replacement a cross-check: the critic that wrote it is not
   the one that should decide it is safe to apply.

---

## 11. Testing candidate 1, and correcting §10.2

Candidate 1 — audit the outline against `## Rules` before FLOW-4 — was tested
against the outline that produced the deadlock, which is free and decisive: the
answer is already known. Three designs were tried.

| design | cost | score | found |
|---|---|---|---|
| scan for problems | $0.113 | 5 | beats 9 and 1 |
| rule by rule, all five visited | $0.071 | 4 | beats 9 and 1 |
| clause by clause, 18 clauses | $0.125 | 4 | beats 9 and 1 |

**Adopted.** It is the cheapest check in the pipeline and it found two defects
the full five-critic gate never caught across three attempts and a patch:

- **beat 9** has Bauer, a field-team member, personally set a permanent
  RECOVERED line that the rules reserve to the duty controller;
- **beat 1** fires the automatic callout at exactly twenty minutes after 02:45
  when the rule requires a gap of *more than* twenty.

Both are cheap in an outline and expensive in a chapter. FLOW-3 now runs it and
`specs/flow.yaml` records `critiques/outline.audit.json` as an output.

### 11.1 It did not find beat 7, and that corrects the record

No design flagged beat 7, including one that decomposed the rules into eighteen
clauses and checked each separately. The compound-rule hypothesis — that the
critic finds the first violated clause and stops — is wrong.

Reading the rule again against what the audits say:

> Only the duty controller may set a casualty RECOVERED, and only on two
> independent confirmations — field-team callsign and beacon tag number —
> entered within 30 minutes of each other; **the line is permanent, and a
> correction is a new line.**

Line 0471 corrects line 0447. Does a correction line need its own two
confirmations, or does it carry the original's? **The sentence supports both.**
The run's science critic took the first reading and found line 0471 validated on
a voice tape and a reconciliation, neither of which is a callsign. Three audits
took the second and passed it, one noting in as many words that 0447's BERG 4
callsign at 15:55 and tag 7-1142 at 16:18, twenty-three minutes apart, satisfy
the rule.

**So the defect is in `bible/world.md`, one layer below where §10.2 put it.** Not
a writer that underperformed, not an outline that ordered the impossible — a rule
that reads two ways. Two critics then pulled in opposite directions on the same
sentence for three attempts, each correct under its own reading, and nothing in
LOOP-003 can arbitrate that because both are right.

An ambiguous rule does not fail loudly. It fails as a disagreement nobody can
settle, and it costs three attempts, a patch and a halted run to discover.
`SKILL.md` now asks the FLOW-3 audit to report ambiguity as a finding in its own
right, which is the only cheap moment to catch it.

### 11.2 What this changes about candidate 2

Cross-checking the level-2 replacement with the other critics would **not** have
saved this chapter. Outline did review science's replacement and rejected it —
that is exactly the 10 → 7 in §10.2. The cross-check was effectively performed
and the deadlock happened anyway, because the disagreement was not about the
replacement's quality but about what the rule means.

Candidate 2 is still worth having for the ordinary case, where a repair breaks
something by accident. It is not the fix for this one, and §10.6 overstated it.
