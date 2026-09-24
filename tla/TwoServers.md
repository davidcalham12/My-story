# TwoServers.tla — two servers, one database, one orphan sweep

SPEC-EXAM-005 item O4. A second spec beside `Harness.tla`, which is untouched.

`Harness.tla` models one run inside one server. This spec models what `Harness.tla` cannot see: **two backend servers pointed at the same SQLite file**, each running the orphan sweep when it starts. Red-team case 13 (`docs/red-team-log.md`) is that situation: the eval server started on :8001, its sweep marked the example novel's run `halted: process`, and the novel's orchestrator on :8000 was alive and still writing.

## What the code does

`backend/main.py::build_service()` migrates, then calls `RunService.sweep_orphans()` (`backend/runs/service.py`, line ~712) before the first request:

```python
rows = self.conn.execute(
    "SELECT id FROM runs WHERE finished_at IS NULL AND source = 'v2'").fetchall()
for run_id in swept:
    write_repo.halt(self.conn, run_id, "process",
                    "found running at startup; the process is gone")
```

`write_repo.halt()` sets `halted` **and** `finished_at`. `write_repo.finish()` sets `finished_at` and `stage`, and **does not clear** `halted`. So a live run that gets swept keeps saying `halted: process` after it finishes. The sweep assumes one server per database, and it assumes a server's children die with it. Case 13 breaks the first assumption and case 9 breaks the second.

## The model

| variable | meaning | in the code |
|---|---|---|
| `up[s]` | server `s` is running | a uvicorn process |
| `live[s]` | the run in `s`'s memory, or `None` | `RunService._live` (lost when the process dies) |
| `owner[r]` | the server that launched `r` | implicit: whichever process holds the `claude -p` child |
| `created[r]` | the row exists | `runs` row created by `start()` |
| `alive[r]` | the orchestrator process is running | the `claude -p` subprocess |
| `finished[r]` | `finished_at IS NOT NULL` | `runs.finished_at` |
| `halted[r]` | `halted IS NOT NULL` | `runs.halted` |

| action | code |
|---|---|
| `Start(s)` | `build_service()`: migrate, then `sweep_orphans()`; `_live` starts empty |
| `Sweep` (inside `Start`, and `Resweep`) | `write_repo.halt(..., "process", ...)` on every selected row; selects `finished_at IS NULL`, and with `GUARD` also "the process is not alive" |
| `Resweep(s)` | **not in the code.** A running server re-runs the guarded sweep. Enabled only with `RESWEEP`, which the spec forbids without `GUARD` |
| `Launch(s, r)` | `start()`: refused with `AlreadyRunning` when `s`'s own `_live` is set; knows nothing of the other server's run |
| `Finish(r)` | the watcher sees the process end and calls `finish()`; `halted` untouched |
| `OrphanExit(r)` | the process ends with no server watching it (its server died): nothing touches the row |
| `Crash(s)` | the server dies or is stopped; `_live` is lost; the child may die with it or survive (case 9) |

Two servers, two runs, three booleans per run. There is no `Done` action because a server can always start or crash, so every state has a successor and the deadlock check stays on.

`GUARD` and `RESWEEP` are constants, so the same spec file serves all three configs.

## Properties

| kind | name | says |
|---|---|---|
| safety | `NoLiveRunMarkedHalted` | `\A r : alive[r] => ~halted[r]`. Case 13 violates this |
| safety | `HaltedIsFinished` | a halted row always has `finished_at`, because `halt()` writes both |
| safety (action) | `StartLeavesNoOrphan` | right after a server starts, no row says "running" with no process behind it. The guard must not stop the sweep doing its job |
| liveness | `OrphansEventuallyHalted` | `Orphan(r) ~> halted[r]`, where an orphan is a row that exists, is not finished, and has no live process |

Fairness: a server that is down eventually starts again (`WF` on `Start`), and a server that could re-sweep eventually does (`WF` on `Resweep`). Nothing forces a server to crash.

## Results (TLC 2.19, Temurin 21, 1 worker, 2026-09-24)

```
cd tla
java -cp tla2tools.jar tlc2.TLC -config TwoServers.cfg          TwoServers.tla
java -cp tla2tools.jar tlc2.TLC -config TwoServersGuardOnly.cfg TwoServers.tla
java -cp tla2tools.jar tlc2.TLC -config TwoServersGuarded.cfg   TwoServers.tla
```

