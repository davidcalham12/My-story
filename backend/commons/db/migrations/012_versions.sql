-- Every published copy of a novel, and why it exists.
--
-- A reader who asks for one fact to change gets a second novel, not an edited
-- first one: `dist/v1/` is what somebody has already read, and the exam's AC-7
-- is that it stays exactly as it was. Until this table the only record of a
-- publication was a directory on disk, and a directory cannot say what it was
-- published *for* — which is precisely what the "what changed" page of v2 is
-- written from, and what a reader comparing two PDFs needs.
--
-- `parent` is the version this one was regenerated from. NULL only for the
-- first: a later version with no parent is a version whose provenance was lost,
-- and the CHECK refuses it rather than letting the change page render empty.
--
-- No row is written for a regeneration the gate halted. A halted attempt leaves
-- its workspace directory behind with no `novel.html` in it and no row here,
-- which is how the two are told apart afterwards (docs/spec.md §7, the accepted
-- gap: the reader change runs the ordinary gate and may fail it).
CREATE TABLE versions (
  run_id     TEXT    NOT NULL REFERENCES runs(id),
  n          INTEGER NOT NULL CHECK (n >= 1),
  parent     INTEGER CHECK (parent IS NULL OR parent < n),
  reason     TEXT    NOT NULL,            -- why this version was published
  created_at TEXT    NOT NULL,
  PRIMARY KEY (run_id, n),
  CHECK (parent IS NOT NULL OR n = 1)
) STRICT;
