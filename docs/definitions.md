# Definitions

The vocabulary of this system. Adapted from the *AI Novel-Generation Ontology*
(Definitions and Mermaid Diagrams), with each term mapped to what NovaForge
actually builds, and with the gaps named rather than glossed over.

**How to read the mapping.** Three states:

- **built** — NovaForge has this, under the name given.
- **partial** — something close exists and falls short in a stated way.
- **absent** — the ontology names it and NovaForge has nothing. Listed because a
  gap you can name is a decision; a gap you cannot is a bug waiting.

> **One discrepancy, recorded.** The build brief refers to *nine* quality
> dimensions. The ontology lists **ten** (§5 below). Nothing here drops one to
> make the count match: ten are listed and the disagreement is noted where a
> reader will meet it.

---

## 1. Core entities

**Work** — the novel as a top-level record: title, genre, logline, target
length, POV and tense defaults. Set once, edited only for scope changes.
→ **built**, as a `run`: slug, premise, profile, the config snapshot.

**World** — the setting's reality and the rules governing what is possible.
Canon; a change ripples forward through everything drafted after it.
→ **built**, as `bible/world.md`, written by `worldbuilder`.

**Tech/Magic System ⚙** — the explicit rule-set for non-mundane elements:
capabilities, costs, limits, access. Canon. *The entity most responsible for plot
holes when under-specified — if a rule isn't written down, drafting improvises
one inconsistently.*
→ **built**, as the `## Rules` section of `world.md`. NovaForge generalises it:
the rules need not be physics. "The stall closes at two and the masa is gone by
noon" is as enforceable as an exhaust velocity, and for most genres more useful.
The `science-critic` reads bullets from under that heading **and nowhere else**,
so a rule written elsewhere is never enforced.

**Character** — identity, voice, goals, arc, relationships, and a knowledge-state
that changes scene by scene.
→ **partial**. The sheet is built (`bible/characters.md`, canonical names that
travel in every later packet). The knowledge-state is **absent** — see §4.

**Faction/Organization** — a group with its own goals and resources, tracked like
a Character but without an internal voice.
→ **built**, as `## Factions` in `world.md`, count scaled by profile.

**Location** — a place, with a "currently present" state that changes per scene.
→ **absent** as an entity. Locations exist inside prose and outline entries;
nothing tracks who is where.

**Object/Artifact** — anything plot-relevant a character can carry, lose or seek,
with tracked location and owner.
→ **absent** as an entity. Same as Location: present in the text, not modelled.

**Timeline/Event** — the in-world chronology, **append-only**; you add events,
you do not rewrite history without a deliberate retcon pass.
→ **built**, as `bible/timeline.md`. The append-only discipline is asserted in
the prompt, not enforced by the store.

**PlotThread** — one cause-and-effect line: setup, complications, resolution,
with a status (open / complicating / resolved) at every point.
→ **partial**. Promises exist in the outline (`novel.promises`, which chapter
advances which), but no thread carries a status through the manuscript.

**Theme/Motif** — the abstract idea explored; the recurring concrete symbol that
expresses it. Global, referenced by scenes.
→ **absent**. Nothing names or tracks either.

**Scene** — one POV, one location, one continuous stretch of time, a cast, a
goal, a conflict, an outcome that changes something. The atomic unit of drafting.
→ **partial, and this is the deepest structural difference.** NovaForge drafts a
**chapter** at a time, not a scene. Beats live inside the chapter's outline entry
and the writer produces the whole chapter in one call. The ontology's "Scene
Context Packet" therefore becomes a *chapter* context packet here.

**Chapter / Part / Act** — structural groupings. A Chapter is what a reader
consumes in one sitting.
→ **built** for Chapter. Acts exist in the outline as prose, not as entities.

**Beat** — the smallest unit of narrative change: one shift in state (a reveal, a
reversal, a decision). A scene is a sequence of beats.
→ **built**, and it is load-bearing. Beats are **numbered** in each chapter's
outline entry so `outline-critic` can score `10 − 3 per missing beat − 1 per beat
out of order` and name which one is missing.

**StyleGuide / Voice Profile** — prose-level constraints: diction, rhythm, POV and
tense rules, banned tics, formatting.
→ **partial**. `style-editor` normalises presentation and **may not change a
word**; there is no declared voice profile it applies.

**Constraint** — non-craft requirements: audience, content policy, word budget,
obligations to earlier books.
→ **built**, as `config/` and the profiles: chapters, word bands, counts, budget
ceiling.

**QualityCheck / Rubric** — a named criterion, how it is scored, and at what stage
it applies.
→ **built**, as the five characteristics of LOOP-003. See §5.

**PipelineStage / Agent** — process metadata: which step produced a given entity,
so provenance and revision responsibility are traceable.
→ **built**, and it is the part NovaForge has taken furthest: one log row per
call with agent, model, tokens in and out, cost, duration and a real timestamp,
plus a provenance grade on every figure the panel shows.

---

## 2. Relationships

The ontology's edges, and whether anything in NovaForge can answer them.

