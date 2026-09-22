"""A9, A10 — the eight v1 runs import, and their gaps stay visible.

D22 makes the importer the schema's first test. It is a hard one on purpose: the
eight runs carry three critique shapes, eight chapter schemas and five critic
sets, and three wrote no gate rows at all.
"""

from pathlib import Path

import pytest

from backend.commons.db.import_v1 import import_all

OUTPUT = Path(__file__).resolve().parents[2] / "output"

#: The eight runs this module is about, by name. It used to say `== 8` and count
#: what was on disk, which held until v2 wrote its first novel into the same
#: `output/` directory and the count became nine. The test was measuring the
#: filesystem, not the import — a real defect in the test, found by a real run.
V1_RUNS = (
    "a-night-shift-dispatcher-at-a-mountain",
    "cyberpunk-stolen-memory-broker",
    "deep-space-salvage-derelict",
    "generation-ship-votes-to-wake",
    "ice-station-water-recycler-surplus",
    "last-lighthouse-keeper-on-titan",
    "night-dispatcher-recovered-climber",
    "the-beginning-after-the-end",
    "titan-lighthouse-distress-calls",
)


@pytest.fixture
def imported(db):
    return db, import_all(db, OUTPUT, slugs=V1_RUNS)


def test_the_named_v1_runs_import(imported):
    _, reports = imported
    got = {r.slug for r in reports}
    on_disk = {s for s in V1_RUNS if (OUTPUT / s / "state.json").exists()}
    assert got == on_disk, sorted(got ^ on_disk)
    assert len(got) >= 8


def test_a_live_v2_run_is_not_imported_as_history(db):
    """The importer must not adopt a run v2 is in the middle of producing.

    Marking it `pre-loop003` would file a run judged by five characteristics
    among the ones judged by three, which is the exact contamination the source
    column exists to prevent.
    """
    live = sorted(
        p.name
        for p in OUTPUT.iterdir()
        if p.is_dir() and (p / "state.json").exists() and p.name not in V1_RUNS
    )
    if not live:
        pytest.skip("no v2 run in output/ yet")

    db.execute(
        "INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
        "started_at, source) VALUES (?, ?, ?, ?, ?, ?, ?, 'v2')",
        ("live", live[0], "a premise", "tiny", "{}", "FLOW-4",
         "2026-09-22T00:00:00Z"),
    )
    reports = import_all(db, OUTPUT)
    assert live[0] not in {r.slug for r in reports}


def test_every_run_is_marked_pre_loop003(imported):
    db, _ = imported
    sources = {r["source"] for r in db.execute("SELECT source FROM runs")}
    assert sources == {"pre-loop003"}


def test_imported_runs_are_excluded_from_statistics(imported):
    """The exclusion has to be expressible as a query, or it is a note nobody
    applies. A pass rate over runs judged by three characteristics does not
    measure what it claims."""
    db, _ = imported
    counted = db.execute(
        "SELECT COUNT(*) AS n FROM runs WHERE source = 'v2'"
    ).fetchone()["n"]
    assert counted == 0


def test_completeness_records_what_was_missing(imported):
    """A gap must read as a gap. A run that never wrote gate rows must not end
    up resembling one whose gate passed everything first time."""
    db, _ = imported
    without_gate = [
        r["run_id"] for r in db.execute(
            "SELECT run_id FROM run_completeness "
            "WHERE field = 'gate_decisions' AND state = 'absent'"
        )
    ]
    assert without_gate, "three v1 runs wrote no gate rows; that must be recorded"
    for slug in without_gate:
        rows = db.execute(
            "SELECT COUNT(*) AS n FROM gate_decisions WHERE run_id = ?", (slug,)
        ).fetchone()["n"]
        assert rows == 0


def test_the_fifth_characteristic_is_absent_from_older_runs(imported):
    """`outline` was added by LOOP-003. Runs predating it must say so rather
    than appearing to have scored zero on it."""
    db, _ = imported
    absent = db.execute(
        "SELECT COUNT(*) AS n FROM run_completeness "
        "WHERE field = 'critic:outline' AND state = 'absent'"
    ).fetchone()["n"]
    assert absent >= 6


