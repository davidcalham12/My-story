# U2b — cast, the chronology and the open questions (FLOW-2, second half)

One unit: the people exist, and this gives the story its order of events, the
questions it will not answer yet, and the rows every later stage reads. Read
`.claude/skills/storymaker/SKILL.md` first — the agents' tool boundary, the
logging duties and the ceiling are there and are not repeated here.

**Why this is half a unit.** FLOW-2 used to be one process and ended at 100,669
tokens against a ceiling of 100,000. See `units/cast-characters.md` §0 for the
arithmetic; what matters here is that U2a already wrote `bible/characters.md`
and you read it from disk, because nothing carries between units but disk.

## 1. Dispatch `character-architect`

Its prompt must carry the **full text of `bible/world.md` and of
`bible/characters.md`** — it has a Read tool but the packet it is judged on is
the one you send, and a timeline written against a cast it went looking for is a
timeline for whoever it found — plus:

- the premise and `novel.tone` from `config.snapshot.json`
- the counts for `timeline_rows` and `mysteries`
- `novel.chapters`, because the mysteries commit to chapter numbers

It writes `bible/timeline.md` and `bible/mysteries.md` itself. **Say in the
prompt that `bible/characters.md` is already written and must not be touched.**
This is the last dispatch permitted to write the Story Bible, and after it
**the canon is fixed**.

`bible/mysteries.md` is the only part of the Bible that commits to *when*: each
question names the chapter that plants it and the chapter that lands it. Ask for
the `Planted:` and `Lands:` lines explicitly — without them nothing downstream
can tell whether the book keeps its promises.

## 2. Run the stage's checks

```bash
python -m backend.checks FLOW-2 <run_dir>
```

It reports `rules resolve` and `promises name chapters`. **The Bible is now
whole and nothing has cited it yet** — this is the cheapest moment in the run to
find a rule with no number and a promise with no chapter, because every later
stage quotes both, and a correction made now costs one dispatch instead of an
outline and eight chapters.

If the check reports `unstated`, send `character-architect` back for the missing
`Planted:` and `Lands:` lines. U3 will stop for the same reason at a higher
price.

A rule with no number is `bible/world.md`'s defect, not yours to renumber: the
critics and the outline audit cite rules by number, and a number you invented
decays the arbitration record without anyone noticing. Record it in
`logs/agents.jsonl` and let U3a's check report it — it is the same check.

## 3. Ingest the Bible into the tables

```bash
python -m backend.bible.ingest <run_dir>
```

**Nothing new is written by a model here.** This reads exactly the four Markdown
files the writer and the critics are given and stores their characters,
chronology rows and facts. Asking an agent to emit the same canon a second time
as JSON would be a second source of truth, and the two would disagree by chapter
three — which is the failure the Bible exists to prevent.

The `facts` rows it writes are what the publish gate's `mandatory_facts` check
counts against in U5, and what `fact_usage` matches each promoted chapter
against in U4. A run that skips this ends with a validator that reports every
brief fact uncovered and cannot tell anyone whether that is true.

It is a parser, so it misses what prose hides from a regular expression; each
extraction in that module says what it will miss. **Running it twice is safe**
and changes nothing but the rows it re-reads, so any later unit that corrects
the Bible runs it again.

It leaves `bible/.ingest.json`, which is the last file this unit owes. That
receipt is why the unit is done: the first resumed run found the Markdown on
disk, called the cast finished, and left the story bible empty behind it.

## 4. Record and finish

The four Bible files are on disk, the rows are in the database, the receipt is
written, and `state.json` and `logs/agents.jsonl` carry what happened
(SKILL.md §6).

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the outline is U3a's unit, and the conductor is already waiting
to start it.
