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
        if self.key == "cast":
            # The receipt is the unit's other half. The first resumed run
            # skipped `cast` on the strength of these three files while the
            # ingest into SQLite had never run, and the story bible — with
            # fact_usage, mandatory_facts and the Lean export on top of it —
            # was empty. A unit's contract is what it left behind, all of it.
            return ("bible/characters.md", "bible/timeline.md", "bible/mysteries.md",
                    "bible/.ingest.json")
        if self.key == "outline":
            return ("outline.md", "critiques/outline.audit.json")
        if self.key == "chapter":
            return (f"chapters/ch{self.chapter:02d}.md",
                    f"chapters/ch{self.chapter:02d}.summary.md")
        return ("dist/book.md", "synopsis.md")


def units_for(cfg: dict) -> list[Unit]:
    """The whole run, as processes, in `flow.yaml` order.

    The chapter count comes from the resolved config and never from a literal
    here: a number written in two places disagrees within a month.
    """
    chapters = int(cfg["novel"]["chapters"])
    return [Unit("world"), Unit("cast"), Unit("outline"),
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


ProcessFactory = Callable[[Unit, str], object]


@dataclass
class Conductor:
    """Drives the units of one run, one process at a time."""

    conn: sqlite3.Connection
    run_id: str
    slug: str
    run_dir: Path
    cfg: dict
    process_factory: ProcessFactory
    #: Called with each derived state so a caller can relay progress.
    on_event: Callable[[dict], None] | None = None
    #: Set by `run()` so whoever owns the conductor can stop the live child.
    process: object | None = None
    seq: int = 0

    def _spawn(self, unit: Unit) -> object:
        return self.process_factory(unit, prompt_for(unit, slug=self.slug, run_dir=self.run_dir))

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
            watcher = ContextWatcher(ceiling=ceiling, halt_on_orchestrator_turn=True)
            process = self._spawn(unit)
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


def real_process(run_dir: Path, *, cwd: Path, max_budget_usd: float | None,
                 model: str | None) -> ProcessFactory:
    """The factory the service uses: a real `claude -p` per unit."""

    def make(unit: Unit, prompt: str) -> RunProcess:
        return RunProcess.for_prompt(prompt=prompt, cwd=cwd,
                                     max_budget_usd=max_budget_usd, model=model)

    return make
