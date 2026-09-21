---
id: SPEC-002
title: the gate — five characteristics, three attempts, patch_then_halt
status: approved
created: 2026-09-21
approved: 2026-09-21 by David Calderon
---

# SPEC-002 — the gate

## What is wanted

`backend/chapters/domain.py`: the rules that decide whether a chapter ships.
**Pure functions over values, importing only the standard library** — no database,
no HTTP, no model. In v1 these rules were entangled with network calls, so the
only way to exercise them was to write a novel.

Five things live here:

1. **The five characteristics** and their aggregation.
2. **`length` and `chatter`**, which are arithmetic and computed here rather than
   asked of anyone.
3. **The patch applier** — substitutions matched literally.
4. **The feedback sheet**: building it, and validating it before it is sent.
5. **The attempt ladder**, including which draft ships when the attempts run out.

## Why

Every rule below was arrived at by a run that went wrong. They are worth stating
as code precisely because they are not obvious, and each has a guarantee resting
on it in `verification.md`.

## Out of scope

- Calling any model. The service layer dispatches; this decides.
- Writing anything to disk or database.
- The FLOW-3 outline audit — that belongs to the `outline` feature.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| B1 | A chapter passes only when **all five** characteristics are ≥ 8; aggregation is `min` | **T** |
| B2 | A characteristic with **no usable verdict is excluded** from the minimum — never counted as 10, never as 0 — and is recorded as unscored | **T** |
| B3 | `length` scores 10 inside the band widened by `tolerance_pct`, 0 outside | **T** |
| B4 | `chatter` scores 0 unless the draft's first line opens `# Chapter` | **T** |
| B5 | `outline` aggregates as `10 − 3·missing − 1·out_of_order`, floor 0 | **T** |
| B6 | Patches apply by **literal match**; a `find` that does not match is skipped and counted, never applied approximately | **T** |
| B7 | Applying patches changes **nothing the findings did not name** | **T** |
| B8 | The sheet carries all five scores, a DO-NOT-TOUCH list, four fields per finding, and a RESOLVED list; an incomplete sheet **fails validation and is not sent** | **T** |
| B9 | A level-2 sheet carries literal replacements; a level-1 sheet must not | **T** |
| B10 | A sheet never quotes a previous chapter | **T** |
| B11 | When attempts run out, the **best** draft is identified, not the last | **T** |
| B12 | A late finding — present in the first draft, unmentioned then — is marked and **does not block** | **T** |
| B13 | `domain.py` imports only the standard library | **A** |

## Notes

B13 is **A** and checkable by reading the import list; a test asserting it would
be better and is cheap, so the plan includes one anyway.
