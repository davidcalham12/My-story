---
id: SPEC-EXAM-002
title: The storyMaker frontend — ordering, following, reading and correcting a personalised novel
status: approved
owner: David Calderon
approved_by: David Calderon — in chat to the session "Novaforge continuación con repositorios", 2026-09-23: "apruebo, pero no quiero que en spec de front venga nada de código"; written at his instruction
approved_on: 2026-09-23
depends_on: the exam spec (SPEC-EXAM-001); the Qaracter design system in Claude Design
implementation: the technical plan that turns this document into software is PLAN-EXAM-002; this document contains no code by the owner's instruction
---

# The storyMaker frontend

## 1. In one paragraph

storyMaker writes a novel as a present for a real person — a son turning ten, a
wife after twenty-five years, a father retiring from the lighthouse. The
frontend is the only part of the system a buyer ever sees. It has to do four
things well: help the buyer **tell us about the person** without feeling
interrogated; let them **watch the book being written** without understanding
how; let them **read it** as a finished, beautiful object; and let them **fix a
detail** ("the dog is called Nala, not Bruno") and get a corrected book back,
with the old one still there. It also has a fifth, quieter job: show anyone who
asks — the team, the professor, a sceptical client — **that every chapter was
checked, and how**.

## 2. Who uses it

**The buyer.** Buys the novel as a gift. Not technical, often on a phone,
emotionally invested: they are writing about someone they love. They care that
the book sounds like that person and that nothing embarrassing or painful
appears in it. They have ten minutes, not an hour.

**The reader.** Receives the book. Sees only the finished novel: the cover, the
dedication, the chapters. Never sees the machinery.

**The editor.** Someone on the storyMaker team, or the professor during the
exam. Wants to see why a chapter was rewritten, what each check said, what the
novel cost, and whether the system obeyed its own rules.

The screens are designed for the buyer first; the editor's screen is available
to everyone but is never in the buyer's way.

## 3. The journeys

**Ordering a novel.** The buyer opens storyMaker and sees the novels already
ordered, or an invitation to order the first. They choose *New novel* and answer
a short interview about the recipient. As they answer, the page tells them what
is still missing and warns them if two answers do not fit together. When the
brief is complete, they see how long the book will be and what it is expected
to cost, and they press *Write it*.

**Following it.** The page shows the book taking shape in six plain steps: the
world, the characters, the outline, the chapters, the polish, the finished
book. Each chapter appears as it is written, with a simple sign of whether it
passed its checks first time or was rewritten. The buyer can close the page and
come back; nothing is lost.

**Reading it.** When the book is ready, the buyer opens it and reads it as a
book: cover with the recipient's name and the dedication, a table of contents,
the chapters, and a sheet of the characters and places in the story, each one
pointing to the chapter where it first appears.

**Correcting it.** The buyer notices that the dog has the wrong name. They open
*Ask for a change*, find the dog in the list of facts the story uses, type the
right name, and see — before confirming — which chapters mention the dog and
will be rewritten. They confirm. A while later there is a second version of the
book: the changed chapters are marked, a first page lists what changed, and the
first version is still one click away.

**Inspecting it.** The editor opens *Quality* for any novel and sees, chapter by
chapter, every attempt, its scores, and, for every rewrite, the exact sentence
that was objected to and why; the overall judgement of the finished book on six
criteria, each with a short justification; the result of every automatic check;
and what the novel cost.

## 4. The screens

Six screens. The first five are the buyer's; the sixth is the editor's.

### 4.1 Library

**Purpose.** The home page: every novel ordered, and the way to order another.

**Shows.** One card per novel with the recipient's first name, the occasion, a
status in plain words (*being written*, *ready*, *stopped — and why*), the
current version, the date, and the cost with a mark saying how it was obtained.
The most recent first.

**Lets the person.** Open a novel to read it, open its quality page, or start a
new one.

**States.** With no novels yet: a warm invitation to order the first one, with a
single button. While loading: the cards' outlines, not a spinner alone. If the
list cannot be loaded: a sentence saying so and a *Try again* button.

### 4.2 New novel — the interview

