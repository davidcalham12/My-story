"""Did the run obey its own gate? SPEC-004 A10.

`verification.md` §3.1 stayed critical on one line: *the only signal is reading a
book with a bad chapter in it*. This is the earlier signal — it cannot prevent a
disobeyed halt, it makes one visible when the run ends.

The tests build the records a disobedient run would leave, because the real runs
were all obedient and a check nothing has ever failed has not been shown to check
anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.commons.db import repository
from backend.runs.archive import archive_run
from backend.runs.conformance import audit, summary

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "output/lighthouse-keeper-ledger"
SHEETS = ROOT / "specs/loops/LOOP-003/sheets/lighthouse-keeper-ledger"

PASS = {"continuity": 10, "science": 10, "outline": 10, "length": 10, "chatter": 10}


def make_run(db, run_id="r"):
    repository.create_run(db, run_id=run_id, slug=run_id, premise="p",
                          profile="tiny", tone=None, snapshot="{}")
    return run_id


def add(db, run_id, chapter, attempt, aggregate, verdict, promoted=False):
    scores = dict(PASS) if aggregate is None else {
        **PASS, "continuity": aggregate}
    if aggregate is None:
        scores = {k: None for k in PASS}
    repository.save_attempt(
        db, run_id=run_id, chapter=chapter, attempt=attempt, title=None,
        draft_path=f"chapters/ch{chapter:02d}.attempt{attempt}.md", words=500,
        scores=scores, verdict=verdict, aggregate=aggregate, findings=[],
        promoted=promoted,
    )


def test_a_clean_chapter_raises_nothing(db):
    run = make_run(db)
    add(db, run, 1, 1, 7, "retry")
    add(db, run, 1, 2, 10, "accept", promoted=True)
    assert audit(db, run) == []


def test_a_draft_promoted_below_the_threshold_is_caught(db):
    """The outcome the whole system exists to prevent, seen from the record."""
    run = make_run(db)
    add(db, run, 1, 1, 7, "retry")
    add(db, run, 1, 2, 6, "accept", promoted=True)
    breaches = audit(db, run)
    assert any(b.rule == "promoted below the threshold" for b in breaches), breaches


def test_a_patched_rescue_is_not_reported_as_a_breach(db):
    """It passed, and it did not pass on its own. Both are legitimate."""
    run = make_run(db)
    add(db, run, 1, 1, 4, "retry")
    add(db, run, 1, 2, 5, "retry")
    add(db, run, 1, 3, 9, "patched", promoted=True)
    assert audit(db, run) == []


def test_a_verdict_the_rule_would_not_give_is_caught(db):
    run = make_run(db)
    add(db, run, 1, 1, 3, "accept", promoted=True)
    assert any(b.rule == "verdict the rule would not give" for b in audit(db, run))


def test_a_fourth_attempt_is_caught(db):
    run = make_run(db)
    for attempt in (1, 2, 3, 4):
        add(db, run, 1, attempt, 5, "retry")
    assert any(b.rule == "more attempts than allowed" for b in audit(db, run))


def test_a_chapter_that_failed_without_halting_is_caught(db):
    """The book would have a hole in it that nobody decided to make."""
    run = make_run(db)
    add(db, run, 1, 1, 5, "retry")
    add(db, run, 1, 2, 4, "retry")
    add(db, run, 1, 3, 4, "retry")
    assert any(b.rule == "failed without halting" for b in audit(db, run))


def test_the_same_chapter_halted_raises_nothing(db):
    run = make_run(db)
    add(db, run, 1, 1, 5, "retry")
    add(db, run, 1, 2, 4, "retry")
    add(db, run, 1, 3, 4, "halt")
    repository.halt(db, run, "gate", "three attempts and the patch, exhausted")
    assert [b for b in audit(db, run) if b.rule == "failed without halting"] == []


def test_two_promoted_drafts_for_one_chapter_are_caught(db):
    run = make_run(db)
    add(db, run, 1, 1, 10, "accept", promoted=True)
    add(db, run, 1, 2, 10, "accept", promoted=True)
    assert any(b.rule == "more than one draft promoted" for b in audit(db, run))


def test_an_attempt_with_no_aggregate_is_unjudgeable_not_delinquent(db):
    """Absent read as failure is the mirror of absent read as zero.

    The first version of this audit reported six of the eight v1 runs as having
    promoted chapters below the threshold. They had recorded no usable scores at
    all: the record could not answer, and the check answered anyway.
    """
    run = make_run(db)
    add(db, run, 1, 1, None, "accept", promoted=True)
    assert audit(db, run) == []
    result = summary(db, run)
    assert result["verdict"] == "unchecked"
    assert result["unjudgeable"] == 1
    assert result["attempts_checked"] == 0


def test_a_pre_loop003_run_is_not_judged_by_a_rule_that_did_not_exist(db):
    """The same category error `source` was added to prevent.

    Those runs were scored on two or three characteristics with
    `accept_with_warnings` available. Today's rule produces confident nonsense
    over them — it reported chapters that scored 10 as ones that should not have
    been retried, which says nothing about whether the gate of the day was obeyed.
    """
    run = make_run(db, "old")
    db.execute("UPDATE runs SET source = 'pre-loop003' WHERE id = ?", (run,))
    add(db, run, 1, 1, 3, "accept", promoted=True)
    assert audit(db, run) == []
    result = summary(db, run)
    assert result["verdict"] == "not_applicable"
    assert "did not exist" in result["why"]


def test_a_run_with_no_attempts_is_unchecked_not_conformant(db):
    """Three states, not two. This is the zero-for-absent mistake in costume."""
    run = make_run(db)
    result = summary(db, run)
    assert result["verdict"] == "unchecked"
    assert result["attempts_checked"] == 0


def test_the_first_real_run_obeyed_its_own_gate(db):
    """The one that matters: a real run, read back from its own files.

    Three chapters, seven drafts, three promotions, every one at 10.
    """
    run = make_run(db, "fd3af0c64ced")
    archive_run(db, run, RUN_DIR, sheets_dir=SHEETS)
    result = summary(db, run)
    assert result["attempts_checked"] == 7
    assert result["breaches"] == []
    assert result["verdict"] == "conformant"


@pytest.mark.parametrize("aggregate", range(0, 8))
def test_no_aggregate_below_the_threshold_can_be_promoted_quietly(db, aggregate):
    """Exhaustive over the range that matters, because the check is cheap."""
    run = make_run(db, f"r{aggregate}")
    add(db, run, 1, 1, aggregate, "accept", promoted=True)
    assert audit(db, run), f"aggregate {aggregate} promoted and nothing said"
