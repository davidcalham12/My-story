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
TLC needs a JDK (a portable Temurin 21 in the owner's user folder, no administrator rights).

**Result, 2026-09-23 20:24 UTC:** model checking completed, no error found. 44,145 states generated, **18,253 distinct**, graph depth 38, all four safety properties and the liveness property hold on 5 chapters, 2 retries, 1 reader change, 1 crash.

**Counterexample found on the way:** the first run reported a deadlock in 4 states: `BriefRejected` leads to `Halted`, which had no successor. Not a defect of the harness — a finished run has nothing left to do — but it hid everything else, because TLC stops at the first error. Fixed by an explicit `Done` action (a finished run stays finished), which keeps the deadlock check on for real deadlocks. Recorded in `docs/iterations.md`.

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

## Two servers on one database — `TwoServers.tla`
A second spec (SPEC-EXAM-005 O4) for what `Harness.tla` cannot see: two backend servers sharing one SQLite file, each running `sweep_orphans` at start-up. `TwoServers.cfg` (the sweep as written) makes TLC find red-team case 13 in 4 states: a live run marked `halted: process`. `TwoServersGuardOnly.cfg` (sweep only runs whose process is dead) holds every safety property but leaves an orphan un-swept. `TwoServersGuarded.cfg` (guard + re-sweep while up) passes everything on 398 distinct states. The mapping to code, the traces and the limits are in [`TwoServers.md`](TwoServers.md). The guard is specified, not implemented.
