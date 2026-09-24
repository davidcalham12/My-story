---
id: SPEC-EXAM-008
title: The real cost of every change to a novel, measured, sent to Langfuse and read back from it
status: approved
owner: David Calderon
requested_by: David Calderon — in chat to the coordinating session, 2026-09-24: "quiero que se vea el costo real de cada cosa que se modifique, o sea ese costo tomalo por novela y de lo que te dice en langfuse"
decisions: chosen by the owner in the same session — source "Langfuse, con respaldo local"; detail "Total en $ y minutos" and "Orquestador vs agentes"
approved_by: David Calderon — in chat to the coordinating session, 2026-09-24, after the build session's seven-point review was folded in as §8: "apruebo el SPEC-EXAM-008"
approved_on: 2026-09-24
names_protected_value: none. This measures and shows cost; it does not change the budget ceiling or how it is enforced.
depends_on: backend/runs (the result event), tools/export_to_langfuse.py, SPEC-EXAM-007 (run_segments), SPEC-EXAM-006 (one process per agent), frontend pages library and read
---

# SPEC-EXAM-008 — The cost of every change, as Langfuse records it

## 1. What is wanted, and why

The owner wants to see, **for each novel**, what **each thing that was done to
it** really cost. By "each thing" he means:
- the first generation;
- a continuation;
- a reader change;
- a chapter redone.

The cost he wants is the one **Langfuse shows**.

**What exists today, and what is wrong with it:**
- Each Claude Code process ends with a `result` event that carries
  `total_cost_usd` and **`modelUsage`, the cost per model**. That figure is
  **measured**.
- Measured, the example novel is:
  - first run: 53.17 $ = Opus 48.79 + Haiku 4.38;
  - resume: 21.03 $ = Opus 19.34 + Haiku 1.69.
- So **agents are 8 % and the orchestrator 92 %**, measured.
- What Langfuse shows today is a per-call cost **estimated** from token counts
  and a price table: 2.88 $ for the agents across 50 calls. **That estimate is
  half the measured figure.** Some calls were never seen, and prompt caching is
  not fully priced. It is also summed with nothing measured, so Langfuse
  cannot show the real total.
- The panel shows no cost per change at all.

## 2. The unit: a *change*

A **change** is one thing done to a novel that launches Claude Code:

| kind | example |
|---|---|
| `generate` | the first run (FLOW-0 to FLOW-6, or as far as it got) |
| `continue` | a SPEC-EXAM-007 continuation |
| `reader_change` | "the cardboard observatory becomes a treehouse" → v3 |
| `redo` | chapter 3 of v3 redone after the arrival check failed |

A change groups one or more processes. Each process leaves one `result`.

For each change, the figures are:

| figure | from | provenance |
|---|---|---|
| total $ | Σ `result.total_cost_usd` of its processes | measured |
| minutes | Σ `result.duration_ms` | measured |
| orchestrator $ and model | `modelUsage` entries for the orchestrator's model (Sonnet or Opus) | measured |
| agents $ and model | `modelUsage` entries for the agents' model (Haiku) | measured |

- With the Python loop (SPEC-EXAM-006), each agent is its own process, so the
  agents' figure is measured process by process as well.
- A process with no `result` (killed, crashed) gives **absent**, never 0, and
  the change shows "incomplete: N processes without a result".

## 3. Recording

- Table `changes(run_id, n, kind, label, version, chapters, started_at,
  finished_at, total_usd, minutes, orchestrator_model, orchestrator_usd,
  agents_model, agents_usd, provenance, langfuse_trace_id)`. It reuses
  SPEC-EXAM-007's `run_segments` if the plan finds it fits; it must not
  become two tables that say the same thing.
- **Written the moment each `result` arrives**, not at the end. A run cut
  halfway still shows what it spent.
- **Backfill from what is already on disk**, at $0:
  - the example novel's first run (event seq 2038) and its resume;
  - the v3 attempts, including the one cut by the org's spend limit (7.52 $);
  - the v3 ch03 on Sonnet (4.24 $);
  - v3 ch10 and the redo when they end;
  - both evals.

## 4. Langfuse

- **One trace per change**, in the novel's session. Inside it, two
  generations carry the **measured** cost:
  - `orchestrator` (its model, measured `cost_details.total`);
  - `agents` (Haiku, measured `cost_details.total`).
- The per-call observations stay, with their tokens, but their estimated cost
  moves to **metadata** (`estimated_cost_usd`) and **not** to `cost_details`.
  Otherwise Langfuse would add estimated and measured together and show a
  total that is neither.
- The trace is tagged with `kind`, `version` and the chapters, and its
  metadata says `provenance: measured` and which `result` events it came from.

