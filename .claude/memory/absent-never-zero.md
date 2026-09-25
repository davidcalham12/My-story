---
name: absent-never-zero
description: a figure nobody measured is NULL with a reason, never 0; every number carries its provenance
type: feedback
---

Every figure carries one of measured, reported, reconstructed, estimated or absent.
A missing figure is NULL with a sentence saying why; the panel shows "not measured",
never "$0".

**Why:** a 0 claims something nobody checked. A malformed critic reply once scored 10
and passed a draft; a halted unit leaves no `result`, so its cost is absent, not free
(docs/verification.md §3.24).

**How to apply:** in code, tests and docs. A sum over segments with one absent is
absent, or a floor that says it is one (the SR-05 per-novel cap). See
[[orchestrator-cost]].
