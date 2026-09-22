"""Starting and following a run. Knows nothing about HTTP.

**Claude Code orchestrates.** This launches it, reads its stream, persists what
it learns, and stops it when a watcher trips. It is what the four Vite plugins do
in v1, moved to Python with SQLite behind it.

There is no Anthropic SDK in this project and no `ANTHROPIC_API_KEY` anywhere.
The only access to a model is the user's Claude Code session on this machine.
"""

from __future__ import annotations

import hashlib
import json
import queue
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from backend.commons.config import loader
from backend.commons.config.settings import Settings
from backend.commons.db import repository as write_repo
from backend.commons.log.calls import CallRow, write_call
from backend.commons.runner.process import ReplayProcess, RunProcess
from backend.commons.runner.watch import (
    BudgetWatcher,
    ContextWatcher,
    State,
    WatchTripped,
    apply,
    context_size,
)
from backend.runs import repository as read_repo
from backend.runs import conformance
from backend.runs.archive import archive_run


class AlreadyRunning(Exception):
    """A queue of one: a single `claude -p` alive at a time."""


class NotFound(Exception):
    pass


def slugify(premise: str) -> str:
    """A fallback only.

    The real slug is LEARNED from the `output/<slug>/` paths the run writes,
    because Claude Code derives it from the premise itself. Guessing it would
    open the wrong novel, or none.
    """
    words = re.sub(r"[^a-z0-9\s-]", "", premise.lower()).split()
    return "-".join(words[:6])[:40] or "untitled"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Live:
    run_id: str
    events: "queue.Queue[dict | None]" = field(default_factory=queue.Queue)
    done: bool = False
    result: str = ""
    process: object | None = None


