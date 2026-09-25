# Anexo N — Lean: invariantes de la cronología

Source: `docs/spec.md` §1 (Lean 4 chronology validator), §2 (validator
`lean_chronology`, kind c), §5 (Lean runs only if elan installs without
administrator rights) and AC-11.

## What is here

`Chronology.lean` states the example novel's timeline (run `02412b7fe29e`,
`the-other-side-of-the-hill`) as concrete Lean lists and proves two invariants
by `decide`:

| theorem | what it says |
|---|---|
| `events_in_order` | the thirteen events of the timeline are in chronological order (day, then moment of the day) |
| `story_within_one_week` | the whole story happens within one week, so no stated age changes between events |
| `ages_possible` | every stated age (Leo 10, Rosa 10, Elena 12) is between 0 and 120 |

The events and ages are transcribed from the run's own Story Bible,
`output/the-other-side-of-the-hill/bible/timeline.md` and `characters.md`.

## Status: not run

- **`lake build` / `lean Chronology.lean` has not been run.** elan, Lean's
  installer, needs administrator rights on the build machine, which the project
  does not have. This is the reason the spec admits for AC-11, and it is
  recorded as `lean_chronology: not run: elan unavailable` in `validations`.
- **The file was transcribed by hand, not generated.** The exporter the spec
  names (`backend/formal/lean_export.py`, from the SQLite `chronology` table) was
  not written: it was the second cut in PLAN-001 Part 6. The file therefore
  proves the invariants over this one run's chronology, not over every run.
- **What it would not catch today.** Brief 05's impossible dates are refused
  earlier, at FLOW-0 (a memory dated before the birth date). A wedding at nine is
  a possible date but an implausible age; catching it would need an invariant on
  the age at a named event, which this file does not state.

## To run it where elan is available

```
lean Chronology.lean
```

No output and exit code 0 means the three theorems hold.
