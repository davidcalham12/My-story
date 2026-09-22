-- SPEC-006. `prose` becomes the sixth characteristic.
--
-- The CHECK on `scores.characteristic` names the five literally, and SQLite
-- cannot ALTER a constraint. So the table is rebuilt, which is the right kind of
-- work for this change: the constraint is the thing that makes a typo in a
-- critic's name impossible, and widening it is a decision that should cost a
-- migration rather than a config edit.
--
-- The old rows keep their meaning. A pre-SPEC-006 attempt has five scores and no
-- `prose` row, and that is correct — it was judged by five characteristics.
-- Backfilling a `prose` score would invent a judgement nobody made, and a NULL
-- row would say the critic ran and returned nothing. Neither happened: it did
-- not exist.

PRAGMA foreign_keys = OFF;

CREATE TABLE scores_new (
  attempt_id     INTEGER NOT NULL REFERENCES attempts(id),
  characteristic TEXT NOT NULL CHECK (characteristic IN
                   ('continuity', 'science', 'outline', 'length', 'chatter',
                    'prose')),
  -- NULL means the critic returned no usable verdict. It is EXCLUDED from the
  -- minimum, never counted as a pass: 10 invents an approval and 0 invents a
  -- rejection. This once returned 10 and a malformed reply silently passed.
  score          INTEGER CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
  note           TEXT,
  PRIMARY KEY (attempt_id, characteristic)
) STRICT;

INSERT INTO scores_new (attempt_id, characteristic, score, note)
  SELECT attempt_id, characteristic, score, note FROM scores;

DROP TABLE scores;
ALTER TABLE scores_new RENAME TO scores;

PRAGMA foreign_keys = ON;
