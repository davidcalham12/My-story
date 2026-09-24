-- Which brief a run was filling.
--
-- Until now the two halves of the product did not touch. `POST /api/briefs`
-- stored what the buyer ordered, `POST /api/runs` took a premise somebody
-- typed, and no column, table or function joined them. The gap was found by
-- writing the eval harness and discovering it had to compose the premise
-- itself; the interview in SPEC-EXAM-002 assumes the join exists.
--
-- Nullable, and it stays nullable. A run started from a bare premise is not a
-- degraded run: it is the demo, the stress profile and every run recorded
-- before this migration. NULL here means "no brief", which is a different
-- claim from "a brief that asked for nothing".
--
-- A foreign key rather than a copy of the payload. The brief is the only
-- record of what the novel was *for*, and two copies of it disagree the first
-- time the buyer corrects an age.
ALTER TABLE runs ADD COLUMN brief_id TEXT REFERENCES briefs(id);

-- One index, because the question asked of this column is always "what became
-- of this brief" and never "which brief did this run come from" — the latter
-- is already a primary-key lookup from the run row you are holding.
CREATE INDEX IF NOT EXISTS idx_runs_brief ON runs(brief_id) WHERE brief_id IS NOT NULL;
