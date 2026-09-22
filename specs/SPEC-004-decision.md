# SPEC-004 — What happens after an attempt is decided by code

status: approved
date: 2026-09-22
closes: verification.md §3.1 (partially — see "What this does not close")
related: SPEC-002-gate, LOOP-003 §2, verification.md G6

## What is wanted

**The rule that decides what follows an attempt lives in `chapters/domain.py`,
not in a paragraph of `SKILL.md`.**

Today `aggregate()` produces a verdict for one attempt and stops there. Whether
the next event is another attempt, the patch, an acceptance or a halt is decided
by the orchestrator reading prose:

> *If the chapter still does not pass after the patch, **stop the run**.*

That sentence is the project's central safety claim — G6, **critical** — and it
is enforced by a model following instructions. `verification.md` grades it **D**
and §3.1 says why: there is no code to test, because there is no code.

## Why

Three reasons, in the order they matter.

**It is the one critical guarantee below its minimum letter.** Everything else
critical is T or A. This is D, and D means *it worked the once we watched*.

**"Code before agent" is already the house rule** (`verification.md` §4,
`AGENTS.md` §5). A decision expressible as arithmetic over values is exactly what
that rule says must not be left to judgement. It has moved six other checks; this
is the one that matters most and it was the one left behind.

**A model deciding under pressure is the failure mode.** The paragraph is read at
the moment a run has spent an hour and is about to be thrown away. That is
precisely when "well, it is only just below" gets rationalised — and
`accept_with_warnings`, the exit this replaced, is what rationalising looks like
when it wins.

## What is explicitly out of scope

- **Making Python execute the halt.** The orchestrator still stops the run and
  still declines to promote the file. This spec decides; it does not act.
- **Changing the threshold, the five characteristics or the three attempts.**
  `AGENTS.md` §6 — none is touched.
- **The patch itself.** `apply_patches()` already exists and is tested.
- **Removing the paragraph from `SKILL.md`.** It stays, rewritten to say *call
  the script and obey it* rather than *work it out*.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| A1 | A passing attempt decides `accept`, whatever attempt number it is | **T** |
| A2 | A failing attempt with attempts remaining decides `retry` | **T** |
| A3 | A failing attempt on the last allowed one decides `patch`, never `accept` | **T** |
| A4 | A failing attempt after the patch decides `halt` | **T** |
| A5 | An attempt that passes only after the patch decides `accept` with `patched` recorded | **T** |
| A6 | No input decides `accept` below the threshold — exhaustively, over every aggregate 0–10 at every attempt number | **T** |
| A7 | An aggregate of `None` (no characteristic produced a usable verdict) never decides `accept` | **T** |
| A8 | The decision is reachable as a script the orchestrator runs, and prints one word plus its reason | **T** |
| A9 | `SKILL.md` instructs the orchestrator to call it and obey it | **I** |
| A10 | The orchestrator actually obeys it | **D** |

## What this does not close

**A10 is the residue, and it is the honest half of §3.1.** Moving the decision
into code means the *rule* is no longer a judgement — that part becomes **T** and
stops being an accepted risk. Whether the orchestrator calls the script and does
what it says remains a procedure, testable only by a real run.

So §3.1 does not disappear. It narrows, from *the whole decision is a paragraph*
to *the decision is arithmetic and obeying it is a procedure*, and it says so.

## Gaps this spec leaves

| gap | level |
|---|---|
| A10 — obeying the decision is still procedural (§3.1, narrowed) | **critical** |
