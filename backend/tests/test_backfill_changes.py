"""SPEC-EXAM-008 AC-5: the backfill rebuilds each change's row from what is on disk.

Everything is copied into a tmp directory and a fresh in-memory database; the
real `novaforge.db` and `output/` are never opened. The resume stream is the
example novel's own, committed in this repository. The first run's `result`
lives only in the live database (events seq 2038), so it is given here in the
shape it has there, with the figures SPEC-EXAM-008 §1 measured from it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend.commons.db import repository as repo
from backend.costs import backfill

ROOT = Path(__file__).resolve().parents[2]
NOVEL = ROOT / "output" / "the-other-side-of-the-hill"
RUN_ID = "02412b7fe29e"
SLUG = "the-other-side-of-the-hill"

OPUS = "claude-opus-5[1m]"
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5"


def _result(total, by_model, ms=60_000, **extra) -> dict:
    return {"type": "result", "subtype": "success", "is_error": False,
            "total_cost_usd": total, "duration_ms": ms, "num_turns": 1,
            "modelUsage": {k: {"costUSD": v} for k, v in by_model.items()}, **extra}


def _stream(path: Path, model: str, *results: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [{"type": "system", "subtype": "init", "model": model}]
    lines += list(results)
    path.write_text("".join(json.dumps(l) + "\n" for l in lines), encoding="utf-8")


@pytest.fixture
def novel(db, tmp_path) -> Path:
    """The example novel's run: its first run in `events`, its resume on disk."""
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="exam", tone=None, snapshot={})
    first = [{"type": "system", "subtype": "init", "model": OPUS},
             {"type": "assistant", "message": {"model": OPUS, "content": []}},
             _result(53.174548899999984, {OPUS: 48.794548899999984, HAIKU: 4.38},
                     ms=7_118_940)]
    for seq, event in enumerate(first, start=2036):
        repo.append_event(db, RUN_ID, seq=seq, type=event["type"], payload=json.dumps(event))
    run_dir = tmp_path / SLUG
    (run_dir / "logs").mkdir(parents=True)
    shutil.copyfile(NOVEL / "logs" / "resume.stream.jsonl",
                    run_dir / "logs" / "resume.stream.jsonl")
    return run_dir


def _rows(db) -> list[dict]:
    return [dict(r) for r in db.execute(
        "SELECT * FROM changes WHERE run_id = ? ORDER BY n", (RUN_ID,))]


def test_the_example_novel_is_53_17_and_21_03_measured(db, novel):
    backfill.rebuild(db, novel, RUN_ID)

    rows = _rows(db)
    first, resume = rows[0], rows[1]
    assert (first["kind"], resume["kind"]) == ("generate", "continue")
    assert round(first["total_usd"], 2) == 53.17
    assert round(first["orchestrator_usd"], 2) == 48.79 and round(first["agents_usd"], 2) == 4.38
    assert first["orchestrator_model"] == OPUS and first["agents_model"] == HAIKU
    assert round(resume["total_usd"], 2) == 21.03
    assert round(resume["orchestrator_usd"], 2) == 19.34
    assert round(resume["agents_usd"], 2) == 1.69
    assert {first["provenance"], resume["provenance"]} == {"measured"}
    assert "events seq 2038" in json.loads(first["sources"])
    assert json.loads(resume["sources"]) == ["logs/resume.stream.jsonl"]
    assert round(first["total_usd"] + resume["total_usd"], 2) == 74.20


def test_the_backfill_is_idempotent(db, novel):
    backfill.rebuild(db, novel, RUN_ID)
    backfill.rebuild(db, novel, RUN_ID)
    assert [r["kind"] for r in _rows(db)] == ["generate", "continue"]


def test_it_fills_the_rows_spec_007_already_wrote_rather_than_adding(db, novel):
    repo.open_change(db, RUN_ID, n=1, kind="generate", started_at="2026-09-24T15:24:29Z",
                     ceiling_usd=60.0, ceiling_by="profile")
    repo.open_change(db, RUN_ID, n=2, kind="continue", started_at="2026-09-24T17:41:17Z",
                     ceiling_usd=21.83, ceiling_by="owner", total_usd=21.0301599,
                     provenance="measured", note="recorded afterwards from cost.json")
    backfill.rebuild(db, novel, RUN_ID)
    rows = _rows(db)
    assert [r["n"] for r in rows] == [1, 2]
    assert rows[1]["ceiling_by"] == "owner", "what 007 recorded is kept"
    assert round(rows[1]["orchestrator_usd"], 2) == 19.34


