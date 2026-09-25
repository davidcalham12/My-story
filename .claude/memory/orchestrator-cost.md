---
name: orchestrator-cost
description: the orchestrator, not the agents, is most of a novel's bill; measure it from modelUsage
type: project
---

Measured on the example novel (`result.modelUsage`, 2026-09-24): first run 53.17 USD
= Opus 48.79 + Haiku 4.38; resume 21.03 = Opus 19.34 + Haiku 1.69. The agents are
~8 %. The same reader-change chapter cost 7.52 on Opus and 4.24 on Sonnet.

**Why:** the orchestrator re-reads its whole context every turn (22.8 M cache-read
tokens on one resume). A snapshot taken before `models.orchestrator` was set ran on
the CLI default, Opus, while the config said Sonnet.

**How to apply:** profiles set `models.orchestrator: sonnet`; never Haiku (see
[[writer-isolation]]). Check the model in `modelUsage`, not in the config. The
per-call estimate from `config/pricing.json` came out at about half the measured
figure: report measured cost from `result` events (SPEC-EXAM-008). See
[[absent-never-zero]].
