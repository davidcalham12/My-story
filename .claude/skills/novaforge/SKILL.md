---
name: novaforge
description: Write a novel from a premise by orchestrating the eight NovaForge subagents through the six stages of specs/flow.yaml, with a per-chapter quality gate. Use when asked to draft, generate or continue a NovaForge novel, or when asked to run a stage of the pipeline.
---

# NovaForge — the orchestration procedure

You are the orchestrator. The eight agents in `.claude/agents/` are subagents
you dispatch with the Agent tool. This file is the procedure; `specs/flow.yaml`
is the contract it implements.

**The premise decides what kind of book this is.** Not this file, not the agent
files and not the config. All eight agents used to open by declaring themselves
hard science fiction; none does now, and `novel.tone` is null until you set it.
Read the genre off the premise and carry it into every prompt.

**Read `specs/flow.yaml` and the config before you start.** They are not
decoration — the stage order, the gate thresholds and every number below come
from them, and they may have changed since this file was written. Where this
file and the spec disagree, the spec wins and you should say so.

## 0. Set up the run

Ask for, or take from the request:

- **the premise** — one or two sentences
- **the profile** — `tiny` (3 chapters), `small` (8), `medium` (18), `full` (34)

Then:

1. Read `config/novel.config.json`, then read `config/profiles/<profile>.json`
   and overlay it. A profile is partial: it states what it changes and nothing
   else, so overlay key by key rather than replacing whole sections. The profile
   overrides the whole `bible` block, and that matters: those counts are the
   size of the book's canon, and a three-chapter run handed a twelve-chapter
   Story Bible spends every chapter introducing things it has no room to use.

2. **Decide the genre and say so.** `novel.tone` is null unless somebody set it.
   Read it off the premise and write what you decided into the merged config
   before anything else runs.

   This is the single most consequential line in the run. It reaches every one
   of the eight agents, none of which has a genre of its own any more. It used
   to say `hard-scifi` permanently, and the results were exactly what you would
   expect: a cyberpunk premise came back as an engineering document with a
   bandwidth budget, and a premise about a pop star trying quesadillas came back
   unrecognisable. Name the genre the way a reader would — "cyberpunk noir,
   street level", "warm comic realism", "cosy mystery" — not the way a
   taxonomy would.

   Then, if the genre is not science fiction, **look at the critic list**.
   `quality_gate.critics` includes `science`, which is the world critic under a
   historical name: it audits the draft against the bullets under `## Rules` in
   `bible/world.md`, whatever kind of rules those are. That works for any genre
   as long as the rules are the story's own. What does not work is a world bible
   full of arithmetic in a story with no room for it — see FLOW-1.
3. Derive a slug from the premise — lowercase, hyphenated, at most 40
   characters — unless one was given.
4. Create the workspace: `output/<slug>/` with `bible/`, `chapters/`,
   `critiques/`, `dist/` and `logs/`.
5. Write the merged configuration to `output/<slug>/config.snapshot.json`. A run
   nobody can reconstruct the settings of is a run nobody can explain.
6. Write `output/<slug>/state.json` with the premise, the profile, the slug and
   an empty `chapters` list.

**Tell the user the plan before you spend anything**: the genre you read off the
premise, the profile, the chapter count, the target words per chapter and how
many subagent calls that implies. Put the genre first — it is the one they can
correct in a word, and the one that makes every other number worthless if it is
wrong.
A `full` run is thirty-four chapters through a gate — it is not a thing to start
by accident.

## 1. FLOW-1 — worldbuild

Dispatch `worldbuilder`. Its prompt must carry, because it has no Read tool:

- the premise, verbatim
- `novel.tone` — the genre you decided, in the words you decided it in
- `novel.chapters`
- the counts from `bible`: `factions`, `technology_entries`, `world_rules`,
  `world_min_words`, `world_max_words`
- the absolute path of the workspace, so it can write `bible/world.md`

When it returns, read `bible/world.md` yourself and check the `## Rules` heading
exists with at least `bible.world_rules.min` bullets under it. If it does not,
dispatch again with that as the correction. Nothing downstream can recover a
missing rules section: the science critic reads from under that heading and
nowhere else.

## 2. FLOW-2 — characters

Dispatch `character-architect`. Its prompt must carry the **full text of
`bible/world.md`** — it has no Read tool either — plus the premise, the tone,
and the counts for `characters`, `timeline_rows` and `mysteries`.

