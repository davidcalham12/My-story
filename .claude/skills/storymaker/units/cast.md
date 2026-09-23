# U2 — cast (FLOW-2, and the story-bible ingest)

One unit: the world exists, and this gives it people, a chronology and its open
questions. Read `.claude/skills/storymaker/SKILL.md` first — the agents' tool
boundary, the logging duties and the ceiling are there and are not repeated here.

## 1. Dispatch `character-architect`

Its prompt must carry the **full text of `bible/world.md`** — it has a Read tool
but the packet it is judged on is the one you send, and a cast written against a
world it went looking for is a cast written against whatever it found — plus:

- the premise and `novel.tone` from `config.snapshot.json`
- the counts for `characters`, `timeline_rows` and `mysteries`
- `novel.names`

Carry `novel.names` verbatim. Its default, `familiar`, asks for names a reader
can say out loud and tell apart. A run once produced five four-syllable names
inside fourteen hundred words, and a reader who cannot keep the cast straight
has already stopped reading.

It writes `bible/characters.md`, `bible/timeline.md` and `bible/mysteries.md`
itself. It is the second and last agent permitted to write the Story Bible, and
after this unit **the canon is fixed**.

## 2. The canonical names live in the file, not in your head

Every later prompt carries the canonical character names, and the `continuity`
characteristic checks spelling against them. You do not hand them on — your
conversation ends here. They are the bold-lead bullets of `bible/characters.md`:

```
- **Ada Rowe** — keeper of the Corbie Light, eleven years on the post
```

`backend/bible/ingest.py`, `backend/chapters/names.py` and
`bible.domain.canonical_names` all read exactly that shape, and a character
written without the bold is invisible to all three. If the count of bullets does
not match `bible.characters`, dispatch again with that as the correction rather
than letting three readers disagree about who is in this book.

## 3. Run the stage's checks

```bash
python -m backend.checks FLOW-2 <run_dir>
```

It reports `rules resolve` and `promises name chapters`. **The Bible is now
written and nothing has cited it yet** — this is the cheapest moment in the run
to find a rule with no number and a promise with no chapter, because every later
stage quotes both, and a correction made now costs one dispatch instead of an
outline and eight chapters.

`bible/mysteries.md` is the only part of the Bible that commits to *when*: each
question names the chapter that plants it and the chapter that lands it. If the
check reports `unstated`, send `character-architect` back for the `Planted:` and
`Lands:` lines — without them nothing downstream can tell whether the book keeps
its promises, and U3 will stop for the same reason at a higher price.

## 4. Ingest the Bible into the tables

```bash
python -m backend.bible.ingest <run_dir>
```

**Nothing new is written by a model here.** This reads exactly the four
Markdown files the writer and the critics are given and stores their characters,
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

## 5. Record and finish

The three Bible files are on disk, the rows are in the database, and
`state.json` and `logs/agents.jsonl` carry what happened (SKILL.md §6).

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the outline is U3's unit, and the conductor is already waiting
to start it.
