# U4.n — one chapter (FLOW-4)

One unit: **one** chapter, from its first draft to a promoted `chNN.md` with its
summary and its critiques on disk. Read `.claude/skills/storymaker/SKILL.md`
first — the six characteristics, `min`, the threshold, the three attempts,
`patch_then_halt`, the sheet's five rules, the verdict vocabulary, the logging
duties and the ceiling are all there, and none of them is repeated here.

Your prompt names one chapter number. Do not draft another, do not read another
chapter's prose, and do not tidy a previous chapter you notice is wrong — say so
and let a person decide.

## 1. Assemble the writer's context — and nothing more

The prompt for `chapter-writer` contains exactly:

- the four Bible files, in full
- **this chapter's outline entry only**
- the rolling summary, capped at `context.max_summary_words` words, built from
  the `chNN.summary.md` files your prompt names
- the canonical character names
- the chapter number, its title, and `novel.words_per_chapter.target`

**It never contains a previous chapter's prose.** That is the architectural claim
of the project, and it holds for two reasons worth keeping separate: you do not
put prose in the prompt, and the subagent has only `Glob`, which returns paths
and cannot return contents — so the guarantee does not rest solely on your
discipline.

The Bible is fixed and the outline entry is one chapter's. **The summary chain is
the only part of a chapter's packet that can grow with the book**, which is why
`max_summary_words` is the whole of the claim that chapter thirty-four's prompt
is the size of chapter one's.

## 2. Write every attempt down before you score it

`chapters/chNN.attemptK.md`, before scoring, every time. This is not
bookkeeping: the rejected drafts are the only thing "the writer changed only
what was cited" can be measured from, and a run that overwrites them has
destroyed the evidence rather than saved a file. The measurement script then
reports *not measurable*, which is the honest answer and a useless one.

## 3. Run the gate, in this order

**`length` and `chatter` first, before dispatching anything**, because they are
arithmetic and cost nothing.

```bash
wc -w < <run_dir>/chapters/chNN.attemptK.md
```

Count with a command, never by eye. The band is `words_per_chapter.min` to
`.max`, widened by `tolerance_pct`.

If `chatter` scores 0 — the draft does not begin with `# Chapter`, so it is not a
chapter yet — redraft on that alone and do not spend four model calls judging the
prose of something that has to be rebuilt anyway. **Do not take the same
shortcut when only `length` fails:** an off-band draft is still a chapter, and
the continuity, science, outline and prose findings are what the redraft is
steered by. Skipping them there buys a minute and spends it on a worse second
draft.

**Then dispatch the four model critics in the same message**, as four tool calls
in one reply — subject to the concurrency sum in SKILL.md §7. Not "one after the
other quickly": in the same reply. They are independent, they judge a text that
is already fixed, and nothing either returns changes what the others are asked.

This is the easiest minute in the run to lose, and it keeps being lost. Two runs
were measured: the first ran them in series in two chapters out of four, the
second in three out of four, with continuity and science starting fifty seconds
apart on chapter 2. Check yourself afterwards by subtracting the two `ts` values
you logged; if they are more than a few seconds apart they ran in series, and
that belongs in the gate row's `note` rather than left for whoever reads the log.

### Scoring `prose`

`prose-critic` returns quoted `major` and `minor` findings and **no score**. You
do not compute one either — you ask:

```bash
echo '{"major": <n>, "minor": <n>}' \
  | python -m backend.chapters.score_prose <run_dir>/chapters/chNN.attemptK.md \
                                           <run_dir>/bible/characters.md
```

It runs the mechanical check itself and applies

```
prose = 10 − 3·mechanical − 2·major − 1·minor,   floored at 0
```

returning the score, its arithmetic in `why`, and the mechanical defects quoted
so you can put them in the sheet.

**You supply only the two counts, because they are the only part you know.** The
mechanical term is not an input: a critic asked to count what a script already
counted will disagree with it, and then the score depends on which of the two you
asked. If the critic reports a mechanical defect anyway, drop it — it is already
charged, and one fault charged twice costs the chapter six points instead of
three.

**Count only findings the critic actually quoted.** A finding without a quote
cannot be sent to the writer and cannot be verified afterwards, so it is not a
finding; say so in the gate row rather than letting it lower a score in silence.
**Check the critic's own arithmetic against what it quoted**, here and for
`outline`: its `notes` state its counts, the findings are what it can defend.

## 4. Ask what happens next, and do it

Aggregate with `min` and ask `decide` (SKILL.md §3). What each answer asks of
you:

- **`accept`** — promote it, and **do not write `chapters/chNN.md` yourself**:

  ```bash
  python -m backend.chapters.promote <run_dir> <n>
  ```

  It re-reads the chapter's critiques, recomputes the aggregate, asks `decide`
  again and copies the draft **only on `accept`**; on anything else it refuses,
  exits non-zero and leaves the file untouched. That is deliberate belt and
  braces: on a real run a chapter scored 5 and was copied into the book anyway,
  because writing that file was a one-line copy and nothing stood between the
  copy and the book. You still hold `Write`; the point is that the correct path
  is now the shorter one.

- **`retry`** — redraft against the sheet at the level the reason names (§5).

- **`patch`** — apply the critics' own replacement sentences by literal
  substitution, then rescore with `"patched": true`. For `length` and `chatter`
  this is trivial — trim words, fix the first line. For the four model
  characteristics it is the sentence the critic proposed, which you **arbitrate
  before applying**: a false finding has been overruled before, and a replacement
  built on one would write the error into the book by hand.

- **`halt`** — **stop the run.** Do not promote the chapter and do not write a
  summary. Report what happened and end: the conductor stops the sequence, and
  no later unit starts.