def test_versions_aborted_changes_and_redos(db, novel):
    dist = novel / "dist"
    # v3: the first pass wrote ch03 and ch10; ch03 was redone. The redo kept the
    # first pass's stream in the set-aside directory (the new `_set_aside`).
    _stream(dist / "v3" / "logs" / "ch10.stream.jsonl", SONNET,
            _result(4.5717264, {SONNET: 4.162, HAIKU: 0.4097264}))
    _stream(dist / "v3" / "chapters" / "_redo-20260924T212801Z" / "ch03.stream.jsonl", SONNET,
            _result(4.24, {SONNET: 3.88, HAIKU: 0.36}))
    (dist / "v3" / "chapters" / "_redo-20260924T212801Z" / "ch03.md").write_text("x", encoding="utf-8")
    _stream(dist / "v3" / "logs" / "ch03.stream.jsonl", SONNET,
            _result(1.4989115, {SONNET: 1.3374, HAIKU: 0.1615115}))
    # Cut by the org's spend limit: a version that never was.
    _stream(dist / "_aborted-change-2" / "logs" / "ch03.stream.jsonl", OPUS,
            _result(7.5226195, {OPUS: 6.6448, HAIKU: 0.8778195}, is_error=True))
    _stream(dist / "_aborted-change-2" / "logs" / "ch10.stream.jsonl", OPUS,
            _result(0, {}, ms=349, is_error=True))
    # The first demo, before streams were kept: nothing to read.
    (dist / "_aborted-change-1" / "chapters").mkdir(parents=True)

    backfill.rebuild(db, novel, RUN_ID)
    rows = {(r["kind"], r["version"], r["label"]): r for r in _rows(db)}

    v3 = next(r for (k, v, _), r in rows.items() if k == "reader_change" and v == 3)
    assert json.loads(v3["chapters"]) == [3, 10]
    assert round(v3["total_usd"], 2) == 8.81, "4.24 set aside + 4.57"
    redo = next(r for (k, v, _), r in rows.items() if k == "redo" and v == 3)
    assert json.loads(redo["chapters"]) == [3]
    assert round(redo["total_usd"], 2) == 1.50
    assert round(v3["total_usd"] + redo["total_usd"], 2) == 10.31

    cut = next(r for (k, _, label), r in rows.items() if label and "_aborted-change-2" in label)
    assert cut["kind"] == "reader_change" and cut["version"] is None
    assert round(cut["total_usd"], 2) == 7.52
    assert round(cut["orchestrator_usd"], 2) == 6.64

    demo = next(r for (k, _, label), r in rows.items() if label and "_aborted-change-1" in label)
    assert demo["total_usd"] is None and demo["provenance"] == "absent", "never 0"
    assert "no stream" in demo["note"]


def test_a_stream_the_redo_overwrote_before_it_was_kept_is_absent(db, novel):
    """Before this change a redo overwrote logs/chNN.stream.jsonl: the first
    pass's bill for that chapter is gone from disk (v3 ch03, 4.24 USD)."""
    dist = novel / "dist"
    _stream(dist / "v3" / "logs" / "ch10.stream.jsonl", SONNET,
            _result(4.5717264, {SONNET: 4.162, HAIKU: 0.4097264}))
    _stream(dist / "v3" / "logs" / "ch03.stream.jsonl", SONNET,
            _result(1.4989115, {SONNET: 1.3374, HAIKU: 0.1615115}))
    (dist / "v3" / "chapters" / "_redo-20260924T212801Z").mkdir(parents=True)
    (dist / "v3" / "chapters" / "_redo-20260924T212801Z" / "ch03.md").write_text("x", encoding="utf-8")

    backfill.rebuild(db, novel, RUN_ID)
    rows = _rows(db)
    v3 = next(r for r in rows if r["kind"] == "reader_change" and r["version"] == 3)
    assert round(v3["total_usd"], 2) == 4.57
    assert v3["unresulted"] == 1
    assert "incomplete: 1 process without a result" in v3["note"]
    assert "overwritten" in v3["note"]


def test_a_run_whose_process_never_sent_a_result_is_absent(db, tmp_path):
    """Eval 01: stopped with no `result`."""
    repo.create_run(db, run_id="eval01", slug="eval-01", premise="a premise long enough",
                    profile="eval", tone=None, snapshot={})
    repo.append_event(db, "eval01", seq=1, type="system",
                      payload=json.dumps({"type": "system", "subtype": "init", "model": OPUS}))
    (tmp_path / "eval-01").mkdir()
    backfill.rebuild(db, tmp_path / "eval-01", "eval01")
    r = db.execute("SELECT * FROM changes WHERE run_id = 'eval01'").fetchone()
    assert r["kind"] == "generate" and r["total_usd"] is None
    assert r["provenance"] == "absent" and r["unresulted"] == 1


def test_the_cli_dry_run_writes_nothing(db, novel, monkeypatch, capsys):
    monkeypatch.setattr(backfill, "_connect", lambda: db)
    assert backfill.main([str(novel), "--dry-run"]) == 0
    assert _rows(db) == []
    out = capsys.readouterr().out
    assert "53.17" in out and "21.03" in out


def test_a_version_the_run_published_itself_is_not_a_reader_change(db, novel):
    """dist/v2 of the example novel is the completed book (release --next after
    the resume), not a reader change: no stream, no redo, no row of its own."""
    (novel / "dist" / "v2").mkdir(parents=True, exist_ok=True)
    (novel / "dist" / "v2" / "novel.html").write_text("<html></html>", encoding="utf-8")
    labels = [p.label for p in backfill.plan(db, novel, RUN_ID)]
    assert "dist/v2" not in labels