Carry `novel.names` too. It is passed to the agent verbatim and its default,
`familiar`, asks for names a reader can say out loud and tell apart. A run once
produced five four-syllable names inside fourteen hundred words, and a reader
who cannot keep the cast straight has already stopped reading.

It returns the canonical character names. **Keep that list.** Every later prompt
carries it, and it is what the continuity critic checks spelling against.

## 3. FLOW-3 — outline

Dispatch `plot-architect` with all four Bible files quoted in full, the chapter
count, the canonical names, and `novel.promises` and `novel.beats_per_chapter`.

It returns the outline as text. **You** write it to `output/<slug>/outline.md`.

### Audit the commission before anyone writes it

Dispatch `science-critic` with the outline entries and `bible/world.md`, asking
it whether every beat can happen **without breaking a rule**. There is no draft;
it is judging the commission, not prose.

This is the cheapest check in the pipeline and it earns its place. Run against a
real outline it cost $0.07-$0.13 and found two defects the full five-critic gate
never caught across three attempts and a patch: a beat that had a field-team
member set a permanent RECOVERED line the rules reserve to the duty controller,
and a beat that fired an automatic callout at exactly twenty minutes when the
rule says more than twenty. Both were cheap to fix in the outline and expensive
to discover in a chapter.

Ask for a finding per violated clause, not per beat — a rule that says **who may
act, on what evidence, and within what window** is three clauses, and a beat can
satisfy the window while using evidence the rule never admitted.

**Also ask which rules are AMBIGUOUS, and treat that as a finding.** This is not
padding. A run deadlocked on a rule that read two ways: the science critic held
that a correction line needs its own two confirmations, three separate audits
held that it inherits the original line's, and both readings are defensible from
the same sentence. Two critics then pulled in opposite directions on the same
draft for three attempts and the chapter could not pass. An ambiguous rule does
not fail loudly; it fails as a disagreement nobody can arbitrate, and the place
to fix it is `bible/world.md`, before FLOW-4.

Where a beat is impossible or a rule reads two ways, dispatch `plot-architect`
again with that finding, or fix the rule, and do not start FLOW-4 on a commission
that contradicts canon. A chapter cannot be redrafted into obeying a rule its own
outline told it to break.

### Write the audit down in this exact shape

`output/<slug>/critiques/outline.audit.json`, and **these keys, spelled this
way**:

```json
{"stage": "FLOW-3", "agent": "science-critic", "ts": "<a real clock reading>",
 "verdict": "clean" | "defects",
 "violations":  [{"chapter": 3, "beat": 4, "rule": "R1", "clause": "...",
                  "severity": "high", "claim": "...", "fix": "...",
                  "arbitration": "UPHELD ... | OVERRULED ..."}],
 "ambiguities": [{"rule": "R5", "clause": "...", "reading_a": "...",
                  "reading_b": "...", "outline_assumes": "a" | "b" | "neither",
                  "arbitration": "...", "applied": "..."}]}
```

**Both arrays always, even when empty.** Two real runs wrote this file two
different ways — one used `ambiguities`, the other `ambiguous_rules` with a
`violations_note` beside an empty `violations` — and a reader that wants to ask
"how often does the audit find something" cannot, because the question has two
spellings. v1 wrote its critiques in three shapes for the same reason: nobody
said which. **A contract nobody stated cannot be enforced, and this is the
statement.**

Start every `arbitration` with `UPHELD` or `OVERRULED`. The word is read by a
script; the sentence after it is for a person.

Then split it on `### Chapter N — Title` and keep one entry per chapter. If the
split yields fewer entries than `novel.chapters`, the outline is malformed —
dispatch again rather than writing chapters from nothing. Anything other than
that exact heading shape, `**Chapter 1: Title**` most often, breaks the split.

## 4. FLOW-4 — chapters, with the gate

For each chapter `n` from 1 to `novel.chapters`:

### Assemble the writer's context — and nothing more

The prompt for `chapter-writer` contains exactly:

- the four Bible files, in full
- **this chapter's outline entry only**
- the rolling summary, capped at `context.max_summary_words` words
- the canonical character names
- the chapter number, its title, and `novel.words_per_chapter.target`

**It never contains a previous chapter's prose.** That is the architectural claim
of the project. Here it holds for two reasons that are worth keeping separate:
you do not put prose in the prompt, and the subagent has only `Glob`, which
returns paths and cannot return contents — so the guarantee does not rest solely
on your discipline. Do not add `Read` to that agent to make something easier.

