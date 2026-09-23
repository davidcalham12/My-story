# storyMaker — for Claude Code

storyMaker writes a personalised novel as a gift: ten chapters in which the
recipient recognises their own name, history and details, and which reads
from beginning to end without stumbling. It is the NovaForge v2 harness,
adapted for that client.

**Read `AGENTS.md` first.** It is the process: nothing is built without an
approved spec, nothing is coded without an approved plan, tests come first.
This file only adds what is specific to Claude Code. What is being built, and
why, is `docs/spec.md`.

## The one idea

**The writer of a chapter never receives the prose of an earlier chapter.** It
receives the story bible, its own outline entry and a short rolling summary.
This is held by a capability, not a promise: the chapter writer's only tool is
`Glob`, which returns paths and cannot return contents (`.claude/agents/`).
Everything else in the system exists to make a whole novel possible under that
constraint: the story bible in SQLite, the six-characteristic gate, the
summaries.

## Who does what

| part | where | rule |
|---|---|---|
| the procedure | `.claude/skills/novaforge/SKILL.md` | the only implementation of the pipeline; Python never re-implements a stage |
| the structure | `specs/flow.yaml` | stage order, inputs, outputs, failure policy |
| the numbers | `config/novel.config.json` and `config/profiles/` | chapters, words, thresholds, budget; never a literal in code |
| the agents | `.claude/agents/` | twelve agents; the `tools:` line of each is its authority and a test pins it |
| the hooks | `.claude/hooks/` | chapter validation and the forbidden-words policy, on every chapter written |
| the backend | `backend/` | launches Claude Code, watches its stream, archives to SQLite, serves the panel |

**Claude Code is the orchestrator. There is no API key and no SDK.** The
backend launches `claude -p --output-format stream-json --verbose` with the
prompt on stdin, never as an argument.

## Running it

```bash
pip install fastapi uvicorn pydantic pyyaml pytest httpx sqlite-vec playwright langfuse
python -m playwright install chromium
USE_RECORDED_STREAM=true python -m pytest backend/tests -q     # replayed, costs nothing
USE_RECORDED_STREAM=false python -m uvicorn backend.main:app --port 8000   # real, costs the subscription
cd frontend && npm install && npm run dev
```

Before launching a real run: **check that no other orchestrator process is
alive.** A stopped server left three running once, billing for novels nobody
asked for (`docs/red-team-log.md`, case 9).

## Never changed without an approved spec that names it

The threshold of 8 · the six characteristics · three attempts · the `tools:`
line of any agent · patch-then-halt · the 100,000-token ceiling · the budget
ceiling. Each was reached by a run that went wrong; `docs/verification.md`
holds the guarantee that rests on it.

## Models

The twelve agents run on Haiku. The orchestrator runs on the session's model:
on Haiku it stopped dispatching the project's agents and the writer's
isolation disappeared (`docs/iterations.md`).

## Where to read next

- `docs/spec.md` — the exam spec and every decision taken after it (§8)
- `specs/` — the specs and plans, each approved in its header
- `docs/verification.md` — every guarantee, how it is proved, and what is not
- `docs/trade-offs.md`, `docs/iterations.md`, `docs/red-team-log.md` — the reasoning
- `evals/briefs/` — the five evaluation briefs
- `tla/Harness.tla` — the harness as a state machine
