-- SPEC-EXAM-008: what each change cost, in the table SPEC-EXAM-007 created.
--
-- Still one table (§8.1). These three columns say how complete a row's figures
-- are, which the figures alone cannot:
--
-- `results`     how many `result` events were summed into it;
-- `unresulted`  how many processes ended without one (killed, crashed, cut):
--               their cost is absent, never 0;
-- `sources`     a JSON list of where each `result` was read — `events seq N`,
--               a stream file under the run directory — so the export and the
--               panel can say which records a figure came from.
ALTER TABLE changes ADD COLUMN results INTEGER;
ALTER TABLE changes ADD COLUMN unresulted INTEGER;
ALTER TABLE changes ADD COLUMN sources TEXT;
