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


class NotLive(Exception):
    """A halt for a run that is not the one in flight, or is already over."""


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


def unique_slug(conn, base: str) -> str:
    """`base`, or `base-2`, `base-3`, … — the first one no run holds.

    `runs.slug` is UNIQUE and the fallback is the premise's first six words, so
    two premises that share them used to 500 (SPEC-010 W3). The learned slug
    still overwrites this one when the stream reveals it.
    """
    taken = {row[0] for row in conn.execute("SELECT slug FROM runs WHERE slug LIKE ?", (base + "%",))}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Live:
    run_id: str
    events: "queue.Queue[dict | None]" = field(default_factory=queue.Queue)
    done: bool = False
    result: str = ""
    process: object | None = None
    seq: int = 0  # the last stream line persisted to `events`; dense per run
    # Set by halt(): the user's reason wins over what the loop would otherwise
    # conclude from a stream that simply ended.
    halt_requested: tuple[str, str] | None = None


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
            slug = unique_slug(self.conn, slugify(premise))
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
        process = self._process(premise, profile, tone, cfg)
        live.process = process
        state = State()
        budget = self._budget_watcher(cfg)
        context = ContextWatcher(ceiling=cfg["context"]["max_concurrent_tokens"])
        halted: tuple[str, str] | None = None

        try:
            process.start()
            for raw, event in process.lines():
                # The stream is the record (FR-RNR-3). The raw line lands
                # before anything is derived from it: a crash between this
                # row and the stage it implies loses the derivation, never the
                # evidence.
                live.seq += 1
                write_repo.append_event(self.conn, live.run_id, seq=live.seq,
                                        type=str(event.get("type") or "unknown"),
                                        payload=raw)
                state = apply(state, event)
                self._record(live.run_id, state, event)
                live.events.put({
                    "stage": state.stage, "detail": state.headline,
                    "chapter": state.chapter, "attempt": state.attempt,
                    "agent": state.agent, "slug": state.slug,
                    "seq": live.seq,  # the SSE `id:` — which line produced this
                })
                try:
                    context.observe_event(event)
                    budget.observe(state)
                except WatchTripped as trip:
                    halted = (trip.kind, trip.detail)
                    process.stop()
                    break

            if live.halt_requested:
                # The stream ended because we ended it. Saying `process` here
                # would file the user's decision as the orchestrator's death.
                halted = live.halt_requested
            elif halted is None and not state.finished:
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

    def ceiling_for(self, cfg: dict) -> float:
        """The run's budget ceiling: the profile's figure, lowered — never raised
        — by `NOVAFORGE_BUDGET` when set (FR-BUD-4).

        Two lines of defence read this one number: `--max-budget-usd` on the
        `claude -p` argv and the `BudgetWatcher` on the stream. Two sources would
        mean two ceilings, and a run obeys whichever is smaller without saying so.
        """
        figure = float(cfg["budget"]["max_cost_usd"])
        env = self.settings.budget_ceiling_usd
        return figure if env is None else min(figure, env)

    def _budget_watcher(self, cfg: dict) -> BudgetWatcher:
        return BudgetWatcher(ceiling_usd=self.ceiling_for(cfg), pricing=loader.load_pricing())

    def _process(self, premise: str, profile: str, tone: str, cfg: dict):
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
            # The same figure the BudgetWatcher holds (ceiling_for).
            max_budget_usd=self.ceiling_for(cfg),
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
            # `task_progress` reports the subagent's `total_tokens` — input and
            # output together, the only per-subagent figure the CLI emits — not
            # the three input fields an orchestrator turn carries (SPEC-010 W2).
            from_total = size > 0 and "total_tokens" in usage and "input_tokens" not in usage
            write_call(self.conn, CallRow(
                run_id=run_id, stage=state.stage or "unknown",
                agent=str(event.get("subagent_type") or "unknown"),
                # There is no model id to record: the call went through the
                # Claude Code session, and naming a model would be inventing one.
                model="claude-code-session",
                ts=_now(), chapter=state.chapter, attempt=state.attempt,
                # `absent` rather than zero: a zero would say the packet was
                # tiny, which is a different claim from "not reported".
                input_tokens=size or None,
                output_tokens=int(usage.get("output_tokens") or 0) or None,
                provenance="measured" if size else "absent",
                note=("total_tokens: the subagent's whole usage, input and output "
                      "together, as the CLI reports it; an upper bound on the packet")
                     if from_total else None,
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

            # The parser skips a line it cannot read; the record says so. The
            # backend writes no log file, so the database is the log (P-8).
            for raw in getattr(live.process, "skipped", None) or []:
                write_repo.warn(self.conn, live.run_id, "malformed_line", raw)

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

    # ------------------------------------------------------------- halting

    def halt(self, run_id: str) -> None:
        """The user's halt (FR-RUN-5). The process is stopped and the run is
        marked `halted: user` through the same `_finish` the watchers use — the
        archive, the warnings and the sentinel that frees every follower are
        not special-cased for this reason any more than for `budget`."""
        self.get(run_id)  # NotFound if it never existed
        with self._lock:
            live = self._live
            if not live or live.run_id != run_id or live.done:
                raise NotLive(run_id)
            live.halt_requested = ("user", "halted by the user")
            process = live.process
        if process is not None:
            process.stop()

    def sweep_orphans(self) -> list[str]:
        """FR-RUN-7. A v2 run with no `finished_at` when the server starts has
        no process behind it — the one that had it died with the server. Mark
        it, or the panel shows a run that is still going, forever.

        Imported runs are left alone: `pre-loop003` history has no process and
        may honestly lack a finish time."""
        rows = self.conn.execute(
            "SELECT id FROM runs WHERE finished_at IS NULL AND source = 'v2'"
        ).fetchall()
        swept = [r["id"] for r in rows]
        for run_id in swept:
            write_repo.halt(self.conn, run_id, "process",
                            "found running at startup; the process is gone")
        return swept

    def _result_of(self, run_id: str) -> str:
        """What a run that is not live ended as, read from its row."""
        run = self.get(run_id)
        if run.get("halted"):
            return f"halted: {run['halted']}"
        if run.get("stage") == "complete":
            return "complete"
        # Neither: created and never swept. Only reachable between a start
        # and the next startup sweep; the old word, with the detail beside it.
        return "not live"

    # ----------------------------------------------------------- following

    def follow(self, run_id: str, after_seq: int | None = None) -> Iterator[dict]:
        """A snapshot from the database, the persisted lines after `after_seq`
        if a client says where it stopped (`Last-Event-ID`), then live events.

        Every live frame carries the `seq` of the line that produced it, so the
        client's `Last-Event-ID` is a row number in `events` and nothing has to
        be interpreted on either side.
        """
        yield {"event": "snapshot", "data": self.detail(run_id)}

        if after_seq is not None:
            for row in write_repo.events_after(self.conn, run_id, after_seq):
                yield {"event": "line", "id": row["seq"], "data": row}

        live = self._live
        if not live or live.run_id != run_id:
            # Not the run in flight: finished, halted, or swept. The panel does
            # setDetail() with this frame, so it carries the whole detail — the
            # two words alone broke the Run page on every finished run
            # (SPEC-010 W1).
            yield {"event": "done", "data": {"result": self._result_of(run_id), **self.detail(run_id)}}
            return
        if live.done:
            # A follower arriving after the end. The queue's sentinel was
            # consumed by whoever was following at the time; waiting on it
            # again used to block this reader forever.
            yield {"event": "done", "data": {"result": live.result, **self.detail(run_id)}}
            return

        while True:
            item = live.events.get()
            if item is None:
                break
            yield {"event": "progress", "id": item.get("seq"), "data": item}
        yield {"event": "done", "data": {"result": live.result, **self.detail(run_id)}}

    def stop(self, run_id: str) -> None:
        live = self._live
        if live and live.run_id == run_id and live.process is not None:
            live.process.stop()  # type: ignore[attr-defined]
