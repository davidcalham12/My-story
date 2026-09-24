"""One fresh orchestrator per unit of work.

SPEC-EXAM-003. Until today a novel was one Claude Code conversation from the
first word of the world to the last page of the book, and its context grew with
the book: a measured median of 147,000 tokens and peaks of 642,000. The owner
requires that nothing in a run exceed 100,000 concurrent tokens, and the way to
satisfy that is not a bigger ceiling — it is to stop the orchestrator
accumulating.

So Python conducts. For each unit of work it launches a **new** `claude -p`,
hands it a short prompt naming a procedure file and some paths, lets it do that
one unit, and reads the results off disk. Each process starts clean; its context
is bounded by its unit rather than by the book.

**This module holds no stage logic** (AC-7). It knows the order of the units,
which files each one must leave behind, and how to tell whether a unit has
already been done. What a unit *does* is written in
`.claude/skills/storymaker/units/*.md`, read by Claude Code, exactly as the
procedure has always been written rather than coded.

Two things fall out of the shape and are worth naming, because they were
expensive to get any other way:

- **Resume is free.** A unit whose outputs are on disk is skipped, so a run that
  died at chapter four restarts at chapter four. Nothing has to be remembered.
- **The orphan hole closes.** There is one child at a time and the conductor
  owns it, so stopping the conductor stops the run (red-team case 9, 2026-09-23:
  three orchestrators billed for half an hour after their servers were killed).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from backend.chapters.loop import mode as chapter_loop_mode
from backend.commons.db import repository as write_repo
from backend.commons.runner.process import RunProcess
from backend.commons.runner.watch import ContextWatcher, State, WatchTripped, apply

ROOT = Path(__file__).resolve().parents[2]
PROCEDURES = ROOT / ".claude" / "skills" / "storymaker" / "units"


@dataclass(frozen=True)
class Unit:
    """One process's worth of work, and how to tell it was done."""

    key: str
    #: The chapter this unit writes, when it writes one.
    chapter: int | None = None

    @property
    def name(self) -> str:
        return f"chapter {self.chapter}" if self.chapter else self.key

    @property
    def procedure(self) -> Path:
        return PROCEDURES / f"{self.key}.md"

    @property
    def outputs(self) -> tuple[str, ...]:
        """The files this unit must leave behind, relative to the run directory.

        This is the unit's contract and the resume check at once. A unit that
        ends without them did not do its work, whatever its last line said.
        """
        if self.key == "world":
            return ("bible/world.md",)
        if self.key == "cast-characters":
            return ("bible/characters.md",)
        if self.key == "cast-chronology":
            # The receipt is this unit's other half. The first resumed run
            # skipped the whole cast on the strength of its Markdown while the
            # ingest into SQLite had never run, and the story bible — with
            # fact_usage, mandatory_facts and the Lean export on top of it —
            # was empty. A unit's contract is what it left behind, all of it,
            # and the ingest runs last, so the receipt belongs here.
            return ("bible/timeline.md", "bible/mysteries.md", "bible/.ingest.json")
        if self.key == "outline-write":
            return ("outline.md",)
        if self.key == "outline-audit":
            return ("critiques/outline.audit.json",)
        if self.key == "chapter":
            return (f"chapters/ch{self.chapter:02d}.md",
                    f"chapters/ch{self.chapter:02d}.summary.md")
        return ("dist/book.md", "synopsis.md")


def units_for(cfg: dict) -> list[Unit]:
    """The whole run, as processes, in `flow.yaml` order.

    The chapter count comes from the resolved config and never from a literal
    here: a number written in two places disagrees within a month.

    **Why FLOW-2 and FLOW-3 are two processes each.** The first conductor run
    measured what a fresh orchestrator carries before it reads anything:
    ~48,800 tokens, three times over (`novaforge-v2` domain-knowledge §8.8).
    Against a 100,000 ceiling that leaves a unit about 51,000 to work in, and
    `cast` ended at 100,669 and `outline` at 109,722. Three probes with
    fifteen, five and two tools all started at ~50,600, so the floor is not
    the tool list and a leaner prompt cannot buy the room back.

    The only lever left is a smaller unit, and its price is honest: each half
    re-pays the floor, so the split costs one more ~48,800-token arrival per
    stage and buys each half its own 51,000 to work in. It is worth paying
    exactly where a unit did not fit — which is these two, and not `world`,
    which finished at 82,686.
    """
    chapters = int(cfg["novel"]["chapters"])
    return [Unit("world"),
            Unit("cast-characters"), Unit("cast-chronology"),
            Unit("outline-write"), Unit("outline-audit"),
            *(Unit("chapter", n) for n in range(1, chapters + 1)),
            Unit("finish")]


def is_done(unit: Unit, run_dir: Path) -> bool:
    """Whether this unit's outputs are all on disk.

    The filesystem is the checkpoint. Asking it is what makes resume a property
    of the arrangement rather than a feature somebody has to maintain.
    """
    return all((run_dir / rel).is_file() for rel in unit.outputs)


