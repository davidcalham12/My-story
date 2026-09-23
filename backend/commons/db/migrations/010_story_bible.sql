-- The Story Bible, as rows instead of four Markdown files.
--
-- The Bible has always existed — `bible/world.md`, `characters.md`,
--`timeline.md`, `mysteries.md` — and nothing has ever been able to ask it a
-- question. "Which chapters would have to be rewritten if this fact changed"
-- was a `grep` somebody ran by hand, and the answer was worth exactly as much
-- as their patience. The reader change in `docs/spec.md` §4 AC-7 cannot rest on
-- that: it regenerates *only* the chapters a fact reaches, so the set of
-- chapters has to be recorded when the chapter is promoted, not reconstructed
-- afterwards from prose nobody kept.
--
-- These tables are filled by `backend.bible.ingest` from the same Markdown the
-- agents already write, and by `backend.chapters.fact_usage` after a chapter is
-- promoted. **The agents write no SQL and are not asked to.** A script reading
-- Markdown is class T; an agent reporting what it used is class D at best
-- (AGENTS.md §5, "code before agent").

-- One row per fact the book has promised to be true.
--
-- `source` is a closed list because `mandatory_facts` (spec §2) selects on it:
-- `source = 'brief' AND mandatory = 1` is the set of things the buyer paid for
-- and a typo in that word would silently exempt one. `world`, `characters`,
-- `timeline` and `mysteries` are the Bible files; `brief` is the interview's
-- structured answers and `freetext` is what the buyer typed in prose, which is
-- untrusted and stored so it can be shown to be untrusted (AC-2).
--
-- `mandatory` is 0 for everything the Bible invented. Only the brief can carry
-- an obligation: the recipient's dog's name is owed to the reader, the colour
-- of an invented lighthouse is not.
CREATE TABLE facts (
  id        INTEGER PRIMARY KEY,
  run_id    TEXT    NOT NULL REFERENCES runs(id),
  kind      TEXT    NOT NULL CHECK (kind IN
              ('rule', 'character', 'place', 'chronology', 'mystery',
               'recipient', 'freetext')),
  text      TEXT    NOT NULL CHECK (length(trim(text)) > 0),
  source    TEXT    NOT NULL CHECK (source IN
              ('world', 'characters', 'timeline', 'mysteries', 'brief',
               'freetext')),
  mandatory INTEGER NOT NULL DEFAULT 0 CHECK (mandatory IN (0, 1)),
  -- Ingest is re-run whenever FLOW-2 is re-run after a correction. Without this
  -- a second pass would double every fact, and `impact` would then count each
  -- chapter twice and rewrite it twice.
  UNIQUE (run_id, source, text)
) STRICT;

-- Which chapter of which version used which fact.
--
-- A row exists only where the fact's words were actually found in the promoted
-- prose. **A chapter that used nothing has no rows here; it does not have a
-- zero** — the two are different facts and the reader change depends on telling
-- them apart.
--
-- `version_id` is a plain INTEGER with NO foreign key. The `versions` table
-- belongs to E6 and does not exist yet; a foreign key here would make this
-- migration wait for one it does not need, and migrations are never edited
-- after they have run. The first published version is 1.
CREATE TABLE fact_usage (
  fact_id    INTEGER NOT NULL REFERENCES facts(id),
  version_id INTEGER NOT NULL,
  chapter    INTEGER NOT NULL CHECK (chapter >= 1),
  -- The literal string that was found. It is the evidence for the row: without
  -- it "this chapter uses fact 12" is an assertion nobody can check, and the
  -- matching is string matching, which is exactly the kind of claim that needs
  -- its working shown.
  matched    TEXT    NOT NULL,
  PRIMARY KEY (fact_id, version_id, chapter)
) STRICT;

-- The cast, by the name every packet carries.
--
-- `canonical_name` is the spelling the continuity critic and `chapters/names.py`
-- check against — Nell Harker, never Nell Harper.
--
-- `birth_date` and `first_chapter` are NULL when nothing has said otherwise.
-- This Bible states no birth dates at all; a personalised novel's does, and the
-- Lean chronology invariant (age >= 0 at every event) can only be exported for
-- the characters that have one. NULL says "not stated". 0 would say "born in
-- year zero", and `1` for first_chapter would say "appears in chapter 1", which
-- is a claim about a chapter that may not be written yet.
CREATE TABLE characters (
  run_id         TEXT NOT NULL REFERENCES runs(id),
  canonical_name TEXT NOT NULL,
  role           TEXT,
  birth_date     TEXT,
  first_chapter  INTEGER CHECK (first_chapter IS NULL OR first_chapter >= 1),
  PRIMARY KEY (run_id, canonical_name)
) STRICT;

-- The places the world sets itself in, for the reader's sheet.
--
-- `note` is the sentence the place was named in. It is provenance: a place
-- extracted from prose by string matching is a guess, and the sentence is what
-- lets a reader see whether the guess was a good one.
CREATE TABLE places (
  run_id         TEXT NOT NULL REFERENCES runs(id),
  canonical_name TEXT NOT NULL,
  note           TEXT,
  first_chapter  INTEGER CHECK (first_chapter IS NULL OR first_chapter >= 1),
  PRIMARY KEY (run_id, canonical_name)
) STRICT;

-- The timeline, one row per event, in the order the Bible lists them.
--
-- `moment` keeps the Bible's own words — "3 March, eleven years ago, 3 a.m.",
-- "Day 12 — Mon 22 May". Normalising those to a date would invent a precision
-- the story does not have, and every run's timeline uses a different clock.
-- `seq` is what orders them, because it is the only ordering that survives the
-- difference.
--
-- `excludes_after` is the chapter the row pins itself to — the `(Chapter 2)` a
-- timeline writes beside a present-day event. After that chapter the event has
-- happened and may not be written as still to come. NULL is the honest value
-- for the backstory rows, which name no chapter; it is not chapter 0.
CREATE TABLE chronology (
  id             INTEGER PRIMARY KEY,
  run_id         TEXT    NOT NULL REFERENCES runs(id),
  seq            INTEGER NOT NULL,
  event          TEXT    NOT NULL,
  moment         TEXT    NOT NULL,
  place          TEXT,
  excludes_after INTEGER CHECK (excludes_after IS NULL OR excludes_after >= 1),
  UNIQUE (run_id, seq)
) STRICT;

-- Who is in the event. Its own table because the Lean export reasons over
-- (event, person) pairs — an age invariant is a statement about one person at
-- one moment — and because a comma-separated column is a list nobody can join.
CREATE TABLE chronology_participants (
  chronology_id  INTEGER NOT NULL REFERENCES chronology(id),
  canonical_name TEXT    NOT NULL,
  PRIMARY KEY (chronology_id, canonical_name)
) STRICT;

CREATE INDEX idx_facts_run_kind ON facts(run_id, kind);
CREATE INDEX idx_fact_usage_chapter ON fact_usage(version_id, chapter);
CREATE INDEX idx_chronology_run ON chronology(run_id, seq);
