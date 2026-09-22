# SPEC-006 — `prose`, a sixth characteristic

status: approved
date: 2026-09-22
changes: the five characteristics — `AGENTS.md` §6 requires this spec to exist
narrows: verification.md §3.9
builds on: SPEC-005 (the mechanical floor)

## What is wanted

**A sixth characteristic, `prose`, which can stop a chapter for being badly
written.**

The five judge whether a chapter is *correct*: against the Bible, against the
world's rules, against its outline entry, against a word band, against a heading.
None of them reads whether it is any good. A chapter can satisfy all five and be
badly written, and the gate gives it a 10.

That is not hypothetical. **Three visible defects shipped** — a sentence
duplicated verbatim, a timeline error on screen, a paragraph stating the same
fact twice — and all three survived redraft rule 2, *change only what was cited*,
because no finding named them and nothing was looking.

## Why now, and what was tried first

`AGENTS.md` §5 requires saying why a script will not do. SPEC-005 already did
what a script can: repeated sentences, glued headings, echoed openings,
near-miss names — equality and regexes, $0, class **T**.

**What a script cannot reach is what is left:** voice, pacing, dialogue,
originality, and whether a sentence earns its place. Those need judgement, and
judgement here means a model.

The recommendation against building this was *not yet, for want of data*: one
chapter has reached attempt 3 in the project's history, and the mechanical check
found **zero duplicated sentences across nine books**, which suggests the
anecdote overstated the problem. **The decision to build it anyway was taken
deliberately and is recorded here**, because that is what this file is for.

## The design, and the one thing it gets right

**The arithmetic is fixed; only the findings are judgement.** Exactly the shape
of `outline`, and for the same reason: a score a model picks freely is a number
nobody can check, while a score derived from counted findings can be recomputed
against them.

```
prose = 10 − 3·mechanical − 2·major − 1·minor,  floored at 0
```

| term | what it counts | class |
|---|---|---|
| `mechanical` | what `backend/chapters/prose.py` found — repeated sentence, glued heading, echoed opening | **T**, deterministic |
| `major` | a paragraph that advances nothing; dialogue that any character could speak; a stated fact restated | **D**, the critic's judgement |
| `minor` | a clumsy line, a repeated word inside a paragraph, a register slip | **D** |

So `prose` is **T for the formula and the mechanical term, D for the rest** —
and the orchestrator can check the critic's sum against its own findings, the
way it already does for `outline`.

**Every finding carries a quote.** Without one it cannot enter a feedback sheet,
because redraft rule 2 needs the exact text, and a prose finding with no quote is
an opinion the writer cannot act on. The critic is told to omit a finding it
cannot quote rather than to describe it.

## What is explicitly out of scope

- **Scoring "quality" directly.** The critic never picks a number; it finds
  defects and the formula does the rest.
- **Rewriting.** Like every critic, it may propose a literal replacement at
  level 2 and nothing else.
- **The threshold, the three attempts, `min`.** Unchanged.
- **Judging the Bible, the rules or the outline.** Those have critics. A prose
  finding that is really a continuity finding is out of scope and the critic is
  told to leave it to `continuity`.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| A1 | `prose` is one of six characteristics in `domain.py`, `flow.yaml`, the config, the schema and the panel | **T** |
| A2 | `score_prose` implements the formula with a floor of 0 | **T** |
| A3 | The mechanical term comes from `prose.find`, not from the critic | **T** |
| A4 | A `prose` below the threshold blocks a chapter, through `min`, like any other | **T** |
| A5 | An unusable `prose` verdict is excluded, never counted as a pass | **T** |
| A6 | `prose-critic` holds `tools: Glob` — it cannot read a previous chapter either | **A** |
| A7 | Every `prose` finding carries a quote, or is not a finding | **I** |
| A8 | The score reproduces between runs | **U** — it does not, and cannot |
| A9 | That a chapter scoring 10 on `prose` is well written | **U** |

## What this costs, stated before it is paid

**Money.** Measured: the writer spent ~12,000 tokens on a first attempt and the
three model critics ~56,000 between them. The critics are already the larger
half. A fourth model critic is **+33% of that half, roughly +15% of a run** —
about $3 on a short book and **$7–8 on eight chapters**.

**Reproducibility, and this is the real price.** Three of five characteristics
were already model judgements. It is now **four of six, and the new one is the
most subjective of the four.** "It passed the gate" was already a statement about
one run; it is now a weaker one. `verification.md` G3 says so.

**A new way to damage a correct chapter.** At attempt 3 the critic hands the
writer its own literal replacement. A prose critic's replacement is a rewritten
sentence — larger and more opinionated than a corrected clause. Arbitration has
already refused two such replacements on arithmetic in one run, and refused one
this week that would have written an error into six chapters. **That defence is
now carrying more weight than it was designed for.**

## Gaps this spec leaves

| gap | level |
|---|---|
| A8 — `prose` does not reproduce, and it is the least reproducible of the six | important |
| A9 — a 10 on `prose` is the absence of named defects, not a judgement that the writing is good | important |
| The cost of a false `prose` finding is a rewritten sentence, which is the largest patch any critic can propose | important |
