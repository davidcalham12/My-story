-- What was ordered, kept apart from what was run.
--
-- A brief is accepted before a run exists: FLOW-0 checks it, the buyer fixes
-- the age or answers the missing tone, and only then does anything cost money
-- (SPEC-EXAM-001 §2, `schema_brief` "before anything is spent"). A brief stored
-- only as a column on `runs` could not exist in that window, which is the whole
-- window the interviewer works in.
--
-- It is also the only record of what the novel was *for*. The premise, the
-- Bible and the chapters are all derived; when chapter 7 calls the dog by the
-- wrong name, this row is the one that settles whether the buyer said Bruno.
--
-- `payload` is the brief as `Brief` accepted it — whole, as JSON, not spread
-- into columns. The schema lives in Pydantic and a second copy here would drift
-- from it within a month; `json_valid` is the part SQLite can actually hold.
-- The free text is stored with it, injection and all: it is data, and a store
-- that edited it would be reading it.
CREATE TABLE briefs (
  id         TEXT NOT NULL PRIMARY KEY,
  created_at TEXT NOT NULL,                    -- a real clock reading, UTC
  payload    TEXT NOT NULL CHECK (json_valid(payload)),
  CHECK (length(id) > 0)
) STRICT;