### Run the gate

The critics are `quality_gate.critics` in the config. **Six now** — LOOP-003
added the fifth, SPEC-006 the sixth — and every one of them scores from the first
attempt:

| characteristic | who runs it | how |
|---|---|---|
| `continuity` | subagent | dispatch `continuity-critic` with the draft and the Bible |
| `science` | subagent | dispatch `science-critic` with the draft and `bible/world.md` |
| `outline` | subagent | dispatch `outline-critic` with the draft and **this chapter's outline entry, beats numbered** |
| `prose` | subagent | dispatch `prose-critic` with the draft, the genre and the tone |
| `length` | **you** | count words in the shell; score 10 inside the band, 0 outside |
| `chatter` | **you** | scan for preamble; score 0 if the draft does not begin with `# Chapter` |

`outline` exists because the others all ask whether the draft is *correct* and
none asks whether it is *the chapter the outline commissioned*. A draft that is
consistent with the Bible, obeys the world, sits in the word band and is about
something else entirely used to pass this gate cleanly.

**`prose` asks the question none of the other five ask: is it well written?** It
returns quoted `major` and `minor` findings and **no score** — you compute it:

```bash
python -m backend.chapters.check_prose output/<slug>/chapters/chNN.attemptK.md   output/<slug>/bible/characters.md          # the mechanical term
```

```
prose = 10 − 3·mechanical − 2·major − 1·minor,   floored at 0
```

`mechanical` is the count of defects **that script** found, never a number the
critic gives you. A critic asked to count what a script already counted will
disagree with it, and then the score depends on which of the two you asked. If
the critic reports a mechanical defect anyway, drop it: it is already charged.

**Check its arithmetic, as you do for `outline`.** The critic's `notes` state its
own counts; recompute them from the findings it actually quoted. A finding
without a quote is not a finding — do not count it, and say so in the gate row.

Dispatch the four critic subagents **in the same message**, as four tool calls in
one reply. Not "one after the other quickly" — in the same reply. They are
independent, they judge a text that is already fixed, and nothing either returns
changes what the other is asked.

This is the easiest minute in the run to lose, and it keeps being lost. Two runs
have now been measured: the first ran them in series in two chapters out of
four, the second in three out of four. In the second run continuity and science
started fifty seconds apart on chapter 2 and thirty seconds apart on chapter 3,
and each of those gaps is one critic finishing before the other was asked.

Check yourself afterwards: subtract the two `ts` values you logged for a
chapter's critics. If they are more than a few seconds apart they ran in series,
and that is a fact worth writing in the row's `note` rather than one to leave
for whoever reads the log later.

Run `length` and `chatter` **first**, before dispatching anything, because they
are arithmetic and cost nothing. If `chatter` scores 0 — the draft does not begin
with `# Chapter`, so it is not a chapter yet — redraft on that alone and do not
spend two model calls judging the prose of something that has to be rebuilt
anyway. Do *not* take the same shortcut when only `length` fails: an off-band
draft is still a chapter, and the continuity and science findings are what the
redraft is steered by. Skipping them there buys a minute and spends it on a
worse second draft.

Count words with a command, never by eye:

```bash
wc -w < output/<slug>/chapters/ch0N.md
```

The band is `words_per_chapter.min` to `.max`, widened by `tolerance_pct`.

Aggregate with `quality_gate.aggregate` — `min`, so **a chapter is only as good
as its worst characteristic**. A chapter passes when **all five are at 8 or
above**, not when the average is.

**Write every attempt's draft to `chapters/ch0N.attemptK.md` before you score
it.** This is not bookkeeping. The rejected drafts are the only thing "the
writer changed only what was cited" can be measured from, and a run that
overwrites them has destroyed the evidence rather than saved a file. The
measurement script reports that as *not measurable*, which is the honest answer
and a useless one.

### The three attempts, and why the third is different

`quality_gate.max_revisions` is 2, so there are three attempts. The principle
LOOP-003 runs on is that **each failed attempt must make the next one easier,
not merely better informed.** So the feedback escalates in concreteness until
there is nothing left to interpret:

| attempt | what the writer gets | what it is asked to do |
|---|---|---|
| 1 | the Bible, its outline entry, the rolling summary | write the chapter |
| 2 | the above, plus a **level-1 sheet**: per finding, the exact quote, what is wrong, against what, and *how it should read* — described, not written | correct only what is marked, touching as few lines as possible |
| 3 | the above, plus a **level-2 sheet**: per open finding, **the literal replacement sentence, written by the critic** | integrate those sentences; do not rewrite |