| relationship | answerable? |
|---|---|
| Character PARTICIPATES_IN Scene | no — cast is prose in the outline entry |
| Scene BELONGS_TO Chapter | n/a — the chapter is the unit |
| PlotThread SETUP_IN / PAYS_OFF_IN Scene | partial — promises are named per chapter, not linked |
| Object LOCATED_AT Location, changing over the Timeline | no |
| **Character KNOWS Fact, as of a point on the Timeline** | **no — and this is the one that matters most; see §4** |
| Theme EXPRESSED_VIA Motif; Motif APPEARS_IN Scene | no |
| Faction OPPOSES / ALLIES_WITH Faction or Character | partial — stated in prose in `## Factions` |
| QualityCheck APPLIES_TO PipelineStage output | **yes**, fully |

Note the shape: NovaForge models the **process** thoroughly and the **story
world** thinly. Everything about what was generated, by whom, at what cost, with
what verdict, is structured. Almost everything about who knows what, and where
the knife is, lives in prose.

---

## 3. Anatomy layers

The zoom-in structure, from engine to sentence.

| layer | NovaForge |
|---|---|
| Premise / Logline | the run's premise, one or two sentences |
| Global outline | `outline.md`, acts as prose, turning points per chapter |
| Plot threads | promises, named per chapter |
| Chapter outline | the per-chapter entry: POV, tension, promise advanced, beats |
| Scene outline | **absent** — the chapter is the unit |
| Beats | numbered, and scored by a critic |
| Prose | the drafted chapter |
| Micro-craft | `style-editor`, presentation only |

**Cross-cutting, owned by no layer:**

- **Voice** — narrator's and each character's. *Not checked by any of the five
  characteristics.* No critic grades prose quality, and three shipped defects are
  traceable to that.
- **Pacing** — macro and micro. Approximated by the word band, which is a length
  check and not a pacing one.
- **World logic ⚙** — a rule established early constrains everything drafted
  later. **Enforced**, by `science-critic` against `## Rules`, and now also
  against the *outline* before drafting begins.

---

## 4. Context-management tiers

The ontology's tiers, and NovaForge's answer to each. This section is why the
ontology was worth reading: it names two tiers NovaForge does not have.

| tier | NovaForge |
|---|---|
| **Canon (Story Bible)** — world, characters, tech, style; *retrieved selectively, never dumped whole* | **built** as the four Bible files — but **dumped whole** into every packet today. Phase 5 introduces selective retrieval; §6 says where that is safe and where it is not. |
| **Structural (Outline)** — always in context for the chapter being drafted | **built**. The writer receives **its own entry only**. |
| **Rolling narrative state** — compressed synopsis, updated every chapter | **built**, and it is the only channel between chapters. Moving from a word-capped blob to a list of structured facts `{fact, chapter, kind}` is a v2 decision. |
| **Continuity ledger** — established facts that must not be contradicted; append-only, queried per scene | **partial**. `continuity-critic` checks against the Bible and the summary; there is no separate append-only ledger of facts established *in the prose*. |
| **Foreshadowing ledger** — planted elements and whether they have paid off; checked at outline time | **absent**. Promises are declared in the outline; nothing records whether one was planted or paid off. |
| **Knowledge-state per character** — what each character knows as of now. *The tier most systems skip, and the most common source of continuity errors.* | **absent**, and the ontology's warning is why v2 creates `character_knowledge(run_id, character, fact_id, learned_in_chapter)` **empty, now** — creating it later means rewriting the importer. |
| **Scene Context Packet** — the assembled, scene-specific bundle, *built in advance rather than left to the drafting step to retrieve for itself* | **built**, as the `ContextPacket`, per chapter rather than per scene. Assembled in advance, counted before sending, and the writer's has **no field that can carry another chapter's prose**. |

That last row is where NovaForge's central claim lives. The ontology recommends
assembling the packet in advance; NovaForge makes the packet's *type* the
boundary, so what an agent was not handed it cannot go and get.

---

## 5. Quality dimensions

The ontology names ten. NovaForge's gate scores **five characteristics**, each
0–10, all of which must reach 8, aggregated with `min` — a chapter is worth what
its worst characteristic is worth.

| # | ontology dimension | NovaForge |
|---|---|---|
| 1 | **Continuity** | `continuity` — a model critic |
| 2 | Character consistency | partially inside `continuity`; voice and knowledge-state unchecked |
| 3 | Plot logic | **unchecked** |
| 4 | Pacing | approximated by `length`, which is a word count |
| 5 | Prose craft | **unchecked** — three shipped defects trace to this |
| 6 | Dialogue | **unchecked** |
| 7 | **Genre fit** | `science` — plausibility against the world's own declared rules |
| 8 | **Structural function** | `outline` — does the chapter deliver the beats it was commissioned for |
| 9 | Reader experience | **unchecked** |
| 10 | Originality | **unchecked** |

Plus `chatter`, which is not an ontology dimension at all: it checks the draft
opens with `# Chapter` and carries no model preamble. It exists because a
generated draft that begins "Here is the chapter you asked for" is a failure mode
no craft rubric anticipates.

