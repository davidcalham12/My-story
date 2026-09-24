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
from backend.commons.title import title_of
from backend.commons.config.settings import Settings
from backend.brief import domain as brief_domain
from backend.policy import forbidden
from backend.commons.db import repository as write_repo
from backend.commons.log import agent_usage
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
from backend.runs import conductor
from backend.runs import repository as read_repo
from backend.runs import conformance
from backend.runs.archive import archive_run


class AlreadyRunning(Exception):
    """A queue of one: a single `claude -p` alive at a time."""


class BriefNotReady(Exception):
    """The brief no longer passes FLOW-0, so no run is started.

    Free to refuse, expensive to discover halfway through a novel.
    """


class NotLive(Exception):
    """A halt for a run that is not the one in flight, or is already over."""


class NotFound(Exception):
    pass


class OrchestrationRefused(BriefNotReady):
    """The config asks for a combination that cannot run as asked (SPEC-EXAM-006
    AC-5d). A `BriefNotReady` so the router answers it as it answers any refusal
    to start: nothing was created, and the sentence says why."""


class Refused(Exception):
    """A continuation or a bin move that is not done, with the reason why.

    Every refusal carries a sentence the panel shows as it is (SPEC-EXAM-007
    §2, §3): a refusal the owner cannot read is a button that does nothing.
    """


class CeilingRequired(Exception):
    """A continuation that needs a ceiling in USD typed for it (SPEC-EXAM-007 §2).

    A run stopped by its budget, one with nothing left of its profile's
    ceiling, or one whose spend was never measured, does not start without one.
    """


#: Where a binned run's directory goes, under the output directory. Nothing in
#: it is deleted; `restore` moves it back (SPEC-EXAM-007 §3).
BIN = "_papelera"


def _move(src: Path, dst: Path) -> None:
    """A rename, never a copy: same volume, so it is all or nothing. On
    Windows it fails while a file inside is open, which is the case a readable
    refusal exists for."""
    src.rename(dst)


def slugify(premise: str) -> str:
    """A fallback only.

    The real slug is LEARNED from the `output/<slug>/` paths the run writes,
    because Claude Code derives it from the premise itself. Guessing it would
    open the wrong novel, or none.
    """
    words = re.sub(r"[^a-z0-9\s-]", "", premise.lower()).split()
    return "-".join(words[:6])[:40] or "untitled"


def unique_slug(conn, base: str, bin_dir: Path | None = None) -> str:
    """`base`, or `base-2`, `base-3`, … — the first one no run holds.

    `runs.slug` is UNIQUE and the fallback is the premise's first six words, so
    two premises that share them used to 500 (SPEC-010 W3). The learned slug
    still overwrites this one when the stream reveals it.
    """
    taken = {row[0] for row in conn.execute("SELECT slug FROM runs WHERE slug LIKE ?", (base + "%",))}
    # A binned run's directory keeps its name in the bin; a new run that took
    # it could never be restored beside it (SPEC-EXAM-007 §7.6).
    if bin_dir is not None and bin_dir.is_dir():
        taken |= {p.name for p in bin_dir.iterdir() if p.name.startswith(base)}
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
    #: The context watcher, so `_finish` can write down what it measured.
    context: object | None = None
    #: Under the conductor: the units that ran, and each one's largest turn.
    units: list[str] = field(default_factory=list)
    largest_turn: dict[str, int] = field(default_factory=dict)
    #: Which `changes` row (its `n`) this process is (SPEC-EXAM-007); None
    #: when the caller opened none.
    segment: int | None = None


