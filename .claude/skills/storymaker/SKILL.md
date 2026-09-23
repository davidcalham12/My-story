---
name: storymaker
description: The rules every StoryMaker unit obeys — the agents and their tool boundary, the six-characteristic gate, the feedback sheet, the vocabulary a script reads, the logging duties and the 100,000-token ceiling. One unit of a run is one fresh process; the unit files under `units/` say what each one does. Read this file together with the unit file your prompt names.
---

# StoryMaker — the rules a unit runs under

**You are one unit of a run, not the run.** Python is the conductor
(`backend/runs/conductor.py`): it launches a fresh process per unit of work,
hands it the paths it needs, reads its outputs off disk and launches the next
one. Your process ends when your unit is done, and nothing you hold in this
conversation survives it.

That is the whole point, and it is worth knowing why you are shaped this way.
One process used to orchestrate an entire novel, accumulating the Bible, every
draft, every critique and every sheet: measured median 147,000 tokens, peaks of
642,000. The owner requires that no part of a run exceed 100,000 concurrent
tokens (SPEC-EXAM-003). A ceiling on that single conversation would have halted
every novel; a ceiling on a unit is simply the size of the unit.

So **this file is not a procedure and will never be run start to finish.** It is
the set of rules your unit's procedure assumes. `specs/flow.yaml` is the
contract both implement: stage order, gate thresholds, iteration limits and
failure policy live there and nowhere else, and they may have changed since this
was written. Where this file and the spec disagree, the spec wins and you say so.

## The unit files

| unit | file | stages | writes |
|---|---|---|---|
| U1 world | `units/world.md` | FLOW-1 | `bible/world.md` |
| U2 cast | `units/cast.md` | FLOW-2 + the story-bible ingest | `bible/characters.md`, `timeline.md`, `mysteries.md`; the `facts` rows |
| U3 outline | `units/outline.md` | FLOW-3 + the commission audit | `outline.md`, `critiques/outline.audit.json` |
| U4.n chapter | `units/chapter.md` | FLOW-4 for **one** chapter | `chNN.md`, its attempts, its critiques, its summary |
| U5 finish | `units/finish.md` | FLOW-5 + FLOW-6 | `chNN.final.md`, `synopsis.md`, `dist/book.md`, the validations |

Read **your** unit file and this one. Reading another unit's file tells you
about work that is not yours and costs you the context this design exists to
protect.

## 0. What the conductor has already done

Before your process starts, Python has merged `config/novel.config.json` with
`config/profiles/<profile>.json` key by key, created the workspace with its
`bible/`, `chapters/`, `critiques/`, `dist/` and `logs/` subdirectories, written
the merged settings to `config.snapshot.json` and opened `state.json`. It also
told the buyer what the run would cost before it started spending it.

**Do not redo any of that, and do not re-read the two config files it merged.**
The snapshot is the configuration of this run — a run whose settings nobody can
reconstruct is a run nobody can explain, and reconstructing them from two files
and a merge rule is how two units come to disagree about the chapter count.

Every path in your unit file is relative to the run directory your prompt names.

## 1. The agents, and the boundary that is not made of discipline

The files in `.claude/agents/` are subagents you dispatch with the Agent tool.
Their `tools:` line is a structural guarantee, not a convenience:

