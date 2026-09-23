---
id: SPEC-011
title: The novels are generated with Haiku — the agents' model line, the orchestrator's model, and what that does to the record
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "yo apruebo", answering the list that named this document; written at his instruction
approved_on: 2026-09-23
depends_on: docs/architecture.md §4, config/pricing.json, .claude/agents/*.md, backend/commons/runner/process.py, AGENTS.md §6
ordered_by: David Calderon, in chat to the session "Novaforge continuación con repositorios", 2026-09-23 — "las novelas que se hagan que se generen con el modelo de haiku"
---

# SPEC-011 — The generation model is Haiku

The owner's order is one sentence. `AGENTS.md` §5 says a change of behaviour
gets a short spec first, and this one changes the thing every cost and every
gate figure in `docs/` was measured under. This is the short spec. It touches
**no `tools:` line** (`AGENTS.md` §6); it touches the `model:` line beside it,
which is not protected, and it says what the change costs the record.

## 1. What is wanted, and why

**W1 — every novel-writing agent runs on Haiku.** The ten files in
`.claude/agents/` carry `model: opus` (four authors) or `model: sonnet` (six
critics and editors). All ten become `model: haiku`. Claude Code resolves the
alias to the current Haiku, which `config/pricing.json` prices as
`claude-haiku-4-5`. The owner wants the novels cheaper to generate while the
frontend and the exam are built; every run from now on is a test run.

**W2 — the orchestrator's model is a config value, passed to `claude -p`.**
Today the runner passes no `--model`, so the orchestrator runs on the
session's default. The orchestrator's own turns are most of a run's cost
(`domain-knowledge.md` §2.2). A new key `models.orchestrator` in
`config/novel.config.json` (default `null` = the CLI's default) is passed as
`--model <alias>` when set; profiles may override it. **This spec sets it to
`null`**: the owner ordered the *novels* onto Haiku, which is the agents; putting
the orchestrator on Haiku too is a separate decision with a named risk (§4),
and this spec leaves the knob in place so that decision is a config edit, not
a code change.

**W3 — the record says what model each figure was measured under.** Every
cost and pass rate in `docs/` was measured with Opus authors and Sonnet
critics. `architecture.md` §4's table changes to `haiku`; the cost figures in
`README.md`, `domain-knowledge.md` §5 and §8 gain the sentence that they were
measured before SPEC-011, under the previous models, and are not comparable to
Haiku runs. `test_every_agent_names_its_model` admits `haiku`.

## 2. Out of scope, named

- The `tools:` line of any agent (`AGENTS.md` §6). Unchanged, and the
  front-matter test keeps pinning it.
- The threshold, the six characteristics, the three attempts, the ceilings.
- Judging whether Haiku's drafts pass the gate as often as Opus's did. That is
  what the next real runs measure; §4 records it as a gap, not a claim.
- Changing `pricing.json` rates.

## 3. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | every `.claude/agents/*.md` front matter reads `model: haiku`; `test_every_agent_names_its_model` accepts `haiku` and the ten files pass it | T |
| AC-2 | `architecture.md` §4 headings and table say `haiku` for all ten; `test_each_agents_model_matches_its_front_matter` passes | T |
| AC-3 | `RunProcess.for_run` appends `--model <alias>` to the argv when `models.orchestrator` is set in the resolved config, and appends nothing when it is `null`; the prompt stays on stdin | T |
| AC-4 | the `tools:` line of every agent is byte-identical before and after (the existing `test_agents_frontmatter` assertions) | T |
| AC-5 | `README.md`, `domain-knowledge.md` §5 and §8 and `verification.md` G13 say which model family their cost figures were measured under and that Haiku runs are not comparable to them | I |
| AC-6 | the first real `tiny` run after this spec records, in `logs/agents.jsonl`, `model: claude-haiku-4-5` on every agent row, and its `cost.json` is written beside it | D |

## 4. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| The gate's pass rate and the redraft count under Haiku are unknown; the six-characteristic threshold of 8 was calibrated on Opus drafts and Sonnet judges | important | the owner's order; the next real runs measure it and `domain-knowledge.md` gets a section for it | `patch_then_halt` firing more often; `measure.mjs` G2 falling |
| The critics on Haiku judge with less nuance than Sonnet did, so `prose` and `continuity` findings may be noisier both ways | important | four of six characteristics were already model judgements (§3.6); the arbitration and the quote rule are the mitigation, unchanged | more overruled findings in `late_findings.jsonl` |
| The orchestrator's model stays the CLI default; putting it on Haiku would cut most of the cost and would weaken procedure obedience (§3.1, §3.12) | important | a config knob, `null` by default, so the owner can decide it without a code change; the risk is named here so the decision is informed | `conformance` breaches on a Haiku-orchestrated run |
| Every measured cost in `docs/` predates this change | incidental | the figures stay true of what they measured; AC-5 labels them | a reader comparing a Haiku run to $16.25 |