class RunService:
    def __init__(self, conn: sqlite3.Connection, settings: Settings):
        self.conn = conn
        self.settings = settings
        self._live: Live | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------- reading

    def _titled(self, run: dict) -> dict:
        # The book's title for the panel, from the same place the PDF takes it.
        return run | {"title": title_of(self._dir_of(run))}

    def _dir_of(self, run: dict) -> Path:
        """Where the run's files are: its own directory, or the bin's."""
        out = Path(self.settings.output_dir)
        return (out / BIN if run.get("trashed_at") else out) / run["slug"]

    def list(self, trashed: bool = False) -> list[dict]:
        return [self._titled(r) | self._standing(r)
                for r in read_repo.list_runs(self.conn, trashed=trashed)]

    def get(self, run_id: str) -> dict:
        run = read_repo.get_run(self.conn, run_id)
        if not run:
            raise NotFound(run_id)
        return self._titled(run) | self._standing(run)

    # ------------------------------------------------ stopped (SPEC-EXAM-007)

    def _is_live(self, run_id: str) -> bool:
        live = self._live
        return bool(live and live.run_id == run_id and not live.done)

    def _snapshot(self, run_id: str) -> dict:
        row = self.conn.execute(
            "SELECT config_snapshot FROM runs WHERE id = ?", (run_id,)).fetchone()
        return json.loads(row["config_snapshot"] or "{}") if row else {}

    def _standing(self, run: dict) -> dict:
        """Whether the run can be continued, from where, and at what price.

        **Stopped means units are missing and no process is live** (§7.1), not
        a stage: the example novel stopped itself at 8/10 with `stage =
        complete`. A snapshot with no chapter count (imported history) has no
        units to ask about, and falls back to its row.
        """
        run_dir = self._dir_of(run)
        live = self._is_live(run["id"])
        snapshot = self._snapshot(run["id"])
        try:
            missing = conductor.first_missing(snapshot, run_dir)
            complete = missing is None
        except (KeyError, TypeError, ValueError):
            missing = None
            complete = run.get("stage") == "complete" and not run.get("halted")
        stopped = not live and not complete

        spent, provenance = _spent(self._segments(run["id"], run_dir))
        try:
            left = self._left(run, self._segment_config(run["profile"], snapshot), spent)
            asks, why = False, None
        except CeilingRequired as exc:
            left, asks, why = None, True, str(exc)

        return {
            "live": live,
            "complete": complete,
            "stopped": stopped,
            "resume_from": missing.name if stopped and missing else None,
            "resume_stage": missing.stage if stopped and missing else None,
            # Across every segment; None when any of them is unmeasured.
            "spent_usd": spent,
            "spent_provenance": provenance,
            "asks_for_figure": asks,
            "figure_reason": why,
            "ceiling_left_usd": left,
            "context_refusal": (self._context_refusal(run, snapshot, missing, run_dir)
                                if stopped else None),
        }

    def _context_refusal(self, run: dict, cfg: dict, unit, run_dir: Path) -> str | None:
        """§2 and §7.5: a unit that halted on the 100k ceiling, about to be sent
        a packet estimated over it again, is not continued.

        With `chapter_loop = claude` the packet cannot be measured before
        launch, so this is an **estimate** and says so. It refuses only for the
        unit that halted; any other unit may continue.
        """
        if run.get("halted") != "context" or unit is None:
            return None
        if not (run.get("halted_detail") or "").startswith(f"{unit.name}:"):
            return None
        ceiling = int(cfg["context"]["max_concurrent_tokens"])
        estimate = conductor.estimate_packet(unit, run_dir)
        if estimate <= ceiling:
            return None
        return (f"{unit.name} stopped on the {ceiling:,}-token ceiling and would be "
                f"sent the same packet again: estimated {estimate:,} tokens (the "
                f"~{conductor.STARTUP_FLOOR:,} a fresh orchestrator carries plus a "
                f"quarter of the bytes it reads). Continuing would spend on a run "
                f"that must stop again; it becomes continuable when the packet is "
                f"smaller.")

    def _segments(self, run_id: str, run_dir: Path) -> list[dict]:
        """The run's segments; for a run recorded before there were any, the
        ones its row and its `cost.json` imply, without writing them (§7.4)."""
        rows = read_repo.segments(self.conn, run_id)
        if rows:
            return rows
        run = self.conn.execute(
            "SELECT started_at, finished_at, cost_usd, cost_provenance, "
            "config_snapshot FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return []
        snapshot = json.loads(run["config_snapshot"] or "{}")
        first = {
            "n": 1, "kind": "generate",
            "started_at": run["started_at"], "finished_at": run["finished_at"],
            "orchestrator_model": (snapshot.get("models") or {}).get("orchestrator"),
            "chapter_loop": (snapshot.get("orchestration") or {}).get("chapter_loop") or "claude",
            "ceiling_usd": (snapshot.get("budget") or {}).get("max_cost_usd"),
            "ceiling_by": "profile",
            "total_usd": run["cost_usd"],
            "provenance": run["cost_provenance"] or (
                "absent" if run["cost_usd"] is None else "measured"),
            "note": "recorded at its first continuation, from the run's row",
        }
        try:
            on_disk = json.loads((run_dir / "cost.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            on_disk = {}
        resume = on_disk.get("resume")
        if isinstance(resume, dict) and isinstance(on_disk.get("first_run_usd"), (int, float)):
            # The example novel's hand-made resume block (docs/spec.md §8): its
            # first run and its second segment, each from its own result event.
            # What the second ran under was not recorded, so it stays NULL.
            first |= {"total_usd": float(on_disk["first_run_usd"]),
                      "provenance": "measured",
                      "note": "recorded at its first continuation, from cost.json's first_run_usd"}
            return [first, {
                "n": 2, "kind": "continue", "started_at": None, "finished_at": None,
                "orchestrator_model": None, "chapter_loop": "claude",
                "ceiling_usd": None, "ceiling_by": "owner",
                "total_usd": resume.get("total_cost_usd"),
                "provenance": resume.get("provenance") or "measured",
                "note": ("recorded afterwards from cost.json's hand-made resume block; "
                         "its start time, model and ceiling were not recorded, so "
                         "started_at is when this row was written"),
            }]
        if first["total_usd"] is None and isinstance(on_disk.get("total_cost_usd"), (int, float)):
            first |= {"total_usd": float(on_disk["total_cost_usd"]),
                      "provenance": on_disk.get("provenance") or "measured"}
        return [first]

    def _segment_config(self, profile: str, snapshot: dict) -> dict:
        """§7.2: the snapshot, with `models` and `orchestration` from the
        profile as it is today — for this segment only. Nothing is written."""
        cfg = json.loads(json.dumps(snapshot))
        try:
            today = loader.resolve(profile)
        except Exception:  # noqa: BLE001 - a profile that no longer exists
            return cfg
        for key in ("models", "orchestration"):
            if key in today:
                cfg[key] = today[key]
        return cfg

    def _left(self, run: dict, cfg: dict, spent: float | None) -> float:
        """What a continuation may spend when nobody types a figure (§2).

        The profile's ceiling minus what the run has spent across all its
        segments. A spend nobody measured cannot be subtracted — absent is not
        zero — so the panel asks for a figure instead.
        """
        if run.get("halted") == "budget":
            raise CeilingRequired(
                "this novel stopped on its budget ceiling; continuing needs a new "
                "ceiling in USD for this continuation")
        try:
            ceiling = self.ceiling_for(cfg)
        except (KeyError, TypeError, ValueError):
            raise CeilingRequired("this run's profile has no budget ceiling on "
                                  "record; type a ceiling in USD") from None
        if spent is None:
            raise CeilingRequired(
                f"what this novel has spent is not measured, so the profile's "
                f"ceiling of ${ceiling:.2f} cannot be reduced by it; type a "
                f"ceiling in USD")
        left = ceiling - spent
        if left <= 0:
            raise CeilingRequired(
                f"it has spent ${spent:.2f} of the profile's ceiling of "
                f"${ceiling:.2f}; nothing is left, so type a ceiling in USD")
        return left

    def detail(self, run_id: str) -> dict:
        return {
            "run": self.get(run_id),
            "attempts": read_repo.attempts_with_scores(self.conn, run_id),
            "cost": read_repo.cost(self.conn, run_id),
            "warnings": read_repo.warnings(self.conn, run_id),
            "completeness": read_repo.completeness(self.conn, run_id),
            # Measured, shown, never halted on (docs/spec.md §8).
            "orchestrator_context": read_repo.orchestrator_context(self.conn, run_id),
            # Did the run obey its own gate? Computed from the archive rather
            # than trusted, because the orchestrator writes both the record and
            # the decisions in it.
            "conformance": conformance.summary(self.conn, run_id),
        }

    # ------------------------------------------------------------ starting

    def brief_of(self, brief_id: str) -> "Brief":
        """The stored brief, or `NotFound`. Re-validated on the way out.

        It was checked before it was stored, so this cannot normally fail —
        which is exactly why it is worth doing. A payload that stopped parsing
        means the schema moved under a brief somebody is still waiting on, and
        finding that here beats finding it in the middle of a paid run.
        """
        row = self.conn.execute(
            "SELECT payload FROM briefs WHERE id = ?", (brief_id,)).fetchone()
        if row is None:
            raise NotFound(f"no brief {brief_id}")
        return brief_domain.parse(json.loads(row["payload"]))

    def start_from_brief(self, brief_id: str, profile: str,
                         chapters: int | None = None) -> dict:
        """The join: what was ordered becomes what is running.

        Three things travel, and each lands somewhere the rest of the pipeline
        already reads, rather than in a prompt nobody can check afterwards:

        - the **premise**, composed by `brief.domain.premise` — recipient,
          occasion, tone, traits, memories and the mandatory facts, and
          deliberately not the free text;
        - the **forbidden terms**, into `forbidden_words` at level `client`,
          which is the level 011_policy.sql reserves for a brief's own terms.
          A term that lived only in the writer's prompt is a term the writer
          sometimes still writes and nothing downstream notices;
        - the **facts**, into `facts` — the buyer's promises as `mandatory`
          rows the publish gate counts one by one, and the free text as a
          single `freetext` row that is a lead and never an instruction.

        The brief is re-checked first. A brief that no longer passes FLOW-0
        must not start a run: the run costs money and the refusal is free.
        """
        brief = self.brief_of(brief_id)
        verdict = brief_domain.check(json.loads(json.dumps(brief.model_dump())))
        if verdict.status != "ok":
            raise BriefNotReady(
                f"brief {brief_id} does not pass FLOW-0 ({verdict.status}); "
                "nothing is started")

        # The length is the buyer's, within what the profile was priced for:
        # its budget ceiling was sized for its own chapter count, and a longer
        # book under the same ceiling stops half-written (owner, 2026-09-24).
        # `chapters` is asked for explicitly by the panel; without it the
        # profile decides, which is what the eval harness relies on.
        priced_for = int(loader.resolve(profile)["novel"]["chapters"])
        if chapters is not None and not 1 <= chapters <= priced_for:
            raise BriefNotReady(
                f"a novel of {chapters} chapters: this profile writes between 1 "
                f"and {priced_for}; nothing is started")

        started = self.start(brief_domain.premise(brief), profile,
                             brief.tone or "", brief_id=brief_id, chapters=chapters)

        with self.conn:
            for term in brief.forbidden_terms:
                forbidden.add_term(self.conn, "client", term)
        write_repo.save_brief_facts(self.conn, started["id"],
                                    brief_domain.facts(brief))
        return started | {"brief_id": brief_id}

    def start(self, premise: str, profile: str, tone: str,
              brief_id: str | None = None, chapters: int | None = None) -> dict:
        with self._lock:
            if self._live and not self._live.done:
                raise AlreadyRunning("a run is already in flight; the queue is one")
            run_id = uuid.uuid4().hex[:12]
            slug = unique_slug(self.conn, slugify(premise),
                               bin_dir=Path(self.settings.output_dir) / BIN)
            cfg = loader.resolve(profile)
            refused = conductor.refusal(cfg, single=self.settings.single_orchestrator)
            if refused:
                raise OrchestrationRefused(refused)
            if chapters is not None:
                # Into the snapshot, which is what every stage reads.
                cfg["novel"]["chapters"] = chapters
            write_repo.create_run(
                self.conn, run_id=run_id, slug=slug, premise=premise, profile=profile,
                # None means the orchestrator reads the genre off the premise and
                # records what it decided. A default here would weld it shut.
                tone=tone.strip() or None, snapshot=cfg, brief_id=brief_id,
            )
            write_repo.save_skill_sha(self.conn, run_id, at_start=self._skill_sha())
            write_repo.open_change(
                self.conn, run_id, n=1, kind="generate", started_at=_now(),
                orchestrator_model=(cfg.get("models") or {}).get("orchestrator"),
                chapter_loop=(cfg.get("orchestration") or {}).get("chapter_loop") or "claude",
                ceiling_usd=self.ceiling_for(cfg), ceiling_by="profile")
            live = Live(run_id=run_id, segment=1)
            self._live = live

        threading.Thread(
            target=self._execute, args=(live, premise, profile, tone, cfg), daemon=True
        ).start()
        return {"id": run_id, "slug": slug}

    def _execute(self, live: Live, premise: str, profile: str, tone: str, cfg: dict) -> None:
        """Conduct the run, one fresh orchestrator per unit (SPEC-EXAM-003).

        The single process that used to write a whole novel carried the whole
        novel in its context. The conductor launches one per unit instead, so
        the 100,000 ceiling is a bound a run can actually keep.
        """
        if self.settings.use_recorded_stream:
            # The recording is one stream for a whole novel, so replaying it
            # through a conductor would be replaying a shape that no longer
            # exists. The fixture keeps testing the single-process path, which
            # is also the fallback, and `test_conductor.py` tests the other.
            return self._execute_single(live, premise, profile, tone, cfg)
        if self.settings.single_orchestrator:
            # The approved fallback (spec §8, Q29), taken on purpose.
            return self._execute_single(live, premise, profile, tone, cfg)

        self._conduct(live, cfg, self.get(live.run_id)["slug"])

    def resume(self, run_id: str, *, ceiling_usd: float | None = None,
               _wait: bool = False) -> dict:
        """Continue a run that stopped, in the directory it stopped in.

        The first real conductor run halted at `cast` with its four Bible files
        already on disk. Relaunching seemed like the way to continue and was
        not: `POST /api/runs` makes a **new** run, `unique_slug` gave it a `-2`,
        and the conductor looked into an empty directory and did the work again.
        Resume has to name the run that stopped.

        What makes this cheap is that nothing has to be remembered. The
        conductor asks the filesystem which units are done, so a resumed run is
        an ordinary run whose first units are already finished.

        SPEC-EXAM-007 adds what a continuation runs under: `models` and
        `orchestration` from the profile as it is today, for this segment only
        (§7.2), and a ceiling that is the owner's typed figure, or the profile's
        minus the measured spend (§2). Each continuation is a `changes` row of
        kind `continue`, in the table SPEC-EXAM-008 shares.
        """
        run = self.get(run_id)
        if run.get("trashed_at"):
            raise Refused(f"run {run_id} is in the bin; restore it before continuing it")
        if run["complete"]:
            raise NotLive(f"run {run_id} is complete: every unit's outputs are on "
                          "disk, so there is nothing to resume")
        with self._lock:
            if self._live and not self._live.done:
                raise AlreadyRunning("a run is already in flight; the queue is one")
            if run["context_refusal"]:
                raise Refused(run["context_refusal"])
            cfg = self._segment_config(run["profile"], self._snapshot(run_id))
            refused = conductor.refusal(cfg, single=self.settings.single_orchestrator)
            if refused:
                raise OrchestrationRefused(refused)
            prior = self._segments(run_id, self._dir_of(run))
            if ceiling_usd is not None:
                # The owner's figure for this continuation, lowered — never
                # raised — by NOVAFORGE_BUDGET, as the profile's is.
                env = self.settings.budget_ceiling_usd
                ceiling = float(ceiling_usd) if env is None else min(float(ceiling_usd), env)
                ceiling_by = "owner"
            else:
                ceiling = self._left(run, cfg, _spent(prior)[0])
                ceiling_by = "profile"

            if not read_repo.segments(self.conn, run_id):
                # Recorded before segments existed: write the ones its row and
                # its cost.json imply, so the record starts at its launch.
                for seg in prior:
                    write_repo.open_change(
                        self.conn, run_id,
                        **(seg | {"n": read_repo.last_change(self.conn, run_id) + 1,
                                  "started_at": seg["started_at"] or _now()}))
            n = read_repo.last_change(self.conn, run_id) + 1
            model = (cfg.get("models") or {}).get("orchestrator")
            write_repo.open_change(
                self.conn, run_id, n=n, kind="continue", started_at=_now(),
                orchestrator_model=model,
                chapter_loop=(cfg.get("orchestration") or {}).get("chapter_loop") or "claude",
                ceiling_usd=ceiling, ceiling_by=ceiling_by)
            # The halt being resumed past stops being the run's state. It stays
            # in `events` and in the warnings; the row says running.
            write_repo.reopen(self.conn, run_id)
            live = Live(run_id=run_id, segment=n)
            self._live = live

        args = (live, cfg, run["slug"], ceiling)
        if _wait:
            self._conduct(*args)
        else:
            threading.Thread(target=self._conduct, args=args, daemon=True).start()
        return {"id": run_id, "slug": run["slug"], "resumed": True, "segment": n,
                "ceiling_usd": ceiling, "ceiling_by": ceiling_by,
                "orchestrator_model": model}

    # -------------------------------------------------------------- the bin

    def trash(self, run_id: str) -> dict:
        """Move a stopped novel to the bin. Nothing is deleted (§3)."""
        run = self.get(run_id)
        if run.get("trashed_at"):
            raise Refused(f"run {run_id} is already in the bin")
        if run["live"]:
            raise Refused(f"run {run_id} is live; halt it before moving it to the bin")
        if run["complete"]:
            raise Refused(f"run {run_id} is a complete novel: a published book is not "
                          "a stopped novel, and removing one is a different decision")
        out = Path(self.settings.output_dir)
        _relocate(run["slug"], out / run["slug"], out / BIN / run["slug"],
                  f"{BIN}/{run['slug']}/ already exists in the bin; nothing was moved")
        write_repo.set_trashed(self.conn, run_id, True)
        return {"id": run_id, "trashed": True}

    def restore(self, run_id: str) -> dict:
        """Move a binned novel back where it was, and clear `trashed_at`."""
        run = self.get(run_id)
        if not run.get("trashed_at"):
            raise Refused(f"run {run_id} is not in the bin")
        out = Path(self.settings.output_dir)
        _relocate(run["slug"], out / BIN / run["slug"], out / run["slug"],
                  f"output/{run['slug']}/ already exists again; restoring would put "
                  "one novel on top of another, so nothing was moved")
        write_repo.set_trashed(self.conn, run_id, False)
        return {"id": run_id, "trashed": False}

    def _conduct(self, live: Live, cfg: dict, slug: str,
                 ceiling: float | None = None) -> None:
        """Drive the units of one run. Shared by `start` and `resume`.

        `ceiling` is this segment's; None means the profile's (`ceiling_for`).
        """
        ceiling = self.ceiling_for(cfg) if ceiling is None else ceiling
        budget = BudgetWatcher(ceiling_usd=ceiling, pricing=loader.load_pricing())
        state = State()
        halted: tuple[str, str] | None = None
        run_dir = Path(self.settings.output_dir) / slug

        def on_event(item: dict) -> None:
            nonlocal state
            state = item.pop("state")
            self._record(live.run_id, state, item.pop("event"))
            budget.observe(state)          # may raise; the conductor catches it
            live.events.put(item)

        factory = getattr(self, "_conductor_factory", None) or conductor.real_process(
            run_dir, cwd=Path(self.settings.repo_root),
            max_budget_usd=ceiling,
            model=(cfg.get("models") or {}).get("orchestrator"))

        maestro = conductor.Conductor(
            conn=self.conn, run_id=live.run_id, slug=slug, run_dir=run_dir,
            cfg=cfg, on_event=on_event, process_factory=factory,
            max_budget_usd=ceiling,
            seq=self._last_seq(live.run_id),
            chapter_loop=self._chapter_loop(live, run_dir, cfg),
        )
        live.process = maestro             # `halt` stops the unit in flight
        try:
            outcome = maestro.run()
            state, halted = outcome.state, outcome.halted
            live.units = [u.name for u in outcome.units_run]
            live.largest_turn = outcome.largest_turn
            if live.halt_requested:
                halted = live.halt_requested
        except Exception as exc:
            halted = ("interrupted", str(exc)[:500])
        finally:
            # The conductor names the directory, so here the slug is known
            # rather than learned; the cost and the archive need it either way.
            state.slug = state.slug or slug
            self._finish(live, state, halted)

    def _chapter_loop(self, live: Live, run_dir: Path, cfg: dict):
        """SPEC-EXAM-006: the Python loop for chapter units, or None on the
        default path. The conductor hands it what the run has left to spend."""
        if conductor.chapter_loop_mode(cfg) != "python":
            return None
        from backend.chapters import loop

        runner = getattr(self, "_loop_runner", None) or loop.real_runner(
            Path(self.settings.repo_root))

        stop = threading.Event()

        def run_one(n: int, left: float | None):
            return loop.run_chapter(run_dir, n, runner=runner, conn=self.conn,
                                    run_id=live.run_id, ceiling_usd=left, stop=stop)

        # `halt` reaches the conductor, and through this the loop's processes.
        run_one.stop = stop.set
        return run_one

    def _last_seq(self, run_id: str) -> int:
        """Where this run's stream got to, so a resumed one carries on counting.

        `seq` is what `Last-Event-ID` resumes from, so it is dense across the
        whole run — including the units a previous process wrote.
        """
        row = self.conn.execute(
            "SELECT MAX(seq) AS s FROM events WHERE run_id = ?", (run_id,)).fetchone()
        return int(row["s"] or 0)

    def _execute_single(self, live: Live, premise: str, profile: str, tone: str,
                        cfg: dict) -> None:
        """One orchestrator for the whole novel: the fallback, and what the
        recorded stream replays."""
        process = self._process(premise, profile, tone, cfg)
        live.process = process
        state = State()
        budget = self._budget_watcher(cfg)
        context = ContextWatcher(ceiling=cfg["context"]["max_concurrent_tokens"])
        live.context = context
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
                    before = context.turns_over_ceiling
                    context.observe_event(event)
                    if context.turns_over_ceiling > before == 0:
                        write_repo.warn_orchestrator_context(
                            self.conn, live.run_id,
                            turn_tokens=context.largest_orchestrator_turn,
                            ceiling=context.ceiling)
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
                # The CLI's own ceiling is a budget halt, or the panel never
                # asks for a new one (SPEC-EXAM-007 §7.7).
                kind = ("budget" if state.last_subtype == conductor.BUDGET_SUBTYPE
                        else "gate")
                halted = (kind, state.error)
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
            model=(cfg.get("models") or {}).get("orchestrator"),
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

        # One row per finished agent call, from the Agent tool's own result:
        # four usage figures, the resolved model, the duration; cost estimated
        # from config/pricing.json. `task_progress` gave one blended total and
        # no output, and is no longer written here (backend/commons/log/agent_usage.py).
        usage = agent_usage.from_event(event)
        if usage is not None:
            write_call(self.conn, agent_usage.row(
                run_id, state, usage, loader.load_pricing(), _now()))

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

            units = len(getattr(live, "units", []) or [])
            earlier: list[dict] = []
            if live.segment is not None:
                write_repo.close_change(
                    self.conn, live.run_id, live.segment, total_usd=state.total_cost_usd,
                    provenance=("absent" if state.total_cost_usd is None else
                                     "reconstructed" if state.results < units else
                                     "measured"))
                earlier = [seg for seg in read_repo.segments(self.conn, live.run_id)
                           if seg["n"] < live.segment]

            if state.total_cost_usd is not None:
                self._write_cost(state, units=units, earlier=earlier)

            # The parser skips a line it cannot read; the record says so. The
            # backend writes no log file, so the database is the log (P-8).
            for raw in getattr(live.process, "skipped", None) or []:
                write_repo.warn(self.conn, live.run_id, "malformed_line", raw)

            if live.context is not None:
                write_repo.save_orchestrator_context(
                    self.conn, live.run_id,
                    turns=live.context.orchestrator_turns,
                    largest=live.context.largest_orchestrator_turn,
                    over_ceiling=live.context.turns_over_ceiling)

            self._check_procedure_held(live)
            self._archive(live, state)
        except Exception as exc:  # noqa: BLE001 - see the docstring
            live.result = (live.result or "complete") + f" | bookkeeping failed: {exc!r}"
        finally:
            live.done = True
            live.events.put(None)

    def shutdown(self) -> None:
        """Stop the orchestrator this server owns, before the server goes.

        A server that is killed used to leave its `claude -p` running and
        spending, while the startup sweep wrote `halted: process` in the
        database — the row said the run was over while the process billed
        (verification.md §3.23, red-team case 9). Closing that hole is a
        hook, not a clever idea: whoever owns the child stops it.
        """
        live = self._live
        if live is None or live.done:
            return
        process = live.process
        if process is not None:
            process.stop()
        live.done = True
        try:
            write_repo.halt(self.conn, live.run_id, "process",
                            "the server stopped; its orchestrator was stopped with it")
        finally:
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

    def _write_cost(self, state: State, *, units: int = 0,
                    earlier: list[dict] | None = None) -> None:
        """The whole run's cost, orchestrator included, straight from Claude Code.

        This is the figure v1 could not see. Its absence is why a $6.21 estimate
        stood in for $49.33, and having it turns that gap from a hole into a
        datum — measured, not modelled.

        **Unless a unit is missing from it.** Under the conductor each unit
        sends its own `result`, and a unit the context or budget watcher stops
        is killed mid-turn and sends none. The sum is then every unit that
        finished and nothing for the one that did not, which is a real figure
        with a unit-shaped hole in it. That is `reconstructed`, not `measured`,
        and the count of silent units is written beside it so a reader can see
        how big the hole is rather than trusting a total that looks whole.
        """
        if not state.slug:
            return
        silent = max(0, units - state.results)
        path = Path(self.settings.output_dir) / state.slug / "cost.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        this = "measured" if not silent else "reconstructed"
        total, provenance, extra = state.total_cost_usd, this, {}
        if earlier:
            # A continued run: the total is every segment's, not this one's
            # (SPEC-EXAM-007 §7.3). A segment with no figure makes the total a
            # lower bound, and the grade says so rather than reading as whole.
            known = [seg["total_usd"] for seg in earlier if seg["total_usd"] is not None]
            total = state.total_cost_usd + sum(known)
            if len(known) < len(earlier) or any(
                    seg["provenance"] != "measured" for seg in earlier):
                provenance = "reconstructed"
            extra = {"segments": [
                *({"n": seg["n"], "kind": seg["kind"], "cost_usd": seg["total_usd"],
                   "provenance": seg["provenance"]} for seg in earlier),
                {"n": earlier[-1]["n"] + 1, "kind": "continue",
                 "cost_usd": state.total_cost_usd, "provenance": this},
            ]}
        path.write_text(json.dumps({
            "_comment": "From Claude Code's own result events, summed over the "
                        "run's units. The orchestrator turns are included — "
                        "which is most of it.",
            "total_cost_usd": total,
            "turns": state.turns,
            "duration_ms": state.duration_ms,
            "subagent_dispatches": len(state.dispatched),
            "units_run": units or None,
            "units_that_reported": state.results,
            "units_stopped_before_reporting": silent,
            "provenance": provenance,
            "_comment_provenance": None if not silent else (
                f"{silent} unit(s) were stopped mid-turn and sent no result, so "
                "their cost is in no record. This total is every unit that "
                "finished and nothing for the ones that did not — a lower bound, "
                "not the bill."),
            **extra,
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


def _relocate(slug: str, src: Path, dst: Path, exists: str) -> None:
    """Move a run's directory to or from the bin, or refuse with a reason."""
    if dst.exists():
        raise Refused(exists)
    if not src.exists():
        return  # a run that never wrote a file: only its row moves
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        _move(src, dst)
    except OSError as exc:
        raise Refused(
            f"could not move {slug}/: a file in it is open in another program "
            f"({exc.strerror or exc}). Close it and try again; nothing was moved."
        ) from exc


def _spent(segments: list[dict]) -> tuple[float | None, str]:
    """What a run has spent across its segments, and how that is known.

    None when any segment has no figure: a sum that skipped one would read as
    the whole bill, and absent is never zero.
    """
    if not segments or any(seg["total_usd"] is None for seg in segments):
        return None, "absent"
    measured = all(seg["provenance"] == "measured" for seg in segments)
    return (float(sum(seg["total_usd"] for seg in segments)),
            "measured" if measured else "reconstructed")
