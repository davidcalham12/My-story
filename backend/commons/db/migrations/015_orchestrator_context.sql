-- What the orchestrator's own turns cost in context, per run.
--
-- The 100,000-token ceiling is about the packets the AGENTS receive. The
-- orchestrator accumulates — Bible, drafts, findings, turn after turn — and
-- across two real runs its turns ran at a median of 147,000 and a peak of
-- 642,000. Halting on those would halt every novel, so nothing here stops a
-- run: these three columns exist so the figure is written down instead of
-- living in one watcher's memory for the length of one run.
--
-- NULL, not 0, on every one of them. A run nobody watched has no measurement;
-- `orchestrator_turns_over_ceiling = 0` is the claim that it was watched and
-- never crossed, which is a different sentence.
ALTER TABLE runs ADD COLUMN orchestrator_turns INTEGER;
ALTER TABLE runs ADD COLUMN largest_orchestrator_turn INTEGER;
ALTER TABLE runs ADD COLUMN orchestrator_turns_over_ceiling INTEGER;
