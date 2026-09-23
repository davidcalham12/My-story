"""The orchestrator's own context: measured, reported, never a reason to halt.

`docs/spec.md` §8. The 100,000-token ceiling is about the packets the *agents*
receive. The orchestrator accumulates — it carries the Bible, the drafts, the
findings, turn after turn — and across two real runs its turns ran at a median
of 147,000 and a peak of 642,000. **Halting on those would halt every novel**,
which is why this figure is watched, written down and shown, and why nothing
here stops a run.

The ceiling itself does not move (`AGENTS.md` §6). What changes is that the
number stops living only in a watcher's memory for the length of one run.
"""

from pathlib import Path

import pytest

from backend.commons.db import repository as repo
from backend.commons.runner.process import ReplayProcess
from backend.commons.runner.watch import ContextWatcher

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "recorded-run.stream.jsonl"
CEILING = 100_000


@pytest.fixture
def watched() -> ContextWatcher:
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    watcher = ContextWatcher(ceiling=CEILING)
    for event in process.events():
        watcher.observe_event(event)  # must never raise on an orchestrator turn
    return watcher


def test_the_watcher_counts_the_turns_that_crossed_the_ceiling(watched):
    assert watched.largest_orchestrator_turn > CEILING
    assert watched.turns_over_ceiling >= 1
    assert watched.turns_over_ceiling <= watched.orchestrator_turns


def test_a_run_whose_orchestrator_crossed_the_ceiling_is_not_halted(watched):
    """The whole point. A watcher that counted these and stopped would have
    stopped every run this project has ever made."""
    assert watched.turns_over_ceiling >= 1  # it did cross
    # `observe_event` raised nothing above; the run is free to continue.


def test_the_three_figures_are_written_to_the_run(db):
    repo.create_run(db, run_id="r1", slug="s1", premise="a premise", profile="tiny",
                    tone=None, snapshot={})
    repo.save_orchestrator_context(db, "r1", turns=66, largest=182_964, over_ceiling=12)
    row = db.execute("SELECT orchestrator_turns, largest_orchestrator_turn, "
                     "orchestrator_turns_over_ceiling FROM runs WHERE id = 'r1'").fetchone()
    assert (row[0], row[1], row[2]) == (66, 182_964, 12)


def test_a_run_nobody_watched_has_no_figures_rather_than_zeroes(db):
    """Absent is not zero, and here the difference is the whole claim: 0 turns
    over the ceiling is a measurement, NULL is 'nobody looked'."""
    repo.create_run(db, run_id="r2", slug="s2", premise="a premise", profile="tiny",
                    tone=None, snapshot={})
    row = db.execute("SELECT orchestrator_turns, largest_orchestrator_turn, "
                     "orchestrator_turns_over_ceiling FROM runs WHERE id = 'r2'").fetchone()
    assert row[0] is None and row[1] is None and row[2] is None


def test_the_first_crossing_writes_one_warning_naming_the_figure(db):
    repo.create_run(db, run_id="r3", slug="s3", premise="a premise", profile="tiny",
                    tone=None, snapshot={})
    repo.warn_orchestrator_context(db, "r3", turn_tokens=182_964, ceiling=CEILING)
    repo.warn_orchestrator_context(db, "r3", turn_tokens=250_000, ceiling=CEILING)

    rows = db.execute("SELECT kind, detail FROM run_warnings WHERE run_id = 'r3'").fetchall()
    assert len(rows) == 1, "the first crossing, not every turn: one warning per run"
    kind, detail = rows[0][0], rows[0][1]
    assert kind == "orchestrator-context"
    assert "182,964" in detail and "100,000" in detail


def test_the_detail_payload_reports_them_as_measured(db, tmp_path):
    from backend.commons.config.settings import Settings
    from backend.runs.service import RunService

    repo.create_run(db, run_id="r4", slug="s4", premise="a premise", profile="tiny",
                    tone=None, snapshot={})
    repo.save_orchestrator_context(db, "r4", turns=66, largest=182_964, over_ceiling=12)
    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                                  use_recorded_stream=True))

    context = svc.detail("r4")["orchestrator_context"]

    assert context["turns"] == 66
    assert context["largest_turn_tokens"] == 182_964
    assert context["turns_over_ceiling"] == 12
    assert context["ceiling"] == CEILING
    assert context["provenance"] == "measured"


def test_a_run_without_the_figures_reports_them_absent(db, tmp_path):
    from backend.commons.config.settings import Settings
    from backend.runs.service import RunService

    repo.create_run(db, run_id="r5", slug="s5", premise="a premise", profile="tiny",
                    tone=None, snapshot={})
    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                                  use_recorded_stream=True))

    context = svc.detail("r5")["orchestrator_context"]

    assert context["provenance"] == "absent"
    assert context["turns"] is None and context["largest_turn_tokens"] is None