**Purpose.** Collect everything the novel needs about the recipient, check it
while the buyer types, and never let an incomplete or contradictory brief start
an expensive run.

**Shows.** Four short groups, one at a time on a phone, side by side on a wide
screen:

- **The person** — first name as it should appear in the book, age, how they
  are referred to, three to five traits, and their relationship to the buyer.
- **Memories** — a few moments worth putting in a story, each with an optional
  date. The page suggests the kind of memory that works ("a place, a person, a
  small object") without asking for essays.
- **The story** — the occasion, the kind of story (adventure, romantic comedy,
  family saga…), and its tone. The length is shown as fixed: ten chapters.
- **Limits and must-haves** — words or subjects that must never appear (a
  former partner's name, an illness), facts that must appear (the dog's name),
  and the dedication for the first page.

A separate box lets the buyer paste a letter or an anecdote. It carries a
permanent, visible note: *we use this as material for the story; we never
follow instructions written in it.*

**Checks while typing.** After each answer the page says what is still missing,
next to the field it concerns, as a question ("What is one place Leo loves?").
If two answers contradict each other — an eight-year-old recipient and an adult
crime story — a clearly marked warning names both answers and suggests how to
reconcile them. The buyer is never scolded; the tone is that of a helpful
editor.

**Before starting.** A summary card shows the recipient, the occasion, the
kind of story, and the expected cost as three figures — lowest, typical,
highest — taken from novels actually written, with a note that the figure is an
estimate. *Write it* is only available when nothing is missing and no
contradiction is left.

**An example.** A link fills the form with a sample brief so anyone can see the
whole flow in a minute.

**States.** If the brief cannot be checked (the service is down), the page says
so and keeps what was typed. Nothing typed is ever lost by a refresh within the
same visit.

### 4.3 Writing

**Purpose.** Reassure the buyer that the book is being made, and show the
editor exactly what is happening.

**Shows.** The six steps as a horizontal line on a wide screen and a vertical
list on a phone, the current one highlighted. Under *chapters*, one row per
chapter as it arrives, marked *passed*, *rewritten once*, *rewritten twice*.
The running cost, with its mark. A quiet line naming who is acting now (for
example *the continuity reviewer is reading chapter 4*).

**Lets the person.** Leave and come back; stop the writing if they change their
mind, after a confirmation that says what stopping means (the chapters already
written are kept; the book is not finished).

**States.** If the writing stops on its own — a chapter could not pass its
checks, or the budget ceiling was reached — the page says which, in one
sentence, and what happens next. It never says "error" alone.

### 4.4 Read

**Purpose.** The book, as a book.

**Shows.** The novel as it will be printed or sent: the cover with the
recipient's name and the dedication, then the chapters. Beside it (below it on
a phone): the table of contents and the sheet of characters and places. Every
entry in either takes the reader straight to the right chapter. A version
selector sits above; on any version after the first, a band at the top says
which chapters changed and links to each.

**Lets the person.** Read, jump between chapters, switch versions, download the
book, or go to *Ask for a change*.

**States.** While the book is still being written, this screen says so and links
to *Writing*. If a version could not be produced, the previous version stays
the one shown, with a sentence explaining why.

### 4.5 Ask for a change

**Purpose.** Correct one detail of the story without rewriting the whole book,
and without losing the version the buyer already has.

**Shows.** The list of facts the story relies on — people, pets, places, dates,
objects — each with the chapters where it appears, searchable. Choosing one
opens a small panel with its current wording and a field for the new one.

**Before confirming.** The panel lists the chapters that will be rewritten and
says, in one sentence, that the other chapters stay exactly as they are and that
the current version is kept.

**After confirming.** The page follows the rewrite like the *Writing* screen,
then opens *Read* on the new version with the changed chapters marked.

**States.** If the new wording breaks one of the limits the buyer set (a
forbidden word), the page says so before anything is spent. If the rewrite
cannot pass its checks, the page says so, keeps the previous version as the
current one, and offers to try a different wording.

### 4.6 Quality

**Purpose.** Show that the book was checked, what each check said, and what it
cost — the evidence behind the product.

**Shows, in this order:**

