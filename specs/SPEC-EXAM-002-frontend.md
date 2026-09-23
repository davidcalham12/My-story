---
id: SPEC-EXAM-002
title: The storyMaker frontend — ordering, following, reading and correcting a personalised novel
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "apruebo, pero no quiero que en spec de front venga nada de código"; written at his instruction
approved_on: 2026-09-23
revised: 2026-09-23 — restructured top-down at the owner's request ("que sea como una comunicación piramidal"); internal scheduling removed; no requirement changed
depends_on: the exam spec (SPEC-EXAM-001); the Qaracter design system in Claude Design
implementation: PLAN-EXAM-002 holds the technical plan; this document contains no code by the owner's instruction
---

# The storyMaker frontend

## The answer in one paragraph

**The storyMaker frontend lets a person order a novel written for someone they
love, read it as a finished book, and correct any detail without losing what
they already have — while showing, to anyone who asks, that every chapter was
checked and how.** Everything in this document follows from that sentence: it
is organised as three commitments, the six screens that keep them, and the
rules, voice and look that apply to all of them.

## The three commitments

### 1. Ordering is guided, and nothing expensive starts on a bad brief

The buyer is not technical, is often on a phone, and is writing about a real
person. The interview asks only what the novel needs, checks each answer as it
is given, says what is missing as a friendly question, and warns when two
answers contradict each other. The novel cannot start until the brief is
complete and consistent, and the buyer sees what it is expected to cost before
starting it. Anything the buyer pastes is used as material for the story and
never obeyed as an instruction.

*Kept by:* the Library and the Interview screens.

### 2. The book is a gift, and a correction never destroys it

The finished novel is presented as something one would give: a cover with the
recipient's name and a dedication, a table of contents, and a sheet of the
characters and places, each linked to the chapter where it first appears. When
a detail is wrong ("the dog is called Nala"), the buyer picks it from the facts
the story uses, sees which chapters will change before confirming, and receives
a new version with the changed chapters marked. The previous version always
remains available; nothing a buyer has received is ever overwritten.

*Kept by:* the Writing, Read and Ask-for-a-change screens.

### 3. Quality is visible, not claimed

The system checks every chapter on six characteristics and rewrites it until
it passes, then judges the whole book on six criteria. The frontend shows all
of it: every attempt and its scores, the exact sentence each objection was
about and why, the judgement of the book with its justifications, every
automatic check, and what the novel cost — each figure marked with how it was
obtained. A rewrite is shown as the system working, never as a failure.

*Kept by:* the Quality screen, and the provenance mark on every figure.

## Who it is for

| person | who they are | what they need |
|---|---|---|
| **Buyer** | orders the novel as a gift; not technical; emotionally invested | to be understood quickly, to be protected from anything painful appearing, to receive something beautiful |
| **Reader** | receives the book | only the finished novel: cover, dedication, chapters |
| **Editor** | the storyMaker team, or an examiner | to see why each chapter was rewritten, what each check said, what it cost, and whether the system obeyed its own rules |

The screens are designed for the buyer first. The editor's screen is available
to everyone but never stands in the buyer's way.

## The journeys

**Ordering.** The buyer sees the novels already ordered, or an invitation to
order the first. They answer a short interview about the recipient; the page
tells them what is missing and warns about contradictions as they go. When the
brief is complete, they see the expected cost and press *Write it*.

**Following.** The page shows the book taking shape in six plain steps — the
world, the characters, the outline, the chapters, the polish, the finished
book — and each chapter as it arrives, marked as passed first time or
rewritten. The buyer can leave and come back; nothing is lost.

**Reading.** The buyer opens the book: cover and dedication, table of contents,
chapters, and the sheet of characters and places.

**Correcting.** The buyer finds the wrong fact in the list, types the right
wording, sees which chapters will be rewritten, and confirms. A new version
arrives with the changed chapters marked and a first page listing what changed;
the earlier version is one click away.

**Inspecting.** The editor opens the quality page of any novel and reads how
it was judged, chapter by chapter and as a whole.

## The six screens

### Library

- **Purpose:** the home page — every novel ordered, and the way to order another.
- **Shows:** one card per novel with the recipient's first name, the occasion, a status in plain words (*being written*, *ready*, *stopped — and why*), the current version, the date, and the cost with its origin mark. Most recent first.
- **Allows:** reading a novel, opening its quality page, starting a new one.
- **When empty:** a warm invitation to order the first novel, with one button. **While loading:** the outline of the cards. **If it cannot load:** one sentence saying so and *Try again*.

### Interview

