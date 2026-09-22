# NovaForge

A multi-agent harness that writes novels under a bounded context.

**The central claim:** the writer of a chapter never receives the prose of a
previous chapter. It gets the Story Bible, its own outline entry and a bounded
rolling summary, so a later chapter's prompt is the size of an early one's.

That is **structural** — `chapter-writer` holds `tools: Glob`, which returns
paths and cannot return contents, so prior prose is unreachable rather than
merely unpassed. **Whether the resulting book holds together over thirty-four
chapters is not established**: the longest run is eight, and the two runs that
exist disagree about whether later chapters get harder. `docs/verification.md` §7
and `docs/domain-knowledge.md` §3.3b.

## Running it

```bash
# backend — the tests replay a recorded run and cost nothing
pip install fastapi uvicorn pydantic pyyaml pytest httpx sqlite-vec
python -m pytest backend/tests -q
python -m uvicorn backend.main:app --port 8000

# frontend
cd frontend && npm install && npm run dev
```

**Claude Code is the orchestrator. There is no API key and no SDK.** The backend
launches `claude -p` as a subprocess, reads its event stream and archives it. So
`claude` must be on PATH and signed in on this machine. Set
`USE_RECORDED_STREAM=false` to orchestrate for real — every real run costs the
subscription, which is why the tests replay a recording instead.

## Where to start reading

| you want | read |
|---|---|
| how work gets done here | `AGENTS.md` |
| the stack, the orchestration, memory, the token ceiling | `docs/architecture.md` |
| the vocabulary, mapped from the ontology | `docs/definitions.md` |
| what eleven runs actually showed, with numbers | `docs/domain-knowledge.md` |
| every guarantee and the evidence behind it | `docs/verification.md` |
| **what is *not* verified, and why that is a decision** | `docs/verification.md` §3 |
| the quality gate and how it was arrived at | `specs/loops/LOOP-003/README.md` |

## Is a run sound?

```bash
python -m backend.report output/<slug>
```

One command, three answers in the order they matter: **did the gate hold**,
**what did it cost**, and **what is unchecked**. The last section is not
politeness — a report listing only what it verified reads as a clean bill of
health, and nothing here reads whether the prose is any good.

It exits non-zero only for a gate breach. A run nobody archived reports
`unchecked` and exits 0: it has not failed, it has not passed, and an exit code
cannot say the second without lying.

## What a real run costs

Two v2 runs are measured, both from Claude Code's own `result` event.

| | chapters | words | cost | v1, comparable |
|---|---|---|---|---|
| `lighthouse-keeper-ledger` | 3 | 1,831 | **$18.82** | $7.45 |
| `cartographer-inconstant-valley` | 8 | 11,133 | **$54.87** | $49.33 |

**The overhead does not scale with the book.** At three chapters v2 costs 2.5×
what v1 did; at eight, **eleven per cent** — for roughly twice the judging and
*fewer* orchestrator turns. Most of the extra is fixed: the Bible, the outline,
the audit before anyone writes. Per thousand words the eight-chapter runs are
$4.60 and $4.93.

## What it does not give you

- **The gate does not reproduce.** Four of its six characteristics are model
  judgements, so "it passed the gate" is a statement about one run.
- **The gate can be disobeyed, and has been.** On the eight-chapter run two
  chapters entered the book that should not have. The decision is arithmetic and
  promotion is a script that refuses — but the orchestrator holds `Write` and
  always will, so what the system guarantees is **detection**, not prevention.
  Every run writes a `conformance.json` beside its book saying which it was.
- **No tamper-evident audit.** The log is a record the orchestrator writes.
- **One user, one run at a time.** A local tool.
- **Retrieval is not exhaustive**, which is why the rules and the outline entry
  are always passed whole.
- **Nobody measures whether the prose is good.** Three mechanical defects are
  checked by a script; voice, pacing, dialogue and originality are not checked at
  all, by anything.

Every one of those is a row in `docs/verification.md` §3 with its scope, its
signal and who reviews it. **A gap that is listed is a decision. A gap that is
not listed is a defect.**
