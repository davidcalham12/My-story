# tla/ — the harness as a state machine

`Harness.tla` models generation: configuring, planning, writing and validating each chapter with bounded retries and patch-then-halt, publishing a version, resuming after a crash, and regenerating only the chapters a reader change affects. `Harness.cfg` checks it on 5 chapters, 2 retries, 1 reader change and 1 crash.

## Properties
| kind | name | says |
|---|---|---|
| safety | `PublishedOnlyValidated` | no published version holds a chapter that did not pass every validator |
| safety | `NoDuplicateNoLoss` | resuming neither duplicates nor loses a chapter |
| safety | `RetriesBounded` | retries never exceed the limit |
| safety (action) | `VersionsPreserved` | a published version is never modified or removed |
| liveness | `Terminates` | every run ends published or halted |

## How to run
```
java -cp tla2tools.jar tlc2.TLC -config Harness.cfg Harness.tla
```
TLC needs a JDK. **Status:** not run yet on the build machine — no JDK installed and installing one needs the owner's approval; the specification is written and reviewed. Result and any counterexample are recorded in `docs/iterations.md` when it runs.

## Specification ↔ code
Each action corresponds to a state or transition of the per-stage conductor (SPEC-EXAM-003).

| action | code |
|---|---|
| `BriefAccepted` / `BriefRejected` | `POST /api/briefs`: the brief validates, or returns incomplete/contradiction and no run starts (`backend/brief/`) |
| `Plan` | conductor units U1 world, U2 cast, U3 outline + audit (`backend/runs/conductor.py`) |
| `Draft` | the chapter writer's draft inside unit U4.n |
| `Pass` | the gate's `min` ≥ 8, `decide` → accept, `promote` copies the draft; the unit's output contract is met; next unit or U5 publishes a `versions` row |
| `Retry` | `decide` → retry with the escalating feedback sheet |
| `HaltAtGate` | `decide` → patch, then halt: the run is `halted: gate`, no chapter promoted |
| `Crash` | the unit's process dies without a result event |
| `Resume` | the conductor skips every unit whose accepted output exists and restarts at the first that has none |
| `ReaderChange` | `python -m backend.versions.change`: `fact_usage` names the chapters, a new version regenerates only those, earlier versions untouched |