On the second attempt the writer interprets a description. On the third it does
not interpret at all — it integrates a given text. And if even that fails:

**You do not work out what happens next. You ask, and you obey.** After every
scored attempt, run:

```bash
echo '{"aggregate": <min>, "attempt": <n>, "patched": <true|false>}' \
  | python -m backend.chapters.decide
```

It answers `accept`, `retry`, `patch` or `halt`, with its reason. **Do what it
says, including when you disagree with it.** If you think it is wrong, say so to
the user in the report — do not act on the disagreement.

This used to be a paragraph you read and applied yourself, and it was moved into
code deliberately (SPEC-004). You read it at the worst possible moment: a run has
been going for an hour and is about to be thrown away. That is exactly when "it
is only just below" gets rationalised, and `accept_with_warnings` — the exit this
replaced, which put a chapter that had failed three times into the book with a
note in the margin — is what rationalising looks like when it wins.

What each answer asks of you:

- **`accept`** — promote the draft to `chapters/chNN.md`. If the answer's
  `verdict` is `patched`, record `patched`, not `accept`: it passed, and it did
  not pass on its own.
- **`retry`** — redraft against the sheet at the level the reason names.
- **`patch`** — apply the critics' own replacement sentences by literal
  substitution, then rescore. For `length` and `chatter` this is trivial — trim
  words, fix the first line. For the three model characteristics it is the
  sentence the critic proposed, which you **arbitrate before applying**: you have
  overruled a false finding before, and a replacement built on one would write
  the error into the book by hand. Then ask again with `"patched": true`.
- **`halt`** — **stop the run.** Do not promote the chapter, do not run FLOW-5 or
  FLOW-6. By construction the only way to arrive here is a critic's replacement
  that was itself wrong and that arbitration did not catch, and that is worth a
  person looking at before another chapter is written.

**Where this guarantee is weakest, said plainly:** `outline` is the hardest to
patch, because a missing beat is not a sentence but a paragraph. Its level-2
replacement is that paragraph, written by the critic in the book's voice. That
is a larger thing to insert blind than a corrected clause, and it is the part of
"it will pass by the third" that rests on the most.

### The sheet

`specs/loops/LOOP-003/sheet_template/v01.md` is the format and it does not vary.
Fill it, then **run `node specs/loops/LOOP-003/validate-sheet.mjs <file>` and do
not send a sheet that fails.** An unsent sheet is a bug caught; a half-filled one
is an attempt wasted, because a writer without the quote is back to guessing,
which is the state attempt 1 was already in.

Five rules the sheet obeys, each of which is in the validator:

1. **All five scores, including the passing ones.** The writer has to know what
   is already right in order to leave it alone.
2. **An explicit DO NOT TOUCH list.** In the saved run the writer changed two
   lines and then one. That restraint is the thing to protect: a writer that
   takes the opportunity to improve an approved paragraph is the commonest way
   a score that was passing stops passing.
3. **Four fields per finding** — quote, what is wrong, against what, how it
   should read — or it does not go. The quote is literal. "Against what" points
   at the Bible or the outline, **never at a previous chapter**: the writer has
   never seen one, and this sheet is not the hole through which it finally does.
4. **A RESOLVED list.** The writer learns what worked, and so does the loop —
   which phrasing of "how it should read" produced a correction first time is
   the only thing this loop actually learns.
5. **Every finding, worst first, none trimmed.** A finding held back to keep the
   sheet short is a finding that fails again next attempt.

Write each sheet to **`specs/loops/LOOP-003/sheets/<slug>/chNN.attemptK.md`** as
you send it. The slug is not decoration: the flat path has no run dimension, and
the second run to use this loop silently overwrote the first's chapter 1 and
chapter 3 sheets. They were recoverable from git and were restored byte-exact,
which is luck. The sheets are the only record of what the writer was actually
told, and §8.1 of LOOP-003 says the one thing this loop learns is read out of
them.

### The late finding

A critic that raises something on the third attempt which was equally present in
the first draft, and said nothing then, has moved the goalposts. Mark that
finding **late**: record it in `specs/loops/LOOP-003/late_findings.jsonl`, patch
it if you can, and **do not let it block the chapter**.

