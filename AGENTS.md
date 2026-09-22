# AGENTS.md — how work gets done in this repository

Instructions for the AI that writes the code here. Read this before anything
else.

This file is about **process**: what has to be approved before what, and what
"done" means. It is not about the novel-writing agents — the catalogue of those
ten lives in [`docs/architecture.md`](docs/architecture.md) §4.

Three processes, with gates between them: **docs → specs → code**. Nothing
advances without the stage before it approved.

---

## 1. States and approval

| artefact | states | who approves |
|---|---|---|
| `docs/*.md` | living — no states, updated continuously | — |
| `specs/SPEC-NNN-*.md` | `draft` → `approved` | a human, by writing `status: approved` with a date in the header |
| `specs/PLAN-NNN-*.md` | `draft` → `approved` | the same |
| code | exists only where an approved PLAN covers it | — |

**Approval is an explicit human act written into the file.** An "ok" in a chat
does not change a state, and neither does an agent's own judgement that
something is obviously right. If the header does not say `approved`, it is not.

The reason is narrow and worth keeping: a state written in a file survives the
conversation that produced it. Anything else has to be remembered by someone.

---

## 2. Working on `docs/`

**Update the documentation in the same change that alters the behaviour it
describes.** A change to the gate that does not touch `architecture.md` is
incomplete, not "to be documented later".

- Always in English.
- `definitions.md` changes when a term is new or shifts meaning.
- `domain-knowledge.md` changes when a run teaches something. With its number.
- `architecture.md` changes when a decision changes.
- `verification.md` changes when a guarantee changes, or when its letter does.

**Every change to `docs/` cites where it came from** — a run, a spec, a
decision. A claim with no provenance is an opinion that will be read as a fact
by whoever comes next.

---

## 3. Writing a spec

**Ask before you write.** Use the `grilling` skill for the questions whose
answers are not in the repository. Find the facts yourself — the filesystem, the
runs, the logs are all readable, and asking a human for something you could look
up wastes their attention on the wrong thing. **Never write a spec with a gap
filled by an assumption.**

A spec is `specs/SPEC-NNN-short-name.md` and contains:

- a header with `status` and a date
- **what is wanted**, and **why**
- **what is explicitly out of scope** — the section that stops a spec growing
  while it is being implemented
- **acceptance criteria that can be verified**, each with its **T/A/I/D/U**
  letter (see `docs/verification.md`)
- **the gaps it leaves**, each with its level — below

A criterion with no letter is not a criterion. If the honest letter is **U**,
write U — an unverifiable acceptance criterion is worth knowing about before the
work starts, not after.

### The gaps a spec leaves

**Every spec lists what it does not verify, and at what level of criticality.**
Those rows travel from the spec into `docs/verification.md` §3 and live there.

The rule they answer to: **a gap that is written down is an engineering decision;
a gap that is not written down is a defect.** It costs a paragraph to be the
first kind.

Two consequences, because they are what makes the section work rather than
decorate it:

- **A critical guarantee whose letter is only I or D opens a gap row
  automatically.** Not a discussion — the criticality table in
  `verification.md` §1 fixes the minimum letter, and anything below it is an
  accepted risk that has to be named as one. Three rows in the current document
  exist because of this rule and not because anyone noticed.
- **A gap row is never removed except by the evidence that closed it.** Deleting
  one because it reads badly is the exact failure this apparatus exists to
  prevent.

---

## 4. Writing a plan

**No implementation plan without an approved spec.** A `PLAN-NNN` references
exactly one `SPEC-NNN` whose status is `approved`. **If the spec changes, the
plan returns to `draft`** — a plan built on a spec that has since moved is a plan
for a system nobody asked for.

The plan lists, in this order:

1. **the tests**, first
2. the code changes
3. the changes to `docs/` and to the spec itself

**A plan with no tests is not approved.** Not "should have tests" — is not
approved.

---

## 5. Writing code

**No code without an approved plan that covers it.** Including a quick fix.
Especially a quick fix: if something is urgent, write the short spec, get it
approved, then write it. The rule exists for exactly the moment it feels
expensive.

**TDD, in the order that makes it mean something:**

1. Write the test. **Watch it fail.** A test that has never failed has not been
   shown to test anything.
2. Write the smallest code that passes it.
3. Refactor with the tests green.

**Tests replay a recorded stream and cost $0.** That recording covers the
runner, the parser, the persistence, the SSE and both watchers. **It cannot cover
the procedure in `SKILL.md`** — that needs a real run, and a real run costs the
subscription every time. Say which half a change is in before claiming it is
tested.

### Code before agent

**Before proposing an agent for a task, say why a script will not do.** If one
will, it is a script.

A script gives class **T**; an agent gives **D** at best. Every check that moves
from agent to code improves reliability and cost at once, which is why
`verification.md` §4 keeps the list of the ones that have moved — and the ones
that should next.

### Definition of done, for any change

- tests green in CI
- the spec updated if the final behaviour differs from what was approved
- `docs/` updated
- `verification.md` updated if a guarantee or its letter changed
- **`verification.md` §3 updated if the change opened or closed a gap** — a gap
  closed silently is as bad as one left unwritten, because the next reader cannot
  tell which rows are still true
- a skill installed if a technology entered the project

All six. A change missing any of them is not done, it is in progress.

---

## 6. Never touched without an approved SPEC that names it

- the threshold of **8**
- the **six characteristics**
- the **third attempt** as the last
- the **`tools:` line of any agent** — that line IS the authority model, and
  `chapter-writer`'s `Glob` is why prior prose is unreachable rather than merely
  unpassed
- the **100,000-token ceiling**, in either of its two layers
- the **budget ceiling**

These are not configuration in the sense of "tune freely". Each was arrived at
by a run that went wrong, and each has a guarantee resting on it in
`verification.md`. Changing one is a decision with a name and a date, not an
implementation detail.

---

## 7. What this file links to rather than repeats

| what | where |
|---|---|
| the ten novel-writing agents, with skills | `docs/architecture.md` §4 |
| the guarantees and their T/A/I/D/U letters | `docs/verification.md` |
| the vocabulary | `docs/definitions.md` |
| what the runs taught | `docs/domain-knowledge.md` |
| commands, permissions, Claude Code specifics | `claude.md` |

Repeating them here would create a second source of truth, and the two would
disagree within a month.
