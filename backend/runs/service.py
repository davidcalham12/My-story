"""Starting and following a run. Knows nothing about HTTP."""

from __future__ import annotations

import queue
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from backend.commons.budget.ceiling import Budget
from backend.commons.config import loader
from backend.commons.config.settings import Settings
from backend.commons.context.semaphore import TokenSemaphore
from backend.commons.context.tokens import DeterministicCounter
from backend.commons.db import repository as write_repo
from backend.commons.llm.dispatch import Dispatcher
from backend.commons.llm.engine import MockEngine
from backend.runs import repository as read_repo
from backend.runs.orchestrator import Orchestrator, Progress


class AlreadyRunning(Exception):
    """A queue of one. Nothing here justifies a second worker."""


class NotFound(Exception):
    pass


def slugify(premise: str) -> str:
    words = re.sub(r"[^a-z0-9\s-]", "", premise.lower()).split()
    return "-".join(words[:6])[:40] or "untitled"


@dataclass
class Live:
    """A run in flight, and the queue its progress flows through."""

    run_id: str
    events: "queue.Queue[dict | None]" = field(default_factory=queue.Queue)
    done: bool = False
    result: str = ""


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
            # The genre is read off the premise unless one was given. No agent
            # declares one, and a default here would weld it shut again.
            decided = tone.strip() or "read the genre off the premise itself"
            write_repo.create_run(self.conn, run_id=run_id, slug=slug, premise=premise,
                                  profile=profile, tone=decided, snapshot=cfg)
            live = Live(run_id=run_id)
            self._live = live

        thread = threading.Thread(target=self._execute, args=(live, slug, premise,
                                                              profile, decided),
                                  daemon=True)
        thread.start()
        return {"id": run_id, "slug": slug}

    def _execute(self, live: Live, slug: str, premise: str, profile: str, tone: str) -> None:
        def on_progress(p: Progress) -> None:
            live.events.put({"stage": p.stage, "detail": p.detail, "chapter": p.chapter})

        try:
            dispatcher = Dispatcher(
                engine=self._engine(),
                semaphore=TokenSemaphore(
                    loader.resolve(profile)["context"]["max_concurrent_tokens"]),
                budget=Budget(ceiling_usd=self.settings.budget_ceiling_usd,
                              pricing=loader.load_pricing()),
                counter=DeterministicCounter(),
                conn=self.conn,
                run_id=live.run_id,
            )
            orchestrator = Orchestrator(
                conn=self.conn, dispatcher=dispatcher, run_id=live.run_id, slug=slug,
                premise=premise, profile=profile, tone=tone,
                workspace=Path(self.settings.output_dir) / slug,
                on_progress=on_progress,
            )
            live.result = orchestrator.run()
        except Exception as exc:  # the run dies; the record must not
            write_repo.halt(self.conn, live.run_id, "interrupted", str(exc)[:500])
            live.result = "halted: interrupted"
        finally:
            live.done = True
            live.events.put(None)

    def _engine(self):
        if self.settings.use_mock_engine:
            return MockEngine()
        key = self.settings.api_key
        if not key:
            raise RuntimeError(
                "the real engine needs ANTHROPIC_API_KEY in the environment; "
                "it is never read from a file or an argument"
            )
        from backend.commons.llm.engine import AnthropicEngine

        return AnthropicEngine(key)

    # ----------------------------------------------------------- following

    def follow(self, run_id: str) -> Iterator[dict]:
        """A snapshot from the database, then live events.

        The snapshot first is what makes a reconnection safe: the client never
        accumulates, so it cannot end up holding half a state. The stream is a
        view; the database is the record.
        """
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
        yield {"event": "done", "data": {"result": live.result,
                                         **self.detail(run_id)}}
