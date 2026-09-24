---
description: A reader changes one fact; only the chapters that use it are rewritten, as a new version
argument-hint: <slug> <fact-id> "<new wording>"
---

The reader-change demo (exam §2, evidence 3). Arguments: `$ARGUMENTS`.

**This spends money.** Run `/status` first, say what it will cost from the
chapters it touches, and do not launch until the owner approves in this session.

1. Show which chapters would change, before anything is spent:
   `GET /api/runs/{id}/facts/{fact_id}/impact`. The list is a floor: a
   paraphrase is missed, never invented.
2. Keep the procedure the book was written with, so the new chapters match the
   old ones: set `NOVAFORGE_CHANGE_PROCEDURE_REV` to the commit the book was
   written at (for *The Other Side of the Hill*, `c35fdc9^`).
3. Run it: `python -m backend.versions.change <slug> --fact <fact-id> --to "<wording>"`.
   The impacted chapters go through the same gate — threshold 8, three
   attempts, patch-then-halt.
4. Confirm: `dist/v<n>/novel.pdf` opens with the page of **what changed**,
   linking to each rewritten chapter; the previous version's folder is
   untouched; the new version appears in *Read*.
5. Report chapters rewritten, cost (measured, from the stream's `result`) and
   minutes.
