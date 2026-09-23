# Report — backend v1, from the spec to a tested branch

Written for the professor, who reads this before the branch is merged. Branch
`backend-v1`, cut from `main` at `92b0cad`, 2026-09-22. Everything below is in
the repository; the report points at it and adds nothing that is not.

## 1. What was asked

The runbook *backend v1: de la spec a la rama probada* — twelve steps: place the
documents, merge the two `verification.md` drafts and check the docs for
coherence, commit and branch, grill the spec, approve it, write the plan, converge
plan and architecture, approve the plan, build phase by phase with the tests
first, run the acceptance criteria and two real runs, revise `verification.md`,
write this.

## 2. What happened, step by step

| paso | outcome | where |
|---|---|---|
| 0–2 | `verification.md` v2 merged from two drafts without raising a letter; `docs/_authority.md`; coherencia-docs found 17 incidents, all resolved in three commits by lote | `docs/verification.md` §8 row 2; `4fa6025`, `ce7e2a1`, `91ab246` |
| 3 | committed on `main`, branch `backend-v1` | `92b0cad` |
| 4 | the spec grilled: the repository answered everything it could first (§3.2, *the draft against the build*); eight questions went to the owner; all eight answered with the recommendation; renamed SPEC-007 because SPEC-001 already existed | `specs/SPEC-007-backend-v1.md` §3.2, §12a |
| 5 | approved — dictated in chat, written by the building session, and the header says so | `16e493b` |
| 6–7 | `PLAN-007`, twelve phases kept with the runbook's numbers; the convergence loop stopped at round 2 with zero new gaps (round 1: eight, one of them a false finding corrected later); coherencia-docs again: 6 more incidents, resolved | `specs/PLAN-007-backend-v1.md` Part 3a, *Convergence loop* |
| 8 | approved, same way; P-1 (`tiny` budget 5.0 → 25.0) resolved with it | `8b70b00` |
| 9 | twelve phases, one commit each (two for 6.10), tests first, every new test seen red before its code — with the two exceptions named in the commits | `f70d671` … `3831b50` |
| 10 | 21 criteria run; two real runs through the backend | SPEC-007 §10.1 |
| 11 | `verification.md` v3 | §8 row 3 |
| 12 | this | — |

## 3. What the branch contains

37 files changed, 2032 insertions(+), 168 deletions(-). Twenty-one commits after the cut:

```
a0ca0de Paso 11 (part 1): verification.md v3 — what PLAN-007 changed, before the real runs report
3831b50 PLAN-007 6.12: the call log's timestamps are checked at FLOW-6 (SPEC-007 §8.2, AC-16)
1065966 PLAN-007 6.11: /api/health reports the database, migrations, sqlite-vec and the model's cache (FR-HLT-1)
e184a4f PLAN-007 6.10: the route pin, corrected
3b5e3a7 PLAN-007 6.10: no route reads a file by path — pinned (AC-10, Q2)
5168e90 PLAN-007 6.9: the Node instruments learn the sixth characteristic
bd73751 PLAN-007 6.7: halt, the startup sweep, Last-Event-ID replay, the import CLI
c734c7a PLAN-007 6.5: the budget ceiling comes from the profile (FR-BUD-4); tiny is 25.0
d7939d5 PLAN-007 6.4: every stream line persisted before fan-out; --max-budget-usd in argv
61dc86f PLAN-007 6.3: config_hash — a run's configuration as a fingerprint (FR-CFG-1)
d9ca380 PLAN-007 6.2: the events table — the stream itself becomes the record
f70d671 PLAN-007 6.1: the three switches the recorded stream lacked
8b70b00 PLAN-007 approved
8098804 docs: resolver INC-020..025 (Lote B aprobado con el plan)
a26c610 docs: coherencia-docs Lote A after PLAN-007 — a count that lied and two nines
b8a0f23 PLAN-007: convergence loop, rounds 1 and 2, stopped at zero new gaps
4f8e073 PLAN-007 draft: twelve phases, tests before code, what is verify / build / retired
16e493b SPEC-007: status approved, at the owner's explicit dictation
efc882c SPEC-007 (was SPEC-001-backend-v1): the eight Paso 4 answers, incorporated
ed7b654 SPEC-001 §3.2: the facts the repository answers before Paso 4 asks anything
```