## 5. Redrafting, and four rules each of which was once got wrong

These were found by running the pipeline, not by reading it. Every one of them
made the gate weaker in a way that looked like it was working. (The rule about a
critic that returns no usable verdict, and the rule about late findings, are in
SKILL.md §3.)

**1. Hand back the draft, not only the findings.** A redraft prompt that carries
the findings without the text they quote is asking for "repair these and change
nothing else" when there is nothing to change — so the writer starts a fresh
chapter each round, against findings quoting text that is no longer in it, and
the rewrite can come back worse than what it replaced.

This is not a hole in the context policy, and the distinction is the whole
point: the policy forbids a **previous chapter's** prose. This is the writer's
own rejected draft of the chapter it is writing now.

**2. Ask for substitutions, not for a chapter.**

```json
{"patches": [{"find": "<text copied EXACTLY from the draft>",
              "replace": "<the corrected text>",
              "why": "<which finding this addresses>"}]}
```

Apply them yourself, matching `find` literally. Two things follow: anything the
findings do not name **cannot** change, because you do not touch it; and "was
this finding addressed" stops being a judgement — either the quoted text is
still there or it is not. A `find` that does not match is skipped and counted,
never applied approximately. If no patch applies at all, fall back to a full
rewrite rather than burning the attempt on nothing, and record which happened.

**3. Keep the best draft, not the last.** Track the highest aggregate as you go.
A chapter whose first draft scored 7 and whose third scored 4 must ship the 7 —
a rewrite is not guaranteed to be an improvement and the gate must not assume it
was. An *accepted* draft is the one that passed, which is not always the best.

**4. Two things that cost nothing.** Tell the writer when it is on its last
allowed draft, because one that knows spends its effort on the findings rather
than on flourishes. And after a redraft, check whether the quoted passages are
still present verbatim — if one survived, the repair did not happen, and that is
arithmetic rather than judgement.

## 6. The mechanical prose check, which is not a seventh characteristic

```bash
python -m backend.checks FLOW-4 <run_dir> <n>
```

It reports a sentence repeated word for word, a heading glued to the previous
line, a paragraph echoing another's opening, and whether the summary is inside
its cap. **It never blocks a chapter on its own** — its count feeds `prose`,
which does. What it finds, you fix the way you fix anything else: a literal
substitution, quoted, in the next sheet. A duplicated sentence is exactly the
shape redraft rule 2 wants.

What it **cannot** see is in its own output, under `not_checked`. A clean result
means three mechanical defects are absent, not that the prose is good.

**Write its output to `critiques/chNN.prose.json`, clean or not.** A check whose
result exists only in this conversation cannot be read afterwards by anyone —
and this conversation ends with this chapter. "We ran it and it was fine" is not
a record.

## 7. Record it

- **`chapters/chNN.md`** — written by `promote`, not by you.

- **`chapters/chNN.summary.md`** — a summary you write, under
  `context.max_summary_words`. This is the only channel between chapters, so it
  carries what a later chapter cannot be written without: what changed, who now
  knows what, and what is still open. It must exist before your unit ends,
  because the next chapter's prompt names it.

  The cap was being exceeded: on a real `small` run five of six summaries were
  over the 200-word cap, the worst by 23%, because a number nobody measures
  becomes a target rather than a limit. If the check reports over, **write it
  again, shorter** — you still have the chapter in front of you, which is
  exactly what the next unit will not have. Do not fix it by truncation: a
  dropped sentence costs more than the words it saves, because it is the only
  channel there is.

- **`critiques/chNN.<characteristic>.json`** — one per characteristic, **all
  six**, carrying every iteration's score and findings, not just the last. The
  envelope shape is SKILL.md §5. `length` and `chatter` get files too even
  though you computed them yourself: recent runs folded those two into
  `chNN.gate.json` and wrote no file, and the measurement script then cannot see
  six scores and reports every chapter as never having passed. **The rejected
  draft's critique is the evidence that the gate did something**, and it is the
  first thing worth opening when someone asks whether this pipeline is real.

- **One `gate_decision` row per iteration** in `logs/agents.jsonl`. This is not
  optional and it is not the same thing as the critique file: a run once wrote
  complete, careful critique files and no gate rows, and the panel's whole
  Quality screen was empty for a run whose gate had sent a chapter back and got
  a better one — the work happened, and the record of it was in a place nothing
  reads.

  ```json
  {"ts":"...","event":"gate_decision","stage":"FLOW-4","chapter":2,"iteration":1,
   "scores":{"length":10,"chatter":10,"continuity":10,"science":6,"outline":9,"prose":8},
   "aggregate":6,"threshold":8,"verdict":"retry","note":"..."}
  ```

- **Which facts the promoted chapter used**, after `promote` has written
  `chNN.md`:

  ```bash
  python -m backend.chapters.fact_usage <run_dir> <n>
  ```

  Rejected drafts are not recorded: the book is what shipped, and a fact used
  only by a draft nobody kept is not used. It is **string matching of canonical
  names and fact text against the prose, not semantics**, so a fact the chapter
  paraphrased is reported uncovered. That error runs one way and only one way —
  a covered fact reported uncovered costs a person a minute with the chapter,
  while a fact reported covered that the prose never carries would be a gift
  novel delivered without the thing the buyer asked for. U5's `mandatory_facts`
  check reads exactly these rows.

## 8. Finish

Say which attempt passed and whether it passed on its own or after a patch, and
name the critique file worth opening if the chapter was ever rejected.

---

Read only the files your prompt named — this chapter's outline entry, the Bible,
the summaries it lists. Write only to the paths it named. Then end your turn:
the next chapter is the next unit, and the conductor will not start it until
your process is gone.
