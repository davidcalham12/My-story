# U5 — finish (FLOW-5 and FLOW-6)

One unit: every chapter has passed the gate, and this one turns them into a
book — one voice, a synopsis, the assembled manuscript, and the two validators
the publish gate owes. Read `.claude/skills/storymaker/SKILL.md` first — the
agents' tool boundary, the logging duties and the ceiling are there and are not
repeated here.

**You are the only unit that sees the whole run, and you see it from disk.** The
chapters, the critiques and `state.json` are what happened; nothing was carried
here in a conversation.

## 1. FLOW-5 — style, and FLOW-6's synopsis, in one message

Dispatch `style-editor` for **every approved chapter in one message**. The
passes are independent — that is the whole premise of the stage, one voice
applied to chapters written in isolation — so there is no reason for chapter 3
to wait on chapter 1.

Dispatch `publisher` in that same message. FLOW-6 is drawn after FLOW-5 in the
flow spec, but read what the synopsis is written from: the Bible, the outline
and the chapter summaries — **not the chapters**, because a synopsis is written
from canon. None of those is touched by the style pass, so waiting buys nothing
and costs a round. Give it `outputs.synopsis.words.min`/`.max` and
`comparables`, and write its reply to `synopsis.md`.

Both agents have `Glob` only, so everything they judge is in the prompt you
send; the concurrency sum in SKILL.md §7 applies to that message like any other.

**Check the style pass with arithmetic.** Count the words in what it returns and
compare with what you sent. If the counts differ, the pass rewrote something —
discard it, copy the unedited chapter to `chapters/chNN.final.md` instead, and
name that chapter in your report. **The published text must be the text the gate
approved**; the style editor normalises presentation and is deliberately unable
to rewrite a word.

## 2. Assemble the book yourself

In the shell, concatenating the `.final.md` files in order, with the synopsis in
front if `outputs.markdown.include_synopsis` is true. Write `dist/book.md`.

**Do not ask a subagent to do this.** Concatenation is a mechanical
transformation, and a model asked to perform one will paraphrase a sentence in
the middle that the gate already approved.

## 3. Run the book's checks

```bash
python -m backend.checks FLOW-6 <run_dir>
```

It reads `dist/book.md`, so it runs after the assembly and before anything
reports on it. This is the last moment a promise landing in a chapter that was
never written can be found before a reader finds it — and the only moment
anything reads the book *whole*: every check before this one read a chapter at a
time, and a sentence repeated in chapters 2 and 7 is invisible to all of them.
One shipped, because the Bible quoted a character's line verbatim as a sample of
how he speaks and two chapters five apart used it word for word.

## 4. The judge

Dispatch `judge` with the assembled book and the brief it was written from — the
genre, the tone, the recipient and the occasion. It returns six criteria —
`continuity`, `tone`, `narrative_arc`, `character_coherence`, `pacing`,
`natural_personalisation` — each a score 0–10 **and a justification**. Write the
reply to `critiques/judge.json`; `backend/publish/judge.py` is the schema it has
to satisfy and the only writer into `validations`. There is no command-line
entry point for it on this branch: leave the file where the backend reads it
rather than inventing one.

It is the first reader to see the book whole — every chapter was written by a
writer that could not read another — and it runs **once per version**.

**The justification is the point, not the score.** The six characteristics of
the chapter gate are each checked against something a person can open: the
Bible, the world's rules, the outline, a word count. This one is checked against
nothing, so the only thing separating its 6 from a 9 it could equally have
written is the sentence beside it — and the owner's own six scores are printed
next to the judge's, which is a comparison that needs reasons on both sides. A
criterion that arrives without its justification is **rejected**, and the gate
sees a malformed reply rather than a set of scores. Send it back rather than
filling the gap yourself.

**A criterion it could not judge is omitted, never scored 0**, and excluded from
the mean (SKILL.md §5). Five nines and an absence is a 9 on a weaker rubric;
counting the absence as 0 makes it 7.5 and publishes a claim about a criterion
nobody looked at. The mistake costs more here than anywhere: the judge runs
once, on a finished book, and there is no attempt 2.

**Nothing redrafts the book on its verdict.** It is the measurement, not a gate.

## 5. The mandatory facts

`mandatory_facts` is a set difference, not a judgement: the mandatory facts of
this run, minus the ones this version used — the `facts` rows U2 ingested,
against the `fact_usage` rows each chapter unit wrote on promotion.

**It reports the leftovers by id**, and that is the whole design. A percentage
cannot be settled: 75% tells a reader a quarter is wrong and nothing about which
quarter, so the number is read as a grade and the missing fact ships. An id can
be settled in ten seconds by opening the chapter — which is exactly what an
uncovered id asks you to do, because `fact_usage` is string matching and a fact
the writer paraphrased is reported uncovered. If the prose genuinely does not
carry it, say so: that is a gift novel missing the thing the buyer asked for,
and it is not a number to accept.

**No mandatory facts is no denominator, not a perfect score.** `0/0` is neither
1.0 nor 0.0, and a brief with no mandatory facts is the commonest run this
validator will ever see.

## 6. Report

Tell the user: the workspace path, **chapters that passed on their own versus
chapters that needed the patch**, total words, the path of any chapter whose
style pass was discarded, the judge's mean with any unscored criterion named,
and the uncovered mandatory fact ids. Then name the file worth opening first —
a `critiques/*.json` from a chapter that was rejected once, because that is what
shows the gate working.

That first figure used to read "approved versus accepted with warnings", which
was the old exit's vocabulary surviving in the report after it had been removed
from the gate. Under `patch_then_halt` nothing is accepted with warnings: either
a chapter reached the threshold or the run halted long before you were started.

Read those figures out of the critiques, the gate rows and `state.json`. A
number you remember is a number you estimated, and this unit remembers nothing.

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the run ends when your process does.
