# storyMaker

A personalised novel as a gift: ten chapters in which the recipient recognises
their own name, history and details, and which reads from beginning to end
without stumbling. Built on the NovaForge v2 harness (history kept) for the
Harness Engineering final exam.

**The one idea:** the writer of a chapter never receives the prose of an earlier
chapter. It gets the Story Bible, its own outline entry and a capped rolling
summary. That is a capability, not a promise — `chapter-writer` holds only
`tools: Glob`, which returns paths and cannot return contents — and a test pins
every agent's tool line (`AGENTS.md` §6). **Whether a book holds together over
many chapters is not established**: the longest run is ten, and one novel is
not a curve. `docs/verification.md` §3.

## Running it

```bash
pip install fastapi uvicorn pydantic pyyaml pytest httpx sqlite-vec playwright langfuse
python -m playwright install chromium

# the tests replay a recorded run and cost nothing
USE_RECORDED_STREAM=true python -m pytest backend/tests -v -p no:cacheprovider

# real: every run spends the owner's Claude Code subscription
USE_RECORDED_STREAM=false NOVAFORGE_ORCHESTRATOR=single python -m uvicorn backend.main:app --port 8000
cd frontend && npm install && npm run dev          # the panel
```

**Claude Code is the orchestrator. There is no API key and no SDK.** The backend
launches `claude -p` with the prompt on stdin, reads its event stream and
archives it in SQLite. Before a real run, check that no other orchestrator is
alive (`docs/red-team-log.md`, cases 9 and 13). Copy `.env.example` to `.env`;
Langfuse credentials come only from the environment.

## The example brief, and the novel it produced

The example brief is [`evals/briefs/01-hijo.json`](evals/briefs/01-hijo.json): a
tenth-birthday gift to a son, with three real moments and three facts the book
must contain. To produce the novel from it:

```bash
curl -X POST localhost:8000/api/briefs -H 'content-type: application/json' \
     --data-binary @evals/briefs/01-hijo.json                 # → {"id": "<brief_id>"}
curl -X POST localhost:8000/api/runs -H 'content-type: application/json' \
     -d '{"brief_id": "<brief_id>", "profile": "exam"}'
python -m backend.publish.release output/<slug>              # v1: personalise, PDF, validators
```

Or from the panel: **New novel → Interview**, then **Open** to read it.

| file | what |
|---|---|
| [`ejemplos/novela-ejemplo.pdf`](ejemplos/novela-ejemplo.pdf) | the complete ten-chapter novel (v2) |
| [`ejemplos/novela-ejemplo-v1-8-capitulos.pdf`](ejemplos/novela-ejemplo-v1-8-capitulos.pdf) | v1: the eight chapters the first run reached before its ceiling |
| [`ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf`](ejemplos/novela-ejemplo-v3-cambio-del-lector.pdf) | v3: a reader change (one fact) propagated only to the chapters that used it, with its "what changed" page |

The recipient's alias is put in by code at publication: the orchestrator, under
the organisation's privacy policy, writes a placeholder, and no model is given
the name (`docs/verification.md` §3.23).

## What it cost, measured

From Claude Code's own `result` events, per change, read back from Langfuse
(`GET /api/runs/{id}/costs`, SPEC-EXAM-008):

| change | cost | orchestrator | agents |
|---|---|---|---|
| write chapters 1–8 | 53.17 USD | Opus 48.79 | Haiku 4.38 |
| continue: chapters 9–10, style, synopsis | 21.03 USD | Opus 19.34 | Haiku 1.69 |
| reader change v3, chapters 3 and 10 (Sonnet) | 10.31 USD — 6.07 confirmed in Langfuse; 4.24 measured from a stream later overwritten | Sonnet | Haiku |
| two reader-change attempts that did not publish | 7.52 USD + one not measured | Opus | Haiku |

**The orchestrator is most of the bill** (~92 % of the book's 74.20 USD); the
Haiku agents that write and judge are ~8 %. Moving the orchestrator from Opus to
Sonnet roughly halved a chapter's cost (7.52 → 4.24 USD). The chapter loop in code (SPEC-EXAM-006) is built
and tested at $0; its real spike has not been run.

## Where to read

| you want | read |
|---|---|
| how work is done here: spec → plan → tests → code | `AGENTS.md`, `CLAUDE.md` |
| the exam spec and every decision taken after it | `docs/spec.md` (§8) |
| the specs and plans, each approved in its header | `specs/` |
| every guarantee, how it is proved, and what is not | `docs/verification.md` (§3: the gaps) |
| the evals, with numbers | `evals/results.md` |
| trade-offs, iterations, red-team log | `docs/trade-offs.md`, `docs/iterations.md`, `docs/red-team-log.md` |
| explainers and diagrams | `docs/explainers/`, `docs/diagrams/` |
| TLA+ (TLC passes; each action mapped to code) | `tla/README.md` |
| Lean (the chronology's invariants) | `lean/README.md` |
| the browser MCP sessions | `docs/browser-mcp.md` |
| the security report | `docs/security-report.md` |
| skills, subagents, commands, project memory | `docs/skills.md`, `docs/subagents.md`, `.claude/` |
| the presentation and its annexes | `presentacion/README.md` |

## What it does not give you

- **The gate does not reproduce.** Four of its six characteristics are model
  judgements, so "it passed the gate" is a statement about one run.
- **The gate does not check that a changed fact arrived**; the reader change's
  arrival check does (`docs/spec.md` §8). It was added after v3's chapter 3
  passed the gate without the fact.
- **The gate can be disobeyed.** The decision is arithmetic and promotion is a
  script that refuses, but the orchestrator holds `Write`: what the system
  guarantees is **detection, not prevention** — every run writes a
  `conformance.json` saying which it was.
- **Mandatory facts are matched literally**: a paraphrased fact reads as
  uncovered, never as covered.
- **Nobody measures whether the prose is good** beyond the judge (8.33 on v2)
  and the owner's reading (8). A report-only linter flags restated sentences.
- **One user, one run at a time, no login.** A local tool.

Every one of those is a row in `docs/verification.md` §3. **A gap that is listed
is a decision. A gap that is not listed is a defect.**
