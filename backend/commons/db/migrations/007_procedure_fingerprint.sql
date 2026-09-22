-- The procedure a run actually ran under.
--
-- `SKILL.md` IS the pipeline — Annex C left exactly one implementation of it —
-- and it is a file on disk that anyone can edit while a run is in flight. That
-- happened: SPEC-006 added a sixth characteristic during an eight-chapter run,
-- and chapters 1-2 were judged by five while everything after could be judged by
-- six. Nothing noticed, because nothing was looking.
--
-- The config is snapshotted per run for exactly this reason. The procedure was
-- not. A run whose procedure changed underneath it is not a clean sample, and
-- the difference between a sample and a contaminated one has to be a recorded
-- fact rather than something someone remembers.
--
-- Nullable: runs that finished before this existed have no fingerprint, and that
-- is absent, not "unchanged".
ALTER TABLE runs ADD COLUMN skill_sha_at_start TEXT;
ALTER TABLE runs ADD COLUMN skill_sha_at_end   TEXT;
