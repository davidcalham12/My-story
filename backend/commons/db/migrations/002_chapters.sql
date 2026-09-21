-- One row per attempt, not per chapter. The rejected drafts are the only thing
-- "the writer changed only what was cited" can be measured from, and a run that
-- overwrites them has destroyed the evidence rather than saved a file.
CREATE TABLE attempts (
  id          INTEGER PRIMARY KEY,
  run_id      TEXT NOT NULL REFERENCES runs(id),
  chapter     INTEGER NOT NULL,
  attempt     INTEGER NOT NULL,
  title       TEXT,
  draft_path  TEXT NOT NULL,             -- chapters/chNN.attemptK.md
  words       INTEGER NOT NULL,
  aggregate   INTEGER,                   -- min of the scored characteristics
  verdict     TEXT CHECK (verdict IN ('accept', 'retry', 'patched', 'halt')),
  -- Was this the draft that shipped? Distinct from "the best draft": an
  -- accepted draft is the one that passed, which is not always the best.
  promoted    INTEGER NOT NULL DEFAULT 0,
  ts          TEXT NOT NULL,
  UNIQUE (run_id, chapter, attempt)
) STRICT;

-- One row per characteristic per attempt. Five for a v2 run; fewer for an
-- imported one, which is what run_completeness records.
CREATE TABLE scores (
  attempt_id     INTEGER NOT NULL REFERENCES attempts(id),
  characteristic TEXT NOT NULL CHECK (characteristic IN
                   ('continuity', 'science', 'outline', 'length', 'chatter')),
  -- NULL means the critic returned no usable verdict. It is EXCLUDED from the
  -- minimum, never counted as a pass: 10 invents an approval and 0 invents a
  -- rejection. This once returned 10 and a malformed reply silently passed.
  score          INTEGER CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
  note           TEXT,
  PRIMARY KEY (attempt_id, characteristic)
) STRICT;

CREATE TABLE findings (
  id             INTEGER PRIMARY KEY,
  attempt_id     INTEGER NOT NULL REFERENCES attempts(id),
  characteristic TEXT NOT NULL,
  severity       TEXT NOT NULL,
  kind           TEXT,
  -- Copied from the draft character for character. It is the finding's
  -- identity: nothing else survives a redraft, so "is this the same finding"
  -- has an answer rather than a judgement.
  quote          TEXT,
  claim          TEXT,
  fix            TEXT,
  reference      TEXT,
  -- 0 when the orchestrator examined it and refused it. A critic overruled and
  -- right is a different event from one overruled and wrong.
  upheld         INTEGER NOT NULL DEFAULT 1,
  ruling         TEXT,
  -- Raised on a later attempt though present in the first draft and unmentioned
  -- then. Recorded, patched where possible, and NEVER blocking: without this
  -- the third-attempt guarantee does not exist, because something new can
  -- always appear.
  late           INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE TABLE gate_decisions (
  id         INTEGER PRIMARY KEY,
  run_id     TEXT NOT NULL REFERENCES runs(id),
  chapter    INTEGER NOT NULL,
  attempt    INTEGER NOT NULL,
  aggregate  INTEGER NOT NULL,
  threshold  INTEGER NOT NULL,
  verdict    TEXT NOT NULL,
  note       TEXT,
  ts         TEXT NOT NULL
) STRICT;

CREATE TABLE sheets (
  id         INTEGER PRIMARY KEY,
  run_id     TEXT NOT NULL REFERENCES runs(id),
  chapter    INTEGER NOT NULL,
  attempt    INTEGER NOT NULL,           -- the attempt this sheet commissioned
  level      INTEGER NOT NULL CHECK (level IN (1, 2)),
  body       TEXT NOT NULL,
  validated  INTEGER NOT NULL,           -- it does not go out otherwise
  lines_cited INTEGER NOT NULL,
  ts         TEXT NOT NULL,
  UNIQUE (run_id, chapter, attempt)
) STRICT;

CREATE INDEX idx_attempts_run ON attempts(run_id, chapter);
CREATE INDEX idx_findings_attempt ON findings(attempt_id);
CREATE INDEX idx_gate_run ON gate_decisions(run_id, chapter);
