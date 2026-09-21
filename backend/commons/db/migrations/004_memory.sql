-- The rolling summary, as structured facts rather than a blob of prose. A cap
-- by COUNT is countable; the word cap it replaces was not.
CREATE TABLE summary_facts (
  id       INTEGER PRIMARY KEY,
  run_id   TEXT NOT NULL REFERENCES runs(id),
  chapter  INTEGER NOT NULL,             -- where it was established
  kind     TEXT NOT NULL CHECK (kind IN
             ('event', 'state-change', 'knowledge', 'open-question')),
  fact     TEXT NOT NULL,
  -- Only on `knowledge` facts. This is what fills character_knowledge, and
  -- without it that table has no source.
  who      TEXT,
  -- Set when the cap dropped it. Dropping an open-question is a promise
  -- abandoned quietly, so it is recorded rather than deleted.
  dropped_at_chapter INTEGER
) STRICT;

-- The tier the ontology calls the most common source of continuity errors: what
-- each character knows as of a point in the story. Created now and EMPTY on
-- purpose — creating it later means rewriting the importer.
CREATE TABLE character_knowledge (
  run_id             TEXT NOT NULL REFERENCES runs(id),
  character          TEXT NOT NULL,
  fact_id            INTEGER NOT NULL REFERENCES summary_facts(id),
  learned_in_chapter INTEGER NOT NULL,
  PRIMARY KEY (run_id, character, fact_id)
) STRICT;

-- Chunks of canon, for retrieval. The vec0 virtual table that indexes these is
-- created in Phase 5, when the embedder exists; the chunk rows are the durable
-- half and the index is rebuildable from them.
CREATE TABLE chunks (
  id          INTEGER PRIMARY KEY,
  run_id      TEXT NOT NULL REFERENCES runs(id),
  source_path TEXT NOT NULL,             -- which file it came from
  ordinal     INTEGER NOT NULL,          -- where in that file
  text        TEXT NOT NULL,
  -- Which model produced the vector. Two models of the same dimension are
  -- accepted by the store and return confident nonsense; this column is the
  -- only thing that catches it.
  embed_model TEXT
) STRICT;

CREATE INDEX idx_facts_run ON summary_facts(run_id, chapter);
CREATE INDEX idx_chunks_run ON chunks(run_id);
