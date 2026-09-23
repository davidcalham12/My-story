"""The conductor: one fresh orchestrator per unit of work (SPEC-EXAM-003).

One process per novel accumulates the whole book in its context — a measured
median of 147,000 tokens and peaks of 642,000 — so a 100,000 ceiling applied to
it would halt every novel. The answer is not a bigger ceiling: it is to stop the
orchestrator accumulating. Python launches a **fresh** process per unit, hands it
paths and a procedure file, and reads the results off disk.

Nothing here talks to a model. Every test drives a fake process whose lines are
written by the test, which is the only way to assert what the conductor does
with a halt, a resume or a unit that never ends.
"""

import json

import pytest

from backend.commons.config import loader
from backend.commons.db import repository as repo
from backend.runs import conductor as C

SLUG = "a-novel"
RUN_ID = "r1"


class FakeProcess:
    """A `claude -p` that says what the test tells it to, and records that it ran."""

    def __init__(self, lines: list[str], *, writes: dict | None = None, run_dir=None):
        self._lines = lines
        self._writes = writes or {}
        self._run_dir = run_dir
        self.started = False
        self.stopped = False
        self.skipped: list[str] = []

    def start(self) -> None:
        self.started = True
        # A real unit writes its outputs before it ends; the conductor reads
        # them from disk, so the fake has to put them there too.
        for rel, body in self._writes.items():
            path = self._run_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    def lines(self):
        for raw in self._lines:
            yield raw, json.loads(raw)

    def events(self):
        for _, event in self.lines():
            yield event

    def stop(self) -> None:
        self.stopped = True

    @property
    def returncode(self):
        return 0

    def stderr_text(self) -> str:
        return ""


def result_line(ok: bool = True) -> str:
    return json.dumps({"type": "result", "subtype": "success" if ok else "error",
                       "total_cost_usd": 0.4, "num_turns": 3, "duration_ms": 1000})


def turn(tokens: int) -> str:
    """An orchestrator turn of a given size, in the shape the stream uses."""
    return json.dumps({"type": "assistant", "message": {
        "content": [{"type": "text", "text": "working"}],
        "usage": {"input_tokens": 2, "cache_creation_input_tokens": tokens - 2,
                  "cache_read_input_tokens": 0, "output_tokens": 1}}})


@pytest.fixture
def run(db, tmp_path):
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    (tmp_path / SLUG).mkdir(parents=True, exist_ok=True)
    return tmp_path / SLUG


# ------------------------------------------------------------- the sequence


def test_the_units_are_the_flow_in_order_with_one_per_chapter():
    """AC-1. Three chapters in `tiny`, so five stages become seven processes."""
    units = C.units_for(loader.resolve("tiny"))

    assert [u.key for u in units] == ["world", "cast", "outline",
                                      "chapter", "chapter", "chapter", "finish"]
    assert [u.chapter for u in units] == [None, None, None, 1, 2, 3, None]
    assert [u.name for u in units][:5] == ["world", "cast", "outline",
                                           "chapter 1", "chapter 2"]


def test_the_chapter_count_comes_from_the_profile_and_never_from_a_literal():
    assert sum(1 for u in C.units_for(loader.resolve("exam")) if u.key == "chapter") == 10
    assert sum(1 for u in C.units_for(loader.resolve("tiny")) if u.key == "chapter") == 3


def test_every_unit_names_a_procedure_file_that_exists(run):
    for unit in C.units_for(loader.resolve("tiny")):
        assert unit.procedure.is_file(), f"{unit.name}: {unit.procedure} is not there"


def test_a_unit_prompt_names_paths_and_the_procedure_never_contents(run):
    """§2: nothing is carried between units. A prompt that pasted the Bible in
    would put the book back in the context this whole change exists to empty."""
    unit = [u for u in C.units_for(loader.resolve("tiny")) if u.chapter == 2][0]
    (run / "bible").mkdir(exist_ok=True)
    (run / "bible" / "world.md").write_text("THE WORLD'S SECRET RULES", encoding="utf-8")

    prompt = C.prompt_for(unit, slug=SLUG, run_dir=run)

    assert "units/chapter.md" in prompt
    assert "chapter 2" in prompt.lower()
    assert str(run) in prompt or SLUG in prompt
    assert "THE WORLD'S SECRET RULES" not in prompt


# ------------------------------------------------------------------ resume


