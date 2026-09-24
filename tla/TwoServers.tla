--------------------------- MODULE TwoServers ---------------------------
(***************************************************************************)
(* Two backend servers sharing ONE SQLite database (SPEC-EXAM-005 O4).    *)
(*                                                                        *)
(* Each server, when it starts, runs the orphan sweep of                  *)
(* backend/runs/service.py `sweep_orphans`: every v2 run whose            *)
(* `finished_at` is NULL is marked `halted: process` ("found running at   *)
(* startup; the process is gone"), and `halt()` also sets `finished_at`.  *)
(* The sweep assumes one server per database. Red-team case 13: the eval  *)
(* server started on :8001 and swept the example novel that was live on   *)
(* :8000. Red-team case 9: a server that stops can leave its orchestrator *)
(* alive, and its own restart sweeps that live run.                       *)
(*                                                                        *)
(* GUARD   = FALSE : the sweep as written (TLC finds case 13).            *)
(* GUARD   = TRUE  : the sweep skips a run whose process is alive         *)
(*                   ("check the pid before sweeping").                   *)
(* RESWEEP = TRUE  : a server may re-run the guarded sweep while it is    *)
(*                   up, not only at start-up. Only safe with the guard.  *)
(*                                                                        *)
(* The mapping from each action to the code is in tla/TwoServers.md.      *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS Servers,   \* two servers on the same database ({s1, s2})
          Runs,      \* run rows that can be created ({r1, r2})
          None,      \* model value: no run
          GUARD,     \* BOOLEAN: the sweep checks the process first
          RESWEEP    \* BOOLEAN: the guarded sweep also runs while up

ASSUME GUARD \in BOOLEAN /\ RESWEEP \in BOOLEAN
ASSUME RESWEEP => GUARD      \* an unguarded periodic sweep would be worse

VARIABLES up,        \* up[s]: server s is running
          live,      \* live[s]: the run in s's memory (`self._live`), or None
          owner,     \* owner[r]: the server that launched r's process
          created,   \* created[r]: r's row exists
          alive,     \* alive[r]: r's orchestrator process is running
          finished,  \* finished[r]: r's row has `finished_at` set
          halted     \* halted[r]: r's row has `halted` set

vars == <<up, live, owner, created, alive, finished, halted>>

TypeOK ==
  /\ up       \in [Servers -> BOOLEAN]
  /\ live     \in [Servers -> Runs \cup {None}]
  /\ owner    \in [Runs -> Servers \cup {None}]
  /\ created  \in [Runs -> BOOLEAN]
  /\ alive    \in [Runs -> BOOLEAN]
  /\ finished \in [Runs -> BOOLEAN]
  /\ halted   \in [Runs -> BOOLEAN]

Init ==
  /\ up       = [s \in Servers |-> FALSE]
  /\ live     = [s \in Servers |-> None]
  /\ owner    = [r \in Runs |-> None]
  /\ created  = [r \in Runs |-> FALSE]
  /\ alive    = [r \in Runs |-> FALSE]
  /\ finished = [r \in Runs |-> FALSE]
  /\ halted   = [r \in Runs |-> FALSE]

\* The rows the sweep selects. Unguarded: `finished_at IS NULL`. Guarded: and
\* the run's process is not alive.
Swept(r) == created[r] /\ ~finished[r] /\ (GUARD => ~alive[r])

\* `write_repo.halt(conn, id, "process", ...)` on every selected row: sets
\* `halted` and `finished_at` in one transaction.
Sweep ==
  /\ halted'   = [r \in Runs |-> IF Swept(r) THEN TRUE ELSE halted[r]]
  /\ finished' = [r \in Runs |-> IF Swept(r) THEN TRUE ELSE finished[r]]

\* A server starts: `build_service()` in backend/main.py migrates, then
\* sweeps, before the first request. It starts with nothing in memory.
Start(s) ==
  /\ ~up[s]
  /\ up' = [up EXCEPT ![s] = TRUE]
  /\ live' = [live EXCEPT ![s] = None]
  /\ Sweep
  /\ UNCHANGED <<owner, created, alive>>

\* A running server re-runs the guarded sweep (RESWEEP only). Enabled only
\* when it would mark something, so that it is a real step.
Resweep(s) ==
  /\ RESWEEP /\ up[s]
  /\ \E r \in Runs : Swept(r)
  /\ Sweep
  /\ UNCHANGED <<up, live, owner, created, alive>>

\* A server launches a run: `start()` refuses with AlreadyRunning when its own
\* `_live` is set and not done (the queue is one). It knows nothing about the
\* other server's run.
Launch(s, r) ==
  /\ up[s] /\ live[s] = None /\ ~created[r]
  /\ live'    = [live EXCEPT ![s] = r]
  /\ owner'   = [owner EXCEPT ![r] = s]
  /\ created' = [created EXCEPT ![r] = TRUE]
  /\ alive'   = [alive EXCEPT ![r] = TRUE]
  /\ UNCHANGED <<up, finished, halted>>

\* The process ends and the server that is watching it records the result:
\* `finish()` sets `finished_at` and `stage`, and does NOT clear `halted`.
Finish(r) ==
  /\ alive[r] /\ owner[r] # None /\ live[owner[r]] = r
  /\ alive'    = [alive EXCEPT ![r] = FALSE]
  /\ finished' = [finished EXCEPT ![r] = TRUE]
  /\ live'     = [live EXCEPT ![owner[r]] = None]
  /\ UNCHANGED <<up, owner, created, halted>>

\* The process ends with nobody watching it (its server died; case 9): the
\* row is not touched. This is how a real orphan is made.
OrphanExit(r) ==
  /\ alive[r] /\ owner[r] # None /\ live[owner[r]] # r
  /\ alive' = [alive EXCEPT ![r] = FALSE]
  /\ UNCHANGED <<up, live, owner, created, finished, halted>>

\* A server dies (or is stopped). Its memory is lost. The process it was
\* watching may die with it, or survive as an orphan still running
\* (red-team case 9: stopping the server left the orchestrator alive).
Crash(s) ==
  /\ up[s]
  /\ up'   = [up EXCEPT ![s] = FALSE]
  /\ live' = [live EXCEPT ![s] = None]
  /\ \E survives \in BOOLEAN :
       alive' = [r \in Runs |->
                   IF r = live[s] THEN survives ELSE alive[r]]
  /\ UNCHANGED <<owner, created, finished, halted>>

\* No Done action is needed: a server can always start or crash, so every
\* state has a successor and TLC's deadlock check stays on.
Next ==
  \/ \E s \in Servers : Start(s) \/ Resweep(s) \/ Crash(s)
  \/ \E s \in Servers, r \in Runs : Launch(s, r)
  \/ \E r \in Runs : Finish(r) \/ OrphanExit(r)

\* A server that is down eventually starts again; a server that could
\* re-sweep eventually does. Nothing forces a server to crash.
Fairness == \A s \in Servers : WF_vars(Start(s)) /\ WF_vars(Resweep(s))

Spec == Init /\ [][Next]_vars /\ Fairness

---------------------------------------------------------------------------
\* A row that says "running" (no finished_at) with no process behind it.
Orphan(r) == created[r] /\ ~alive[r] /\ ~finished[r]

\* SAFETY 1 (the point) — a run whose process is alive is never marked
\* halted. Red-team case 13 is a violation of this.
NoLiveRunMarkedHalted == \A r \in Runs : alive[r] => ~halted[r]

\* SAFETY 2 — a halted row always has finished_at: `halt()` writes both.
HaltedIsFinished == \A r \in Runs : halted[r] => finished[r]

\* SAFETY 3 (action) — right after a server starts, no orphan is left
\* un-halted: the sweep still does its job with the guard on.
StartLeavesNoOrphan ==
  [][ (\E s \in Servers : ~up[s] /\ up'[s]) =>
        \A r \in Runs : ~Orphan(r)' ]_vars

\* LIVENESS — no orphan says "running" forever.
OrphansEventuallyHalted == \A r \in Runs : Orphan(r) ~> halted[r]
=============================================================================