def prompt_for(unit: Unit, *, slug: str, run_dir: Path) -> str:
    """The short prompt one unit gets.

    **Paths, never contents.** Pasting the Bible in here would put the book back
    into the context this whole design exists to empty, and it would do it
    invisibly, one unit at a time.
    """
    lines = [
        f"unit: {unit.name}",
        f"slug: {slug}",
        f"run directory: {run_dir}",
        f"procedure: .claude/skills/storymaker/units/{unit.key}.md",
        "",
        "Read that procedure and follow it for this unit only. Read only the",
        "files it names, under the run directory above. Write the outputs it",
        "names. Then end your turn — the conductor launches the next unit.",
        "",
        "Outputs this unit owes:",
        *(f"  {rel}" for rel in unit.outputs),
    ]
    if unit.chapter:
        lines.insert(1, f"chapter: {unit.chapter}")
    return "\n".join(lines) + "\n"


@dataclass
class Outcome:
    units_run: list[Unit] = field(default_factory=list)
    units_skipped: list[Unit] = field(default_factory=list)
    halted: tuple[str, str] | None = None
    state: State = field(default_factory=State)
    largest_turn: dict[str, int] = field(default_factory=dict)


def refusal(cfg: dict, *, single: bool) -> str | None:
    """The sentence a run is refused with, or None.

    The single orchestrator writes the whole novel in one process and has no
    chapter units to hand the loop. Ignoring the switch there would run a novel
    the owner asked to run otherwise, so the pair is refused before anything
    starts (SPEC-EXAM-006 §2, AC-5d).
    """
    if single and chapter_loop_mode(cfg) == "python":
        return ('orchestration.chapter_loop = "python" needs the conductor, and '
                "NOVAFORGE_ORCHESTRATOR=single runs the whole novel in one process with "
                "no chapter units to hand the loop; unset one of the two. Nothing was "
                "started.")
    return None


#: `(unit, prompt, budget_left)`. The third argument is what the **run** has
#: left to spend, not what the unit may have: a factory that makes a child has
#: to know what the child may spend, so the signature says so.
ProcessFactory = Callable[[Unit, str, "float | None"], object]


