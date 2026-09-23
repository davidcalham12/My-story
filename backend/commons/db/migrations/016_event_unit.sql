-- Which unit's orchestrator produced this line.
--
-- SPEC-EXAM-003 replaced one process per novel with one process per unit of
-- work, so "the stream" is now several streams end to end. `seq` stays dense
-- across the whole run — it is still the SSE resume point — and this column is
-- what lets a reader ask which fresh orchestrator said a thing.
--
-- NULL on every row written before the conductor existed: absent, not "the
-- first unit".
ALTER TABLE events ADD COLUMN unit TEXT;
