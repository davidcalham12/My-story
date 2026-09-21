# NovaForge — for Claude Code

A multi-agent harness that writes novels. Nine agents across six stages, with a
five-characteristic quality gate between the draft and the book.

**The central claim:** the writer of a chapter never receives the prose of a
previous chapter. It receives the Story Bible, its own outline entry, and a
bounded rolling summary. Everything else about this system exists to make a long
book possible under that constraint.

The repository is in **English** — documentation, code, comments, prompts.

---

## Running it

```bash
# backend
uv sync
uv run pytest                      # mock engine; no network, no cost
uv run fastapi dev backend/main.py

# frontend
cd frontend && npm install && npm run dev

# database
uv run python -m backend.commons.db.migrate
```

**Tests run on the mock engine and cost nothing.** A suite that needs a
credential does not run in CI, and a suite that does not run in CI is
documentation. The real engine is opt-in through `USE_MOCK_ENGINE=false` and
reads `ANTHROPIC_API_KEY` **from the environment only** — never from a file,
never from a chat message, never from a command line argument.

---

## Where things are decided

| what | where |
|---|---|
| stage order, inputs, outputs, `on_fail` | `specs/flow.yaml` |
| every number: chapters, words, thresholds, counts | `config/novel.config.json` + `config/profiles/` |
| what each agent is told | `backend/<feature>/prompts/<agent>.md` |
| what each agent is *handed* | its `ContextPacket` in `backend/commons/context/` |

**The orchestrator contains no literal of structure or number.** A chapter count,
a threshold, a stage order written into Python is a second source of truth, and
the two will disagree. Read them from the spec and the config.

---

## The architecture, in two rules

**Backend — vertical slices, dependencies inward.**
Inside a feature: `router → service → domain`, and `service → repository` through
a Protocol. `domain.py` imports only the standard library, which is what lets the
gate's arithmetic be tested without a database, a server or a model.
`service.py` must not import FastAPI.

**Features do not import each other.** `chapters/` does not import `bible/`; they
compose in `runs/` or share through `commons/`. Same rule the frontend's
Feature-Sliced Design applies to its slices.

`commons/` is not "shared code" — it is **what nobody may skip**. The token
counter lives in `commons/llm`, which is the only path to a model, so no feature
can send a prompt without it being counted and charged against the budget.

Frontend is Feature-Sliced Design v2.1. Layers import downward only; the
`widgets` layer is not used.

---

## Every new technology brings its skill

A library, framework or tool entering this project gets a skill installed
**before the first line that uses it**. Read the skill in full before installing
it: a skill is text with instructions, and one that carries executable code,
downloads things, or asks for credentials is not installed — say so instead.

Installed: `fastapi` · `react` · `sqlite` · `sqlite-vec` ·
`sentence-transformers` · `feature-sliced-design` · `frontend-design` ·
`verification` · `grill-me` · `grilling`. Sources and licences are in
`docs/architecture.md` §5.

---

## The guarantees

Full statements with their class of evidence are in `docs/verification.md`.

1. **The writer never receives prior prose.** Its `ContextPacket` has no field
   that can carry it, and a test fails if the builder gains one.
2. **100,000 tokens per call**, counted before sending. Over it is an error that
   fails the run, not a warning.
3. **Five characteristics, each 0–10, all ≥ 8, aggregated with `min`.**
   `continuity`, `science`, `outline` (10 − 3 per missing beat − 1 per beat out
   of order), `length` (word count, in band or 0), `chatter` (0 unless it opens
   `# Chapter`). Two are arithmetic and reproduce; three are model judgement and
   do not.
4. **Three attempts, escalating.** Attempt 2 gets the correction described;
   attempt 3 gets the critic's literal replacement sentence.
5. **`patch_then_halt`.** If three attempts fail, the orchestrator applies the
   replacements itself — arbitrating each first — and rescores. If it still
   fails, **the run stops**. Never `accept_with_warnings`.
6. **Only `worldbuilder` and `character-architect` write the Story Bible.** Every
   other agent returns text; the orchestrator writes the file.
7. **The book is assembled in code**, never by an agent. A model asked to
   concatenate paraphrases a sentence in the middle.
8. **The outline is audited against `## Rules` before FLOW-4.** A beat that
   commissions what the world forbids produces a chapter that cannot pass, and no
   redrafting saves it.
9. **Provenance on every figure**: `measured` · `reported` · `reconstructed` ·
   `estimated` · `absent`. **What cannot be measured is said to be unmeasurable,
   never reported as zero.**
10. **Budget ceiling checked before every call.** Exceeding it halts the run with
    what it produced left readable.
11. **No agent declares a genre.** The genre is read off the premise and recorded
    in the run's config snapshot.

---

## Not changed without a recorded decision

The threshold of 8 · the five characteristics · the third attempt as the last ·
the writer's `ContextPacket` · `patch_then_halt` · the 100k ceiling.

These come from `specs/loops/LOOP-003/README.md` §8.3, which also forbids
trimming findings from a feedback sheet, sending a sheet that fails its
validator, quoting a previous chapter's prose in one, and changing the sheet and
the outline formula in the same chapter.

Changing one is a decision to write down in `docs/architecture.md` §6, not an
implementation detail.

---

## Two things that cost a run to learn

**Persist after every stage and every attempt.** A background task that keeps
progress in memory loses it to a restart, and a run measured in hours will meet
one. The SSE stream is a view; the database is the record.

**Never ask a prompt for a quantity without saying how to decide it.** "Write
three to five beats" invites a coin flip. Say what makes it three and what makes
it five.
