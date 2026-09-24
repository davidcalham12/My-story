---
id: SPEC-EXAM-006
title: The chapter loop in Python — the model judges, the code conducts
status: draft — awaiting the owner's approval
owner: David Calderon
requested_by: David Calderon — in chat to the coordinating session, 2026-09-24: "si, escribe el spec del orquestador en python"
approved_by: (pending — the owner approves by dictating a sentence, copied here in his words)
approved_on: (pending)
names_protected_value: none of the values in AGENTS.md §6 changes — the threshold of 8, the six characteristics, three attempts, every agent's `tools:` line, patch_then_halt, the 100,000-token ceiling and the budget ceiling are all kept, and several become stricter (§5). What changes is an architectural rule in CLAUDE.md: "Claude Code orchestrates; Python launches, watches and archives". For FLOW-4 only, behind a switch whose default is the current behaviour, Python conducts. Recorded in docs/architecture.md §8 when approved.
depends_on: SPEC-EXAM-003 (the conductor), backend/chapters/domain.py, backend/commons/runner, backend/publish/run_judge.py (the precedent), .claude/agents/, output/*/dist/*/procedure/chapter.md
---

# SPEC-EXAM-006 — The chapter loop in Python

## 1. What is wanted, and why

**Measured, from Claude Code's own `result` events:**

| unit | total | orchestrator (Opus) | agents (Haiku) |
|---|---|---|---|
| the example novel's resume (ch09–10, FLOW-5, FLOW-6) | 21.03 $ · 51 min | 19.34 $ (92 %) | 1.69 $ |
| v3 reader change, ch03, three attempts, 13 agents | 7.52 $ · 26 min | 6.64 $ (88 %) | 0.88 $ |
| the whole example novel, after PLAN block 1's reimport | 74.20 $ | ~96 % | 2.88 $ (estimated, 50 calls) |

The agents, which write and judge, are a few percent of the bill. **The
orchestrator is almost all of it**, because every turn re-reads its whole
context (22.8 M cache-read tokens on the resume alone).

And **what the orchestrator does in FLOW-4 is deterministic**. The order is fixed
(writer → length/chatter → four critics → `min` → `decide`), the numbers are in
the config, the decision is already a Python function (`chapters.domain.decide`),
the sheet is built and validated by `build_sheet` and `validate_sheet`, patches
are applied by `apply_patches`, promotion is `promote`. The model was being paid
to read a procedure and call functions that already exist.

Two alternatives were rejected on evidence:
- **Haiku as the orchestrator:** tried (`novaforge-v2` commit `179ea1b`,
  run `phantom-station`). It stopped dispatching the project's agents and wrote
  the chapters itself, so the writer's isolation — the project's central
  guarantee — was gone.
- **Sonnet as the orchestrator:** cheaper per token, but still a model reading
  the whole procedure every turn. It is the fallback, not the fix. (Found while
  writing this spec: the `sonnet` setting of commit `0c86509` never reached a
  run; both measured units above ran on Opus. Fixed separately.)

## 2. What is built

**A Python loop that runs one chapter from first draft to promotion**, calling
each agent directly as its own Claude Code process — exactly as
`backend/publish/run_judge.py` already calls `judge`:

```
claude -p --agent <name> --output-format stream-json --verbose
       [--json-schema <schema>]  --max-budget-usd <remaining>
       (packet on stdin, never in argv)
```

- `backend/chapters/loop.py` — the loop (service layer). Imports
  `chapters.domain`, `commons.runner`, and nothing from another feature.
- `python -m backend.chapters.loop <run_dir> <n> [--change <fact_id>]` — one
  chapter, the same unit `U4.n` is today.
- A switch in the config, `orchestration.chapter_loop: "claude" | "python"`,
  **default `"claude"`**: nothing that runs today changes unless the owner turns
  it on. Read by the conductor and by the reader-change path.

**Scope: FLOW-4 only.** FLOW-0 to FLOW-3, FLOW-5 and FLOW-6 stay with Claude
Code. They run once per novel and are not where the money goes.

## 3. The loop, step by step

For chapter *n*, attempt *k* = 1, 2, 3:

1. **Assemble the writer's packet in code**, exactly the list in
   `procedure/chapter.md` §1:
   - the four Bible files;
   - this chapter's outline entry only;
   - the rolling summary from the promoted `chNN.summary.md` files, capped at
     `context.max_summary_words`;
   - the canonical names;
   - number, title and `words_per_chapter.target`.

   On attempts 2 and 3 it also carries the writer's own rejected draft and the
   sheet (redraft rules 1 and 2). **No previous chapter's prose is ever read by
   the loop into a packet**, and a test pins that.
2. **Measure the packet before dispatch** against the 100,000-token ceiling.
   Over the ceiling → halt with the figure, never truncate.