- **`worldbuilder` and `character-architect` hold `Write`.** They are the only
  agents permitted to write the Story Bible (`flow.yaml`'s `writes_bible`), and
  they are the only two that *can*. Every other agent returns text that **you**
  write to disk.
- **Those same two hold `Read`; nobody else does.** Every other agent's prompt
  must carry in full anything it has to see. An agent with `Glob` can list paths
  and cannot open one.
- **`chapter-writer` has `Glob` and nothing else, and that is the architectural
  claim of this project**: it cannot read a previous chapter's prose even if a
  prompt tried to point it at one. Do not add `Read` to it to make something
  easier.

`model: haiku` in those files resolves to whichever Haiku is current; the log
wants the resolved id, not the family word (§6).

## 2. The genre is decided once, and read thereafter

**The premise decides what kind of book this is** — not this file, not the agent
files, not the config. Every agent used to open by declaring itself hard science
fiction, and a premise about a pop star trying quesadillas came back
unrecognisable. None does now, and `novel.tone` is null until somebody sets it.

**U1 reads the genre off the premise and writes it into `config.snapshot.json`
before anything else runs.** Every later unit reads it from there and carries it
into every prompt; no later unit derives it again. Nothing is carried between
units except what is on disk, and two units reading the same premise in two
different moods is precisely the drift this architecture would otherwise
introduce for free. Name the genre the way a reader would — "cyberpunk noir,
street level", "warm comic realism", "cosy mystery" — not the way a taxonomy
would.

If the genre is not science fiction, the characteristic named `science` still
applies: it is the world critic under a historical name, and it audits against
the bullets under `## Rules` in `bible/world.md`, whatever kind of rules those
are.

## 3. The gate

Six characteristics, from `quality_gate.critics`. Four are subagents; two are
arithmetic you run in the shell, which is why those two reproduce and the other
four do not.

| characteristic | who runs it | against what |
|---|---|---|
| `continuity` | `continuity-critic` | the Bible |
| `science` | `science-critic` | `## Rules` in `bible/world.md` |
| `outline` | `outline-critic` | this chapter's outline entry, beats numbered |
| `prose` | `prose-critic` | the writing itself — quoted findings, **no score** |
| `length` | you | `wc -w`, inside the band 10, outside 0 |
| `chatter` | you | 0 if the draft does not begin with `# Chapter` |

`outline` exists because the others all ask whether the draft is *correct* and
none asked whether it was *the chapter the outline commissioned*: a draft that
was consistent with the Bible, obeyed the world, sat in the word band and was
about something else entirely used to pass this gate cleanly (LOOP-003).

**Aggregate with `min`.** A chapter is only as good as its worst characteristic:
it passes when **all six are at 8 or above**, never when the average is.

**Three attempts** — `max_iterations: 3` counts drafts, so one first draft and
up to two rewrites — and **you do not work out what happens after one. You ask,
and you obey:**

```bash
echo '{"aggregate": <min>, "attempt": <n>, "patched": <true|false>}' \
  | python -m backend.chapters.decide
```

It answers `accept`, `retry`, `patch` or `halt`, with its reason. **Do what it
says, including when you disagree with it** — say so in your report, do not act
on the disagreement. This was a paragraph orchestrators applied themselves until
SPEC-004 moved it into code, because you read it at the worst possible moment:
an hour into a run that is about to be thrown away, which is exactly when "it is
only just below" gets rationalised.

**`on_fail: patch_then_halt`.** The exit this replaced, `accept_with_warnings`,
put a chapter that had failed three times into the book with a note in the
margin. **There is no verdict for "kept below the threshold":** a draft still
under 8 after the patch halts the run, because the only way to arrive there is a
critic's replacement that was itself wrong and that arbitration did not catch,
and that is worth a person looking at before another chapter is written.

**A critic that returns no usable verdict is excluded, never counted as a pass.**
10 invents an approval and 0 invents a rejection. Leave it out of the `min`,
record it as unscored, and say so in the gate row's `note`: a gate running on
five characteristics is weaker than one running on six, and that is the truth of
what happened.

**A late finding does not block a chapter.** A critic that raises on attempt 3
something equally present in attempt 1, and said nothing then, has moved the
goalposts: mark it **late**, record it in
`specs/loops/LOOP-003/late_findings.jsonl`, patch it if you can, and let the
chapter through. Without this rule the third-attempt guarantee does not exist,
because something new can always appear — and a critic that accumulates late
findings is a problem to fix in the critic rather than in the chapter.

## 4. The sheet

Each failed attempt must make the next one **easier**, not merely better
informed, so the feedback escalates in concreteness until there is nothing left
to interpret:

| attempt | what the writer gets | what it is asked to do |
|---|---|---|
| 1 | the Bible, its outline entry, the rolling summary | write the chapter |
| 2 | plus a **level-1 sheet**: per finding, the exact quote, what is wrong, against what, and *how it should read* — described, not written | correct only what is marked, touching as few lines as possible |
| 3 | plus a **level-2 sheet**: per open finding, **the literal replacement sentence, written by the critic** | integrate those sentences; do not rewrite |

On attempt 2 the writer interprets a description. On attempt 3 it does not
interpret at all — it integrates a given text.

`specs/loops/LOOP-003/sheet_template/v01.md` is the format and it does not vary.
Fill it, run `node specs/loops/LOOP-003/validate-sheet.mjs <file>`, and **do not
send a sheet that fails**: an unsent sheet is a bug caught, a half-filled one is
an attempt wasted, because a writer without the quote is back in the state
attempt 1 was already in.

Five rules, each of which is in the validator:

1. **All six scores, including the passing ones.** The writer has to know what
   is already right in order to leave it alone.
2. **An explicit DO NOT TOUCH list.** In the saved run the writer changed two
   lines and then one; that restraint is the thing to protect. A writer that
   takes the opportunity to improve an approved paragraph is the commonest way a
   score that was passing stops passing.
3. **Four fields per finding** — quote, what is wrong, against what, how it
   should read — or it does not go. The quote is literal. "Against what" points
   at the Bible or the outline, **never at a previous chapter**: the writer has
   never seen one, and this sheet is not the hole through which it finally does.
4. **A RESOLVED list.** Which phrasing of "how it should read" produced a
   correction first time is the only thing this loop actually learns.
5. **Every finding, worst first, none trimmed.** A finding held back to keep the
   sheet short is a finding that fails again next attempt.

Write each sheet to `specs/loops/LOOP-003/sheets/<slug>/chNN.attemptK.md` as you
send it. The slug is not decoration: the flat path had no run dimension, and the
second run to use this loop silently overwrote the first's chapter 1 and chapter
3 sheets. They were recoverable from git, which is luck. The sheets are the only
record of what the writer was actually told.

**Where this guarantee is weakest, said plainly:** `outline` is the hardest to
patch, because a missing beat is not a sentence but a paragraph, written by the
critic in the book's voice. That is a larger thing to insert blind than a
corrected clause, and it is the part of "it will pass by the third" that rests
on the most.

## 5. The words a script reads

Some vocabulary here is read by code, and a synonym is a failed insert or a
question that can no longer be asked.

- **Verdicts: `accept`, `retry`, `patched`, `halt`.** These four words, not
  `accepted`/`rejected` — the `attempts` table's CHECK admits no others, and
  anything else fails the insert. `patched` is the row for a draft the patch
  brought up to the threshold: it passed, and it did not pass on its own, and a
  reader is entitled to both facts. Where `promote` answers `patched`, record
  `patched`, not `accept`.
- **`arbitration` starts with `UPHELD` or `OVERRULED`.** The word is read by a
  script; the sentence after it is for a person.
- **Provenance is `measured` or `estimated`**, and they are never
  interchangeable. A token figure read out of a tool result is `measured`; one
  computed from a word count is `estimated`. A plausible number and a measured
  one look identical once written down, which is why the run that stamped
  twenty-four rows across twenty-four minutes went unnoticed for seventy-two.
- **Zero, empty and absent are three different claims** (`docs/domain-knowledge.md`
  §7.10). A criterion nobody scored is unscored, not 0; no mandatory facts is no
  denominator, not 100%; a critic that failed to answer is excluded, not a pass.
  Four bugs in one day were all this one substitution.
- **A critique file is an object, not a bare array**, because the panel reads the
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

  A run wrote the bare array, with `problem` where this says `claim`. Both are
  read now, but write this shape: the reader that had to be taught to accept the
  other one was taught after it had already put a blank page in front of someone.

## 6. What every unit logs

Append one row per subagent call to `logs/agents.jsonl` — timestamp, stage,
agent, chapter, iteration, verdict — and update `state.json` once your unit's
outputs are on disk. The conductor resumes from `state.json` and the files, not
from a conversation that no longer exists, so a unit that finishes its work and
does not record it has done the work twice.

**Timestamp from a clock, not from an estimate.** Read
`date -u +%Y-%m-%dT%H:%M:%SZ` rather than working out what the time probably is.

**Record `tokens` and `model` on every agent row, for every stage.** The Agent
tool reports `subagent_tokens` in its result and a task notification repeats it;
take the figure from there. `model` is the **full model id**, not the family
word: `config/pricing.json` is keyed by `claude-haiku-4-5`, and four runs that
wrote `opus` matched no key and showed no cost at all — which reads as "this run
was free" rather than "the name did not match the price list". Three things
about that figure, because getting them wrong makes the numbers worse than
absent:

- **It is cumulative across a resume.** An agent sent back for a redraft reports
  the running total for the whole agent, not the cost of the second attempt. Log
  the *difference* from its previous total, so each row is one attempt.
- **It is a single total**, with no input/output split. Do not invent one.
- **A blocked or wasted call still costs.** Log it with its tokens and the reason
  it produced nothing: one run spent 17,479 tokens on a rewrite the Write tool
  refused, and that is exactly the kind of number a dashboard exists to surface.

Without these fields `tools/export_to_langfuse.py` ships the run with no usage
and no cost, and there is nothing to observe.

**Write your bookkeeping as parallel tool calls in one reply.** The critique
files, the gate row, the log rows and `state.json` are independent of each other
and of the next dispatch, and a unit that writes one file per reply spends its
wall clock on round trips: a measured run spent twenty-five minutes of wall clock
on twelve and a half minutes of subagent work. What can no longer be collapsed is
the boundary between units — the conductor starts the next process only after
yours has ended — so the round trips inside your own unit are the only ones left
to win.

## 7. The 100,000-token ceiling

SPEC-EXAM-003 §2, and it now applies to **you**, not only to the packets you
send:

- **The ceiling is enforced on every orchestrator turn.** A turn whose context
  exceeds 100,000 tokens halts the run with `halted: context`, naming the unit.
  The agents' packets keep their existing check.
- **Concurrency.** Dispatch the four model critics in parallel only if your last
  measured context plus four critic packets — estimated at **words × 1.35** —
  fits under 100,000; otherwise send them in two rounds. The sum before dispatch
  is `estimated`, the figure after it is `measured`, and nothing is reserved:
  Python does not assemble your prompts and cannot reserve on your behalf.
- **The conductor never runs two units at once**, and before launching one it
  checks that no other orchestrator of this run is alive.

A chapter unit carrying three attempts and all their critiques is where this
ceiling is likeliest to be met. That is an accepted gap, not an oversight: the
halt makes it visible rather than silent.

## 8. One command per stage, not a list you remember

```bash
python -m backend.checks <STAGE> <run_dir> [<chapter>]
```

It runs everything that stage owes and names whatever failed. Seven instruments
now stand between a run and a defect, and **remembering which at what moment is
exactly what has failed here**: a chapter promoted at 5, a summary cap exceeded
five times, a verdict written in a vocabulary the database rejects. None of them
was forgotten on purpose.

**It reports; it does not gate.** `decide` and `promote` are the only things
that refuse. A checker that also gated would be a second place the gate lives,
and this repository has spent a day on what that costs.

## 9. Why your unit ends where it does

Every unit file closes with the same three instructions: read only the files
your prompt names, write your outputs to the paths it names, end your turn.
They are not politeness. A unit that goes looking for the rest of the book
rebuilds the accumulating context this architecture exists to remove, and it
does it quietly — the run still finishes, and the only thing broken is the
ceiling the owner asked for. If something you need is genuinely not among the
files you were given, say so and stop: the conductor can name another path far
more cheaply than you can read the book.

---

## What this architecture does not give you

State these when a reader asks what the pipeline guarantees. They are honest
limits, not caveats to bury.

**The gate is not reproducible.** Four of the six characteristics are models.
The same draft can score 8 one run and 7 the next, so "it passed the gate" is a
statement about one run and not a property of the text. `length` and `chatter`
*are* arithmetic and do reproduce.

**There is no tamper-evident audit.** `logs/agents.jsonl` is a record you write,
not a hash chain, and anyone who can edit the file can edit it undetectably.

**Resume is per unit, and a unit restarts from its beginning.** A chapter killed
on attempt 2 is drafted again from attempt 1, and the attempts already paid for
are spent.

**The ceiling is checked on the turn, which is after it.** Nothing reserves
tokens before a call, so a single unit can still exceed 100,000 — it halts,
naming itself, rather than passing quietly.

**PDF export is not available in this architecture** — it was a Python module,
and `outputs.formats` reads `["markdown"]` here. If a config asks for `pdf`, say
so plainly rather than producing something and calling it a PDF.