def test_a_unit_whose_outputs_exist_is_skipped(run):
    """AC-3. Checkpoint and resume, for free: the conductor asks the filesystem
    what has already been accepted rather than remembering it."""
    (run / "bible").mkdir(exist_ok=True)
    (run / "bible" / "world.md").write_text("# The world\n", encoding="utf-8")
    units = C.units_for(loader.resolve("tiny"))

    assert C.is_done(units[0], run) is True          # world
    assert C.is_done(units[1], run) is False         # cast, nothing written


def test_a_run_killed_after_chapter_three_resumes_at_chapter_four(tmp_path):
    run_dir = tmp_path / SLUG
    (run_dir / "chapters").mkdir(parents=True)
    (run_dir / "bible").mkdir()
    for name in ("world", "characters", "timeline", "mysteries"):
        (run_dir / "bible" / f"{name}.md").write_text("x", encoding="utf-8")
    # `cast` is not done until its ingest has run; the receipt says it did.
    (run_dir / "bible" / ".ingest.json").write_text('{"facts": 12}', encoding="utf-8")
    (run_dir / "outline.md").write_text("x", encoding="utf-8")
    (run_dir / "critiques").mkdir()
    (run_dir / "critiques" / "outline.audit.json").write_text("{}", encoding="utf-8")
    for n in (1, 2, 3):
        (run_dir / "chapters" / f"ch{n:02d}.md").write_text("x", encoding="utf-8")
        (run_dir / "chapters" / f"ch{n:02d}.summary.md").write_text("x", encoding="utf-8")

    todo = [u.name for u in C.units_for(loader.resolve("exam")) if not C.is_done(u, run_dir)]

    assert todo[0] == "chapter 4"
    assert "chapter 3" not in todo, "a finished chapter is never written twice"
    assert todo[-1] == "finish"


# ------------------------------------------------------------- driving them


def _conductor(db, run_dir, factory):
    return C.Conductor(conn=db, run_id=RUN_ID, slug=SLUG, run_dir=run_dir,
                       cfg=loader.resolve("tiny"), process_factory=factory)


def test_each_unit_gets_its_own_process_and_none_overlaps(db, run):
    """§2: the conductor never runs two units at once, and never reuses one
    process — a reused process is the accumulating context, back again."""
    made: list[FakeProcess] = []

    def factory(unit, prompt):
        alive = [p for p in made if p.started and not p.stopped]
        assert not alive, f"{unit.name} started while {len(alive)} were still alive"
        writes = {rel: "x" for rel in unit.outputs}
        p = FakeProcess([turn(1000), result_line()], writes=writes, run_dir=run)
        made.append(p)
        return p

    outcome = _conductor(db, run, factory).run()

    assert outcome.halted is None
    assert len(made) == 7 and all(p.started for p in made)
    assert [u.name for u in outcome.units_run] == [u.name for u in C.units_for(loader.resolve("tiny"))]


def test_a_units_halt_stops_the_sequence_and_names_the_unit(db, run):
    """A halt in unit three must not silently write chapters four to ten."""
    made = []

    def factory(unit, prompt):
        writes = {rel: "x" for rel in unit.outputs}
        lines = [turn(1000), result_line()]
        if unit.key == "outline":
            lines = [turn(400_000)]        # over the ceiling, and no result
            writes = {}
        p = FakeProcess(lines, writes=writes, run_dir=run)
        made.append(p)
        return p

    outcome = _conductor(db, run, factory).run()

    assert outcome.halted is not None
    kind, detail = outcome.halted
    assert kind == "context"
    assert "outline" in detail
    assert len(made) == 3, "world, cast, outline — and then it stopped"
    assert made[-1].stopped is True


def test_a_unit_that_ends_without_its_outputs_halts_rather_than_carrying_on(db, run):
    def factory(unit, prompt):
        return FakeProcess([turn(500), result_line()], writes={}, run_dir=run)

    outcome = _conductor(db, run, factory).run()

    assert outcome.halted is not None
    assert outcome.halted[0] == "process"
    assert "world" in outcome.halted[1]


# ------------------------------------------------------------- the evidence


def test_every_stream_line_lands_in_events_with_the_unit_that_produced_it(db, run):
    def factory(unit, prompt):
        return FakeProcess([turn(900), result_line()],
                           writes={rel: "x" for rel in unit.outputs}, run_dir=run)

    _conductor(db, run, factory).run()

    rows = db.execute("SELECT seq, unit FROM events WHERE run_id = ? ORDER BY seq",
                      (RUN_ID,)).fetchall()
    assert len(rows) == 14, "two lines per unit, seven units"
    assert [r["seq"] for r in rows] == list(range(1, 15)), "dense across units"
    assert rows[0]["unit"] == "world" and rows[-1]["unit"] == "finish"
    assert {r["unit"] for r in rows} == {"world", "cast", "outline",
                                         "chapter 1", "chapter 2", "chapter 3", "finish"}