class RunService:
    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self.conn = conn
        self.settings = settings
        self._live: Live | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------- reading

    def list(self) -> list[dict]:
        return read_repo.list_runs(self.conn)

    def get(self, run_id: str) -> dict:
        run = read_repo.get_run(self.conn, run_id)
        if not run:
            raise NotFound(run_id)
        return run

    def detail(self, run_id: str) -> dict:
        return {
            "run": self.get(run_id),
            "attempts": read_repo.attempts_with_scores(self.conn, run_id),
            "cost": read_repo.cost(self.conn, run_id),
            "warnings": read_repo.warnings(self.conn, run_id),
            "completeness": read_repo.completeness(self.conn, run_id),
            # Did the run obey its own gate? Computed from the archive rather
            # than trusted, because the orchestrator writes both the record and
            # the decisions in it.
            "conformance": conformance.summary(self.conn, run_id),
        }

    # ------------------------------------------------------------ starting

    def start(self, premise: str, profile: str, tone: str) -> dict:
        with self._lock:
            if self._live and not self._live.done:
                raise AlreadyRunning("a run is already in flight; the queue is one")
            run_id = uuid.uuid4().hex[:12]
            slug = slugify(premise)
            cfg = loader.resolve(profile)
            write_repo.create_run(
                self.conn, run_id=run_id, slug=slug, premise=premise, profile=profile,
                # None means the orchestrator reads the genre off the premise and
                # records what it decided. A default here would weld it shut.
                tone=tone.strip() or None, snapshot=cfg,
            )
            write_repo.save_skill_sha(self.conn, run_id, at_start=self._skill_sha())
            live = Live(run_id=run_id)
            self._live = live

        threading.Thread(
            target=self._execute, args=(live, premise, profile, tone, cfg), daemon=True
        ).start()
        return {"id": run_id, "slug": slug}

    def _execute(self, live: Live, premise: str, profile: str, tone: str, cfg: dict) -> None:
        process = self._process(premise, profile, tone)
        live.process = process
        state = State()
        budget = BudgetWatcher(ceiling_usd=self.settings.budget_ceiling_usd,
                               pricing=loader.load_pricing())
        context = ContextWatcher(ceiling=cfg["context"]["max_concurrent_tokens"])
        halted: tuple[str, str] | None = None

        try:
            process.start()
            for event in process.events():
                state = apply(state, event)
                self._record(live.run_id, state, event)
                live.events.put({
                    "stage": state.stage, "detail": state.headline,
                    "chapter": state.chapter, "attempt": state.attempt,
                    "agent": state.agent, "slug": state.slug,
                })
                try:
                    context.observe_event(event)
                    budget.observe(state)
                except WatchTripped as trip:
                    halted = (trip.kind, trip.detail)
                    process.stop()
                    break

            if halted is None and not state.finished:
                # The process ended without a `result`. Whatever it wrote is on
                # disk and stays readable; it is not resumable, and resuming
                # would be a different run.
                halted = ("process", "the orchestrator ended without a result event")
            elif halted is None and state.error:
                halted = ("gate", state.error)
        except Exception as exc:
            halted = ("interrupted", str(exc)[:500])
        finally:
            self._finish(live, state, halted)

    def _process(self, premise: str, profile: str, tone: str):
        """The real `claude`, or the recorded stream that stands in for it.

        The recording covers the runner, the parser, the persistence, the SSE and
        both watchers at $0. What it cannot cover is the procedure in `SKILL.md`,
        and that is said here rather than blurred: testing the pipeline itself
        costs the subscription, every time.
        """
        if self.settings.use_recorded_stream:
            return ReplayProcess(fixture=Path(self.settings.recorded_stream))
        return RunProcess.for_run(
            premise=premise, profile=profile, tone=tone,
            cwd=Path(self.settings.repo_root),
        )

    def _record(self, run_id: str, state: State, event: dict) -> None:
        """Persist what the stream just revealed. After every event, not at the end."""
        if state.slug:
            with self.conn:
                self.conn.execute(
                    "UPDATE runs SET slug = ? WHERE id = ? AND slug != ?",
                    (state.slug, run_id, state.slug),
                )
        if state.stage:
            write_repo.set_stage(self.conn, run_id, state.stage)

        if event.get("type") == "system" and event.get("subtype") == "task_progress":
            raw = event.get("usage")
            usage = raw if isinstance(raw, dict) else {}
            size = context_size(usage)
            write_call(self.conn, CallRow(
                run_id=run_id, stage=state.stage or "unknown",
                agent=str(event.get("subagent_type") or "unknown"),
                # There is no model id to record: the call went through the
                # Claude Code session, and naming a model would be inventing one.
                model="claude-code-session",
                ts=_now(), chapter=state.chapter, attempt=state.attempt,
                # `absent` rather than zero. The stream has a slot for these and
                # in the recordings it reads empty; a zero would say the packet
                # was tiny, which is a different claim from "not reported".
                input_tokens=size or None,
                output_tokens=int(usage.get("output_tokens") or 0) or None,
                provenance="measured" if size else "absent",
            ))

    def _finish(self, live: Live, state: State, halted: tuple[str, str] | None) -> None:
        """Close the run, and **always** release whoever is following it.

        Everything between the halt and the `None` is bookkeeping — cost,
        fingerprint, archive, conformance — and every line of it was added after
        the SSE follower was written. **A failure in any of them used to hang
        every follower forever**, because the sentinel that ends the stream came
        last and never ran. A reader waiting on a finished run is worse than a
        missing figure: it looks like the run is still going.

        Found by adding one more bookkeeping step and watching the whole test
        suite stop. The `finally` is the fix; the individual `try`s inside are
        belt and braces.
        """
        try:
            if halted:
                write_repo.halt(self.conn, live.run_id, halted[0], halted[1])
                live.result = f"halted: {halted[0]}"
            else:
                write_repo.finish(self.conn, live.run_id)
                live.result = "complete"

            if state.total_cost_usd is not None:
                self._write_cost(state)

            self._check_procedure_held(live)
            self._archive(live, state)
        except Exception as exc:  # noqa: BLE001 - see the docstring
            live.result = (live.result or "complete") + f" | bookkeeping failed: {exc!r}"
        finally:
            live.done = True
            live.events.put(None)

    def _skill_sha(self) -> str | None:
        """A fingerprint of the procedure, taken at the start and at the end.

        `SKILL.md` **is** the pipeline — Annex C left one implementation of it —
        and it is a file anyone can edit while a run is in flight. That happened:
        a sixth characteristic was added during an eight-chapter run, so its
        first chapters were judged by five and the rest by six. Nothing noticed,
        because the config was snapshotted per run and the procedure was not.
        """
        path = (Path(self.settings.repo_root)
                / ".claude/skills/novaforge/SKILL.md")
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        except OSError:
            # Absent, not "unchanged". A missing fingerprint must not read as a
            # matching one.
            return None

    def _check_procedure_held(self, live: Live) -> None:
        after = self._skill_sha()
        write_repo.save_skill_sha(self.conn, live.run_id, at_end=after)
        row = self.conn.execute(
            "SELECT skill_sha_at_start FROM runs WHERE id = ?", (live.run_id,)
        ).fetchone()
        before = row["skill_sha_at_start"] if row else None
        if before and after and before != after:
            write_repo.warn(
                self.conn, live.run_id, "procedure-changed",
                f"SKILL.md changed while this run was in flight "
                f"({before} → {after}). Its early chapters and its late ones were "
                f"not necessarily produced by the same procedure, so this run is "
                f"not a clean sample of either.",
            )

    def _archive(self, live: Live, state: State) -> None:
        """Read the run's own record off disk into the database. SPEC-003.

        The orchestrator writes the gate's record to files; nothing read them
        back, so the first real run finished with `attempts`, `scores`,
        `findings`, `gate_decisions` and `sheets` empty while every one of those
        facts sat in `output/<slug>/`.

        **A failure here never fails the run.** The novel is on disk either way,
        and an archiver that could destroy a finished run would be worse than no
        archiver. It becomes a warning, which is a row a reader can act on.
        """
        if not state.slug:
            return
        run_dir = Path(self.settings.output_dir) / state.slug
        if not run_dir.is_dir():
            return
        sheets = Path("specs/loops/LOOP-003/sheets") / state.slug
        try:
            report = archive_run(self.conn, live.run_id, run_dir,
                                 sheets_dir=sheets if sheets.is_dir() else None)
        except Exception as exc:  # noqa: BLE001 - see the docstring
            write_repo.warn(self.conn, live.run_id, "archive",
                            f"archiving failed, the run's files are intact: {exc!r}")
            return

        # Did it obey its own gate? Asked the moment the run ends, because the
        # alternative signal — reading a book with a bad chapter in it — arrives
        # far too late to act on. A breach is a warning, not a crash: the run is
        # already over and the files are already written.
        for breach in conformance.audit(self.conn, live.run_id):
            write_repo.warn(self.conn, live.run_id, "gate-breach", str(breach),
                            chapter=breach.chapter)
        self._write_conformance(live, state)

        # `result` stays `complete` or `halted: x`. It is the run's outcome, not
        # a place to report bookkeeping, and a reader parsing it should not have
        # to know about the archive.
        if not report.attempts and any((run_dir / "chapters").glob("ch*.md")):
            write_repo.warn(
                self.conn, live.run_id, "archive",
                "chapters were written but no attempt drafts were found to "
                "archive; the gate's record is missing, which is not the same "
                "as a run that had no attempts",
            )

    def _write_conformance(self, live: Live, state: State) -> None:
        """The audit, written beside the book it is about.

        The database has it, and the database is on one machine. **A novel gets
        copied, attached, read somewhere else** — and a book that failed its gate
        on two chapters should not travel without saying so. The evidence goes
        with the artefact or it is evidence nobody has.
        """
        if not state.slug:
            return
        path = Path(self.settings.output_dir) / state.slug / "conformance.json"
        if not path.parent.is_dir():
            return
        try:
            summary = conformance.summary(self.conn, live.run_id)
            path.write_text(json.dumps({
                "_comment": "Recomputed from this run's own record: what the gate "
                            "decided, against the rule it was supposed to follow. "
                            "`breached` means a chapter entered this book that "
                            "should not have.",
                **summary,
            }, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 - the run is over; never fail it
            try:
                write_repo.warn(self.conn, live.run_id, "conformance",
                                f"could not write conformance.json: {exc!r}")
            except Exception:
                # The handler must not become the failure. A warning that cannot
                # be written is still better than a follower that never returns.
                pass

    def _write_cost(self, state: State) -> None:
        """The whole run's cost, orchestrator included, straight from Claude Code.

        This is the figure v1 could not see. Its absence is why a $6.21 estimate
        stood in for $49.33, and having it turns that gap from a hole into a
        datum — measured, not modelled.
        """
        if not state.slug:
            return
        path = Path(self.settings.output_dir) / state.slug / "cost.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "_comment": "From Claude Code's own result event. The WHOLE run, "
                        "orchestrator turns included — which is most of it.",
            "total_cost_usd": state.total_cost_usd,
            "turns": state.turns,
            "duration_ms": state.duration_ms,
            "subagent_dispatches": len(state.dispatched),
            "provenance": "measured",
        }, indent=2) + "\n", encoding="utf-8")

    # ----------------------------------------------------------- following

    def follow(self, run_id: str) -> Iterator[dict]:
        """A snapshot from the database, then live events."""
        yield {"event": "snapshot", "data": self.detail(run_id)}

        live = self._live
        if not live or live.run_id != run_id:
            yield {"event": "done", "data": {"result": "not live"}}
            return

        while True:
            item = live.events.get()
            if item is None:
                break
            yield {"event": "progress", "data": item}
        yield {"event": "done", "data": {"result": live.result, **self.detail(run_id)}}

    def stop(self, run_id: str) -> None:
        live = self._live
        if live and live.run_id == run_id and live.process is not None:
            live.process.stop()  # type: ignore[attr-defined]
