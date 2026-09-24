---
id: SPEC-EXAM-007
title: A stopped novel can be continued, cheaper and to the same gate, or put in the bin and restored
status: approved
owner: David Calderon
requested_by: David Calderon — in chat to the coordinating session, 2026-09-24: "las novelas que se pararon quiero tener la opcion de eliminarlas o que continue su proceso y quiero que todo este funcionando bien de una manera que gaste menos y que tenga la misma calidad"
decisions: chosen by the owner in the same session — deleting is "Papelera recuperable"; continuing uses "La más barata vigente". His first choice for the budget case, "Pedir un techo nuevo", was withdrawn by him at ~21:45 UTC (§8): Continue never asks for a figure. In the build session he then chose "Tope automático por novela" (SR-05). The interface is in English ("Todo en inglés").
approved_by: David Calderon — in chat to the coordinating session, 2026-09-24: "apruebo el SPEC-EXAM-007"
approved_on: 2026-09-24
names_protected_value: the budget ceiling — the mechanism is unchanged (the CLI's --max-budget-usd plus the watcher). What is new:
  - each continuation carries the profile's ceiling, fresh for that segment and recorded as `ceiling_by = 'profile'`;
  - a novel's total known spend is capped at `budget.novel_ceiling_multiple` (2, in the config) × the profile's ceiling, and past that Continue is refused with the reason (SR-05). Nothing else in AGENTS.md §6 is touched: the gate that judges a continued chapter is the same gate.
depends_on: backend/runs/service.py::resume, backend/runs/router.py, the conductor (SPEC-EXAM-003), SPEC-EXAM-006, frontend pages library and read
---

# SPEC-EXAM-007 — Stopped novels: continue them or bin them

## 1. What is wanted, and why

The library shows novels that stopped: on their budget, on the 100k ceiling, by
the operator, or on the organisation's spend limit. **Today there are four**:

| run | where | why |
|---|---|---|
| `aa1bbe9269aa` | FLOW-1 | organisation spend limit (recorded as `gate`, before e5e3e9b) |
| `8834d0ab189a` (finisterre, eval 04) | FLOW-3 | budget, 25.80 of 25 USD |
| `8ab6c57af9f6` (stone-collector, eval 01) | FLOW-4 | stopped by the operator |
| `db2fed5bd97a` (leo-and-bruno) | FLOW-3 | the 100k ceiling |

From the web, the owner can do nothing with them. He wants two things:
- **continue** a stopped novel, spending less than it would have and to the same quality;
- **remove** one he does not want, recoverably.

`POST /api/runs/{id}/resume` already exists and works (the conductor asks the
filesystem which units are done). It has no button, and it continues with the
**config the run started with** — for every stopped run today, Opus as the
orchestrator, the expensive one.

## 2. Continue

**In the panel.** A stopped novel shows **"Continue"**. Before anything
starts, the panel shows:
- why it stopped;
- what it has spent (measured, or absent);
- which stage it will continue from.

**The cheapest current configuration.** A continued run takes `models` and
`orchestration` from **its profile as it is today**, not from its snapshot:
- today that means Sonnet as the orchestrator;
- once SPEC-EXAM-006's AC-6 is measured and the owner turns the switch on, it
  also means the Python chapter loop.

The snapshot is not rewritten. A `resumed` entry is appended to the run with
the time, the models, the orchestration and the ceiling, so the record says
what each segment ran under.

**Same quality.** The threshold of 8, the six characteristics, three attempts
and patch_then_halt come from the same code for a continued chapter as for a
new one. Chapters already promoted are not redone.

**The ceiling (as changed by the owner, §8).**
- Continue **never asks for a figure**, whatever the reason the run stopped
  (budget, absent spend, anything else).
- Each continuation runs under the profile's ceiling, fresh for that segment,
  recorded as `ceiling_by = 'profile'`. The modal shows it as information.
- **Per-novel cap (SR-05, the owner's "Tope automático por novela").** Once the
  novel's known spend reaches `budget.novel_ceiling_multiple` × the profile's
  ceiling (2 in the config), Continue is refused with that reason.

**Refusals, each with its reason on screen:**
- the run is complete (every unit done);
- the per-novel cap is reached;
- another run is live (as today: the queue is one);
- the run stopped on the 100k ceiling and the continuation would dispatch the
  same unit with the same packet. The panel says so and does not spend on a
  run that must halt again. The run becomes continuable when SPEC-EXAM-006 or
  a smaller packet changes that.

## 3. The bin (papelera)

- **Every novel** except a live one shows **"Move to bin"** (§8). It asks for
  one confirmation, and for a complete novel the confirmation names its
  versions.
- **What moves.** The run's row gets `trashed_at`, and its directory moves to
  `output/_papelera/<slug>/`. Nothing is deleted.
- **The library** hides binned runs from its list and its counts. A
  **"Bin (N)"** view lists them, each with **"Restore"**, which moves the
  directory back and clears `trashed_at`. The directory on disk keeps the name
  `output/_papelera/`; it is never shown in the interface.
- **Langfuse is not touched.** A binned novel's traces stay, because what it
  cost was spent.
- **Refused:** a live run only (§8). A complete novel can be binned; the PDFs
  already in `ejemplos/` are not touched.
- **Permanent deletion is out of scope.** The owner chose a recoverable bin.

## 4. Interfaces

| method | path | body | effect |
|---|---|---|---|
| POST | `/api/runs/{id}/resume` | — (no figure) | as today, plus §2: current models and orchestration, the profile's ceiling fresh for the segment, the per-novel cap, a `changes` row with `kind = 'continue'` |
| POST | `/api/runs/{id}/trash` | — | §3 |
| POST | `/api/runs/{id}/restore` | — | §3 |
| GET | `/api/runs?trashed=true` | — | the bin |

Migration 019 adds `runs.trashed_at` and the table `changes`, shared with
SPEC-EXAM-008. The original launch is `kind = 'generate'` and each
continuation is `kind = 'continue'`, with its time, models, orchestration and
ceiling. There is no `run_segments` table.

## 5. Acceptance criteria

| id | criterion | letter |
|---|---|---|
| AC-1 | A continued run launches with the profile's current `models.orchestrator` (a test pins `--model sonnet` for a run whose snapshot says null) and records the segment | T |
| AC-2 | Continue takes no figure. `--max-budget-usd` is the profile's ceiling for the segment, recorded as `ceiling_by = 'profile'`, also for a run stopped by `budget` or with absent spend. At `novel_ceiling_multiple` × that ceiling, Continue is refused with the reason | T |
| AC-3 | Promoted chapters are not redone after continuing (fake runner) | T |
| AC-4 | Trash and restore move the directory and back, byte-identical; the bin and the library counts are right | T |
| AC-5 | Trash refuses only a live run and bins a complete novel, naming its versions; resume refuses a complete run, a second live one and a novel at its cap, each with its reason | T |
| AC-6 | In the panel, in English: stopped cards show Continue and Move to bin, and complete ones show Move to bin. The Bin view restores. The Continue modal shows the ceiling and has no input. A stopped novel is never "Ready to read" (component tests) | T |
| AC-7 | **Demonstration:** the owner continues one stopped novel from the web, with its measured cost and minutes recorded in from-build.md | D |

## 6. Gaps

| gap | level | why accepted |
|---|---|---|
| A continued run mixes models across segments | incidental | recorded per segment; a reader of the record sees which chapters ran under which |
| Langfuse keeps a binned novel's traces | incidental | on purpose: cost spent is not undone by hiding a novel |
| No permanent deletion | incidental | the owner's choice |

## 7. Precisions from the build session's review against the code

Folded in after approval. They make §2–§4 implementable and do not change what
the owner approved.

1. **"Stopped" means units are missing, not a stage.** A run is stopped when
   `conductor.is_done` reports missing units and no process is live,
   whatever its `stage` says. The example novel stopped itself at 8/10 with
   `stage = complete`, and a rule by stage would never offer "Continuar" there.
   `resume` changes accordingly; a run with every unit done is refused as
   complete.
2. **The config for a segment** = the run's `config_snapshot` with `models` and
   `orchestration` overlaid from the profile as it is today, for this segment
   only. The snapshot row is not rewritten.
3. **Spent is the run's measured spend across all segments.** `ceiling_for`
   and `budget_left` start at 0 in every new process. "Profile ceiling minus
   spent" therefore subtracts the sum of the earlier segments' measured
   `result` costs.
4. **Storage.** Migration 019 adds `runs.trashed_at` and the table `changes`,
   shared with SPEC-EXAM-008, instead of the `run_segments` first proposed
   here.
   - The original launch is `kind = 'generate'`.
   - The hand-made `resume` block in the example novel's `cost.json` becomes a
     `kind = 'continue'` row.
5. **The 100k refusal.**
   - With `chapter_loop = python` the packet is measured before launch, so the
     check is exact.
   - With `claude` it is **estimated**: the measured start-up floor (~49k) plus
     bytes/4 of the unit's declared inputs. The panel says "estimated".
   - The continuation is refused only when the estimate exceeds 100,000 **and**
     the unit is the one that halted; otherwise it may continue.
6. **Bin edge cases.**
   - `unique_slug` also looks in `output/_papelera/`, so a new run never takes
     a binned run's slug.
   - `restore` refuses when `output/<slug>/` already exists, and says why.
   - A move that fails on Windows because a file is open returns a readable
     error, never a 500.
7. **Budget mapping.** A CLI `result` with subtype `error_max_budget_usd`
   must end as `runs.halted = 'budget'`, not `'process'`, or the panel never
   asks for a new ceiling. A test pins it.

## 8. Owner's changes after seeing it built (2026-09-24, ~21:45 UTC)

David Calderon, in chat to the coordinating session: "no me gusto lo del limite
de dinero quiero que nada mas sea continuar y que se gaste lo menos posible
tambien quiero que todas las novelas no solo las que les falta acabar acaben en
el bin". These replace the earlier choices in §2 and §3.

1. **Continue never asks for a figure.** The button continues. The owner's
   earlier choice, "Pedir un techo nuevo", is withdrawn.
   - The budget ceiling (AGENTS.md §6) is **not removed**: its mechanism stays
     as an automatic safety net and the owner does not type anything.
   - Each continuation gets the **profile's ceiling as a fresh ceiling for this
     segment**, recorded with `ceiling_by = 'profile'`.
   - This also applies to a run stopped by its budget and to a run whose spend
     is absent.
   - The modal shows the ceiling as information, not as a question.
   - Removing the ceiling altogether would change a protected value. It is not
     part of this change.
2. **"Lo menos posible."** A continuation always uses the cheapest current
   configuration (§2): Sonnet today, and the Python chapter loop as soon as
   SPEC-EXAM-006's AC-6 is measured and the owner turns it on. Promoted chapters
   are never redone.
3. **Every novel can go to the bin**, the complete ones included.
   - Only a live run is refused.
   - Restore works the same way.
   - Binning a complete novel moves its directory; the PDFs already copied to
     `ejemplos/` are not touched.
   - The confirmation for a complete novel names its versions ("v1, v2, v3
     will be moved to the bin"), so it is not moved by accident.

## 9. Order

After the v3, and after or beside SPEC-EXAM-006's code (both are $0 until
something real is launched). AC-7 costs money and waits for the owner's go and
his ceiling.
