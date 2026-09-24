-- The four usage figures of an agent call, and where its cost came from.
--
-- `calls` was written from `task_progress`, which reports one blended
-- `total_tokens`; output was always NULL and most dispatches left no row. The
-- Agent tool's own result carries input, cache creation, cache read and output
-- separately, and that is what a row is made from now (backend/commons/log/
-- agent_usage.py). `input_tokens` and `output_tokens` keep their meaning.
--
-- `cost_provenance` is separate from `provenance` because they differ: the
-- tokens are measured, the per-call cost is estimated from config/pricing.json.
-- The run's total stays measured, from the `result` event.
ALTER TABLE calls ADD COLUMN cache_creation_input_tokens INTEGER;
ALTER TABLE calls ADD COLUMN cache_read_input_tokens INTEGER;
ALTER TABLE calls ADD COLUMN cost_provenance TEXT
  CHECK (cost_provenance IS NULL OR cost_provenance IN
         ('measured','reported','reconstructed','estimated','absent'));
