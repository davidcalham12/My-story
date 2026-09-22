"""Starting and following a run. Knows nothing about HTTP.

**Claude Code orchestrates.** This launches it, reads its stream, persists what
it learns, and stops it when a watcher trips. It is what the four Vite plugins do
in v1, moved to Python with SQLite behind it.

There is no Anthropic SDK in this project and no `ANTHROPIC_API_KEY` anywhere.
The only access to a model is the user's Claude Code session on this machine.
"""

from __future__ import annotations

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
        if halted:
            write_repo.halt(self.conn, live.run_id, halted[0], halted[1])
            live.result = f"halted: {halted[0]}"
        else:
            write_repo.finish(self.conn, live.run_id)
            live.result = "complete"

        if state.total_cost_usd is not None:
            self._write_cost(state)

        live.done = True
        live.events.put(None)

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
