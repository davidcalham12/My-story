# U3a — outline, the plan (FLOW-3, first half)

One unit: the whole book is planned. Read
`.claude/skills/storymaker/SKILL.md` first — the agents' tool boundary, the
logging duties and the ceiling are there and are not repeated here.

`plot-architect` is the last agent that sees the whole book at once. After U3b
every chapter is written by a writer that sees one entry.

**Why this is half a unit.** FLOW-3 used to be one process and ended at 109,722
tokens against a ceiling of 100,000 — the worst overrun of the run. A fresh
orchestrator arrives carrying about 48,800 before it opens a file, so a unit has
roughly 51,000 to work in, and three probes with fifteen, five and two tools all
started at the same place: the floor is not the tool list, and a leaner prompt
cannot buy the room back. Writing the plan and auditing it are now two
processes. **Your unit ends when `outline.md` exists.** You do not write
`critiques/outline.audit.json`.

## 1. Dispatch `plot-architect`

Its prompt carries all four Bible files quoted **in full** — it has `Glob` and
cannot open one — the chapter count, the canonical names from
`bible/characters.md`, and `novel.promises` and `novel.beats_per_chapter`.

It returns the outline as text. **You** write it to `outline.md`.

## 2. Run the stage's checks

```bash
python -m backend.checks FLOW-3 <run_dir>
```

Two of them matter here for reasons worth stating.

**`promises are reachable`.** A promise planted and never paid is the
foreshadowing failure the ontology names, and it is **the one literary defect a
script can reach** — but only because `bible/mysteries.md` names chapters. If it
reports a landing past the last chapter, the outline owes an answer the book will
not reach, and that is cheaper to fix now than at chapter eight. It reads the
*commitment*, not the chapter: an outline entry that says nothing about the
mystery it was supposed to land passes this and fails a reader.

**`rules resolve`.** The critics and U3b's audit refer to rules by number. If
`bible/world.md` writes them as unnumbered bullets, those numbers are the critic
counting bullets and inventing an identifier, and the arbitration record decays
without anyone noticing. Send `worldbuilder` back to number them; do not
renumber them yourself.

A Bible corrected here is a Bible whose rows are stale, so re-run
`python -m backend.bible.ingest <run_dir>` after any such correction — it is
idempotent and re-reads what changed.

## 3. Leave the outline splittable

U4.n is handed one entry, and it is split on `### Chapter N — Title`. Check the
split yourself: if it yields fewer entries than `novel.chapters`, the outline is
malformed — dispatch again rather than letting a chapter unit be launched with
nothing. Anything other than that exact heading shape, `**Chapter 1: Title**`
most often, breaks the split.

Do this **before you end**, not after the audit. U3b reads the entries one by
one; an outline it cannot split is an audit of nothing.

## 4. Record and finish

`outline.md` is on disk and splits into `novel.chapters` entries, and
`state.json` and `logs/agents.jsonl` carry what happened (SKILL.md §6).

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the audit of this commission is U3b's unit, and the conductor is
already waiting to start it. **Nothing is written from this plan until that
audit has run**, which is the whole reason it is a unit of its own rather than
a paragraph somebody skips.
