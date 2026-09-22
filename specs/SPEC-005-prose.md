# SPEC-005 — The part of prose quality that is arithmetic

status: approved
date: 2026-09-22
narrows: verification.md §3.9
related: AGENTS.md §5 (code before agent), §6 (the five characteristics)

## What is wanted

**A script that finds the prose defects a script can find**, run per chapter,
reporting rather than gating.

§3.9 is the largest gap in the project: nobody measures the prose. Three visible
defects shipped because of it — a sentence duplicated verbatim, a timeline error
on screen, a paragraph stating the same fact twice — and each was kept in by
redraft rule 2, *change only what was cited*, because no finding named them.

## Why not a sixth characteristic

Because `AGENTS.md` §5 says to answer that before proposing an agent, and the
answer holds for two of the three defects:

| defect | what it actually is |
|---|---|
| a sentence duplicated verbatim | **equality** |
| a heading glued to the previous line | **a regex** |
| a paragraph echoing another's opening | **a prefix** |
| a timeline error | **judgement** — not addressed here |

A sixth critic would cost roughly **$0.07 a chapter**, would not reproduce
between runs, and would be **D** forever. This is $0, deterministic and **T**.

**It is a floor under §3.9, not a ceiling over it.** Voice, pacing, dialogue,
originality and whether a sentence earns its place remain **U**, and the report
names what it did not look for so that a clean result cannot be read as a verdict
on the prose.

## What is explicitly out of scope

- **Adding a sixth characteristic, or letting this block a chapter.** The five
  are fixed by `AGENTS.md` §6. A script acquiring a veto by the back door is the
  same change without the spec.
- **A quality score.** A count of mechanical defects is not a grade, and calling
  it one would close the question §3.9 exists to keep open.
- **Judging facts.** Whether a statement contradicts the Bible is `continuity`'s
  job and it has a critic.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| A1 | A sentence repeated verbatim in a chapter is reported, ignoring case and emphasis | **T** |
| A2 | A short repeated line (dialogue beats) is **not** reported | **T** |
| A3 | The chapter's own heading is never a defect | **T** |
| A4 | A heading with no blank line before it is reported | **T** |
| A5 | The report names what it did not check, and carries no score | **T** |
| A6 | Run over every shipped book, it finds something real | **T** |
| A7 | Reachable as `python -m backend.chapters.check_prose <file>` | **T** |
| A8 | That the prose is any good | **U** — unchanged, and unchanged on purpose |

## What it measured

Run over the nine assembled books, **23 defects in six of them, and zero in v2's**:

| | v1 books | v2 book |
|---|---|---|
| `heading-without-a-blank-line` | 20, across 6 books | **0** |
| `echoed-opening` | 3, all in one degenerate early run | 0 |
| `duplicate-sentence` | 0 | 0 |

**Every v1 book glues each chapter heading to the previous chapter's last
sentence** — the shell concatenated with a single newline. CommonMark lets the
heading interrupt the paragraph so it usually renders, but a stricter converter
keeps it as literal text in the middle of a sentence.

v2 assembles in `publish/domain.py`, which joins with a blank line, and its book
has none. **G10 — "the manuscript is assembled in code" — was adopted because a
model asked to concatenate paraphrased. It turns out also to concatenate
correctly**, which nobody had noticed and nothing had measured.

The duplicated sentence on record is not in any shipped book. It predates the
runs that survive.

## Gaps this spec leaves

| gap | level |
|---|---|
| §3.9 — prose quality proper is still unmeasured; this takes three mechanical defects off it and leaves the judgement untouched | important |
| A script cannot see a defect it has no rule for. New rules arrive by someone reading a book and noticing | important |