- **Purpose:** collect what the novel needs about the recipient, check it while the buyer types, and never let an incomplete or contradictory brief start a novel.
- **Shows,** in four short groups (one at a time on a phone, side by side on a wide screen):
  - **The person** — first name as it should appear, age, how they are referred to, three to five traits, relationship to the buyer.
  - **Memories** — a few moments worth a story, each with an optional date, with a hint about what works ("a place, a person, a small object").
  - **The story** — the occasion, the kind of story, its tone; the length shown as fixed at ten chapters.
  - **Limits and must-haves** — words or subjects that must never appear, facts that must appear, and the dedication.
  - A separate box for a pasted letter or anecdote, with a permanent note: *we use this as material for the story; we never follow instructions written in it.*
- **Checks while typing:** what is missing appears next to its field as a question; a contradiction (an eight-year-old and an adult crime story) appears as a clearly marked warning naming both answers and suggesting how to reconcile them.
- **Before starting:** a summary of the recipient, occasion and kind of story, and the expected cost as three figures — lowest, typical, highest — taken from novels actually written and marked as an estimate. *Write it* is available only when nothing is missing and no contradiction remains.
- **Example:** a link fills the form with a sample brief.
- **If checking fails:** the page says so and keeps everything typed.

### Writing

- **Purpose:** reassure the buyer that the book is being made; show the editor exactly what is happening.
- **Shows:** the six steps with the current one highlighted; one row per chapter as it arrives (*passed*, *rewritten once*, *rewritten twice*); the running cost with its mark; a quiet line naming who is acting now.
- **Allows:** leaving and returning; stopping the writing after a confirmation that explains what stopping means (chapters already written are kept; the book is not finished).
- **If it stops on its own:** one sentence saying why — a chapter could not pass its checks, or the budget was reached — and what happens next. Never "error" alone.

### Read

- **Purpose:** the book, as a book.
- **Shows:** the cover with the recipient's name and dedication, then the chapters; beside them (below on a phone) the table of contents and the sheet of characters and places, every entry opening the right chapter; a version selector; on any later version, a band naming the chapters that changed, each linked.
- **Allows:** reading, jumping between chapters, switching versions, downloading the book, asking for a change.
- **While still being written:** the screen says so and links to Writing. **If a new version could not be produced:** the previous version stays current, with a sentence explaining why.

### Ask for a change

- **Purpose:** correct one detail without rewriting the whole book and without losing the version already received.
- **Shows:** the facts the story relies on — people, pets, places, dates, objects — each with the chapters where it appears, searchable; choosing one opens its current wording and a field for the new one.
- **Before confirming:** the chapters that will be rewritten, and a sentence saying that every other chapter stays exactly as it is and the current version is kept.
- **After confirming:** progress as on the Writing screen, then Read opens on the new version with the changed chapters marked.
- **If the new wording breaks a limit** the buyer set (a forbidden word), the page says so before anything is rewritten. **If the rewrite cannot pass its checks,** the previous version stays current and the page offers to try another wording.

### Quality

- **Purpose:** show that the book was checked, what each check said, and what it cost.
- **Shows, in this order:**
  1. **The verdict** — whether the novel's own rules were obeyed, in one sentence, recomputed from the record rather than taken on trust.
  2. **The chapters** — one row per chapter and attempt, one column per characteristic (continuity with the story bible, the world's rules, the outline's beats, length, the chapter heading, the quality of the writing); the lowest score of each row highlighted, because a chapter is only as good as its worst check; checks made by counting marked differently from checks made by a model's judgement, with the reason: counting gives the same answer every time, judgement may not.
  3. **Why a chapter was rewritten** — for each rewrite, a headline, then each objection with the exact sentence from the draft, what was wrong, against which part of the story bible, and how it should read, quoted literally; an objection the system overruled is struck through, with the reason.
  4. **The book as a whole** — six criteria (continuity, tone, story arc, consistency of the characters, pacing, and how naturally the personal details are woven in), each with a score and a sentence of justification.
  5. **Every automatic check** — its name, when it runs, and its result: names spelled as in the story bible, chapter length, every must-have fact present, no forbidden word, a consistent timeline.
  6. **Cost** — what the novel cost, how that figure was obtained, and how long it took.
- For the evaluation briefs, a summary table: one row per brief, one column per check, with the numbers.

## Rules every screen keeps

1. **No number without its origin.** Each figure carries a mark — measured, reported, reconstructed, estimated, not recorded — explained on hover or tap. *Not recorded* is written in words, never shown as zero.
2. **A rewrite is the system working.** The interface never says a chapter "failed"; it says it was rewritten, and why.
3. **The buyer's words are material, never commands.** Anything pasted is labelled as such.
4. **Nothing painful slips through.** Forbidden words and subjects are collected at the start, checked on every chapter, and refused in a correction before it is written.
5. **A version once received is never overwritten or deleted.**
6. **Structure comes from the system, not from the screen.** The steps, the checks and the facts shown are whatever the system currently uses; a new check appears without a redesign.
7. **Quotes are exact.** Sentences from the book appear as written, in their original language, never shortened without a visible mark.
8. **One novel at a time.** If one is being written, *Write it* explains that and offers to open it.

