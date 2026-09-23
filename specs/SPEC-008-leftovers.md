---
id: SPEC-008
title: Two leftovers of backend v1 — the import's fresh-database default and the archive's unknown file
status: approved
owner: David Calderon
approved_by: David Calderon (standing approval given in chat, 2026-09-22 — "yo apruebo todo lo que me pongas"; written by the building session)
approved_on: 2026-09-23
ratified: 2026-09-23 by David Calderon, in chat to the session "Novaforge continuación con repositorios" — "apruebo PLAN-010 y ratifico las specs, sigue con todo"; this line written at his instruction
depends_on: specs/SPEC-007-backend-v1.md, docs/verification.md §3.20, docs/domain-knowledge.md §8.6
---

# SPEC-008 — Two leftovers

Both were found at Paso 10 of the backend-v1 runbook and written down as
`verification.md` §3.20 and `domain-knowledge.md` §8.6 rather than fixed on the
spot, because `AGENTS.md` §5 says a quick fix gets a short spec first. This is
the short spec.

## 1. What is wanted, and why

**W1 — the import CLI on an empty database imports only v1 runs.**
`python -m backend.commons.db.import_v1` without slugs takes every `output/*/`
with a `state.json` for a v1 run and marks it `pre-loop003`. v2 writes a
`state.json` too. On the deployed database the v2 runs are already rows and are
skipped; on an empty one, two came in as history (§3.20). A v2 run excluded from
LOOP-003 statistics it belongs in, and read as pre-loop history in the panel, is
a wrong number that looks like a right one.

**W2 — the archive knows `chNN.prose_check.json`.** `check_prose` writes its
output beside the critiques by design; the archiver does not know the name and
warns `not a chapter critique, skipped` three times per run. A warning that
fires on every run stops being read, and the next real one arrives unread.

## 2. Out of scope

Wiring `commons/search` into `SKILL.md` before the continuity critic
(`verification.md` §3.15, SPEC-007 Q5). That is a change to the procedure, which
only a real run verifies, and the conservative behaviour — the critic receives
the whole Bible — has produced nothing visibly wrong in five runs. It stays a
declared gap with its own spec when someone wants it.

## 3. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | `import_all(conn, output, slugs=None)` skips a directory that carries a v2 marker (`conformance.json`, which only v2 writes) and reports it as skipped, not imported | T |
| AC-2 | The same call on the eight v1 runs still imports them all | T |
| AC-3 | `archive_run` on a directory with `chNN.prose_check.json` beside the critiques produces no `not a chapter critique` note for it | T |
| AC-4 | A file that is genuinely unknown still produces the note | T |

## 4. Gaps this spec leaves

| gap | level | why accepted | how we would notice |
|---|---|---|---|
| A v2 run that halted before writing `conformance.json` has no marker and would import as history on a fresh database | incidental | such a run also has no archive worth importing; the operator can name slugs | a `pre-loop003` row whose `state.json` names a v2 profile stage |
