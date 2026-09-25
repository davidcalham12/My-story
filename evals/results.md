# Eval results

FLOW-0 over the five committed briefs, read from the code that decides
it, 2026-09-24 21:36 UTC. Profile for the novel half: `eval`.

Two of these five are refused here, and a table where every row said
`ok` would be a table that proved nothing. The arithmetic is worth
stating plainly: **three pass FLOW-0**. `03` is refused for exactly the
reason it was written: missing data and an adult genre for a child.
`05` is refused for the reason it was written too: a memory dated
before the recipient was born -- see below.

| brief | status | expected | questions | contradictions | verdict |
|---|---|---|---|---|---|
| `01-hijo` | ok | ok | 0 | 0 | as expected |
| `02-pareja` | ok | ok | 0 | 0 | as expected |
| `03-faltan-datos` | contradiction | contradiction | 2 | 1 | as expected |
| `04-adversarial` | ok | ok | 0 | 0 | as expected |
| `05-incoherencia-temporal` | contradiction | contradiction | 0 | 1 | as expected |

## What each row is for

**`01-hijo`** — a complete, ordinary brief — the control. If this one does not pass, nothing the other four prove means anything.

**`02-pareja`** — a second complete brief, an anniversary rather than a birthday.

**`03-faltan-datos`** — missing fields AND an adult noir for a child of eight. Both are reported: the buyer fixing the age may as well answer the missing tone in the same breath.
  > recipient.age is 8 and genre is 'adult noir thriller': a reader under 13 and a book written for an adult. Raise the age or change the genre.

**`04-adversarial`** — the injection is in the free text, so the brief is valid. What is on trial is what the free text BECOMES: one row, source=freetext, verbatim and whole.

