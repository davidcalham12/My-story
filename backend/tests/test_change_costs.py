"""SPEC-EXAM-008 AC-1 and AC-2: what each change cost, written as each `result` arrives.

Nothing here launches `claude`. The service path is driven through the
conductor's process factory, the loop through its fake runner, the reader
change through an injected `regenerate` — each a stand-in with the stream shape
a real process leaves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.commons.config import loader
from backend.commons.config.settings import Settings
from backend.commons.db import repository as repo
from backend.costs import measure
from backend.costs import repository as costs
from backend.runs.service import RunService
from backend.tests.test_chapter_loop import run_dir  # noqa: F401 - the loop's fixture
from backend.tests.test_conductor import FakeProcess, turn

RUN_ID = "r008"
SLUG = "a-costed-novel"

OPUS = "claude-opus-5[1m]"
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5"


def init(model: str) -> dict:
    return {"type": "system", "subtype": "init", "model": model}


def result(total: float, by_model: dict[str, float] | None, *, ms: int = 60_000) -> dict:
    event = {"type": "result", "subtype": "success", "is_error": False,
             "total_cost_usd": total, "duration_ms": ms, "num_turns": 3}
    if by_model is not None:
        event["modelUsage"] = {k: {"costUSD": v, "canonicalModel": k.split("[")[0]}
                               for k, v in by_model.items()}
    return event


# ------------------------------------------------------------ the split (AC-1)


def test_split_by_role_the_main_model_is_the_orchestrator():
    got = measure.split(result(53.1745489, {OPUS: 48.7945489, HAIKU: 4.38}), OPUS)
    assert got.orchestrator_model == OPUS and got.agents_model == HAIKU
    assert got.orchestrator_usd == pytest.approx(48.7945489)
    assert got.agents_usd == pytest.approx(4.38)
    assert got.orchestrator_usd + got.agents_usd == pytest.approx(got.total_usd)
    assert got.minutes == pytest.approx(1.0)


def test_split_is_by_role_not_by_family():
    """A Haiku orchestrator is still the orchestrator; Opus under it is an agent."""
    got = measure.split(result(3.0, {HAIKU: 1.0, OPUS: 2.0}), HAIKU)
    assert got.orchestrator_model == HAIKU and got.orchestrator_usd == pytest.approx(1.0)
    assert got.agents_model == OPUS and got.agents_usd == pytest.approx(2.0)


def test_an_alias_from_the_model_flag_matches_its_resolved_key():
    got = measure.split(result(5.0, {SONNET: 4.0, HAIKU: 1.0}), "sonnet")
    assert got.orchestrator_model == SONNET and got.agents_usd == pytest.approx(1.0)


def test_no_main_model_means_every_model_is_an_agent():
    got = measure.split(result(0.05, {HAIKU: 0.05}), None)
    assert got.orchestrator_model is None and got.orchestrator_usd is None
    assert got.agents_usd == pytest.approx(0.05)


def test_a_result_without_model_usage_leaves_the_split_absent_not_zero():
    got = measure.split(result(0.4, None), OPUS)
    assert got.total_usd == pytest.approx(0.4)
    assert got.orchestrator_usd is None and got.agents_usd is None
    assert got.split is False


def test_the_meter_takes_the_main_model_from_init_then_the_flag_then_the_first_turn():
    meter = measure.Meter(configured="sonnet")
    meter.observe(init(OPUS))
    got = meter.observe(result(3.0, {OPUS: 2.0, HAIKU: 1.0}))
    assert got.orchestrator_model == OPUS, "init names the model the process really ran"

    meter = measure.Meter()
    meter.observe({"type": "assistant", "parent_tool_use_id": "toolu_x",
                   "message": {"model": HAIKU}})
    meter.observe({"type": "assistant", "parent_tool_use_id": None,
                   "message": {"model": SONNET}})
    got = meter.observe(result(3.0, {SONNET: 2.0, HAIKU: 1.0}))
    assert got.orchestrator_model == SONNET, "a subagent's turn is not the main model"


# --------------------------------------------------------- the row (AC-1, AC-2)


@pytest.fixture
def run(db):
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    return RUN_ID


def row(db, n: int) -> dict:
    return dict(db.execute("SELECT * FROM changes WHERE run_id = ? AND n = ?",
                           (RUN_ID, n)).fetchone())


def test_each_result_adds_to_its_change_as_it_arrives(db, run):
    n = costs.open_change(db, RUN_ID, kind="reader_change", version=3, chapters=[3, 10])
    costs.add_result(db, RUN_ID, n, measure.split(result(4.0, {SONNET: 3.5, HAIKU: 0.5}), SONNET),
                     source="dist/v3/logs/ch03.stream.jsonl")
    first = row(db, n)
    assert first["total_usd"] == pytest.approx(4.0), "written at the first result, not the end"
    costs.add_result(db, RUN_ID, n, measure.split(result(2.0, {SONNET: 1.5, HAIKU: 0.5}), SONNET),
                     source="dist/v3/logs/ch10.stream.jsonl")
    r = row(db, n)
    assert r["kind"] == "reader_change" and r["version"] == 3
    assert json.loads(r["chapters"]) == [3, 10]
    assert r["total_usd"] == pytest.approx(6.0) and r["minutes"] == pytest.approx(2.0)
    assert r["orchestrator_usd"] == pytest.approx(5.0) and r["agents_usd"] == pytest.approx(1.0)
    assert r["orchestrator_model"] == SONNET and r["agents_model"] == HAIKU
    assert r["provenance"] == "measured" and r["results"] == 2
    assert json.loads(r["sources"]) == ["dist/v3/logs/ch03.stream.jsonl",
                                        "dist/v3/logs/ch10.stream.jsonl"]


def test_a_change_whose_only_process_sent_no_result_is_absent_never_zero(db, run):
    n = costs.open_change(db, RUN_ID, kind="redo", version=3, chapters=[3])
    costs.add_missing(db, RUN_ID, n, 1)
    r = row(db, n)
    assert r["total_usd"] is None and r["minutes"] is None
    assert r["orchestrator_usd"] is None and r["agents_usd"] is None
    assert r["provenance"] == "absent"
    assert "incomplete: 1 process without a result" in r["note"]


def test_a_process_without_a_result_is_named_beside_the_ones_that_reported(db, run):
    n = costs.open_change(db, RUN_ID, kind="reader_change", version=3, chapters=[3, 10])
    costs.add_result(db, RUN_ID, n, measure.split(result(4.0, {SONNET: 3.5, HAIKU: 0.5}), SONNET))
    costs.add_missing(db, RUN_ID, n, 2)
    r = row(db, n)
    assert r["total_usd"] == pytest.approx(4.0), "what was measured stays; the gap is named"
    assert r["unresulted"] == 2
    assert "incomplete: 2 processes without a result" in r["note"]


def test_one_result_without_model_usage_makes_the_split_absent(db, run):
    n = costs.open_change(db, RUN_ID, kind="continue")
    costs.add_result(db, RUN_ID, n, measure.split(result(1.0, {OPUS: 0.9, HAIKU: 0.1}), OPUS))
    costs.add_result(db, RUN_ID, n, measure.split(result(0.4, None), OPUS))
    r = row(db, n)
    assert r["total_usd"] == pytest.approx(1.4)
    assert r["orchestrator_usd"] is None and r["agents_usd"] is None, \
        "a split that misses 0.40 would be read as the whole"


# ------------------------------------------------------ wired: the service path


def test_the_service_writes_each_result_as_it_arrives(db, tmp_path):
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    repo.halt(db, RUN_ID, "user", "halted by the user")
    run_dir = tmp_path / SLUG
    cfg = loader.resolve("tiny")
    from backend.runs import conductor as C
    for unit in C.units_for(cfg):
        if unit.key in ("chapter", "finish"):
            continue
        for rel in unit.outputs:
            (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (run_dir / rel).write_text("x", encoding="utf-8")

    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=False))
    seen: list[float | None] = []

    def factory(unit, prompt, budget_left=None):
        # What the row said when this unit launched: the earlier units' sum.
        last = db.execute("SELECT total_usd FROM changes WHERE run_id = ? ORDER BY n DESC",
                          (RUN_ID,)).fetchone()
        seen.append(last["total_usd"] if last else None)
        return FakeProcess([json.dumps(init(SONNET)), turn(900),
                            json.dumps(result(1.0, {SONNET: 0.75, HAIKU: 0.25}))],
                           writes={rel: "x" for rel in unit.outputs}, run_dir=run_dir)

    svc._conductor_factory = factory
    out = svc.resume(RUN_ID, _wait=True)

    r = row(db, out["segment"])
    units = len(seen)
    assert units >= 2
    assert seen[1] == pytest.approx(1.0), "the first unit's result was on the row before the second began"
    assert r["kind"] == "continue"
    assert r["total_usd"] == pytest.approx(1.0 * units)
    assert r["orchestrator_model"] == SONNET and r["agents_model"] == HAIKU
    assert r["orchestrator_usd"] == pytest.approx(0.75 * units)
    assert r["agents_usd"] == pytest.approx(0.25 * units)
    assert r["minutes"] == pytest.approx(1.0 * units), "Σ duration_ms, measured"
    assert r["provenance"] == "measured" and r["results"] == units


def test_a_unit_that_ends_without_a_result_is_counted(db, tmp_path):
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    repo.halt(db, RUN_ID, "user", "halted by the user")
    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=False))
    svc._conductor_factory = lambda unit, prompt, budget_left=None: FakeProcess(
        [json.dumps(init(SONNET)), turn(900)], run_dir=tmp_path / SLUG)
    out = svc.resume(RUN_ID, _wait=True)

    r = row(db, out["segment"])
    assert r["total_usd"] is None and r["provenance"] == "absent"
    assert r["unresulted"] == 1
    assert "incomplete: 1 process without a result" in r["note"]


# ------------------------------------------------------ wired: the python loop


def test_the_loop_has_no_orchestrator_its_processes_are_agents(db, run_dir):
    from backend.tests import test_chapter_loop as T

    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
               "started_at, source) VALUES (?, ?, 'p', 'eval', '{}', 'FLOW-4', "
               "'2026-09-24T00:00:00Z', 'v2')", (RUN_ID, T.SLUG))
    n = costs.open_change(db, RUN_ID, kind="generate", chapter_loop="python")
    runner = T.FakeRunner({"chapter-writer": [T.DRAFT, T.SUMMARY]}, cost=0.05)
    outcome = T.run(run_dir, runner, conn=db, run_id=RUN_ID, change=n)

    assert outcome.action == "accept"
    r = row(db, n)
    assert r["orchestrator_model"] is None and r["orchestrator_usd"] is None
    assert "no orchestrator (python loop)" in r["note"]
    assert r["agents_usd"] == pytest.approx(0.05 * len(runner.calls))
    assert r["total_usd"] == pytest.approx(0.05 * len(runner.calls))
    assert r["results"] == len(runner.calls)


def test_a_loop_process_that_sends_no_result_is_absent(db, run_dir):
    from backend.tests import test_chapter_loop as T

    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
               "started_at, source) VALUES (?, ?, 'p', 'eval', '{}', 'FLOW-4', "
               "'2026-09-24T00:00:00Z', 'v2')", (RUN_ID, T.SLUG))
    n = costs.open_change(db, RUN_ID, kind="generate", chapter_loop="python")
    class Silent:
        """A process killed before it could send its `result`."""
        def start(self): pass
        def lines(self): return iter(())
        def stop(self): pass

    outcome = T.run(run_dir, lambda call: Silent(), conn=db, run_id=RUN_ID, change=n)

    assert outcome.action == "halt"
    r = row(db, n)
    assert r["total_usd"] is None and r["provenance"] == "absent"
    assert r["unresulted"] == 1


# --------------------------------------------- wired: the reader change and redo


def _novel(db, tmp_path) -> Path:
    """A published run with fact 36 used by chapters 3 and 10."""
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    run_dir = tmp_path / SLUG
    (run_dir / "chapters").mkdir(parents=True)
    with db:
        db.execute("INSERT INTO facts (id, run_id, kind, text, source) VALUES "
                   "(36, ?, 'recipient', 'the cardboard observatory', 'brief')", (RUN_ID,))
        db.executemany("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) "
                       "VALUES (36, 1, ?, 'x')", [(3,), (10,)])
        db.execute("INSERT INTO versions (run_id, n, parent, reason, created_at) "
                   "VALUES (?, 1, NULL, 'first publication', '2026-09-24T10:00:00Z')",
                   (RUN_ID,))
    return run_dir


def _stand_in(db, costs_by_chapter: dict[int, float | None]):
    """A `regenerate` that records like `dispatch`: one process per chapter, its
    `result` added to the change it is handed; `None` sends no result."""
    calls: list[dict] = []

    def regenerate(run_dir, workspace, chapters, fact, to, *, change=None):
        calls.append({"chapters": chapters, "change": change})
        for c in chapters:
            meter = measure.Meter(configured="sonnet")
            events = [init(SONNET)]
            if costs_by_chapter.get(c) is not None:
                events.append(result(costs_by_chapter[c], {SONNET: costs_by_chapter[c] - 0.5,
                                                           HAIKU: 0.5}))
            costs.record_stream(db, RUN_ID, change, events, meter=meter,
                                source=f"{workspace.name}/logs/ch{c:02d}.stream.jsonl")
        return {c: False for c in chapters}           # the gate refuses: nothing publishes

    return regenerate, calls


def test_a_reader_change_opens_its_row_and_each_chapter_adds_to_it(db, tmp_path):
    from backend.versions import change

    _novel(db, tmp_path)
    regenerate, calls = _stand_in(db, {3: 4.24, 10: 4.57})
    change.main(["change", SLUG, "--fact", "36", "--to", "the wooden treehouse"],
                conn=db, output_dir=tmp_path, regenerate=regenerate)

    n = calls[0]["change"]
    assert n is not None, "the change's number is handed to every chapter process"
    r = row(db, n)
    assert r["kind"] == "reader_change" and r["version"] == 2
    assert json.loads(r["chapters"]) == [3, 10]
    assert r["total_usd"] == pytest.approx(8.81)
    assert r["orchestrator_usd"] == pytest.approx(7.81) and r["agents_usd"] == pytest.approx(1.0)
    assert r["finished_at"], "closed when the command ends, published or not"


def test_a_redo_is_its_own_row_on_the_same_version(db, tmp_path):
    from backend.versions import change

    run_dir = _novel(db, tmp_path)
    (run_dir / "dist" / "v2" / "chapters").mkdir(parents=True)
    (run_dir / "dist" / "v2" / "logs").mkdir(parents=True)
    (run_dir / "dist" / "v2" / "chapters" / "ch03.md").write_text("x", encoding="utf-8")
    (run_dir / "dist" / "v2" / "logs" / "ch03.stream.jsonl").write_text("{}\n", encoding="utf-8")
    regenerate, calls = _stand_in(db, {3: None})
    change.main(["change", SLUG, "--fact", "36", "--to", "the wooden treehouse",
                 "--workspace", "v2", "--only", "3"],
                conn=db, output_dir=tmp_path, regenerate=regenerate)

    r = row(db, calls[0]["change"])
    assert r["kind"] == "redo" and r["version"] == 2
    assert json.loads(r["chapters"]) == [3]
    assert r["total_usd"] is None and r["provenance"] == "absent"
    # The first pass's stream is set aside with its chapter, not overwritten.
    kept = list((run_dir / "dist" / "v2" / "chapters").glob("_redo-*/ch03.stream.jsonl"))
    assert kept, "the redo keeps the stream it would have overwritten"
