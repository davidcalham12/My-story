# U1 — world (FLOW-1)

One unit: the premise becomes the rules the story runs on. Read
`.claude/skills/storymaker/SKILL.md` first — the agents' tool boundary, the
logging duties and the ceiling are there and are not repeated here.

You are the first process of this run, so you decide one thing nobody else can.

## 1. Read the genre off the premise, and write it down

`novel.tone` in `config.snapshot.json` is null until somebody sets it. Set it —
the reasoning and the wording are SKILL.md §2 — and **write it into
`config.snapshot.json` before you dispatch anything**.

This is the single most consequential line in the run. It reaches every one of
the agents, none of which has a genre of its own any more, and it reaches them
through that file: your conversation ends with this unit, so a genre you decided
and did not record is a genre the next four units will each invent for
themselves.

## 2. Dispatch `worldbuilder`

Its prompt must carry, because it has no Read tool:

- the premise, verbatim, from the brief your prompt names
- `novel.tone` — the genre you just decided, in the words you decided it in
- `novel.chapters`
- the counts from `bible`: `factions`, `technology_entries`, `world_rules`,
  `world_min_words`, `world_max_words`
- the absolute path of the run directory, so it can write `bible/world.md`
  itself — it is one of only two agents that may

Those counts are the size of this book's canon, and the profile overrode them
for a reason: a three-chapter run handed a twelve-chapter Story Bible spends
every chapter introducing things it has no room to use.

## 3. Check what it wrote, and correct it here

Read `bible/world.md` yourself and check the `## Rules` heading exists with at
least `bible.world_rules.min` bullets under it. If it does not, dispatch again
with that as the correction.

**Nothing downstream can recover a missing rules section.** The `science`
characteristic reads from under that heading and nowhere else, and the outline
audit in U3 judges every beat against those bullets. A world without them
produces a gate that passes everything and an audit that finds nothing.

**Number the rules.** The critics and the audit refer to them *by number* —
"R5 rewritten to name the keeper as the writer". Written as unnumbered bullets,
those numbers are the critic counting bullets and inventing an identifier: two
real runs produced 76 such references that resolved to nothing, and a positional
reference points at a different rule the moment one is inserted. If the bullets
come back unnumbered, send `worldbuilder` back to number them — do not renumber
them yourself. The Bible has two authors and you are not one of them.

U2 runs `python -m backend.checks FLOW-2`, which includes `rules resolve`, so a
world that leaves here unnumbered is caught one unit later at the cost of a
second Bible stage. Cheaper to see it now.

## 4. Record and finish

`bible/world.md` is on disk, `config.snapshot.json` carries the tone, and
`state.json` and `logs/agents.jsonl` carry what happened (SKILL.md §6).

---

Read only the files your prompt named. Write only to the paths it named. Then
end your turn — the cast is U2's unit, and the conductor is already waiting to
start it.
