-- A run, and what it was run with.
CREATE TABLE runs (
  id              TEXT PRIMARY KEY,
  slug            TEXT NOT NULL UNIQUE,
  premise         TEXT NOT NULL,
  profile         TEXT NOT NULL,
  tone            TEXT,                  -- read off the premise, recorded here
  config_snapshot TEXT NOT NULL,         -- JSON: what this run actually ran with
  stage           TEXT NOT NULL,
  -- NULL while running. One of: gate | budget | context | interrupted.
  halted          TEXT,
  halted_detail   TEXT,
  -- Runs imported from v1 were judged by a different set of characteristics.
  -- Readable and queryable; excluded from LOOP-003 statistics. Evidence, not
  -- sample.
  source          TEXT NOT NULL DEFAULT 'v2' CHECK (source IN ('v2', 'pre-loop003')),
  started_at      TEXT NOT NULL,
  finished_at     TEXT
) STRICT;

-- What an imported run did NOT carry, so a gap reads as a gap and never as a
-- zero. A run that never wrote gate rows must not resemble one whose gate
-- passed everything first time.
CREATE TABLE run_completeness (
  run_id  TEXT NOT NULL REFERENCES runs(id),
  field   TEXT NOT NULL,
  state   TEXT NOT NULL CHECK (state IN ('present', 'absent', 'partial')),
  note    TEXT,
  PRIMARY KEY (run_id, field)
) STRICT;

-- Run-level warnings that are not failures. The first of them: an
-- open-question fact dropped by the summary cap, which is a promise abandoned
-- quietly and must be visible.
CREATE TABLE run_warnings (
  id      INTEGER PRIMARY KEY,
  run_id  TEXT NOT NULL REFERENCES runs(id),
  kind    TEXT NOT NULL,
  detail  TEXT NOT NULL,
  chapter INTEGER,
  ts      TEXT NOT NULL
) STRICT;
