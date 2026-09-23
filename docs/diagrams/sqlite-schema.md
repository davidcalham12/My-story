# SQLite schema (main tables)

| table | holds | added by |
|---|---|---|
| runs | one row per novel run: premise, profile, stage, halt reason, measured cost, config snapshot | harness migrations 001, 005, 007, 008 |
| events | every line of the orchestrator's stream, in order | harness 009 |
| attempts, scores, findings, gate_decisions, sheets | the gate's record per chapter and attempt | harness 002, 006 |
| calls | one row per subagent call with its token figure and provenance | harness 003 |
| facts, fact_usage, characters, places, chronology | the story bible, and which chapter uses each fact | exam 010 |
| forbidden_words, audit_log | the three-level guardrail and its decisions | exam 011 |
| versions | each published version of a novel and its parent | exam 012 |
| validations | every validator result per version, with its Langfuse score id | exam 013 |
| briefs | the validated brief of each novel | exam 014 |
