---
name: reader-change-arrival
description: the six-characteristic gate does not check that a changed fact is present; the arrival check does
type: project
---

v3's chapter 3 passed the gate with 0 mentions of the changed fact (the observatory).
Since `e0b7c38` a reader change is accepted only if the new text is present and no
variant of the old phrase is (case, plural, article; the phrase, not the word).

**Why:** "a change that does not arrive is not a change" (owner, docs/spec.md §8). It
is the reader change's acceptance condition, like `chatter` — not a seventh
characteristic, and the threshold is unchanged.

**How to apply:** `python -m backend.versions.change --arrival <draft> --to … --old …`;
`--workspace vN --only N` redoes a chapter in an unpublished version and keeps the
earlier files in `_redo-*`. See [[alias-by-code]].
