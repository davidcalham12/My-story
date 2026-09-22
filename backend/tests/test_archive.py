"""SPEC-003 — a finished run's record reaches the database.

Against `output/lighthouse-keeper-ledger/`, v2's first real run and the only one
that has ever carried five characteristics. It reads files, so it costs $0.

The run that motivated this spec finished three chapters, eight drafts and four
feedback sheets, and left `attempts`, `scores`, `findings`, `gate_decisions` and
`sheets` **empty**. Everything was on disk. `save_attempt`, `save_gate` and
`save_sheet` existed and were called by nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.commons.db import repository
from backend.runs.archive import archive_run

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "output/lighthouse-keeper-ledger"
SHEETS = ROOT / "specs/loops/LOOP-003/sheets/lighthouse-keeper-ledger"
RUN_ID = "test-run"


@pytest.fixture
def archived(db):
    repository.create_run(
        db,
        run_id=RUN_ID,
        slug="lighthouse-keeper-ledger",
        premise="a premise",
        profile="tiny",
        tone=None,
        snapshot="{}",
    )
    report = archive_run(db, RUN_ID, RUN_DIR, sheets_dir=SHEETS)
    return db, report


def drafts_on_disk() -> list[tuple[int, int]]:
    """(chapter, attempt) for every attempt draft the run kept."""
    out = []
    for p in sorted((RUN_DIR / "chapters").glob("ch*.attempt*.md")):
        stem = p.stem  # ch01.attempt2
        chapter = int(stem.split(".")[0][2:])
        attempt = int(stem.split("attempt")[1])
        out.append((chapter, attempt))
    return out


def test_every_attempt_on_disk_becomes_a_row(archived):
    db, _ = archived
    rows = {
        (r["chapter"], r["attempt"])
        for r in db.execute("SELECT chapter, attempt FROM attempts WHERE run_id = ?",
                            (RUN_ID,))
    }
    assert rows == set(drafts_on_disk())
    # Seven drafts over three chapters: 2, 3, 2. Not eight — chapter 1's third
    # `science` iteration is a rescore of the second draft, not a third draft.
    assert len(rows) == 7, sorted(rows)


def test_each_attempt_carries_five_scores(archived):
    db, _ = archived
    for row in db.execute("SELECT id, chapter, attempt FROM attempts WHERE run_id = ?",
                          (RUN_ID,)):
        n = db.execute(
            "SELECT COUNT(*) AS n FROM scores WHERE attempt_id = ?", (row["id"],)
        ).fetchone()["n"]
        assert n == 5, f"ch{row['chapter']} attempt {row['attempt']} has {n} scores"


def test_a_score_the_run_never_produced_is_null_not_zero(db):
    """The rule the whole gate rests on, at the archive's edge.

    A characteristic with no usable verdict is NULL. Storing 0 invents a
    rejection and storing 10 invents an approval; a v1 run once did the second
    and a malformed reply silently passed a draft.
    """
    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    attempt_id = repository.save_attempt(
        db, run_id="r", chapter=1, attempt=1, title=None,
        draft_path="chapters/ch01.attempt1.md", words=100,
        scores={"continuity": 9, "science": None, "outline": 9,
                "length": 10, "chatter": 10},
        verdict="retry", aggregate=9, findings=[],
    )
    row = db.execute(
        "SELECT score FROM scores WHERE attempt_id = ? AND characteristic = 'science'",
        (attempt_id,),
    ).fetchone()
    assert row["score"] is None


def test_exactly_one_attempt_per_chapter_is_promoted(archived):
    db, _ = archived
    for chapter in (1, 2, 3):
        n = db.execute(
            "SELECT COUNT(*) AS n FROM attempts WHERE run_id = ? AND chapter = ? "
            "AND promoted = 1", (RUN_ID, chapter),
        ).fetchone()["n"]
        assert n == 1, f"chapter {chapter} promoted {n} attempts"


def test_the_promoted_attempt_is_the_last_one_drafted(archived):
    """It is the draft that reached the threshold, which is the last one written.

    Distinct from "the best draft" on purpose: G6's split says an accepted draft
    is the one that passed, and that is not always the highest-scoring one.
    """
    db, _ = archived
    for chapter in (1, 2, 3):
        promoted = db.execute(
            "SELECT attempt FROM attempts WHERE run_id = ? AND chapter = ? "
            "AND promoted = 1", (RUN_ID, chapter),
        ).fetchone()["attempt"]
        last = max(a for c, a in drafts_on_disk() if c == chapter)
        assert promoted == last


def test_a_gate_row_per_attempt_with_a_verdict_the_schema_admits(archived):
    db, _ = archived
    rows = list(db.execute(
        "SELECT chapter, attempt, aggregate, verdict FROM gate_decisions "
        "WHERE run_id = ?", (RUN_ID,)))
    assert {(r["chapter"], r["attempt"]) for r in rows} == set(drafts_on_disk())
    for r in rows:
        assert r["verdict"] in {"accept", "retry", "patched", "halt"}
        assert r["aggregate"] is not None


def test_the_aggregate_is_the_minimum_of_the_five(archived):
    db, _ = archived
    for a in db.execute("SELECT id, aggregate FROM attempts WHERE run_id = ?", (RUN_ID,)):
        scores = [
            r["score"] for r in db.execute(
                "SELECT score FROM scores WHERE attempt_id = ?", (a["id"],))
        ]
        usable = [s for s in scores if s is not None]
        assert a["aggregate"] == min(usable)


def test_every_sheet_on_disk_becomes_a_row(archived):
    db, _ = archived
    on_disk = sorted(p.name for p in SHEETS.glob("ch*.attempt*.md"))
    rows = list(db.execute(
        "SELECT chapter, attempt, level, validated FROM sheets WHERE run_id = ?",
        (RUN_ID,)))
    assert len(rows) == len(on_disk) == 4
    for r in rows:
        assert r["level"] in (1, 2)
    # Attempt 3 gets a level-2 sheet: the critic's literal replacement.
    third = [r for r in rows if r["attempt"] == 3]
    assert third and all(r["level"] == 2 for r in third)


def test_findings_keep_their_arbitration(archived):
    db, _ = archived
    n = db.execute(
        "SELECT COUNT(*) AS n FROM findings f JOIN attempts a ON a.id = f.attempt_id "
        "WHERE a.run_id = ? AND f.ruling IS NOT NULL", (RUN_ID,)
    ).fetchone()["n"]
    assert n > 0, "the run's critiques carry orchestrator_arbitration; none survived"


def test_upheld_is_false_only_where_the_ruling_says_overruled(archived):
    db, _ = archived
    for r in db.execute(
        "SELECT f.upheld, f.ruling FROM findings f JOIN attempts a ON a.id = f.attempt_id "
        "WHERE a.run_id = ? AND f.ruling IS NOT NULL", (RUN_ID,)
    ):
        assert (r["upheld"] == 0) == r["ruling"].upper().startswith("OVERRULED")


def test_the_measured_cost_is_stored_and_graded_measured(archived):
    db, _ = archived
    on_disk = json.loads((RUN_DIR / "cost.json").read_text(encoding="utf-8"))
    row = db.execute(
        "SELECT cost_usd, cost_provenance, turns FROM runs WHERE id = ?", (RUN_ID,)
    ).fetchone()
    assert row["cost_usd"] == pytest.approx(on_disk["total_cost_usd"])
    assert row["cost_provenance"] == "measured"
    assert row["turns"] == on_disk["turns"]


def test_the_api_prefers_the_measured_total_over_the_sum_of_calls(archived):
    """A reconstructed figure must never stand where a measured one exists.

    The run this spec came from reported the sum over nine `calls` rows while
    $18.82 sat measured in `cost.json` — G12's rule, inverted.
    """
    from backend.runs import repository as read_repo

    db, _ = archived
    payload = read_repo.cost(db, RUN_ID)
    on_disk = json.loads((RUN_DIR / "cost.json").read_text(encoding="utf-8"))
    assert payload["total_usd"] == pytest.approx(on_disk["total_cost_usd"])
    assert payload["total_provenance"] == "measured"


def test_a_run_with_no_result_event_reports_absent_not_zero(db):
    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    from backend.runs import repository as read_repo

    payload = read_repo.cost(db, "r")
    assert payload["total_provenance"] == "absent"
    assert payload["total_usd"] is None


def test_archiving_twice_does_not_duplicate(archived):
    db, _ = archived
    before = db.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()["n"]
    archive_run(db, RUN_ID, RUN_DIR, sheets_dir=SHEETS)
    after = db.execute("SELECT COUNT(*) AS n FROM attempts").fetchone()["n"]
    assert after == before


def test_a_rescore_beyond_the_draft_count_is_recorded_not_dropped(archived):
    """Chapter 1's `science` ran three iterations over two drafts.

    The third was a rescore of the identical draft against an amended rule — no
    prose changed. Iteration index is therefore not attempt index, and a reader
    who assumes it is invents a third draft that never existed.
    """
    db, report = archived
    assert any("rescore" in w.lower() for w in report.notes), report.notes
    n = db.execute(
        "SELECT COUNT(*) AS n FROM attempts WHERE run_id = ? AND chapter = 1",
        (RUN_ID,),
    ).fetchone()["n"]
    assert n == 2


def test_absent_token_figures_do_not_reach_the_reader_as_zero(archived):
    """The project's cardinal rule, broken on its own main screen.

    Every `calls` row of the first real run stored `input_tokens` as NULL,
    honestly, because the stream's per-agent packets report nothing. The reader
    wrapped the sum in COALESCE(..., 0) and the panel printed **"0 / 0" tokens
    for a run that spent $18.82**. The database told the truth and the query
    threw it away.
    """
    from backend.runs import repository as read_repo

    db, _ = archived
    payload = read_repo.cost(db, RUN_ID)
    assert payload["input_tokens"] is None
    assert payload["output_tokens"] is None
    assert payload["tokens_provenance"] == "absent"


def test_measured_token_figures_are_summed_and_graded_measured(db):
    from backend.commons.log.calls import CallRow, write_call
    from backend.runs import repository as read_repo

    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    for tokens in (100, 250):
        write_call(db, CallRow(
            run_id="r", stage="FLOW-4", agent="chapter-writer",
            model="claude-code-session", ts="2026-09-22T00:00:00Z",
            input_tokens=tokens, output_tokens=tokens // 2,
            provenance="measured",
        ))
    payload = read_repo.cost(db, "r")
    assert payload["input_tokens"] == 350
    assert payload["output_tokens"] == 175
    assert payload["tokens_provenance"] == "measured"