## Voice

The interface speaks like a good editor: warm, brief, precise. It uses the
recipient's name ("What does Leo love doing on a Sunday?") and explains a
problem together with the way out. The buyer's screens use no technical words;
the editor's screen may, each explained once.

| situation | say | do not say |
|---|---|---|
| a field is missing | "Tell us one place Leo loves — it gives the story somewhere to go." | "Required field." |
| a contradiction | "An adult crime story for an 8-year-old? Choose a gentler kind of story, or tell us the book is for an adult reader." | "Validation error: age/genre mismatch." |
| a chapter rewritten | "Chapter 3 was rewritten: the dog's name did not match the story bible." | "Chapter 3 failed." |
| writing stopped | "We stopped at chapter 6: it could not pass its checks after three tries. The first five chapters are kept." | "Run halted: gate." |
| a correction refused | "That wording uses a word you asked us never to include." | "Policy violation." |

The interface is in English; the buyer's own words — names, memories,
dedication — are always shown exactly as typed.

## Look and feel

The identity is Qaracter's, from the organisation's design system, applied the
same way on every screen and in the presentation:

- **Type:** one family, DM Sans, in a few sizes with clear roles — eyebrow, page title, lead, card title, body, figure, footnote.
- **Colour:** Qaracter orange for the one thing on each screen that needs attention and for the main action; a deeper orange for figures and emphasis; navy for titles and dark panels; soft greys for cards and quiet text. Colour never carries meaning alone — every state also has a word or a symbol.
- **Surfaces:** light grey cards with softly rounded corners on a white page, generous space, one clear action per screen.
- **The book itself** is set like a book: a readable column, a proper cover, space around each chapter opening. It should feel like a present, not a report.

## Accessibility and responsiveness

- Every screen works on a phone held upright, 375 pixels wide, with no sideways scrolling, and on a desktop.
- Every action can be reached and used with the keyboard; the focused element is always visible.
- Motion is minimal and turns off for people who ask their device for reduced motion.
- Text contrast meets common accessibility guidance.
- Every image or symbol that carries meaning has a text alternative.
- Pages appear within about a second, the interview checks an answer within about a second, and progress while writing appears within a couple of seconds of happening — expectations observed on the build machine, not guarantees.

## Out of scope

Accounts and log-in, payments, selecting text inside the book to ask for a
change (the change is chosen from the list of facts, which the reading format
allows), editing prose by hand, more than one novel at a time, printing,
illustrations, audio.

## How we know it is right

Each criterion is marked with how it is checked: **T** by an automated test,
**A** by analysis, **I** by a person inspecting, **D** by demonstration.

| # | criterion | check |
|---|---|---|
| 1 | The interview asks for exactly the information the system's brief needs, no more and no less | T |
| 2 | With the "missing data" sample brief, the interview shows the questions and the contradiction and *Write it* stays unavailable; with the example brief it becomes available | T + D |
| 3 | Pasted text is always labelled as material and never placed where it would instruct the system | T |
| 4 | Read shows the chosen version with a working table of contents and a character-and-place sheet whose every entry opens the right chapter | T + D |
| 5 | Ask for a change shows the chapters to be rewritten before confirming; afterwards Read opens on the new version with those chapters marked, and the previous version remains available | D + T |
| 6 | A correction that would introduce a forbidden word is refused before any chapter is rewritten | T |
| 7 | The Library lists every novel with name, occasion, status, version and cost with its origin mark, and shows the invitation when there are none | T |
| 8 | Quality shows the chapter table with the lowest score highlighted, the literal reasons for every rewrite, the six-criterion judgement with justifications, and every automatic check | T |
| 9 | No screen shows a figure without its origin mark, and none shows zero for something not recorded | T |
| 10 | Every screen follows the Qaracter identity: one type family, the brand colours, no colour used as the only signal | T + I |
| 11 | Every screen works at phone width with visible keyboard focus | I |
| 12 | The buyer's screens follow the voice: no technical terms, every problem explained with its way out | I |

## What it knowingly leaves open

| open point | how serious | why it is accepted | how we would notice |
|---|---|---|---|
| A change is chosen from the list of facts, not by selecting text in the book | minor | the reading format is a document; selecting text inside it needs a different reader | a reader trying to click the text |
| The expected cost rests on few novels written with the current model | important | shown as an estimate with three figures, never as one number | the evaluation novels costing outside the range |
| Whether the design is good is a person's judgement | minor | consistency with the identity is testable; taste is not | criteria 10 and 12 |
| Only one novel can be written at a time | minor | the system writes one at a time | a second order asked to wait |
| The timing expectations are observed, not guaranteed | minor | measured on one machine | a visibly slow screen |