| config | `GUARD` | `RESWEEP` | result | states |
|---|---|---|---|---|
| `TwoServers.cfg` | FALSE | FALSE | **`NoLiveRunMarkedHalted` violated**, 4-state trace = case 13 | 24 generated, 15 distinct at the stop |
| `TwoServersGuardOnly.cfg` | TRUE | FALSE | every safety property holds on the full state space; **`OrphansEventuallyHalted` violated** | 1,545 generated, **398 distinct**, depth 11 |
| `TwoServersGuarded.cfg` | TRUE | TRUE | **no error**: all three safety properties and the liveness property hold | 1,713 generated, **398 distinct**, depth 11 |

### 1. The sweep as written: case 13 (abbreviated TLC trace)

```
Error: Invariant NoLiveRunMarkedHalted is violated.
State 1: <Initial predicate>   up = (s1 :> FALSE @@ s2 :> FALSE)
State 2: <Start>   up = (s1 :> TRUE @@ s2 :> FALSE)                      \* :8000 starts
State 3: <Launch>  live = (s1 :> r1 ...)  alive = (r1 :> TRUE ...)       \* the novel's run
State 4: <Start>   up = (s1 :> TRUE @@ s2 :> TRUE)                       \* :8001 starts, sweeps
                   alive  = (r1 :> TRUE ...)
                   halted = (r1 :> TRUE ...)  finished = (r1 :> TRUE ...)
24 states generated, 15 distinct states found, 9 states left on queue.
```

That is red-team case 13, step for step: a server starts, launches a run, a second server starts on the same database and marks that run halted while its process is alive.

**The same bug with one server (case 9).** The same spec with `Servers = {s1}` (a one-line change to `TwoServers.cfg`, checked from a scratch copy and not committed) fails in 5 states: `Start → Launch r1 → Crash (the child survives) → Start`, and the restart sweeps a run whose orchestrator is still alive and still billing. A second server is not needed. A process that outlives its server is enough.

### 2. The guard alone: safe, but it leaves an orphan behind

With the guard, TLC explores the whole graph (398 distinct states) and no safety property fails. A sweep never marks a live run, and a server that has just started leaves no orphan.

The liveness property fails, and the lasso shows why (abbreviated):

```
State 5: <Launch>  both servers up; s2 runs r1, s1 runs r2
State 6: <Crash s2>  r1's child survives (case 9)
State 7: <Crash s1>  r2's child dies
State 8: <Start s1>  guarded sweep: r2 halted (dead); r1 skipped (alive)
State 9: <Start s2>  guarded sweep: r1 skipped again (still alive)
State 10: <OrphanExit r1>  r1's process ends, nobody watching: finished = FALSE, halted = FALSE
State 11: Stuttering   \* both servers stay up; r1 says "running" forever
```

The guard does its job. The run it rightly skipped is still unwatched, though, and when that process exits no server is left to record it, so the row says "running" until some server restarts. A sweep that only runs at start-up cannot catch it.

### 3. The fix: guard + re-sweep

Because the guarded sweep never touches a live run, it is safe to run at any time, not only at start-up. With `RESWEEP = TRUE` (a running server re-runs the guarded sweep, e.g. on a timer or when the panel lists runs), TLC finds **no error**: 1,713 states generated, 398 distinct, depth 11. All three safety properties and `OrphansEventuallyHalted` hold.

The two guarded configs reach the same 398 distinct states. The guard changes which states are reachable, and the re-sweep only adds transitions between them.

## What this does not prove

- **The guard is specified and model-checked, not implemented.** `sweep_orphans` is unchanged (SPEC-EXAM-005 §5), and case 13 stays declared.
- **"Alive" is an oracle in the model.** In the code it needs a `pid` column on `runs` (there is none today) and a liveness test that also rules out pid reuse, for example by comparing the process start time or command line with the value stored at launch. A guard that trusts a bare pid can skip a dead run whose pid was recycled, and TLC cannot see that.
- **Same machine only.** A pid means nothing to a server on another host. Two servers on one SQLite file are on one machine, so the model's assumption holds for this project.
- **Separate databases would close case 13 without any guard.** They would not close case 9, which needs the guard or a server that stops its children on shutdown.
- **Two servers and two runs.** Enough to show both failures and the fix. The model says nothing about three or more servers, though nothing in the argument depends on the number.
