# NovaForge — for Claude Code

**Read `AGENTS.md` first; this file only adds what is specific to Claude Code.**
The process — what must be approved before what, and what "done" means — is
there, not here.

A multi-agent harness that writes novels. Ten agents across six stages, with a
six-characteristic quality gate between the draft and the book.

**The central claim:** the writer of a chapter never receives the prose of a
previous chapter. It receives the Story Bible, its own outline entry, and a
bounded rolling summary. Everything else about this system exists to make a long
book possible under that constraint.

The repository is in **English** — documentation, code, comments, prompts.

---

## Running it

```bash
# backend — plain pip and the stdlib runner. `uv` is not installed here and
# every command in this block used to assume it was.
pip install fastapi uvicorn pydantic pyyaml pytest httpx sqlite-vec
USE_RECORDED_STREAM=true python -m pytest backend/tests -q   # replayed; $0
python -m uvicorn backend.main:app --port 8000

# to orchestrate for real — this costs the subscription, every time
USE_RECORDED_STREAM=false NOVAFORGE_DB="$PWD/novaforge.db" NOVAFORGE_BUDGET=20   python -m uvicorn backend.main:app --port 8000
# the orchestrator's model: config/novel.config.json -> models.orchestrator (null = CLI default; e.g. "haiku"); the agents' models are in .claude/agents/*.md

# frontend
cd frontend && npm install && npm run dev

# migrations run themselves on startup; to apply them by hand:
python -c "from pathlib import Path; from backend.commons.db.connection import connect;   from backend.commons.db.migrate import migrate; print(migrate(connect(Path('novaforge.db'))))"
```

**Claude Code is the orchestrator. There is no API key and no SDK.** The backend
launches `claude -p --output-format stream-json --verbose` as a subprocess with
the prompt on **stdin**, reads the stream line by line, forwards it over SSE,
persists state in SQLite and writes `cost.json` from the `result` event. That is
what the four Vite plugins do in v1, in Python.

**Tests run against a recorded stream and cost nothing.** A real run costs the
subscription, every time. The recording covers the runner, the parser, the
persistence, the SSE and both watchers; what it cannot cover is the procedure in
`SKILL.md`, and that is said plainly rather than blurred. Set
`USE_RECORDED_STREAM=false` to orchestrate for real.

---

## Where things are decided

| what | where |
|---|---|
| stage order, inputs, outputs, `on_fail` | `specs/flow.yaml` |
| every number: chapters, words, thresholds, counts | `config/novel.config.json` + `config/profiles/` |
| what each agent is told | `.claude/agents/<agent>.md` — its prompt **and** its `tools:` line |
| what each agent is *handed* | the orchestrator assembles it, following `.claude/skills/novaforge/SKILL.md` |
| what happens after an attempt | `backend/chapters/domain.py::decide`, asked as a script |

Those first two rows used to name a prompts directory under each feature and a
`ContextPacket` module under commons. **Neither exists.** They
were the D2 design, where Python built a typed packet and called an API; Annex C
removed the API and the packet with it, and the authority model went back to
being the `tools:` line.

**The orchestrator contains no literal of structure or number.** A chapter count,
a threshold, a stage order written into Python is a second source of truth, and
the two will disagree. Read them from the spec and the config.

---

## The architecture, in two rules

**Claude Code orchestrates; Python launches, watches and archives.** The
pipeline has exactly one implementation and it is `SKILL.md`. Python does not
execute the stages; it validates that `SKILL.md` does not contradict `flow.yaml`
or `config/`.

**Backend — vertical slices, dependencies inward.**
Inside a feature: `router → service → domain`, and `service → repository` through
a Protocol. `domain.py` imports only the standard library, which is what lets the
gate's arithmetic be tested without a database, a server or a model.
`service.py` must not import FastAPI.

**Features do not import each other.** `chapters/` does not import `bible/`; they
compose in `runs/` or share through `commons/`. Same rule the frontend's
Feature-Sliced Design applies to its slices.

`commons/` is not "shared code" — it is **what nobody may skip**.
`commons/runner` is the only thing that launches a model, and both watchers read
its stream.

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
`docs/architecture.md` §7.

---

## The guarantees

Full statements with their class of evidence are in `docs/verification.md`.

1. **The writer never receives prior prose**, and this is once again
   **structural**: `chapter-writer` holds `tools: Glob`, which returns paths and
   cannot return contents, so the prose is *unreachable* rather than merely not
   passed. `test_agents_frontmatter.py` fails if that line changes.
2. **100,000 tokens, in two layers.** Python no longer assembles the prompts, so
   it cannot reserve before a call. Layer 1 is in `SKILL.md`: the orchestrator
   measures each packet with `wc -w` before dispatching. Layer 2 is
   `commons/runner/watch.py`, measuring the stream's own `usage` and stopping the
   run. **Neither is a reservation taken in advance**, and `verification.md` G2
   says so.

   Two things replaying real runs showed. `input_tokens` alone is nearly always
   2 — almost the whole context arrives cached, so the real size is
   `input + cache_creation + cache_read`. And the orchestrator's own turns run at
   a median of 147,000 tokens: **halting on those would halt every run**, because
   the ceiling was never the orchestrator's budget.
3. **The gate: six characteristics, `min`, threshold 8, three escalating
   attempts, then `patch_then_halt`.** The sequence and the numbers are in
   `docs/architecture.md` §3.3, which scores are arithmetic and which are
   model judgement in `docs/verification.md` G3, and what may not change
   without a spec in `AGENTS.md` §6. This file does not restate them.
4. **Only `worldbuilder` and `character-architect` write the Story Bible.** Every
   other agent returns text; the orchestrator writes the file.
5. **The book is assembled in code**, never by an agent. A model asked to
   concatenate paraphrases a sentence in the middle.
6. **The outline is audited against `## Rules` before FLOW-4.** A beat that
   commissions what the world forbids produces a chapter that cannot pass, and no
   redrafting saves it.
7. **Provenance on every figure**: `measured` · `reported` · `reconstructed` ·
   `estimated` · `absent`. **What cannot be measured is said to be unmeasurable,
   never reported as zero.**
8. **Budget ceiling measured on the stream.** The call that crosses it finishes
    and the next does not start — the overshoot is bounded by one call, not by
    zero. What the run produced is left readable.
9. **No agent declares a genre.** The genre is read off the premise and recorded
    in the run's config snapshot.

---

## Not changed without a recorded decision

The threshold of 8 · the six characteristics · the third attempt as the last ·
the `tools:` line of every agent · `patch_then_halt` · the 100k ceiling ·
the budget ceiling.

Changing one needs **an approved SPEC that names it** — see `AGENTS.md` §6.

`specs/loops/LOOP-003/README.md` §8.3 adds more: no trimming findings from a
feedback sheet, no sending a sheet that fails its validator, no quoting a previous
chapter's prose in one, and no changing the sheet and the outline formula in the
same chapter.

The decision itself is recorded in `docs/architecture.md` §8.

---

## Two things that cost a run to learn

**Persist after every stage and every attempt.** A background task that keeps
progress in memory loses it to a restart, and a run measured in hours will meet
one. The SSE stream is a view; the database is the record.

**Never ask a prompt for a quantity without saying how to decide it.** "Write
three to five beats" invites a coin flip. Say what makes it three and what makes
it five.