**Two of the five reproduce and three do not.** `length` and `chatter` are
arithmetic. `continuity`, `science` and `outline` are model judgements: the same
draft can score 8 one run and 7 the next, so "it passed the gate" is a statement
about one run and not a property of the text.

---

## 6. The five gates

From the pipeline diagram, with what NovaForge does at each.

| # | ontology gate | NovaForge |
|---|---|---|
| 1 | **Developmental edit** — does the arc resolve? | **absent**. The outline is not checked for whether its ending lands. |
| 2 | **Does each scene earn its place?** | **partial, at outline time.** FLOW-3 audits the commission against `## Rules` — it asks whether each beat is *possible*, not whether it *earns its place*. It found defects the full gate missed, for cents. |
| 3 | **Craft check** — voice, pacing, dialogue, originality | **absent.** Exactly the four dimensions listed unchecked in §5. |
| 4 | **Continuity edit** — ledger contradictions? *The most mechanical pass, and the highest-value one to automate first.* | **built, and it is the most developed part of the system**: three model critics plus two arithmetic ones, three attempts with escalating feedback, and `patch_then_halt`. |
| 5 | **Reader-experience pass** (often human) | **absent**, and the ontology's "often human" is the honest reason. |

NovaForge automated gate 4 first, which is what the ontology recommends, and has
built almost nothing at 1, 3 and 5. That is a deliberate shape, not an oversight:
gate 4 is mechanical and checkable, and the others need judgement no rubric in
this system currently renders.

---

## 7. Editorial passes

| pass | NovaForge |
|---|---|
| **Developmental edit** — structure, at the outline layer, before prose | the FLOW-3 audit, narrowly |
| **Line edit** — prose, voice, pacing at sentence level | **absent** |
| **Copy edit** — grammar, spelling, style-guide conformity | `style-editor`, presentation only, and it may not change a word |
| **Continuity edit** — cross-check against the ledger | the gate |
| **Targeted rewrite** — a scoped patch for one flagged issue | **built and central**: the redraft asks for substitutions `{find, replace, why}` applied literally, so anything no finding names **cannot** change |
| **Full regeneration** — redraft from the outline when a patch cannot fix it | **built** as the fallback when no substitution applies, and recorded as such |

The ontology's distinction between a targeted rewrite and a full regeneration is
the one NovaForge learned by getting it wrong: asking for a whole chapter back
"with these fixed and nothing else" relies on the writer's restraint, and a model
handed a whole chapter tends to improve it. Asking for the exact sentences to
replace makes over-rewriting impossible.

---

## 8. NovaForge terms the ontology does not name

Vocabulary this system needs that the glossary above has no word for.

**Characteristic** — one of the five things a chapter is scored on. Narrower than
the ontology's "quality dimension": a characteristic has a scorer, a formula and
a threshold.

**Attempt** — one pass at a chapter. Three at most.

**Feedback sheet** — what the writer receives after a failed attempt. It
escalates: attempt 2 gets the correction *described*, attempt 3 gets the critic's
*literal replacement sentence*. Validated before sending; an incomplete sheet is
not sent.

**Arbitration** — the orchestrator overruling a critic's finding, or refusing a
proposed replacement. Recorded with its reasoning, because a critic that was
overruled and was right is a different event from one that was overruled and was
wrong.

**Late finding** — something raised on a later attempt that was equally present
in the first draft and went unmentioned. Recorded, patched where possible, and
**does not block**: without this rule the third-attempt guarantee does not exist,
because something new can always appear.

**Provenance grade** — how a figure was obtained: `measured`, `reported`,
`reconstructed`, `estimated`, `absent`. What cannot be measured is reported as
unmeasurable, never as zero.

**Halt** — a run stopped deliberately, always with its artefacts left readable.
Four kinds, and the kind is recorded:

- `halted: gate` — a chapter failed three attempts and the patch. No chapter
  file is promoted; the best draft stays at `chNN.attemptK.md`.
- `halted: budget` — the ceiling was reached. The attempt in flight is **kept**,
  marked, unpromoted: it is already paid for.
- `halted: context` — a context packet exceeded 100,000 tokens. Raised where the
  packet is built, not where it is sent.
- `halted: interrupted` — the process died. Artefacts readable; resume is not
  implemented, and the state is sufficient for it to be added without migration.

**Fact** — one entry in the rolling summary: `{fact, chapter, kind}`, with four
closed kinds — `event`, `state-change`, `knowledge`, `open-question` — and
`who` on `knowledge` facts. This is the only channel between chapters. When the
cap bites, every `open-question` survives first; dropping one is recorded as a
run warning, because an abandoned promise is the ontology's foreshadowing failure
arriving quietly.

**pre-loop003** — a run imported from the previous implementation. Readable and
queryable; **excluded from LOOP-003's statistics**, because it was judged by a
different set of characteristics. Evidence, not sample.

**Completeness record** — what an imported run did *not* carry: gate rows,
durations, a critic. Kept per run so a gap reads as a gap rather than as a zero.
