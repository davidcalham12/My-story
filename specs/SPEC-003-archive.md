# SPEC-003 — The run's own record reaches the database

status: approved
date: 2026-09-22
supersedes: nothing
related: SPEC-002-gate, D22, verification.md G12/G13

## What is wanted

**When a run finishes, its gate record is in the database.** Today it is not.

`lighthouse-keeper-ledger` — v2's first real run, three chapters, eight attempts,
four feedback sheets, $18.82 measured — left the database holding **one row in
`runs`, nine in `calls`, and zero in `attempts`, `scores`, `findings`,
`gate_decisions` and `sheets`.** Every one of those facts exists on disk, written
by the orchestrator exactly as `SKILL.md` §"Record it" requires. Nothing reads
them back.

`repository.save_attempt`, `save_gate` and `save_sheet` are written, tested by
nobody, and **called by nothing**. `SKILL.md` line 422 says it best, about a
different failure: *the work happened and the record of it was in a place nothing
reads.*

## Why

The database is the archive, and the panel is a view of the archive. A run that
completes and leaves it empty means:

- the panel shows a finished novel with no gate history — the one screen that
  shows the pipeline is real;
- the measured cost, **$18.82 from Claude Code's own `result`**, is on disk in
  `cost.json` while the API reports a sum over nine `calls` rows. That is a
  `reconstructed` figure standing where a `measured` one exists, which inverts
  the rule G12 exists to hold;
- LOOP-003's statistics cannot be computed from the database for the only run
  that has ever used five characteristics.

## What is explicitly out of scope

- **Writing the rows live, as the run goes.** That would mean the orchestrator
  calling Python per attempt, which is a change to `SKILL.md` and therefore a
  change that cannot be tested at $0. Archiving at completion is testable now.
- **Changing what the orchestrator writes to disk.** The on-disk shapes are the
  input; this spec reads them.
- **Backfilling `summary_facts` or `character_knowledge`.** Inferring those from
  prose is invented data wearing the appearance of measurement — the same rule
  `import_v1` follows.
- **Re-deriving scores.** The archive records what the run decided, not what it
  should have decided.

## Acceptance criteria

| # | criterion | letter |
|---|---|---|
| A1 | Archiving a completed run directory writes one `attempts` row per attempt found, with its draft path and word count | **T** |
| A2 | Each attempt carries **five** `scores` rows; a critic that returned no usable verdict is stored as `NULL`, never 0 or 10 | **T** |
| A3 | `promoted` is 1 for exactly the attempt whose draft matches the accepted `chNN.md`, and 0 for every other | **T** |
| A4 | A `gate_decisions` row per attempt, with the `min` as `aggregate` and a verdict the schema's CHECK admits | **T** |
| A5 | Every feedback sheet on disk becomes a `sheets` row with its level and whether it validated | **T** |
| A6 | Findings are stored with their arbitration; `upheld` is 0 only where the ruling says so in as many words | **T** |
| A7 | The measured `total_cost_usd` is stored on the run, graded `measured`, and the API prefers it over the sum of `calls` | **T** |
| A8 | Archiving twice does not duplicate rows | **T** |
| A9 | A halted run archives what exists and records the halt, rather than refusing | **T** |
| A10 | That the archive is *complete* — that no attempt was made whose files the orchestrator never wrote | **U** |

A10 is the honest one. This reads what is on disk. A chapter whose critique file
was never written is indistinguishable from a chapter that was never attempted,
and `run_completeness` is where that gets recorded rather than smoothed over.

## Gaps this spec leaves

| gap | level |
|---|---|
| A10 — the archive is as complete as the orchestrator's writing was | important |
| Rows arrive at the end, so a run that dies mid-flight archives nothing | important |
