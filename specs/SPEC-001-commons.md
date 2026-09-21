---
id: SPEC-001
title: commons — the machinery nobody may skip
status: approved
created: 2026-09-21
approved: 2026-09-21 by David Calderon
---

# SPEC-001 — `commons`

## What is wanted

The shared machinery every feature depends on, built so that the system's two
central guarantees are properties of the code rather than of anyone's care:

1. **`commons/context`** — a typed `ContextPacket` per agent, its builder, and
   the **concurrent token semaphore**.
2. **`commons/llm`** — the only path to a model: a mock engine driven by an
   explicit plan, and the real Anthropic client behind a flag.
3. **`commons/db`** — connection, numbered SQL migrations, and the schema.
4. **`commons/budget`** — the cost ceiling, projected worst case, checked before
   every call.
5. **`commons/log`** — one row per call, with tokens in and out separated.
6. **`commons/config`** — loading `flow.yaml`, the base config and the profiles.

## Why

Two guarantees were held structurally in v1 and are not held by anything in v2
unless this module holds them.

**G1** — the chapter writer could not reach prior prose because its tool list
could not return file contents. Calling the API directly gives that up. The
replacement is that the writer's packet *has no field that can carry prose*, and
that is only true if one module builds every packet.

**G2** — the ceiling is on tokens **in flight at one instant**, not per call.
Five critics of 30,000 satisfy a per-call limit and put 150,000 in the air. Only
a semaphore on the single path to the model can hold that.

If a feature can construct its own client, both guarantees are decoration.

## Out of scope

- The six features. This is their foundation, not their implementation.
- `sqlite-vec` and embeddings. The schema reserves their tables; Phase 5 fills
  them.
- Resume after an interrupted run. The schema must not preclude it; nothing
  implements it.
- The real engine's cost accounting beyond recording what the API returns.
- Any frontend.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| A1 | The writer's `ContextPacket` has no field able to carry another chapter's prose, and a test fails if the builder gains one | **T** |
| A2 | Five calls reserving 30,000 each, dispatched together, never exceed 100,000 in flight; all five complete; every log row satisfies `in_flight_at_dispatch + tokens_reserved ≤ capacity` | **T** |
| A3 | A reservation larger than total capacity raises before waiting, and the run is marked `halted: context` | **T** |
| A4 | Prompt tokens are counted, never estimated; the mock uses a deterministic tokenizer and the real engine the counting API | **T** |
| A5 | The mock engine, given a plan `{chapter, attempt, fail: [...]}`, produces the named failures — and produces out-of-band and heading-less text on demand, so `length` and `chatter` compute over real text | **T** |
| A6 | Migrations run once, in order, and are recorded; running twice is a no-op | **T** |
| A7 | The budget projects worst case (exact input + `max_tokens`), halts before the call that would exceed the ceiling, and the partial attempt is kept | **T** |
| A8 | Every call writes one log row with input and output tokens separated, exact cost, duration, a real timestamp, `tokens_reserved`, `in_flight_at_dispatch` and `wait_ms` | **T** |
| A9 | All eight v1 runs import, and each carries a completeness record naming what it did not have | **T** |
| A10 | Imported runs are marked `pre-loop003` and are excluded from LOOP-003 statistics | **T** |
| A11 | `commons/llm` is the only path to a model | **I** — nothing enforces it at import time; this is the weakest link and is recorded as such in `verification.md` G2 |
| A12 | The whole suite runs with no network and no credential | **T** |

## Notes

A11 is deliberately **I** and not **T**. An import-boundary test would raise it to
**A**; it is not in this spec's scope, and pretending otherwise would be the exact
failure `verification.md` exists to prevent.
