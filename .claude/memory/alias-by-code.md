---
name: alias-by-code
description: the orchestrator writes a placeholder for the recipient; the alias is put in by code at publication
type: project
---

The organisation's privacy policy makes the orchestrator write the recipient's alias
as `[NOMBRE_ANONIMIZADO]` in the Bible, the outline and the prose. The owner chose to
keep it (decision B, docs/spec.md §8): `backend.publish.personalise` replaces the
token with `recipient.alias` from the stored brief, mechanically, before the
validators and the PDF. The approved text is kept as `chNN.anon.md`.

**Why:** a model instructed not to reproduce personal data would otherwise break the
product's whole point; doing it in code keeps both.

**How to apply:** give models the `.anon` texts (the reader change and the judge do);
run `personalise` before any validator that counts names or facts. Gap declared in
docs/verification.md §3.23. See [[reader-change-arrival]].