Without this rule the third-attempt guarantee does not exist, because something
new can always appear. A critic that accumulates late findings is a critic that
does not read the same way twice, and that is a problem to fix in the critic
rather than in the chapter.

### Four rules for the redraft, each of which was once got wrong

These were found by running the pipeline, not by reading it. Every one of them
made the gate weaker in a way that looked like it was working.

**1. Hand back the draft, not only the findings.** A redraft prompt that carries
the findings without the text they quote is asking for "repair these and change
nothing else" when there is nothing to change — so the writer starts a fresh
chapter each round, against findings quoting text that is no longer in it, and a
rewrite can come back worse than what it replaced.

This is not a hole in the context policy, and the distinction is the whole
point: the policy forbids a **previous chapter's** prose. This is the writer's
own rejected draft of the chapter it is writing now.

**2. Ask for substitutions, not for a chapter.** Rather than the whole chapter
back, ask for the exact sentences to replace:

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

**3. A critic that returns no usable verdict is excluded, never counted as a
pass.** If `continuity-critic` or `science-critic` comes back with something you
cannot parse as a score, do not substitute one: 10 invents an approval and 0
invents a rejection. Leave it out of the `min`, record it as unscored, and say
so in the gate row's `note`. A gate running on three critics is weaker than one
running on four, and that is the truth of what happened.

**4. Keep the best draft, not the last.** Track the highest aggregate as you go.
A chapter whose first draft scored 7 and whose third scored 4 must ship the 7 —
a rewrite is not guaranteed to be an improvement and the gate must not assume it
was. An *accepted* draft is the one that passed, which is not always the best.

Two things that cost nothing and are worth doing. Tell the writer when it is on
its last allowed draft, because one that knows it spends its effort on the
findings rather than on flourishes. And after a redraft, check whether the
quoted passages are still present verbatim — if one survived, the repair did not
happen, and that is arithmetic rather than judgement.

### Check the prose for what a script can see

Before promoting a draft, run:

```bash
python -m backend.chapters.check_prose output/<slug>/chapters/chNN.md
```

It reports a sentence repeated word for word, a heading glued to the previous
line, and a paragraph echoing another's opening. **It does not gate.** There are
six characteristics, and this script is not a seventh. It never blocks a
chapter on its own — its count feeds `prose`, which does.

What it finds, you fix the way you fix anything else: a literal substitution,
quoted, in the next sheet. A duplicated sentence is exactly the shape redraft
rule 2 wants — the quote is the identity, and removing it changes nothing the
findings did not name.

What it **cannot** see is in its own output, under `not_checked`. A clean result
means three mechanical defects are absent, not that the prose is good. Nothing
here measures that.

**Write its output to `critiques/chNN.prose.json`, clean or not.** A check whose
result exists only in this conversation cannot be read afterwards by anyone, and
"we ran it and it was fine" is not a record. A clean file is the evidence the
check ran at all — which is exactly why `length` and `chatter` get critique files
even though you computed them yourself.

### Record it

Write, for each chapter:

- `chapters/ch0N.md` — the accepted draft
- `chapters/ch0N.summary.md` — a summary you write, under
  `context.max_summary_words`, which becomes part of the next chapter's rolling
  summary. This is the only channel between chapters, so it carries what a later
  chapter cannot be written without: what changed, who now knows what, and what
  is still open.
- `critiques/ch0N.<critic>.json` — **one per characteristic, all five**,
  every iteration's score and findings, not just the last. `length` and
  `chatter` get files too even though you computed them yourself: recent runs
  folded those two into `chNN.gate.json` and wrote no file, and the measurement
  script then cannot see five scores and reports every chapter as never having
  passed. **The rejected draft's critique is the evidence that the gate did
  something**, and it is the first thing worth opening when someone asks whether
  this pipeline is real.

  **The envelope is an object, not a bare array**, because the panel reads the
  fields around the iterations:

  ```json
  {"critic": "continuity", "chapter": 2, "kind": "model",
   "agent": "continuity-critic", "drafts": 2,
   "iterations": [
     {"iteration": 1, "score": 4, "findings": [
       {"kind": "timeline-math", "severity": "high",
        "quote": "<copied from the draft>",
        "claim": "<what is wrong>",
        "fix": "<what would fix it>",
        "reference": "bible/timeline.md, Day 2"}]},
     {"iteration": 2, "score": 10, "findings": []}]}
  ```

  A run wrote the array on its own, with `problem` where this says `claim`. Both
  are read now, but write this shape: the reader that had to be taught to accept
  the other one was taught after it had already put a blank page in front of
  someone.

