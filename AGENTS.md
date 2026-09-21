# AGENTS.md — how work gets done in this repository

Instructions for the AI that writes the code here. Read this before anything
else.

This file is about **process**: what has to be approved before what, and what
"done" means. It is not about the novel-writing agents — the catalogue of those
nine lives in [`docs/architecture.md`](docs/architecture.md) §4.

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

A criterion with no letter is not a criterion. If the honest letter is **U**,
write U — an unverifiable acceptance criterion is worth knowing about before the
work starts, not after.

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

**Tests run on the mock engine and cost $0.** A test that needs the real engine
is marked as such and does not run in CI. A suite that needs a credential is a
suite that does not run, and a suite that does not run is documentation.

### Definition of done, for any change

- tests green in CI
- the spec updated if the final behaviour differs from what was approved
- `docs/` updated
- `verification.md` updated if a guarantee or its letter changed
- a skill installed if a technology entered the project

All five. A change missing any of them is not done, it is in progress.

---

## 6. Never touched without an approved SPEC that names it

- the threshold of **8**
- the **five characteristics**
- the **third attempt** as the last
- the writer's **`ContextPacket`**
- the **100,000-token concurrent semaphore**
- the **budget ceiling**

These are not configuration in the sense of "tune freely". Each was arrived at
by a run that went wrong, and each has a guarantee resting on it in
`verification.md`. Changing one is a decision with a name and a date, not an
implementation detail.

---

## 7. What this file links to rather than repeats

| what | where |
|---|---|
| the nine novel-writing agents, with skills | `docs/architecture.md` §4 |
| the guarantees and their T/A/I/D/U letters | `docs/verification.md` |
| the vocabulary | `docs/definitions.md` |
| what the runs taught | `docs/domain-knowledge.md` |
| commands, permissions, Claude Code specifics | `claude.md` |

Repeating them here would create a second source of truth, and the two would
disagree within a month.