# ------------------------------------------------------------ B4: orphans


def test_the_conductor_refuses_to_launch_while_its_child_is_alive(db, run):
    """§2, and red-team case 9. Two orchestrators of one run is how three
    processes billed for half an hour on 2026-09-23 after their servers died."""
    maestro = _conductor(db, run, lambda unit, prompt: FakeProcess([], run_dir=run))
    maestro.process = FakeProcess([], run_dir=run)      # one already in flight
    maestro.process.started = True

    with pytest.raises(RuntimeError, match="already"):
        maestro.run()


def test_stopping_the_conductor_stops_the_unit_in_flight(db, run):
    live = FakeProcess([turn(100)], run_dir=run)
    maestro = _conductor(db, run, lambda unit, prompt: live)
    maestro.process = live
    live.started = True

    maestro.stop()

    assert live.stopped is True


def test_stopping_the_service_stops_the_orchestrator_and_marks_the_run(db, tmp_path):
    """AC-4. A server that is killed used to leave its `claude -p` running and
    spending, while the startup sweep wrote `halted: process` in the database —
    the row said over while the process billed."""
    from backend.commons.config.settings import Settings
    from backend.runs.service import Live, RunService

    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=True))
    child = FakeProcess([], run_dir=tmp_path)
    child.started = True
    svc._live = Live(run_id=RUN_ID, process=child)

    svc.shutdown()

    assert child.stopped is True
    row = db.execute("SELECT halted, halted_detail FROM runs WHERE id = ?", (RUN_ID,)).fetchone()
    assert row["halted"] == "process"
    assert "server" in row["halted_detail"]


def test_a_chapter_unit_that_promoted_nothing_halts_the_run(db, run):
    """Red-team case 10, 2026-09-23. Under budget pressure the single
    orchestrator wrote three failing attempts at chapter 3, promoted none of
    them, and closed the run as `complete` — `patch_then_halt` never fired and
    `dist/` was empty. The conductor cannot do that: a chapter unit owes
    `chNN.md`, and a unit that ends without its outputs halts the sequence."""
    def factory(unit, prompt):
        if unit.chapter == 2:
            # Three attempts on disk and nothing promoted, exactly as it happened.
            writes = {f"chapters/ch02.attempt{k}.md": "a draft" for k in (1, 2, 3)}
        else:
            writes = {rel: "x" for rel in unit.outputs}
        return FakeProcess([turn(900), result_line()], writes=writes, run_dir=run)

    outcome = _conductor(db, run, factory).run()

    assert outcome.halted is not None, "a chapter nobody promoted must stop the book"
    kind, detail = outcome.halted
    assert kind == "process"
    assert "chapter 2" in detail and "ch02.md" in detail
    assert [u.name for u in outcome.units_run][-1] == "chapter 2", "chapter 3 was never written"


