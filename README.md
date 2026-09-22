# NovaForge

A multi-agent harness that writes novels under a bounded context.

**The central claim:** the writer of a chapter never receives the prose of a
previous chapter. It gets the Story Bible, its own outline entry and a bounded
rolling summary — so chapter thirty-four's prompt is the same size as chapter
one's, and the cost curve is flat.

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
| what eight runs actually showed, with numbers | `docs/domain-knowledge.md` |
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

## What one real run cost

`lighthouse-keeper-ledger`: three chapters, seven drafts, four feedback sheets,
**$18.82 measured** from Claude Code's own `result` — 136 turns, 56 minutes. The
same shape under v1 cost $7.45, judged by two characteristics instead of five and
with nothing auditing the outline first.

## What it does not give you

- **The gate does not reproduce.** Three of its five characteristics are model
  judgements, so "it passed the gate" is a statement about one run.
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
