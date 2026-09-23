# PLAN-011 — The generation model is Haiku

status: approved
date: 2026-09-23
implements: SPEC-011-generation-model (approved 2026-09-23)
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "yo apruebo", answering the list that named this document; written at his instruction
approved_on: 2026-09-23
written_by: the session "Novaforge continuación con repositorios"

Two phases, one commit each, tests red first. Executed by `novaforge-05`, reviewed by the writer of this plan, approved by the owner.

## Part 1 — Reference

| what | where |
|---|---|
| the spec | `specs/SPEC-011-generation-model.md` |
| what it touches | `.claude/agents/*.md` (`model:` only), `docs/architecture.md` §4, `backend/tests/test_agents_frontmatter.py`, `backend/commons/runner/process.py`, `backend/runs/service.py` (`_process`), `config/novel.config.json`, `backend/tests/test_runner.py`, `README.md`, `docs/domain-knowledge.md`, `docs/verification.md` |
| what must not move | every `tools:` line; `test_agents_frontmatter.py`'s `EXPECTED` table is unchanged |

## Part 2 — Build order

### 11.1 The agents run on Haiku, and the record says so

**Tests first** — `backend/tests/test_agents_frontmatter.py`:

| test | criterion |
|---|---|
| `test_every_agent_names_its_model` — the admitted set becomes `("opus", "sonnet", "haiku")` **and** a new assertion: every agent's model equals the one `architecture.md` §4 documents (already `test_each_agents_model_matches_its_front_matter`; run and cite) | AC-1, AC-2 |
| `test_the_tools_lines_did_not_move_with_the_model` — the existing `EXPECTED` assertions, run and cited as the evidence | AC-4 |

Seen red: change the ten `model:` lines first; `test_each_agents_model_matches_its_front_matter` goes red against the doc, then the doc is edited and it goes green.

**Code / docs.**
1. Ten `.claude/agents/*.md`: `model: haiku`. Nothing else in the file.
2. `docs/architecture.md` §4: the ten headings `### 4.N name — FLOW-x, haiku` and the table's model column; one sentence under the table: *all ten on Haiku since SPEC-011 (2026-09-23); the figures elsewhere in `docs/` were measured under Opus authors and Sonnet critics.*
3. `README.md` "What a real run costs", `domain-knowledge.md` §5 and §8, `verification.md` G13: the sentence of AC-5.
4. `SKILL.md` §"Record it": the example `model: opus` line becomes `model: haiku`; the id to log is `claude-haiku-4-5`, which `pricing.json` prices.

**Effort.** 0.75 h, *estimated*.

### 11.2 The orchestrator's model is a config knob

**Tests first** — `backend/tests/test_runner.py`:

| test | criterion |
|---|---|
| `test_argv_carries_the_orchestrator_model_when_the_config_sets_one` — `RunProcess.for_run(..., model="haiku")` → `"--model", "haiku"` in the command, after `--allowedTools` and before nothing else; the prompt is still absent from argv | AC-3 |
| `test_argv_carries_no_model_flag_when_the_config_leaves_it_null` — `model=None` → no `--model` in the command | AC-3 |
| `test_the_orchestrator_model_is_read_from_the_resolved_config_not_a_literal` — `service._process` passes `cfg["models"]["orchestrator"]`; a profile overlaying it wins | AC-3, C6 |

**Code.**
1. `config/novel.config.json`: `"models": {"orchestrator": null}` with a `_comment_models_orchestrator` saying what `null` means and why the knob exists (SPEC-011 §4, row 3). The existing `_comment_models` (agents' models live in their files) stays true.
2. `RunProcess.for_run(..., model: str | None = None)`: appends `["--model", model]` when set.
3. `RunService._process`: passes `cfg.get("models", {}).get("orchestrator")`.
4. `loader.resolve` needs no change: the profile overlay is key by key already.

**Docs.** `architecture.md` §3.1 gains one sentence: the orchestrator's model is `models.orchestrator`, `null` = the CLI default. `claude.md` "Running it": one line showing the knob.

**Effort.** 0.75 h, *estimated*.

## Part 3 — Tests by phase

| phase | new tests | criteria |
|---|---|---|
| 11.1 | 1 changed, 2 cited | AC-1, AC-2, AC-4 |
| 11.2 | 3 | AC-3 |

AC-5 is **I** (the owner reads the four sentences). AC-6 is **D**: the first real `tiny` run after both phases, which is also the `--max-budget-usd 1.0` test of SPEC-007 §3.21 if the owner keeps that order — one run answers both, and on Haiku it costs less to find out.

## Part 4 — Gaps this plan leaves

| id | gap | level | why | how we would notice |
|---|---|---|---|---|
| P-1 | the ceiling of `tiny` (25.0) was set for Opus/Sonnet; on Haiku it is loose | incidental | a loose ceiling never halts a good run; tightening it is a profile edit after the first Haiku run is measured | the first Haiku `tiny`'s `cost.json` |
| P-2 | `test_import.py` and `import_v1` expand `opus`/`sonnet`/`haiku` to full ids; the expansion for `haiku` is `claude-haiku-4-5` and must match `pricing.json` | incidental | cited, not changed; a test already covers the model-name expansion | a `calls` row priced at nothing |

## Part 5 — Effort

1.5 h, *estimated*, plus the real run of AC-6.
