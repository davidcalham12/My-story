-- SPEC-003. The run's own measured total, from Claude Code's `result` event.
--
-- It was written to output/<slug>/cost.json and nowhere else, so the panel
-- showed the SUM OVER `calls` instead: a reconstructed figure standing where a
-- measured one existed, which is the exact inversion of the rule G12 holds.
--
-- Every column is nullable on purpose. A run that produced no `result` has no
-- cost, and a NULL says that. A 0 would say the run was free.
ALTER TABLE runs ADD COLUMN cost_usd REAL;
ALTER TABLE runs ADD COLUMN cost_provenance TEXT
  CHECK (cost_provenance IS NULL OR cost_provenance IN
         ('measured','reported','reconstructed','estimated','absent'));
-- Claude Code's own accounting of the run, worth keeping because it is the only
-- place the orchestrator's turns are counted at all.
ALTER TABLE runs ADD COLUMN turns INTEGER;
ALTER TABLE runs ADD COLUMN duration_ms INTEGER;
ALTER TABLE runs ADD COLUMN subagent_dispatches INTEGER;
