-- Every validator's verdict on a version, in one place.
--
-- docs/spec.md §2 names eleven validators of four kinds, and until this table
-- each of them reported somewhere else: the gate wrote `attempts` rows, the
-- guardrail wrote `audit_log`, the judge returned JSON to whoever asked. So
-- "what did every validator say about version 2 of brief 03" was a question
-- answered by reading four places and a directory, and `evals/results.md` —
-- which is exactly that question asked five times over — had nothing to be
-- generated FROM. AC-8 makes the table the source: the eval report is a pivot
-- of these rows by brief × validator, not a document somebody keeps in step.
--
-- `version` is a plain INTEGER and carries NO foreign key, deliberately. Two
-- reasons, and the second is the one that would survive `versions` arriving:
-- this migration is written in a different worktree from `012_versions.sql` and
-- must apply on a database where that table does not exist yet; and a
-- validation is a record of a judgement that was made, which has to stay
-- readable even if the version it judged is later deleted or rebuilt. A verdict
-- that vanishes with its subject is a verdict nobody can audit.
--
-- `value` is TEXT because the validators do not share a scale and must not be
-- forced onto one. §2's own score column reads: pass/fail, a count of
-- deviations, words, a fraction, hits, six scores, and `not run: elan
-- unavailable`. A REAL column turns the first into 1.0 and the last into NULL,
-- and then the pivot prints 0.0 where the honest answer was "fail" or "not run"
-- — docs/domain-knowledge.md §7.10, which is the family this whole table is
-- one `COALESCE` away from joining. A caller that needs arithmetic casts at the
-- point where the decision to cast is visible.
--
-- NULL `value` means the validator was asked and produced nothing usable. The
-- ROW still exists, because a missing row and a NULL value are different
-- claims: one says nobody ran it, the other says it ran and had no answer.
CREATE TABLE validations (
  id            INTEGER PRIMARY KEY,
  run_id        TEXT    NOT NULL REFERENCES runs(id),
  version       INTEGER NOT NULL,      -- the version number; no FK, see above
  validator     TEXT    NOT NULL,      -- the name in docs/spec.md §2, exactly
  kind          TEXT    NOT NULL CHECK (kind IN ('a', 'b', 'c', 'd')),
  -- The sub-verdict, where a validator has more than one. `judge_rubric` writes
  -- six criteria and a 'mean'; `mandatory_facts` writes one row and leaves this
  -- NULL. Without it the six scores would have to be smuggled into `validator`
  -- as `judge_rubric.pacing`, and the pivot AC-8 asks for would have to parse
  -- names back apart.
  criterion     TEXT,
  value         TEXT,                  -- absent is NULL, never 0; see above
  -- Why the validator says what it says. Optional for the kinds that compute —
  -- arithmetic argues for itself — and required below for the kind that judges.
  justification TEXT,
  ts            TEXT    NOT NULL,
  -- Kind b is a model or a human scoring a rubric (§2: `judge_rubric`,
  -- `human_review`). A score from a judgement with no reason beside it cannot
  -- be checked, disputed or acted on, and cannot be told from a number picked
  -- to look decisive. Pydantic refuses one in the agent's reply; this refuses
  -- one from everything else that can reach the table, which is the half that
  -- outlives the phase that wrote the model.
  CHECK (kind <> 'b' OR value IS NULL OR justification IS NOT NULL)
) STRICT;

-- The lookup both routes make and the one `evals/results.md` pivots on.
CREATE INDEX validations_by_version ON validations (run_id, version, validator);