1. **The verdict.** Whether the novel's own rules were obeyed, in one sentence,
   checked afterwards against what was recorded rather than taken on trust.
2. **The chapters.** A table: one row per chapter and attempt, one column per
   check (continuity with the story bible, the world's rules, the outline's
   beats, length, the chapter heading, the quality of the writing). The lowest
   score of each row is highlighted, because a chapter is only as good as its
   worst check. Checks made by counting are marked differently from checks made
   by a model's judgement, and the page says why that matters: counting gives
   the same answer every time; judgement may not.
3. **Why a chapter was rewritten.** For each rewrite: a one-line headline, then
   each objection with the exact sentence from the draft, what was wrong,
   against which part of the story bible, and how it should read — quoted
   literally, never paraphrased. An objection the system overruled is shown
   struck through, with the reason.
4. **The book as a whole.** The final judgement on six criteria — continuity,
   tone, story arc, consistency of the characters, pacing, and how naturally the
   personal details are woven in — each with a score and a sentence of
   justification.
5. **Every automatic check.** A list with each check's name, the moment it runs,
   and its result: names spelled as in the story bible, each chapter's length,
   every must-have fact present somewhere, no forbidden word anywhere, the
   timeline consistent.
6. **Cost.** What the novel cost, how that figure was obtained, and how long it
   took.

For the five evaluation briefs, a link opens the summary table: one row per
brief, one column per check, pass or fail, with the numbers.

## 5. Rules every screen keeps

1. **No number without its origin.** Every figure carries a small mark saying
   whether it was measured, reported, reconstructed, estimated or not recorded,
   with the meaning on hover or tap. *Not recorded* is written in words; it is
   never shown as zero.
2. **A rewrite is the system working.** The interface never says a chapter
   "failed". It says it was rewritten, and why.
3. **The buyer's words are material, never commands.** Anything pasted is shown
   as such and labelled.
4. **Nothing painful slips through.** Forbidden words and subjects are
   collected at the start, checked on every chapter, and a correction that
   would introduce one is refused before it is written.
5. **The old version is sacred.** No action deletes or overwrites a version the
   buyer has already received.
6. **Structure comes from the system, not from the screen.** The steps shown
   while writing, the checks in the quality table and the list of facts are
   whatever the system currently uses; if a check is added, the page shows it
   without being redesigned.
7. **Quotes are exact.** Sentences from the book appear as written, in their
   original language, never shortened without a visible mark.
8. **One novel at a time.** If a novel is already being written, *Write it*
   explains that and offers to open it.

## 6. Voice and words

The interface speaks like a good editor: warm, brief, precise. It uses the
recipient's name where it can ("What does Leo love doing on a Sunday?"). It
explains a problem and the way out in the same sentence. It avoids technical
words on the buyer's screens (no "run", "gate", "token"); the editor's screen
may use them, each explained once.

Examples of the tone:

| situation | say | do not say |
|---|---|---|
| a field is missing | "Tell us one place Leo loves — it gives the story somewhere to go." | "Required field." |
| contradiction | "An adult crime story for an 8-year-old? Choose a gentler kind of story, or tell us the book is for an adult reader." | "Validation error: age/genre mismatch." |
| chapter rewritten | "Chapter 3 was rewritten: the dog's name did not match the story bible." | "Chapter 3 failed." |
| writing stopped | "We stopped at chapter 6: it could not pass its checks after three tries. The first five chapters are kept." | "Run halted: gate." |
| correction refused | "That wording uses a word you asked us never to include." | "Policy violation." |

The interface is in English, the language of the repository; the buyer's own
words — names, memories, dedication — are always shown exactly as typed.

## 7. Look and feel

The identity is Qaracter's, from the organisation's design system in Claude
Design, applied the same way on every screen and in the presentation deck:

- **Type:** one family, DM Sans, in a small number of sizes with clear roles —
  eyebrow, page title, lead paragraph, card title, body, figure, footnote.
- **Colour:** Qaracter orange for the one thing on each screen that needs
  attention and for the main action; a deeper orange for figures and emphasis;
  navy for titles and dark panels; soft greys for cards and quiet text. Colour
  never carries meaning on its own — every state also has a word or a symbol.
