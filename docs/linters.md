# Prose linters (SPEC-EXAM-005 O1)

`backend/linters/repetition.py` — restated sentences and verbal tics. Standard
library, read-only, **report-only: it is not wired into the gate**, so running
it changes no score and no book.

```bash
python -m backend.linters.repetition output/<slug>/chapters/ch*.md
```

## Why it exists

The judge, reading the finished example novel, found a sentence in chapter 5
said twice in a row with contradictory light ("silver in the failing light",
then "silver in the afternoon sun"). All six characteristics had passed that
chapter: a model critic reading one chapter can miss a restatement one sentence
away. A comparison of neighbouring sentences' words cannot.

## What it checks

| check | rule | threshold |
|---|---|---|
| restated sentence | two sentences within 2 of each other sharing ≥ 60 % of their words (Jaccard), both ≥ 6 words | `THRESHOLD = 0.6`, `WINDOW = 2` |
| verbal tic | a three-word phrase, not all stopwords, used ≥ 4 times in one chapter | `TIC_MIN = 4` |

## Measured on the example novel (v2, ten chapters), 2026-09-24

| chapter | restated | tics (phrase × count) |
|---|---|---|
| ch01 | 0 | "his father said" × 4 |
| ch04 | 0 | "of the hill" × 4 |
| **ch05** | **1** — the pair the judge found, score 0.64 | "he could see" × 4 |
| ch07 | 0 | "the way he" × 4 |
| ch08 | 0 | "he thought about" × 4 |
| ch09 | 0 | "was the same" × 4 |
| ch02, ch03, ch06, ch10 | 0 | — |

**One restated sentence in ten chapters, and it is the real one: no false
positive.** The tics are mild, at the threshold, and reported for a human to
judge; none is an error.

## Next step, not taken

Adding "a sentence restated within the paragraph" to the prose critic's brief,
or feeding this linter's findings into the sheet, would have caught ch05 before
publication. Either changes how chapters are judged, which is a protected value
and a decision for the owner, so it is left written down rather than done.