## 5. Reading it back: the panel

- A backend endpoint, `GET /api/runs/{id}/costs`, asks Langfuse for the
  novel's session (the public API `v2/observations`; the legacy endpoints
  return 410 for this organisation) and returns one row per change.
- **Fallback.** If Langfuse does not answer within a few seconds, or has not
  ingested a trace yet, the row comes from the local table and is marked
  **"sin confirmar en Langfuse"**. If Langfuse and the table disagree, both
  figures are shown and the row says so; neither is silently preferred.
- **On a novel's page, a "Costes" section:** one row per change with what it
  was, when, minutes, total, orchestrator (model and $), agents (model and $),
  the source (Langfuse ✓ or local) and a link to the trace. The novel's total
  goes at the bottom.
- **On the library card:** the novel's total $, with its provenance.
- Credentials only from the environment. The endpoint never returns them or
  puts them in a URL.

## 6. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | From a recorded `result` with `modelUsage`, the change's orchestrator and agents figures equal the per-model `costUSD` and sum to `total_cost_usd` | T |
| AC-2 | A process with no `result` makes the change `absent` for the figures it could not measure, never 0 | T |
| AC-3 | The export puts measured cost only on the two generations, and no estimated cost in `cost_details` (a test on the ops list) | T |
| AC-4 | `/costs` reads Langfuse through a fake client; with Langfuse down it returns the local rows marked unconfirmed; on disagreement it returns both | T |
| AC-5 | The backfill gives the example novel exactly 53.17 (Opus 48.79 / Haiku 4.38) and 21.03 (Opus 19.34 / Haiku 1.69) | T |
| AC-6 | The panel shows the Costes section and the card total (component tests) | T |
| AC-7 | **Demonstration:** after re-export, Langfuse's own UI shows the example novel's traces with 74.20 $ in total, and the panel shows the same rows with "Langfuse ✓" | D |

## 7. Gaps

| gap | level | why accepted |
|---|---|---|
| Inside one orchestrated process, the agents' cost is not split by chapter | incidental | `modelUsage` is per process; with the Python loop it becomes per agent |
| Langfuse ingestion is not instant | incidental | the fallback shows the local figure, marked unconfirmed, until it arrives |
| The org's monthly spend limit and the 5-hour window are not shown | incidental | they are account-level; out of scope |

## 8. Precisions from the build session's review against the code

1. **One table, `changes`**, shared with SPEC-EXAM-007. Its columns: `kind`
   (`generate | continue | reader_change | redo`), `version`, `chapters`,
   `ceiling_usd`, `ceiling_by`, plus §3's figures. SPEC-EXAM-007 uses it with
   `kind = 'continue'` instead of creating `run_segments`. There are never two
   tables for this. A reader change or a redo is not a segment of a run: it
   lives in a version workspace, which is why a run-only table did not fit.
2. **Grouping.**
   - `versions/change.py` creates the `changes` row when it starts and passes
     its `change_id` to every chapter process. Each `result` adds to that row.
   - `--workspace vN --only N` creates its own row, `kind = 'redo'`, with the
     same version.
   - The Python loop receives the `change_id` the way it receives the
     `run_id`.
   - On the single path, `service._record` already sees the `result` and
     updates the row there.
3. **Orchestrator versus agents is decided by role, not by model family.**
   - The orchestrator is the process's main model: its `--model`, or the model
     of its first assistant message. Everything else in `modelUsage` is agents.
   - With the Python loop there is **no orchestrator**: `orchestrator_model =
     null` with the note "no orchestrator (python loop)". That is neither 0 nor
     absent.
4. **This supersedes 07fe3fb for cost.** 07fe3fb put the estimated per-call
   cost in `cost_details`, split into input, output and cache, because the
   owner asked to see input against output. Here the per-call **tokens** stay
   split (input, output, cache, visible per call). The per-call
   **estimated $**, with the same split, moves to metadata. `cost_details`
   carries only measured cost, so Langfuse's totals are the real ones.
   `--replace` is still needed on every re-export.
5. **`/costs`**: `get_many` already accepts a `session_id` (v2). Add a short
   timeout and a cache, because the novel page calls it on every load.
6. **Backfill sources.**
   - First run: events seq 2038.
   - Resume: `logs/resume.stream.jsonl`.
   - v3 cut by the org limit: `dist/_aborted-change-2/logs`.
   - v3 on Sonnet: `dist/v3/logs`.
   - **absent**: the first reader-change demo (before 94e64ff, no stream kept)
     and eval 01 (stopped with no `result`).
   - Eval 04 has its `result`.

## 9. Order

After the v3 is published and beside SPEC-EXAM-007: $0 until AC-7, which only
re-exports.