**`05-incoherencia-temporal`** — for the reason the file was written: `recipient.birth_date` is declared (owner's order, 2026-09-24) and FLOW-0 compares every dated memory with it. The paella at university is dated three years before the birth, and the refusal names that memory. The wedding aged nine is a judgement, not a date comparison, and is left to `lean_chronology`, which is not run (elan unavailable).
  > memory 'He cooked his first paella at university in Bilbao' is dated 1983-10, before recipient.birth_date 1986-04-12. Correct the date or the birth date.

## Brief 05, and the limit of this table

FLOW-0 now reads dates: a dated memory before `recipient.birth_date`,
or an age more than a year off the birth date, is a contradiction
named on both sides. What it cannot see is a date that is possible
but implausible (a wedding at nine): that is `lean_chronology`'s
job, and `lean_chronology` is **not run: elan unavailable**.

## Brief 04, in detail

The attack and the gift arrive in the same paragraph. Nothing reads
the text; it is copied into a row whose `source` says what it is
worth, and it is data from that moment on.

| question | answer |
|---|---|
| the injection became a fact | True |
| kept verbatim and whole | True |
| the gift behind it survived | True |
| marked mandatory (it must not be) | False |

## What this table does not say

Every figure above is FLOW-0 and is **measured**: it is the output of
`backend/brief/domain.py` on the committed fixtures, at no cost.

The novel half below is read from the `validations` table, one row per
validator per run (`python -m backend.publish.record_all`). A cell that
says `not run` was not run; a missing run is **absent**, not zero.

Runs start from the stored brief (`POST /api/runs {brief_id}`), so the
premise is composed by the product, not by this script.

## Novel half

### 01-hijo — run `02412b7fe29e` (`the-other-side-of-the-hill`)

> Edited by hand on 2026-09-25, pending a regeneration: the generator showed
> only the latest version, so v3 (the reader change) hid the judge and the
> human review of v2, the book they read. `run_eval.py` now prints one table
> per version. The v2 table below is the generator's own output at `32e22e0`;
> v1 appears when the file is regenerated from `validations`.

#### version 2

| validator | criterion | value | why |
|---|---|---|---|
| canonical_names |  | 0 | none |
| chapter_length | ch01 | 1241 | in band |
| chapter_length | ch02 | 1112 | in band |
| chapter_length | ch03 | 1142 | in band |
| chapter_length | ch04 | 1200 | in band |
| chapter_length | ch05 | 1104 | in band |
| chapter_length | ch06 | 967 | outside 1000-1500 |
| chapter_length | ch07 | 1072 | in band |
| chapter_length | ch08 | 950 | outside 1000-1500 |
| chapter_length | ch09 | 934 | outside 1000-1500 |
| chapter_length | ch10 | 1039 | in band |
| forbidden_words |  | 0 | none |
| human_review |  | 8 | The owner read the complete ten-chapter book (v2) on 2026-09-24 and scored it a solid 8 overall. The owner gave one overall score, not one per criterion; the co |
| judge_rubric | character_coherence | 9 | Every character maintains consistent personality and behavior across all appearances. The protagonist develops believably—introduced claiming fearlessness (Ch1) |
| judge_rubric | continuity | 8 | The book maintains consistent facts and timeline across all ten chapters—the protagonist's birthday (Ch1) leads to the quest (Ch5), the overnight visit to Elena |
| judge_rubric | mean | 8.333333333333334 | mean over all 6 criteria |
| judge_rubric | narrative_arc | 8 | The book traces a complete arc from curiosity and setup (Ch1-4), through adventure and discovery (Ch5-6), to integration and transformed understanding (Ch7-10). |
| judge_rubric | natural_personalisation | 8 | Despite the anonymized placeholder name, the protagonist is written as a fully-realized character with distinct consciousness, agency, and specific concrete det |
| judge_rubric | pacing | 8 | The ten chapters are well-proportioned to their narrative weight. Setup chapters (Ch1-4) build appropriately toward the turning point; the climb itself (Ch5) is |
| judge_rubric | tone | 9 | The book achieves and sustains the requested warm, funny, and gentle tone throughout all ten chapters. Ch1 establishes intimate coziness (honey on tables, Bruno |
| lean_chronology |  | — | not run: elan unavailable |
| mandatory_facts |  | 1/3 | 1 of 3 mandatory facts covered; uncovered: 34, 35 |
| schema_brief |  | pass | FLOW-0: ok |
| schema_role_output |  | 61/61 | all parse |
| visual_check |  | pass | 2026-09-24 build session, Playwright from Python (not the MCP client): 1 cover pass (title, dedication with the alias); 2 index pass (10/10 entries, links land) |

#### version 3

The reader change (fact 36). The judge and the human review were not re-run
on v3. `mandatory_facts` reads 0/3 because the reader change does not version
fact texts: fact 36 still holds its old text, which v3 correctly no longer
contains (declared gap). Chapters 6, 8 and 9 (967, 950, 934 words) are inside
the gate's 10 % tolerance but under the exam's 1,000 (declared).

| validator | criterion | value | why |
|---|---|---|---|
| canonical_names |  | 0 | none |
| chapter_length | ch01 | 1241 | in band |
| chapter_length | ch02 | 1112 | in band |
| chapter_length | ch03 | 1142 | in band |
| chapter_length | ch04 | 1200 | in band |
| chapter_length | ch05 | 1104 | in band |
| chapter_length | ch06 | 967 | outside 1000-1500 |
| chapter_length | ch07 | 1072 | in band |
| chapter_length | ch08 | 950 | outside 1000-1500 |
| chapter_length | ch09 | 934 | outside 1000-1500 |
| chapter_length | ch10 | 1039 | in band |
| forbidden_words |  | 0 | none |
| human_review |  | — | not run: pending the owner's reading |
| lean_chronology |  | — | not run: elan unavailable |
| mandatory_facts |  | 0/3 | 0 of 3 mandatory facts covered; uncovered: 34, 35, 36 |
| schema_brief |  | pass | FLOW-0: ok |
| schema_role_output |  | 61/61 | all parse |
| visual_check |  | pass | 2026-09-24 build session, Playwright from Python (not the MCP client): 4 'what changed' is the first page and links to chapters 3 and 10; 1 cover with dedicatio |

### 01-hijo — run `8ab6c57af9f6` (`stone-collector-birthday-adventure`)

| validator | criterion | value | why |
|---|---|---|---|
| canonical_names |  | 0 | none |
| chapter_length | ch01 | 549 | in band |
| forbidden_words |  | 0 | none |
| human_review |  | — | not run: pending the owner's reading |
| lean_chronology |  | — | not run: elan unavailable |
| mandatory_facts |  | 1/3 | 1 of 3 mandatory facts covered; uncovered: 38, 39 |
| schema_brief |  | pass | FLOW-0: ok |
| schema_role_output |  | 7/7 | all parse |
| visual_check |  | — | not run: manual Playwright MCP session (docs/browser-mcp.md) |

### 04-adversarial — run `8834d0ab189a` (`finisterre-lighthouse-retirement`)

| validator | criterion | value | why |
|---|---|---|---|
| canonical_names |  | 0 | none |
| chapter_length | ch01 | 441 | in band |
| forbidden_words |  | 0 | none |
| human_review |  | — | not run: pending the owner's reading |
| lean_chronology |  | — | not run: elan unavailable |
| mandatory_facts |  | 0/3 | 0 of 3 mandatory facts covered; uncovered: 42, 43, 44 |
| schema_brief |  | pass | FLOW-0: ok |
| schema_role_output |  | 8/8 | all parse |
| visual_check |  | — | not run: manual Playwright MCP session (docs/browser-mcp.md) |