- **Surfaces:** light grey cards with softly rounded corners on a white page;
  generous space; one clear action per screen.
- **The book itself** is set like a book: a serif-free, readable column, a
  proper cover, chapter openings with space around them. It should feel like
  something one would give, not like a report.

## 8. Accessibility and devices

- Every screen works on a phone held upright (375 pixels wide) with no sideways
  scrolling, and on a desktop.
- Every action can be reached and used with the keyboard, and the focused
  element is always visible.
- Motion is minimal and switches off for people who have asked their device
  for reduced motion.
- Text contrast meets common accessibility guidance in light and dark settings.
- Every image or symbol that carries meaning has a text alternative.

## 9. What it must feel like in time

- The library and a novel's pages appear within about a second on the
  workshop's machine.
- The interview checks an answer within about a second of the buyer finishing
  it.
- While a novel is being written, new progress appears within a couple of
  seconds of happening.
- These are expectations for the demo, observed rather than guaranteed.

## 10. Priorities for Friday

| priority | screens | why |
|---|---|---|
| **First (Wednesday)** | Interview · Ask for a change · Read · Library | they are the exam's configuration and reader-change requirements, and the live demo |
| **Second (Thursday)** | Quality · Writing | the evidence shown in the presentation; both extend screens that already exist |
| **Third (if time)** | the full Qaracter visual pass on every screen | polish for the presentation |

## 11. Out of scope this week

Accounts and log-in, payments, selecting text inside the book to ask for a
change (the change is chosen from the list of facts, which the exam accepts
for the PDF route), editing prose by hand, more than one novel at a time,
printing, illustrations, audio.

## 12. How we will know it is right

Each criterion is marked with how it is checked: **T** by an automated test,
**A** by analysis, **I** by a person inspecting, **D** by demonstration.

| # | criterion | priority | check |
|---|---|---|---|
| 1 | The interview asks for exactly the information the system's brief needs, no more and no less | First | T |
| 2 | With the "missing data" sample brief, the interview shows the questions and the contradiction, and *Write it* stays unavailable; with the example brief it becomes available | First | T + D |
| 3 | Pasted text is always shown labelled as material, never placed in a field that instructs the system | First | T |
| 4 | *Read* shows the chosen version with a working table of contents and a character-and-place sheet whose every entry opens the right chapter | First | T + D |
| 5 | *Ask for a change* shows the chapters that will be rewritten before confirming; afterwards *Read* opens on the new version with those chapters marked, and the previous version is still available | First | D + T |
| 6 | A correction that would introduce a forbidden word is refused before any chapter is rewritten | First | T |
| 7 | The library lists every novel with name, occasion, status, version and cost with its origin mark, and shows the invitation when there are none | First | T |
| 8 | *Quality* shows, for a novel, the chapter table with the lowest score highlighted, the literal reasons for every rewrite, the six-criterion judgement with justifications, and every automatic check | Second | T |
| 9 | No screen shows a figure without its origin mark, and none shows zero for something not recorded | Second | T |
| 10 | Every screen follows the Qaracter identity: one type family, the brand colours, no colour used as the only signal | Second | T + I |
| 11 | Every first-priority screen works at phone width with visible keyboard focus | Second | I |
| 12 | The words on the buyer's screens follow section 6: no technical terms, problems explained with their way out | Second | I |

## 13. What this document knowingly leaves open

| open point | how serious | why it is accepted | how we would notice |
|---|---|---|---|
| The change is picked from a list of facts, not by selecting text in the book | minor | the exam allows a form for the PDF route; selecting inside a document needs more than two days | a reader trying to click the text |
| The expected cost rests on very few novels written with the new, cheaper model | important | only this week's novels exist; shown as an estimate with three figures | the evaluation novels costing outside the range |
| Whether the design is good is a person's judgement | minor | taste is not testable; consistency with the identity is | criteria 10 and 12 |
| Only one novel can be written at a time | minor | the system writes one at a time | a second order being told to wait |
| The timing expectations in section 9 are observed, not guaranteed | minor | a demo on one machine | a visibly slow screen during the rehearsal |