def test_the_conductor_prepares_the_workspace_before_the_first_unit(db, tmp_path):
    """The first real conductor run halted here, and the unit was right to stop:
    "I stopped before doing anything, because the unit's inputs are not on disk.
    The run directory named in my prompt does not exist."

    Under one orchestrator, §0 of the skill made the workspace. The conductor
    took §0 over (SPEC-EXAM-003 §2) and did not do this half of it. A unit is
    told to write into a directory; somebody has to have made it.
    """
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    run_dir = tmp_path / SLUG                      # deliberately absent
    maestro = C.Conductor(conn=db, run_id=RUN_ID, slug=SLUG, run_dir=run_dir,
                          cfg=loader.resolve("tiny"),
                          process_factory=lambda unit, prompt: FakeProcess([], run_dir=run_dir))

    maestro.prepare()

    assert run_dir.is_dir()
    for sub in ("bible", "chapters", "critiques", "logs", "dist"):
        assert (run_dir / sub).is_dir(), f"{sub}/ is where a unit is told to write"
    snapshot = json.loads((run_dir / "config.snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["novel"]["chapters"] == 3
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["slug"] == SLUG and state["stage"] == "FLOW-1"


def test_preparing_twice_does_not_overwrite_what_a_unit_wrote(db, tmp_path):
    """Resume calls it again: a snapshot rewritten from the unmerged config
    would throw away the genre unit U1 wrote into it (B1's report, item 3)."""
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    run_dir = tmp_path / SLUG
    maestro = C.Conductor(conn=db, run_id=RUN_ID, slug=SLUG, run_dir=run_dir,
                          cfg=loader.resolve("tiny"),
                          process_factory=lambda unit, prompt: FakeProcess([], run_dir=run_dir))
    maestro.prepare()
    edited = json.loads((run_dir / "config.snapshot.json").read_text(encoding="utf-8"))
    edited["novel"]["tone"] = "warm and funny"
    (run_dir / "config.snapshot.json").write_text(json.dumps(edited), encoding="utf-8")

    maestro.prepare()

    again = json.loads((run_dir / "config.snapshot.json").read_text(encoding="utf-8"))
    assert again["novel"]["tone"] == "warm and funny"


# --------------------------------------------------------------- resuming it


def test_resuming_continues_the_same_run_in_the_same_directory(db, tmp_path):
    """The first real conductor run halted at `cast` and its outputs were on
    disk. Relaunching started a *new* run — `unique_slug` gave it `-2`, so the
    directory was empty and the work was done again. Resume has to mean the run
    that stopped, not a new one that looks like it."""
    from backend.commons.config.settings import Settings
    from backend.runs.service import RunService

    cfg = loader.resolve("tiny")
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=cfg)
    repo.halt(db, RUN_ID, "context", "cast: a turn carried 100,669 tokens")
    run_dir = tmp_path / SLUG
    (run_dir / "bible").mkdir(parents=True)
    for name in ("world", "characters", "timeline", "mysteries"):
        (run_dir / "bible" / f"{name}.md").write_text("x", encoding="utf-8")
    (run_dir / "bible" / ".ingest.json").write_text('{"facts": 12}', encoding="utf-8")

    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=False))
    started: list = []
    svc._conductor_factory = lambda unit, prompt: started.append(unit.name) or FakeProcess(
        [turn(900), result_line()], writes={rel: "x" for rel in unit.outputs}, run_dir=run_dir)

    svc.resume(RUN_ID, _wait=True)

    assert started[0] == "outline", f"world and cast were done; it began at {started[0]}"
    assert "world" not in started and "cast" not in started
    row = db.execute("SELECT halted, stage FROM runs WHERE id = ?", (RUN_ID,)).fetchone()
    assert row["halted"] is None, "the halt that was resumed past is cleared"


def test_resuming_a_finished_run_is_refused(db, tmp_path):
    from backend.commons.config.settings import Settings
    from backend.runs.service import NotLive, RunService

    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    repo.finish(db, RUN_ID)
    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=False))

    with pytest.raises(NotLive):
        svc.resume(RUN_ID, _wait=True)


def test_the_cast_unit_owes_the_ingest_receipt_not_only_the_bible_files(db, run):
    """The first resumed run skipped `cast` because its four Markdown files
    were on disk — and the ingest into SQLite, which happens after them, had
    never run. The story bible was empty, and with it fact_usage,
    mandatory_facts and the Lean export. Files are not the whole unit."""
    cast = [u for u in C.units_for(loader.resolve("tiny")) if u.key == "cast"][0]

    assert "bible/.ingest.json" in cast.outputs

    (run / "bible").mkdir(exist_ok=True)
    for name in ("characters", "timeline", "mysteries"):
        (run / "bible" / f"{name}.md").write_text("x", encoding="utf-8")
    assert C.is_done(cast, run) is False, "the four files alone must not count as done"

    (run / "bible" / ".ingest.json").write_text('{"facts": 33}', encoding="utf-8")
    assert C.is_done(cast, run) is True


def test_the_ingest_leaves_the_receipt_the_contract_asks_for(db, tmp_path):
    from backend.bible import ingest

    repo.create_run(db, run_id="r9", slug="s9", premise="a premise long enough",
                    profile="tiny", tone=None, snapshot={})
    run_dir = tmp_path / "s9"
    (run_dir / "bible").mkdir(parents=True)
    (run_dir / "bible" / "world.md").write_text(
        "# The world\n\n## Rules\n\n- One rule.\n", encoding="utf-8")
    for name in ("characters", "timeline", "mysteries"):
        (run_dir / "bible" / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")

    ingest.ingest(db, run_dir)

    receipt = json.loads((run_dir / "bible" / ".ingest.json").read_text(encoding="utf-8"))
    assert receipt["run_id"] == "r9"
    assert receipt["facts"] >= 1 and "ts" in receipt