Append one row per subagent call to `logs/agents.jsonl`: timestamp, stage, agent,
chapter, iteration, verdict. Update `state.json` after each chapter so an
interrupted run can be resumed from the last accepted one rather than restarted.

**Write the bookkeeping in the same reply that dispatches the next thing.** A
measured run spent twenty-five minutes of wall clock on twelve and a half
minutes of subagent work: half the run was the orchestrator between calls,
writing one file per reply. The critique files, the gate row, the log rows and
`state.json` for chapter *n* are all independent of each other and of chapter
*n*+1's draft, so issue them as parallel tool calls alongside the `Agent` call
that starts the next chapter. They then cost nothing at all, because the writer
is working while they are written.

The one that cannot move is `chapters/ch0N.summary.md`. The next chapter's
prompt carries it, so it is written before that dispatch, not beside it.

**And one `gate_decision` row per iteration, in the same log.** This is not
optional and it is not the same thing as the critique file. A run once wrote
complete, careful `chNN.gate.json` files and no gate rows, and the panel's whole
Quality screen was empty for a run whose gate had sent a chapter back and got a
better one — the work happened and the record of it was in a place nothing reads.
The shape:

```json
{"ts":"...","event":"gate_decision","stage":"FLOW-4","chapter":2,"iteration":1,
 "scores":{"length":10,"chatter":10,"continuity":10,"science":6},
 "aggregate":6,"threshold":8,"verdict":"retry","note":"..."}
```

`verdict` is `accept`, `retry`, `patched` or `halt` — these four words, not
`accepted`/`rejected`, and the `attempts` table's CHECK admits no others: write
anything else and the insert fails.

**There is no verdict for "kept below the threshold".** That was
`accept_with_warnings`, which `patch_then_halt` replaced: a draft still under the
threshold after the patch does not get a row saying so and go into the book — it
gets `halt`, and the run stops. `patched` is the row for a draft the patch
brought up to the threshold: it passed, and it did not pass on its own, and a
reader is entitled to both facts.

**Timestamp from a clock, not from an estimate.** The same run stamped its
twenty-four rows across twenty-four minutes and had actually taken seventy-two.
Nothing warned anybody, because a plausible number and a measured one look
identical once written down. Read the real time — `date -u +%Y-%m-%dT%H:%M:%SZ`
— rather than working out what it probably is.

**Record `tokens` and `model` on every agent row, for every stage.** The Agent
tool reports `subagent_tokens` in its result, and a task notification repeats it;
take the figure from there and write it down.

`model` is the **full model id**, not the family word. The agent files say
`model: opus` because Claude Code resolves that to whichever Opus is current;
`config/pricing.json` is keyed by `claude-opus-5` and `claude-sonnet-5`. Four
runs wrote `opus` and `sonnet`, no key matched, and every one of them showed no
cost at all — which reads as "this run was free" rather than "the name did not
match the price list". The panel now folds the family word in, but it can only do
that while there is exactly one Opus rate on file. Write the id.

Three things about that figure, because getting them wrong makes the numbers
worse than absent:

- **It is cumulative across a resume.** An agent sent back for a redraft reports
  the running total for the whole agent, not the cost of the second attempt. Log
  the *difference* from its previous total, so each row is one attempt.
- **It is a single total**, with no input/output split. Do not invent one.
- **A blocked or wasted call still costs.** Log it with its tokens and the reason
  it produced nothing. The first run of this pipeline spent 17,479 tokens on a
  rewrite the Write tool refused, and that is exactly the kind of number a
  dashboard exists to surface.

Without these fields `tools/export_to_langfuse.py` ships the run with no usage
and no cost, and there is nothing to observe.

## 5. FLOW-5 — style

Dispatch `style-editor` for **every approved chapter in one message**. The
passes are independent — that is the whole premise of the stage, one voice
applied to chapters written in isolation — so there is no reason for chapter 3
to wait on chapter 1.

Dispatch `publisher` in that same message. FLOW-6 is drawn after FLOW-5 in the
flow spec, but read what the synopsis is written from: the Bible, the outline and
the chapter summaries. None of those is touched by the style pass. Waiting for
the style passes to finish before starting it buys nothing and costs a round.

