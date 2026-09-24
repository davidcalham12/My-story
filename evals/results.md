# Eval results

FLOW-0 over the five committed briefs, read from the code that decides
it, 2026-09-24 15:27 UTC. Profile for the novel half: `eval`.

Two of these five are refused here, and a table where every row said
`ok` would be a table that proved nothing. The arithmetic is worth
stating plainly: **three pass FLOW-0**. `03` is refused for exactly the
reason it was written. `05` is refused for a *different* reason than the
one it was written for, and what it was written for is invisible to this
phase -- see below.

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

The columns a novel would fill are **absent**, not zero:

- whether the forbidden terms stayed out of the prose
- whether every mandatory fact reached the book
- whether the gate's six characteristics passed

Nobody has looked, so nothing is claimed. `--novel <id>` looks, at up to
$25 a brief on the `eval` profile.

And one gap this tool made visible rather than papered over: **nothing
in the product turns a brief into a run.** The premise for `--novel` is
composed by this script, which is why the eval can run at all and why
the join is named here instead of assumed.
