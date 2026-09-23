# docs/brief — the start-up documents

The professor's brief and its annexes are the origin of most decisions in
`docs/architecture.md`. This folder holds what the repository has of them
**verbatim**, and says plainly what it does not have.

| document | in this folder | where its content otherwise lives |
|---|---|---|
| `NOVAFORGE-V2-BRIEF.md` | **yes**: [`brief.md`](brief.md) — from `davidcalham12/nova-repo`, 2026-09-23 | `architecture.md` §8.1; `claude.md` rules |
| Anexo B — `agents.md`, memory layers, 100k | **yes**: [`anexo-b.md`](anexo-b.md) | `architecture.md` §8.2 |
| Anexo C — Claude Code orchestrates, no API key | **yes**: [`anexo-c.md`](anexo-c.md) | `architecture.md` §8.4 |
| Anexo D — principios de verificación (best effort) | **yes**: [`anexo-d-verificacion.md`](anexo-d-verificacion.md), as pasted 2026-09-22 (identical to nova-repo's copy) | `verification.md` §1, §3, §4, §5 |
| Runbook — backend v1, spec to tested branch | **yes**: [`runbook-backend-v1.md`](runbook-backend-v1.md) | executed: `docs/REPORT-backend-v1.md` |
| storyMaker exam plan | **yes**: [`storymaker-exam-plan.md`](storymaker-exam-plan.md) — the design session's decoding of the final exam; its counts predate SPEC-006 (says nine agents, five characteristics) | the exam is a separate repository |

Until 2026-09-23 this README said the brief and Annexes B and C were not
available to the building session. They arrived that day through
`nova-repo`, the design session's handoff repository, and are here verbatim.

The documents are kept in their original Spanish: they are source documents,
not project documentation, and translating them would make them paraphrases. Everything else in
`docs/` is in English.

Nothing in this folder is reconstructed from memory.
