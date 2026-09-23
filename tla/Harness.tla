---------------------------- MODULE Harness ----------------------------
(***************************************************************************)
(* The storyMaker harness as a state machine: configuring, planning,      *)
(* writing and validating each chapter (with bounded retries and          *)
(* patch-then-halt), publishing a version, resuming from a checkpoint     *)
(* after a crash, and regenerating only the chapters a reader change      *)
(* affects. It models the per-stage conductor of SPEC-EXAM-003: a crash   *)
(* loses the unit in flight, never an accepted chapter.                   *)
(*                                                                        *)
(* The mapping from each action to the code is in tla/README.md.          *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS Chapters,    \* chapters in a novel (5 in the model)
          MaxRetries,  \* rewrites allowed after the first draft (2)
          MaxChanges,  \* reader changes explored (1)
          MaxCrashes   \* crashes explored (1)

VARIABLES state,     \* where the run is
          ch,        \* the chapter being written or validated
          pending,   \* chapters still to be accepted in this version
          passed,    \* passed[c]: chapter c passed every validator
          retries,   \* retries[c]: rewrites spent on chapter c in this version
          versions,  \* published versions, each a snapshot of `passed`
          changes,   \* reader changes so far
          crashes    \* crashes so far

vars == <<state, ch, pending, passed, retries, versions, changes, crashes>>

Chs    == 1..Chapters
States == {"Configuring", "Planning", "Writing", "Validating",
           "Resuming", "Published", "Halted"}
Min(S) == CHOOSE x \in S : \A y \in S : x <= y

TypeOK ==
  /\ state \in States
  /\ ch \in 0..Chapters
  /\ pending \subseteq Chs
  /\ passed \in [Chs -> BOOLEAN]
  /\ retries \in [Chs -> 0..MaxRetries]
  /\ changes \in 0..MaxChanges
  /\ crashes \in 0..MaxCrashes

Init ==
  /\ state = "Configuring"
  /\ ch = 0
  /\ pending = Chs
  /\ passed = [c \in Chs |-> FALSE]
  /\ retries = [c \in Chs |-> 0]
  /\ versions = << >>
  /\ changes = 0
  /\ crashes = 0

\* The interview produces a valid brief, or the run stops before spending.
BriefAccepted == state = "Configuring" /\ state' = "Planning"
                 /\ UNCHANGED <<ch, pending, passed, retries, versions, changes, crashes>>
BriefRejected == state = "Configuring" /\ state' = "Halted"
                 /\ UNCHANGED <<ch, pending, passed, retries, versions, changes, crashes>>

\* World, cast and outline (units U1-U3), then the first pending chapter.
Plan == state = "Planning" /\ state' = "Writing" /\ ch' = Min(pending)
        /\ UNCHANGED <<pending, passed, retries, versions, changes, crashes>>

\* A draft (first or rewrite) goes to the gate.
Draft == state = "Writing" /\ state' = "Validating"
         /\ UNCHANGED <<ch, pending, passed, retries, versions, changes, crashes>>

\* All six characteristics reach the threshold: the chapter is accepted and
\* checkpointed; the next pending chapter, or publication.
Pass ==
  /\ state = "Validating"
  /\ passed' = [passed EXCEPT ![ch] = TRUE]
  /\ pending' = pending \ {ch}
  /\ IF pending' = {}
       THEN /\ state' = "Published"
            /\ versions' = Append(versions, passed')
            /\ ch' = ch
       ELSE /\ state' = "Writing"
            /\ ch' = Min(pending')
            /\ versions' = versions
  /\ UNCHANGED <<retries, changes, crashes>>

\* Below the threshold with rewrites left: another attempt.
Retry ==
  /\ state = "Validating" /\ retries[ch] < MaxRetries
  /\ retries' = [retries EXCEPT ![ch] = @ + 1]
  /\ state' = "Writing"
  /\ UNCHANGED <<ch, pending, passed, versions, changes, crashes>>

\* Below the threshold after the last attempt and the patch: the run stops;
\* the chapter never enters a version.
HaltAtGate ==
  /\ state = "Validating" /\ retries[ch] = MaxRetries
  /\ state' = "Halted"
  /\ UNCHANGED <<ch, pending, passed, retries, versions, changes, crashes>>

\* The process dies mid-unit: the unit in flight is lost, accepted chapters
\* are not.
Crash ==
  /\ state \in {"Writing", "Validating"} /\ crashes < MaxCrashes
  /\ crashes' = crashes + 1
  /\ state' = "Resuming"
  /\ UNCHANGED <<ch, pending, passed, retries, versions, changes>>

\* The conductor resumes at the first chapter not yet accepted.
Resume ==
  /\ state = "Resuming"
  /\ state' = "Writing" /\ ch' = Min(pending)
  /\ UNCHANGED <<pending, passed, retries, versions, changes, crashes>>

\* A reader changes a fact used by the chapters in A: only those are
\* rewritten, in a new version; published versions are untouched.
ReaderChange ==
  /\ state = "Published" /\ changes < MaxChanges
  /\ \E A \in (SUBSET Chs) \ {{}} :
       /\ pending' = A
       /\ passed' = [c \in Chs |-> IF c \in A THEN FALSE ELSE passed[c]]
       /\ retries' = [c \in Chs |-> IF c \in A THEN 0 ELSE retries[c]]
       /\ ch' = Min(A)
  /\ changes' = changes + 1
  /\ state' = "Writing"
  /\ UNCHANGED <<versions, crashes>>

\* A finished run stays finished. Explicit, so that TLC's deadlock check keeps
\* looking for real deadlocks instead of reporting the terminal states
\* (first counterexample, 2026-09-23: BriefRejected -> Halted, no successor).
Done == state \in {"Published", "Halted"} /\ UNCHANGED vars

Next == BriefAccepted \/ BriefRejected \/ Plan \/ Draft \/ Pass \/ Retry
        \/ HaltAtGate \/ Crash \/ Resume \/ ReaderChange \/ Done

Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

---------------------------------------------------------------------------
\* SAFETY 1 — no published version holds a chapter that did not pass.
PublishedOnlyValidated ==
  \A i \in 1..Len(versions) : \A c \in Chs : versions[i][c]

\* SAFETY 2 — resuming neither duplicates nor loses a chapter: the chapter
\* being worked on is always one not yet accepted, and every chapter is
\* either accepted or pending, never both.
NoDuplicateNoLoss ==
  /\ state \in {"Writing", "Validating"} => ch \in pending
  /\ \A c \in Chs : passed[c] <=> c \notin pending

\* SAFETY 3 — retries never exceed the limit.
RetriesBounded == \A c \in Chs : retries[c] <= MaxRetries

\* SAFETY 4 — a published version is never modified or removed.
VersionsPreserved ==
  [][ /\ Len(versions') >= Len(versions)
      /\ \A i \in 1..Len(versions) : versions'[i] = versions[i] ]_vars

\* LIVENESS — every run ends published or halted; no infinite loop.
Terminates == <>(state \in {"Published", "Halted"})
=============================================================================
