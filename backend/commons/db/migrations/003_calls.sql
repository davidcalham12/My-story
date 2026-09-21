-- One row per model call. This is the table the whole cost and context story is
-- told from, and v1's version of it understated the bill by a factor of eight
-- because it recorded one total with no split and knew nothing of the
-- orchestrator's own turns. Here the orchestrator is code, so every token that
-- reaches a model is in this table.
CREATE TABLE calls (
  id                   INTEGER PRIMARY KEY,
  run_id               TEXT NOT NULL REFERENCES runs(id),
  stage                TEXT NOT NULL,
  agent                TEXT NOT NULL,
  model                TEXT NOT NULL,          -- the full id, never the family word
  chapter              INTEGER,
  attempt              INTEGER,

  -- Separated, so cost is exact rather than bounded.
  input_tokens         INTEGER,
  output_tokens        INTEGER,
  cost_usd             REAL,
  -- How the figures were obtained. Never let an absent figure read as a zero.
  provenance           TEXT NOT NULL DEFAULT 'measured'
                       CHECK (provenance IN ('measured','reported','reconstructed','estimated','absent')),

  -- The semaphore, so two assertions become series: "chapter 34 weighs what
  -- chapter 1 weighed", and "how long the critics waited".
  tokens_reserved      INTEGER,
  in_flight_at_dispatch INTEGER,
  wait_ms              INTEGER,

  duration_ms          INTEGER,
  ts                   TEXT NOT NULL,          -- a real clock reading, never an estimate
  note                 TEXT
) STRICT;

CREATE INDEX idx_calls_run ON calls(run_id, ts);