def test_three_critique_shapes_all_read(imported):
    """Bare array, object with `iterations`, flat object. Being strict about a
    contract nobody stated is not rigour."""
    db, _ = imported
    scored = db.execute(
        "SELECT COUNT(DISTINCT a.run_id) AS n FROM scores s "
        "JOIN attempts a ON a.id = s.attempt_id"
    ).fetchone()["n"]
    assert scored >= 7, "every run with critique files yielded scores"


def test_findings_keep_their_quote_and_ruling(imported):
    """The quote is a finding's identity — nothing else survives a redraft — and
    an overruled finding is a different event from an upheld one."""
    db, _ = imported
    quoted = db.execute(
        "SELECT COUNT(*) AS n FROM findings WHERE quote IS NOT NULL"
    ).fetchone()["n"]
    overruled = db.execute(
        "SELECT COUNT(*) AS n FROM findings WHERE upheld = 0"
    ).fetchone()["n"]
    assert quoted > 0
    assert overruled >= 1, "at least one v1 finding was overruled by arbitration"


def test_v1_token_totals_are_not_split_into_invented_halves(imported):
    """v1 recorded ONE total with no input/output split. Splitting it here would
    be inventing two numbers from one."""
    db, _ = imported
    row = db.execute(
        "SELECT COUNT(*) AS n FROM calls "
        "WHERE input_tokens IS NOT NULL OR output_tokens IS NOT NULL"
    ).fetchone()
    assert row["n"] == 0
    reconstructed = db.execute(
        "SELECT COUNT(*) AS n FROM calls WHERE provenance = 'reconstructed'"
    ).fetchone()["n"]
    assert reconstructed > 0, "the totals are kept, graded for what they are"


def test_family_model_names_are_resolved(imported):
    """Four v1 runs wrote `opus` rather than `claude-opus-5`, so every one of
    them priced at nothing — which reads as free rather than unmatched."""
    db, _ = imported
    families = db.execute(
        "SELECT COUNT(*) AS n FROM calls WHERE model IN ('opus','sonnet','haiku')"
    ).fetchone()["n"]
    assert families == 0


def test_unkept_drafts_are_recorded_as_unkept(imported):
    """Most v1 runs kept only the accepted draft. That evidence loss is the
    reason G7 was unmeasurable, and it is recorded rather than faked."""
    db, _ = imported
    unkept = db.execute(
        "SELECT COUNT(*) AS n FROM attempts WHERE draft_path = '(not kept)'"
    ).fetchone()["n"]
    assert unkept > 0


# ------------------------------------------------- PLAN-007 6.1: the switches


def test_an_unknown_critique_shape_is_a_parse_error_row_not_a_drop(db, tmp_path):
    """AC-7: three shapes are known. A fourth must leave a trace, because a
    silently dropped critique reads later as 'this critic was never run'."""
    import json
    from backend.commons.db.import_v1 import import_run

    run_dir = tmp_path / "fourth-shape"
    (run_dir / "critiques").mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({
        "premise": "A premise.", "profile": "tiny", "stage": "FLOW-6",
        "chapters": [{"n": 1, "drafts": 1}],
    }), encoding="utf-8")
    # A known shape beside the unknown one: the run still imports.
    (run_dir / "critiques" / "ch01.science.json").write_text(
        json.dumps([{"iteration": 1, "score": 9, "findings": []}]), encoding="utf-8")
    (run_dir / "critiques" / "ch01.continuity.json").write_text(
        json.dumps({"verdict": "looks fine", "remarks": ["nothing numeric"]}), encoding="utf-8")

    import_run(db, run_dir)

    scores = db.execute(
        "SELECT characteristic, score FROM scores s JOIN attempts a ON a.id = s.attempt_id "
        "WHERE a.run_id = 'fourth-shape'").fetchall()
    assert [(r["characteristic"], r["score"]) for r in scores] == [("science", 9)]
    warnings = db.execute(
        "SELECT kind, detail, chapter FROM run_warnings WHERE run_id = 'fourth-shape'").fetchall()
    assert [(w["kind"], w["chapter"]) for w in warnings] == [("parse_error", 1)]
    assert "ch01.continuity.json" in warnings[0]["detail"]
