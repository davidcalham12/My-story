-- SPEC-EXAM-007: a stopped novel can be continued, or put in the bin.
--
-- `trashed_at` is NULL for every run that is not in the bin. The directory of a
-- binned run is under output/_papelera/<slug>/; nothing is deleted, and the
-- library hides the row rather than losing it.
ALTER TABLE runs ADD COLUMN trashed_at TEXT;

-- Everything that was done to a run, one row per process-lifetime or request.
-- SPEC-EXAM-007 writes `generate` (the original launch, n = 1) and `continue`
-- (each continuation); SPEC-EXAM-008 will write `reader_change` and `redo` into
-- the same table, so there is one record of what a book cost and under what.
-- The snapshot in `runs.config_snapshot` is never rewritten: what each segment
-- ran under is here.
--
-- Every figure is nullable on purpose. A row that has not ended, or ended
-- without a `result`, has no cost: NULL says that, and a 0 would say it was
-- free. `orchestrator_model` NULL means the CLI's default, as in the config.
CREATE TABLE changes (
  id                  INTEGER PRIMARY KEY,
  run_id              TEXT NOT NULL REFERENCES runs(id),
  n                   INTEGER NOT NULL,
  kind                TEXT NOT NULL
    CHECK (kind IN ('generate','continue','reader_change','redo')),
  label               TEXT,
  version             INTEGER,
  chapters            TEXT,              -- JSON list, or NULL
  started_at          TEXT NOT NULL,
  finished_at         TEXT,
  orchestrator_model  TEXT,
  chapter_loop        TEXT,
  ceiling_usd         REAL,
  -- `profile` when computed from the profile, `owner` when typed in the panel.
  ceiling_by          TEXT,
  total_usd           REAL,
  minutes             REAL,
  orchestrator_usd    REAL,
  agents_model        TEXT,
  agents_usd          REAL,
  provenance          TEXT
    CHECK (provenance IS NULL OR provenance IN
           ('measured','reported','reconstructed','estimated','absent')),
  langfuse_trace_id   TEXT,
  note                TEXT,
  UNIQUE (run_id, n)
) STRICT;