## 4. What was built, against what the spec asked

Most of the backend existed before the spec was approved, so the plan said at
every phase whether it was **verifying**, **building** or **retiring**.

**Built:** the `events` table and every stream line persisted before anything is
derived from it; `Last-Event-ID` replay over it; `POST /api/runs/{id}/halt`;
the startup sweep for orphaned runs; `--max-budget-usd` on the `claude -p` argv
from the profile's figure, with the watcher on the same number; `config_hash`;
`/api/health` reporting the database, migrations, `sqlite-vec` and the model's
cache without loading anything; the import CLI; the Node instruments' sixth
characteristic; `check_log` at FLOW-6; three switches the recorded stream lacked.

**Retired, by decision at Paso 4:** file-by-path read endpoints (the archive
answers), the `outline_audit` script (the audit is a model, and says so), the
Python ports of the Node instruments, the search wiring into the skill, the
import endpoint.

**Verified and cited, unchanged:** the config validators, the calls log, the
vector search at module level, the queue of one, the prompt on stdin.

## 5. The two real runs

- **tiny** — `night-translator-rewriting-phrasebook` — complete; halted=None (None); cost $16.25 (measured); 3 chapters, 4 attempts, 3 promoted; conformance conformant; warnings 3
- **stress** — `cartographer-valley-funding-review` — complete; halted=None (None); cost $20.15 (measured); 3 chapters, 4 attempts, 3 promoted; conformance conformant; warnings 3

What they cost against the last measured tiny ($18.82) and what the stress
profile exercised is in `docs/domain-knowledge.md` §8, written from the runs'
own records. Whether `--max-budget-usd` binds under a subscription is **still not known** —
neither run reached its ceiling — and `verification.md` §3.21 says so.

## 6. What was found on the way, and is written down

Every one of these is in `docs/domain-knowledge.md` §7.11–§7.15 or
`verification.md` §3: the procedure records derived timestamps and labels them
(47 of 50 on the first real run); a second follower of a finished run blocked
forever; the watcher's agent set said nine; a pin was committed red and
corrected; the import CLI on a fresh database takes v2 runs for history. One
of the plan's round-1 findings was false (two writes "without an encoding" had
one on the next line) and the plan says so where it said the opposite.

## 6a. The morning after: SPEC-008

Two of the findings above were fixes, not designs, and `AGENTS.md` §5 wants even
a fix to come through a short spec. `specs/SPEC-008-leftovers.md` and
`PLAN-008` did that on 2026-09-23: the import CLI on a fresh database skips v2
runs by the one file only v2 writes (`conformance.json`), and the archive knows
`prose_check.json`, so a run archives without noise. Four tests, all seen red
first. The search wiring stays out of scope, declared at `verification.md`
§3.15, with the reason.

## 7. What is still not verified

`verification.md` §3 has twenty-one rows and §9 has eight. The ones that this work
opened or left: §3.15 (search built and unwired — a spec of its own), §3.19 (no
log file), §3.21 (whether the budget flag binds), and AC-6's ceiling being testable only on
an injected packet because real streams report zero for the one quantity it is
about. The outline audit stays a model, class D, on purpose.

## 8. What to read first

1. `specs/SPEC-007-backend-v1.md` §3.2 and §12a — what the spec changed to match
   the build, and the eight decisions.
2. `specs/PLAN-007-backend-v1.md` Part 3a — every requirement, its phase, its
   evidence.
3. `docs/verification.md` §3 — the gaps, each with why it is accepted and how we
   would notice.
4. The commit messages from `f70d671` on — each says which tests were red, which
   passed on their first run, and why.

The branch is not merged. That is the professor's call, and this report exists
so it can be made from the repository rather than from a conversation.