3. **Dispatch `chapter-writer`.** Write `chapters/chNN.attemptK.md` before scoring.
4. **Run the hooks' checks in code**: `validate-chapter` (length, canonical
   names) and the forbidden-words `policy`. They are Claude Code hooks on
   `Write`; the loop writes with Python, so it calls the same functions. It
   never keeps a second copy of them.
5. **Score `length` and `chatter` by arithmetic.** `chatter` = 0 → redraft
   without calling the critics (chapter.md §3).
6. **Dispatch the four critics in parallel**: continuity, science, outline and
   prose (plus `bible-critic` where the profile enables it). Each one runs with
   `--json-schema` for its envelope, so a malformed verdict is a schema failure
   rather than a parsing guess.
7. **Keep only findings that quote the draft verbatim.** Score `prose` with
   `score_prose` and `outline` with `score_outline`. Aggregate with `min` and
   ask `decide`.
8. **Act on the decision:**
   - **accept** → `promote`;
   - **retry** → `build_sheet` at the level `decide` names, `validate_sheet`, next attempt;
   - **patch** → `apply_patches` with the critics' replacement sentences, then rescore with `patched: true`;
   - **halt** → stop, write why, no summary.
9. **On accept, get the summary**: one call to `chapter-writer` with its own
   accepted chapter, which is not a previous chapter's prose. Checked by
   `check_summary`. Over the cap → asked once more. Never truncated.
10. **Persist after every step**: `calls` with the four token figures and the
    **measured** cost of that process, `validations`, the gate row, the agents
    log. Then export to Langfuse as today.

## 4. What the model still decides, and what it no longer does

| decision | today | with this spec |
|---|---|---|
| draft, critique, summarise | Haiku agents | Haiku agents, unchanged |
| order, counts, thresholds, retries | the orchestrator reading SKILL.md | code reading `flow.yaml` and `config/` |
| arbitrating a critic's finding that looks wrong | the orchestrator (re-examination by SendMessage) | **not done**: the only filter is mechanical (the quote must be in the draft). Declared as a gap (§7) |
| whether a patch is sound | the orchestrator arbitrates | applied literally; rescored by the same critics |

## 5. What gets stricter

- **Cost per agent becomes measured**, not estimated: each call is its own
  process with its own `result.total_cost_usd`.
- **The 100k ceiling becomes a real reservation**: the packet is measured
  before dispatch, which `verification.md` G2 says is impossible today.
- **The budget is enforced per call**: each process gets
  `--max-budget-usd = ceiling − spent`.
- **The critics run in parallel by construction**, not by the orchestrator
  remembering to (chapter.md §3 records it failing to).
- **The writer's isolation no longer depends on a model's obedience** at all:
  the packet is built by code.

## 6. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | With the switch at `"claude"` (the default), the whole suite passes unchanged | T |
| AC-2 | The loop, driven by recorded agent outputs (a fake runner, $0), reaches accept, retry → accept, patch and halt, and the decisions match `decide` on the same scores | T |
| AC-3 | No packet the loop builds contains text from another chapter's `chNN.md` or `chNN.attemptK.md` (fixture with sentinel strings) | T |
| AC-4 | A packet over 100,000 tokens is not dispatched; the run halts with the figure | T |
| AC-5 | Every `calls` row has input, cache_creation, cache_read, output and a cost with provenance `measured` | T |
| AC-6 | **The spike:** one real chapter, profile `eval`, ceiling 3 USD, measured cost, minutes, attempts and scores, set beside the orchestrated eval-04 chapter and v3 ch03 | D |
| AC-7 | The spike's chapter passes through `promote`, and its critiques and sheet are on disk in the same shape as an orchestrated chapter | I |

## 7. Gaps this spec leaves

| gap | level | why accepted |
|---|---|---|
| No arbitration of a false finding | important | measured twice on the stress run as a re-examination that changed a score. The loop may therefore retry where the orchestrator would not have; the cost of that retry is measured in AC-6 |
| Each agent process pays Claude Code's start-up floor | incidental | the measured ~48,800 tokens were the orchestrator's; an agent's floor is measured in AC-6, not assumed |
| FLOW-0 to FLOW-3, FLOW-5 and FLOW-6 stay orchestrated | incidental | they run once per novel; moving them is a later spec if AC-6 justifies it |
| The loop is new code the night before delivery | important | the switch defaults to the current behaviour; the example novel and the evals are not re-run on it |

## 8. Out of scope

- Changing any agent's prompt or `tools:` line.
- Changing any value in AGENTS.md §6.
- Re-running the example novel or the evals on the loop.
- Using the loop for the v3 reader change: v3 finishes on the proven path first.

## 9. Order and time box

1. v3 finishes on the current path (owner's order: costs → v3 → his novel).
2. Code, test first. AC-1 to AC-5 at $0.
3. AC-6, the spike, only with the owner's go and the 3 USD ceiling.
4. **Time box: if AC-6 is not measured by 02:00 UTC on 2026-09-25**, the work
   stops. The deck then presents the measured table in §1 as the argument, and
   this spec as the designed next step.