**Check its work with arithmetic.** Count the words in what it returns and
compare with what you sent. If the counts differ, the pass rewrote something —
discard it and copy the unedited chapter to `ch0N.final.md` instead, and tell the
user which chapters that happened to. The published text must be the text the
gate approved.

## 6. FLOW-6 — publish

Dispatch `publisher` with the Bible, the outline and the chapter summaries — not
the chapters; a synopsis is written from canon. Give it
`outputs.synopsis.words.min/max` and `comparables`. Write the result to
`synopsis.md`. Dispatch it alongside the style passes, as FLOW-5 says: it reads
nothing they write.

Then **assemble `dist/book.md` yourself**, in the shell, by concatenating the
`.final.md` files in order with the synopsis in front if
`outputs.markdown.include_synopsis` is true. Do not ask a subagent to do this.
Concatenation is a mechanical transformation, and a model asked to perform one
will paraphrase a sentence in the middle that the gate already approved.

PDF export is not available in this architecture — it was a Python module, and
`outputs.formats` reads `["markdown"]` here. If a config asks for `pdf`, say so
plainly rather than producing something and calling it a PDF.

## 7. Report

Tell the user: the workspace path, **chapters that passed on their own versus
chapters that needed the patch**, total words, and the path of any chapter whose
style pass was discarded. Then name the file worth opening first — a
`critiques/*.json` from a chapter that was rejected once, because that is what
shows the gate working.

That first figure used to read "approved versus accepted with warnings", which
was the old exit's vocabulary surviving in the report after it had been removed
from the gate. Under `patch_then_halt` nothing is accepted with warnings; either
a chapter reached the threshold or the run halted.

---

## Where the time goes

Measured, on a three-chapter run that logged `duration_ms` on every call:
**nineteen subagent calls totalling twelve and a half minutes, inside
twenty-five minutes of wall clock.** Half the run was not the models at all. It
was the orchestrator between them — reading a file back, counting words, writing
a critique, appending a log row, one reply at a time.

That changes where the work is. The subagent time is mostly irreducible without
giving something up; the other half is round trips, and round trips are free to
collapse.

**What costs nothing.** Both critics in one reply. All style passes and the
publisher in one reply. The bookkeeping for chapter *n* in the same reply as the
dispatch for chapter *n*+1. Skipping the model critics on a draft that
failed `chatter`. None of these changes a word that reaches the reader, and
together they are worth more than any of the trades below.

**What is not available.** The chapters cannot overlap. Chapter *n* is written
from the rolling summary of chapters 1..*n*-1, so starting two at once means
writing the second from a summary that does not exist yet. That is not a
scheduling detail — the summary chain is the only channel between chapters and
the reason the isolation is survivable at all. FLOW-1, 2 and 3 are sequential for
the same kind of reason: each is written from the one before.

**What is worth knowing about the numbers.** The three Bible stages are the
slowest calls in the run — 101s, 135s and 77s — and they are also the three that
everything downstream is written from. They are the last place to economise.
Chapter drafts, by contrast, came back in about fifteen seconds each. A run is
not slow because the chapters are long.

**What would be faster and would cost something.** Say which, plainly, rather
than doing any of it quietly:

- a smaller model for the writer or the critics — fewer minutes, different prose,
  and a gate judged by a weaker judge
- fewer critics, or a lower threshold — fewer rounds only because fewer drafts
  get sent back
- one draft, no gate — roughly half the wall clock of a run that redrafts, and
  then the pipeline is a prompt with extra steps

None of those is the orchestrator's decision to make.

---

## What this architecture does not give you

State these when a reader asks what the pipeline guarantees. They are honest
limits, not caveats to bury.

**The gate is not reproducible.** Two of the four critics are models. The same
draft can score 8 one run and 7 the next, so "it passed the gate" is a statement
about one run and not a property of the text. The `length` and `chatter` critics
*are* arithmetic and do reproduce.

**There is no tamper-evident audit.** `logs/agents.jsonl` is a record you write,
not a hash chain, and anyone who can edit the file can edit it undetectably.

**There is no enforced budget ceiling.** Nothing stops a run before it spends.
Read the call count out of the plan in step 0 and decide there.

**It does not run unattended.** This is a procedure a person drives inside Claude
Code. It has no headless entry point and will not run in CI.

The `main` branch of this repository holds the Python implementation, which has
all four of those and a byte-reproducible fixture. If what you need is an
auditable harness that runs on its own, that branch is the one — this one trades
those properties for subagents whose isolation is structural rather than
asserted.
