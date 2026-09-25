# Anexo O — Inspección visual con browser MCP

El validador `visual_check` inspecciona el libro renderizado: portada con dedicatoria,
índice con enlaces que llegan, ficha de personajes y lugares, página "what changed" (v > 1)
y ausencia de restos (Markdown, `TODO`, marcadores). Configuración: `.mcp.json`
(Playwright MCP); método y checklist: `docs/browser-mcp.md`.

| fecha | versión | resultado | qué encontró |
|---|---|---|---|
| 2026-09-24 | v1 | fail (check 1) | driven with Playwright from Python by the build session, not through the MCP client. 1 cover: no dedication and no alias — nothing wrote dedication.md for a run started from a brief; fixed for later versions in 4cf8a8e, v1 left as published. 2 index: 8 entries, 8 links land. 3 sheet: 5 characters link to their first ch |
| 2026-09-24 | v2 | pass | the completed book (10 chapters, after the resumed run), same method as v1. 1 cover: title and dedication with the alias. 2 index: 10 entries, 15 links land. 3 sheet: characters link; the one place has no first chapter recorded. 5 no leftovers. Recorded in validations |
| 2026-09-24 | v3 | pass | the reader change (fact 36 → "the wooden treehouse observatory"). 4 what changed: the first page, linking chapters 3 and 10. 1 cover with dedication. 2 index, no broken link. 5 no leftovers. Recorded in validations |

**Qué cambió por ello:** la v1 falló la portada (sin dedicatoria ni alias, porque nada
escribía `dedication.md` en un run que sale de un brief). Se corrigió en `4cf8a8e`; la v2
y la v3 pasan.
