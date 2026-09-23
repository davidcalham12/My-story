# Eval results

FLOW-0 over the five committed briefs, read from the code that decides
it, 2026-09-23 21:29 UTC. Profile for the novel half: `eval`.

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
| `05-incoherencia-temporal` | invalid | invalid | 0 | 0 | as expected |

## What each row is for

**`01-hijo`** — a complete, ordinary brief — the control. If this one does not pass, nothing the other four prove means anything.

**`02-pareja`** — a second complete brief, an anniversary rather than a birthday.

**`03-faltan-datos`** — missing fields AND an adult noir for a child of eight. Both are reported: the buyer fixing the age may as well answer the missing tone in the same breath.
  > recipient.age is 8 and genre is 'adult noir thriller': a reader under 13 and a book written for an adult. Raise the age or change the genre.

**`04-adversarial`** — the injection is in the free text, so the brief is valid. What is on trial is what the free text BECOMES: one row, source=freetext, verbatim and whole.

**`05-incoherencia-temporal`** — and the reason is not the one the file was written for. The fixture carries `recipient.birth_date`, a twelfth key the schema does not declare, and the brief is refused rather than having it silently dropped — a birth date accepted and discarded is the temporal validator reading a brief that never said when the man was born. Remove that key and the brief is `ok`: the memories put Iker at university three years before he was born and at his own wedding aged nine, and **nothing in FLOW-0 looks at a date**. That is what this brief is for, and this table is not where it is answered.

## Brief 05, and the limit of this table

As committed it is `invalid`, and for a schema reason rather than the one
it was written for: it declares `recipient.birth_date` and the schema has
no such field. Refusing beats dropping it — a birth date accepted and
discarded is the temporal validator reading a brief that never said when
the man was born.

With that one key removed the same brief reads **ok**. The memories
still put Iker at university three years before he was born and at his own
wedding aged nine. FLOW-0 does not look at a date, so it cannot see any of
it, and this is the brief that says so out loud.

`lean_chronology` is the validator written to fail it, and it has no writer
yet: two of eleven validators reach the `validations` table today.
So the incoherence in this brief is currently caught by **nothing**, and
that sentence is the finding.

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