@dataclass
class Conductor:
    """Drives the units of one run, one process at a time."""

    conn: sqlite3.Connection
    run_id: str
    slug: str
    run_dir: Path
    cfg: dict
    process_factory: ProcessFactory
    #: The whole run's cost ceiling, shared out across the units rather than
    #: handed to each of them. `None` when the run has no ceiling.
    max_budget_usd: float | None = None
    #: Called with each derived state so a caller can relay progress.
    on_event: Callable[[dict], None] | None = None
    #: Set by `run()` so whoever owns the conductor can stop the live child.
    process: object | None = None
    seq: int = 0
    #: SPEC-EXAM-006: `(chapter, budget_left) -> chapters.loop.Outcome`. Used for
    #: chapter units only when the config's `orchestration.chapter_loop` is
    #: `"python"`; otherwise never called.
    chapter_loop: Callable[[int, "float | None"], object] | None = None
    #: What the loop's own processes cost. Their `result` events never reach this
    #: conductor's stream, and the run's ceiling has to count them.
    loop_spent: float = 0.0

    def _spawn(self, unit: Unit, budget_left: float | None) -> object:
        return self.process_factory(
            unit, prompt_for(unit, slug=self.slug, run_dir=self.run_dir), budget_left)

    def budget_left(self, spent: float | None) -> float | None:
        """What this run may still spend, for the child about to be launched.

        `--max-budget-usd` is a **per-process** flag: the CLI halts itself when
        its own bill crosses the figure on its own argv. Handing every unit the
        run's whole ceiling therefore handed a thirteen-unit run thirteen
        ceilings, which is not what the owner agreed to when they wrote one.

        So each child is launched with the remainder. The stream-side
        `BudgetWatcher` is still the line that binds — it stops mid-unit — and
        this makes the CLI's own halt agree with it instead of contradicting it
        twelve times over.
        """
        if self.max_budget_usd is None:
            return None
        return max(0.0, self.max_budget_usd - (spent or 0.0) - self.loop_spent)

    def prepare(self) -> None:
        """Make the workspace the units are told to write into.

        Under one orchestrator this was §0 of the skill. The conductor took §0
        over (SPEC-EXAM-003 §2) and the first real run found the half that had
        been dropped: unit U1 stopped without writing a word and said so —
        *"the run directory named in my prompt does not exist"* — which is
        exactly right. A unit is told where to write; somebody has to have made
        the place.

        Idempotent, because resume calls it again. In particular the snapshot
        is written **once**: U1 records the genre it chose in there, and
        rewriting it from the unmerged config would throw that away (nothing
        carries between units but disk).
        """
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("bible", "chapters", "critiques", "logs", "dist"):
            (self.run_dir / sub).mkdir(exist_ok=True)

        snapshot = self.run_dir / "config.snapshot.json"
        if not snapshot.is_file():
            snapshot.write_text(
                json.dumps(self.cfg, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")

        state = self.run_dir / "state.json"
        if not state.is_file():
            state.write_text(
                json.dumps({
                    "slug": self.slug,
                    "stage": "FLOW-1",
                    "chapters": [],
                    "_comment": "written by the conductor before the first unit; "
                                "the units keep it current",
                }, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")

    def run(self) -> Outcome:
        if self.process is not None:
            # Two orchestrators of one run is how three processes billed for
            # half an hour on 2026-09-23 after their servers were killed
            # (red-team case 9). One child, owned, at a time.
            raise RuntimeError("a unit of this run is already in flight")
        looped = chapter_loop_mode(self.cfg) == "python"
        if looped and self.chapter_loop is None:
            raise RuntimeError('orchestration.chapter_loop is "python" and no chapter '
                               "loop was handed to the conductor")
        self.prepare()
        outcome = Outcome()
        ceiling = int(self.cfg["context"]["max_concurrent_tokens"])

        for unit in units_for(self.cfg):
            if is_done(unit, self.run_dir):
                outcome.units_skipped.append(unit)
                continue

            # The ceiling binds here, and only here: a unit's context is
            # bounded by its unit, so a turn above 100,000 is a defect
            # rather than the ordinary weight of a long book.
            left = self.budget_left(outcome.state.total_cost_usd)
            if left is not None and left <= 0:
                outcome.halted = ("budget", f"{unit.name}: the run's ceiling of "
                                            f"${self.max_budget_usd:.2f} is spent")
                return outcome

            if looped and unit.key == "chapter":
                outcome.units_run.append(unit)
                result = self.chapter_loop(unit.chapter, left)
                self.loop_spent += float(getattr(result, "cost_usd", 0.0) or 0.0)
                halted = getattr(result, "halted", None)
                if halted is None and not is_done(unit, self.run_dir):
                    missing = [rel for rel in unit.outputs
                               if not (self.run_dir / rel).is_file()]
                    halted = ("process", f"ended without: {', '.join(missing)}")
                if halted:
                    outcome.halted = (halted[0], f"{unit.name}: {halted[1]}")
                    return outcome
                continue

            watcher = ContextWatcher(ceiling=ceiling, halt_on_orchestrator_turn=True)
            process = self._spawn(unit, left)
            self.process = process
            outcome.units_run.append(unit)
            halted: tuple[str, str] | None = None

            try:
                process.start()
                for raw, event in process.lines():
                    self.seq += 1
                    write_repo.append_event(self.conn, self.run_id, seq=self.seq,
                                            type=str(event.get("type") or "unknown"),
                                            payload=raw, unit=unit.name)
                    outcome.state = apply(outcome.state, event)
                    try:
                        watcher.observe_event(event)
                        if self.on_event:
                            # Inside the guard on purpose: the caller's budget
                            # watcher lives here and its trip must stop the unit.
                            self.on_event({"unit": unit.name, "seq": self.seq,
                                           "event": event,
                                           "state": outcome.state,
                                           "stage": outcome.state.stage,
                                           "detail": outcome.state.headline,
                                           "chapter": outcome.state.chapter,
                                           "attempt": outcome.state.attempt,
                                           "agent": outcome.state.agent,
                                           "slug": outcome.state.slug})
                    except WatchTripped as trip:
                        # Under one orchestrator this halt could never fire on
                        # the orchestrator's own turns without halting every
                        # novel. A unit's context is bounded, so now it can.
                        halted = (trip.kind, f"{unit.name}: {trip.detail}")
                        break
            finally:
                process.stop()
                self.process = None

            outcome.largest_turn[unit.name] = watcher.largest_orchestrator_turn

            if halted is None and not is_done(unit, self.run_dir):
                missing = [rel for rel in unit.outputs if not (self.run_dir / rel).is_file()]
                # The unit ended and its work is not there. Carrying on would
                # write chapter five on top of a chapter four that does not
                # exist, which is worse than stopping.
                halted = ("process",
                          f"{unit.name} ended without: {', '.join(missing)}")

            if halted:
                outcome.halted = halted
                return outcome

        return outcome

    def stop(self) -> None:
        """Stop whatever unit is in flight. The conductor owns exactly one."""
        process = self.process
        if process is not None:
            process.stop()
        stop_loop = getattr(self.chapter_loop, "stop", None)
        if stop_loop is not None:
            stop_loop()


def real_process(run_dir: Path, *, cwd: Path, max_budget_usd: float | None,
                 model: str | None) -> ProcessFactory:
    """The factory the service uses: a real `claude -p` per unit."""

    def make(unit: Unit, prompt: str, budget_left: float | None = None) -> RunProcess:
        # The remainder when the conductor knows it; the run's whole ceiling
        # only when there is nothing better, which is the old behaviour and is
        # wrong by exactly the amount the earlier units already spent.
        figure = max_budget_usd if budget_left is None else budget_left
        return RunProcess.for_prompt(prompt=prompt, cwd=cwd,
                                     max_budget_usd=figure, model=model)

    return make
