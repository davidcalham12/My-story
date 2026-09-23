# U2a — cast, the people (FLOW-2, first half)

One unit: the world exists, and this gives it people. Read
`.claude/skills/storymaker/SKILL.md` first — the agents' tool boundary, the
logging duties and the ceiling are there and are not repeated here.

**Why this is half a unit.** FLOW-2 used to be one process and ended at 100,669
tokens against a ceiling of 100,000. A fresh orchestrator arrives carrying about
48,800 before it opens a file, so a unit has roughly 51,000 to work in, and
cutting tools does not move that floor. The only lever was a smaller unit. You
write the cast; U2b writes when things happened and what stays unanswered.

**Your unit ends when `bible/characters.md` exists.** Do not write
`bible/timeline.md` or `bible/mysteries.md` — that is U2b's contract, and a file
claimed by two units is a resume that can never settle.

## 1. Dispatch `character-architect`

Its prompt must carry the **full text of `bible/world.md`** — it has a Read tool
but the packet it is judged on is the one you send, and a cast written against a
world it went looking for is a cast written against whatever it found — plus:

- the premise and `novel.tone` from `config.snapshot.json`
- the count for `characters`
- `novel.names`

Carry `novel.names` verbatim. Its default, `familiar`, asks for names a reader
can say out loud and tell apart. A run once produced five four-syllable names
inside fourteen hundred words, and a reader who cannot keep the cast straight
has already stopped reading.

**Say in the prompt that this dispatch writes `bible/characters.md` only.** The
agent's own procedure describes all three Bible files, because until today it
wrote all three in one go; the instruction that it writes one has to come from
you. It is the second and last agent permitted to write the Story Bible, and
after U2b **the canon is fixed**.

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

Check the count yourself before you finish. It is one `Glob`-free read of a file
you just wrote, and the alternative is U2b building a timeline for people the
parser cannot see.

## 3. Record and finish

`bible/characters.md` is on disk and its bullets parse, and `state.json` and
`logs/agents.jsonl` carry what happened (SKILL.md §6).

Do **not** run `python -m backend.checks FLOW-2` here. It reports on
`bible/mysteries.md`, which does not exist yet; U2b runs it when the Bible is
whole.

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the timeline, the mysteries and the ingest are U2b's unit, and
the conductor is already waiting to start it.
