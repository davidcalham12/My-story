---
id: SPEC-EXAM-004
title: One critic reads the Bible once and scores three characteristics
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-24: "baja el orquestador y menos criticos tambien me gustaria que los gastos bajen si se puede", then, asked how, choosing "Unir tres en uno (Recommended)" — "one critic scores continuity, world rules and outline: 4 model calls per attempt become 2; the six characteristics and the threshold of 8 stay"
approved_on: 2026-09-24
names_protected_value: the six characteristics (AGENTS.md §6) — none is removed, renamed or re-weighted; what changes is how many subagents score them. No existing agent's `tools:` line changes; a new agent is added with `tools: Glob`, the critics' line.
depends_on: .claude/skills/storymaker/SKILL.md §3, .claude/skills/storymaker/units/chapter.md, .claude/agents/, config/novel.config.json quality_gate
---

# SPEC-EXAM-004 — The Bible critic

## 1. What is wanted, and why

**Each attempt at a chapter costs four model critics.** Three of them —
continuity, science (the world's rules) and outline — are each handed the same
Bible and the same draft, and each reads them from scratch. On the example
novel that was most of 44 subagent calls for 8 chapters, and a large share of
119 minutes and 53 USD.

**The owner asked for fewer critics and lower cost.** The six characteristics
are protected, so they stay. What changes is that **one critic, `bible-critic`,
reads the Bible and the draft once and returns the three scores**, each by the
same rules the three separate critics followed. The prose critic stays on its
own, because it judges the writing rather than its correctness. Length and
chatter stay as arithmetic.

**Per attempt: 4 model calls become 2.** The gate — six characteristics, `min`,
threshold 8, three attempts, patch-then-halt — is unchanged.

## 2. Rules

- `bible-critic` holds `tools: Glob`, like every critic, and runs on Haiku.
- Its reply is **one JSON object with exactly three keys**: `continuity`,
  `science` and `outline`. Each holds the object the separate critic used to
  return, with the same score rule.
- The orchestrator writes each key to the file the separate critic's reply went
  to (`critiques/chNN.<characteristic>.json`). Everything downstream — the gate
  row, the sheet, the conformance audit, Langfuse — reads those files and does
  not change.
- **A missing or unusable key is that characteristic unscored**, excluded from
  the `min` and noted, exactly as a critic that returned nothing was. It never
  counts as a pass.
- The three separate critics stay in `.claude/agents/`, unused at the chapter
  gate, so earlier runs stay explicable and no `tools:` line is touched.
  `science-critic` still runs the FLOW-3 outline audit, which is not a gate
  attempt and is unchanged.
- It applies to runs started after it lands; a run already in flight keeps its
  procedure.

## 3. Out of scope

Merging the prose critic. Changing any score rule, the threshold or the number
of attempts. Re-scoring earlier runs.

## 4. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | `bible-critic` exists with `tools: Glob` and model Haiku, and the frontmatter test pins it | T |
| AC-2 | the procedure (SKILL.md §3 and `units/chapter.md`) dispatches `bible-critic` and `prose-critic` — two model critics — and no longer the three separate ones | T |
| AC-3 | the procedure says where each of the three keys is written and that a missing key is unscored, never a pass | T |
| AC-4 | the watcher knows the new agent | T |
| AC-5 | a real one-chapter run scores all six characteristics with two model critics per attempt, cost and minutes measured against eval 01 | D |

## 5. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| one reading judging three things may judge each less sharply than three readings did | important | the owner's decision to lower cost; each section keeps its own score rule and quoted findings | scores or findings drifting from the earlier runs' in `late_findings.jsonl` and the conformance audit |
| a single malformed reply now leaves three characteristics unscored instead of one | important | unscored is excluded and noted, never a pass; the next attempt re-asks | a gate row noting three unscored characteristics |
| built the evening before delivery | important | the owner's decision; AC-5 is the evidence, or the gap is declared | AC-5 not run |
