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
