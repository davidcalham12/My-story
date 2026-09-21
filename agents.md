# The nine agents

One card each: what it is handed, what it returns, what it may write, and what it
never sees.

**The `ContextPacket` is the boundary.** In v1 each agent was a Claude Code
subagent whose tool list decided what it could reach — the chapter writer had
`Glob`, which returns paths and cannot return contents, so a previous chapter's
prose was *unreachable*. In v2 the agents are prompts plus a typed context, and
the boundary is the packet's type: **what an agent cannot be handed, it cannot
read.** That is a weaker class of evidence than v1's and `docs/verification.md`
says so plainly rather than inheriting the old language.

Every packet is built in `backend/commons/context/`, counted against the 100,000
token ceiling before the call, and logged with its size.

Skills are for building this system, not for the agents inside it: an agent
writing a chapter needs a Story Bible, not a SQLite reference. Where that
changes, the row says so.

---

## worldbuilder — FLOW-1

| | |
|---|---|
| **model** | opus |
| **prompt** | `backend/bible/prompts/worldbuilder.md` |
| **skills** | — |

**Receives:** the premise verbatim · the genre and tone, read off the premise ·
the chapter count · the counts for factions, means entries, world rules and the
world's word band.

**Returns:** the Markdown document itself.

**Writes:** `bible/world.md` — one of only two agents that produce the Story
Bible.

**Never sees:** any character. Naming one here fixes a spelling nobody else
agreed to.

**Note:** the `## Rules` heading is load-bearing. The world critic reads bullets
from under it and nowhere else, so a constraint written elsewhere is never
enforced. Rules must be falsifiable by a scene, and a rule whose main effect is
to make someone check a division is a worse rule than one about who is allowed in
the room.

---

## character-architect — FLOW-2

| | |
|---|---|
| **model** | opus |
| **prompt** | `backend/bible/prompts/character-architect.md` |
| **skills** | — |

**Receives:** the premise · genre and tone · the full text of `bible/world.md` ·
counts for characters, timeline rows and mysteries · the `names` instruction,
default `familiar`.

**Returns:** three documents.

**Writes:** `bible/characters.md`, `bible/timeline.md`, `bible/mysteries.md`.

**Never sees:** any prose.

**Note:** it fixes canonical spelling for the whole novel. Those names travel in
every later packet and are what the continuity critic checks against. `familiar`
means names a reader can pronounce on sight and tell apart in a glance — a run
that produced five four-syllable names inside fourteen hundred words lost its
reader on the cast list. A real person named in the premise keeps their real
name.

---

## plot-architect — FLOW-3

| | |
|---|---|
| **model** | opus |
| **prompt** | `backend/outline/prompts/plot-architect.md` |
| **skills** | — |

**Receives:** all four Bible files in full · the chapter count · the canonical
names · the promise and beat counts.

**Returns:** the outline as text. **The orchestrator writes it**, not the agent.

**Writes:** nothing.

**Never sees:** any prose.

**Note:** `### Chapter N — Title` exactly, em dash included; the orchestrator
splits on it and any other shape hands a writer nothing. **Beats are numbered
`1.` `2.` `3.`** so the outline critic can say "beat 3 does not happen". This is
the last agent that sees the whole book at once.

---

## chapter-writer — FLOW-4

| | |
|---|---|
| **model** | opus |
| **prompt** | `backend/chapters/prompts/chapter-writer.md` |
| **skills** | — |

**Receives:** the four Bible files in full · **this chapter's outline entry
only** · the rolling summary, capped · the canonical names · the chapter number,
its title and the target words. On a redraft it also receives **its own rejected
draft** and the feedback sheet.

**Returns:** the chapter, or on a redraft a list of substitutions
`{find, replace, why}`.

**Writes:** nothing.

**NEVER SEES: the prose of any other chapter.** This is the project's central
claim. Its `ContextPacket` has no field that can carry it, and
`tests/test_context.py` fails if the builder gains one.

**Note:** its own rejected draft is not an exception to that rule. The policy
forbids a *previous chapter's* prose; this is the writer's own attempt at the
chapter it is writing now, and handing back findings without the text they quote
is what once made redrafts come back worse than what they replaced.

---

## continuity-critic — FLOW-4 gate

| | |
|---|---|
| **model** | sonnet |
| **prompt** | `backend/chapters/prompts/continuity-critic.md` |
| **skills** | — |

**Receives:** the draft · the Story Bible, or fragments retrieved by vector
search once that is in place.

**Returns:** JSON — a score 0–10 and findings, each with a quote copied
character-for-character from the draft.

**Writes:** nothing.

**Never sees:** any other chapter's prose.

---

## science-critic — FLOW-4 gate, and the outline audit

| | |
|---|---|
| **model** | sonnet |
| **prompt** | `backend/chapters/prompts/science-critic.md` |
| **skills** | — |

**Receives:** the draft · **the whole of `## Rules`, never a retrieved subset**.

**Returns:** JSON — score and findings.

**Writes:** nothing.

**Note:** it audits against *this book's* rules, whatever kind they are, not
against physics; the name is historical. **Its rules are passed whole and never
retrieved** — a rule that was not retrieved is a violation nobody looked for.

It runs a second time, at FLOW-3, auditing the outline against `## Rules` before
any chapter exists. That check costs cents and has found defects the full gate
missed across three attempts and a patch. It is also asked to report **ambiguity**
as a finding in its own right: a rule that reads two ways does not fail loudly —
it fails as a disagreement between critics that nothing can arbitrate, and it
cost one run three attempts, a patch and a halt to discover.

---

## outline-critic — FLOW-4 gate

| | |
|---|---|
| **model** | sonnet |
| **prompt** | `backend/chapters/prompts/outline-critic.md` |
| **skills** | — |

**Receives:** the draft · **this chapter's outline entry entire, with its beats
numbered, never retrieved**.

**Returns:** JSON — score and findings, with the beat number named.

**Writes:** nothing.

**Scoring:** `10 − 3 per beat that does not happen − 1 per beat out of order`,
floor 0. The arithmetic goes in `notes` so the orchestrator can check it.

**Note:** it answers the one question the other four do not — *did the writer
write the chapter the outline commissioned?* Without it, a draft that is
consistent with the Bible, obeys the world, sits in the word band and is about
something else entirely passes cleanly. A beat delivered differently is
delivered: penalise absence and sequence, never phrasing. Nothing audits the
outline itself except the FLOW-3 check above.

---

## style-editor — FLOW-5

| | |
|---|---|
| **model** | sonnet |
| **prompt** | `backend/style/prompts/style-editor.md` |
| **skills** | — |

**Receives:** one approved chapter, and the word count it must return.

**Returns:** the chapter with punctuation and spacing normalised. **No word may
change.**

**Writes:** nothing.

**Note:** the orchestrator counts words before and after and **discards the pass**
if they differ — the published text must be the text the gate approved. This is
arithmetic, not judgement, and it has fired on a pass that changed no word at all
(closing the space in `± 0.30` merged two tokens into one). That is the rule
working, and the discard is recorded.

---

## publisher — FLOW-6

| | |
|---|---|
| **model** | sonnet |
| **prompt** | `backend/publish/prompts/publisher.md` |
| **skills** | — |

**Receives:** the Bible, the outline and the chapter summaries — **not the
chapters**. A synopsis is written from canon.

**Returns:** the synopsis.

**Writes:** nothing.

**Note:** the manuscript is concatenated **in code**. Asking a model to
concatenate produces a paraphrased sentence in the middle of text the gate
already approved.
