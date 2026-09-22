"""A chapter stopped by `prose` alone, through the real archive path, at $0.

SPEC-006 was *specified, implemented and unexercised* — the words LOOP-003 used
about `patch_then_halt` before a stress profile was built to exercise it, and the
reason that profile exists: **waiting for a natural failure is not a plan.**

The critic itself needs a real run and real money. What does not is everything
downstream of it: the aggregation, the archive, the verdict, the promotion and
the conformance audit all have to handle six characteristics, and a bug in any of
them would make `prose` a score nobody acts on.

So this drives the whole chain with a chapter that is a ten on all five older
characteristics and a **five on `prose`**, then passes on the redraft. If the
sixth characteristic cannot stop a chapter here, it cannot stop one anywhere.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from backend.chapters.domain import CHARACTERISTICS
from backend.commons.db import repository
from backend.runs import conformance
from backend.runs.archive import archive_run

RUN = "six"


def build(tmp: Path, prose_scores: dict[int, int | None]) -> Path:
    """A one-chapter run: perfect on the five, whatever `prose_scores` says."""
    (tmp / "chapters").mkdir(exist_ok=True)
    (tmp / "critiques").mkdir(exist_ok=True)
    attempts = sorted(prose_scores)
    for attempt in attempts:
        (tmp / "chapters" / f"ch01.attempt{attempt}.md").write_text(
            f"# Chapter 1 — A\n\nDraft {attempt}.\n", encoding="utf-8")
    for critic in CHARACTERISTICS:
        scores = (prose_scores if critic == "prose"
                  else {a: 10 for a in attempts})
        (tmp / "critiques" / f"ch01.{critic}.json").write_text(json.dumps({
            "critic": critic, "chapter": 1, "drafts": len(attempts),
            "iterations": [{"iteration": a, "score": s, "findings": []}
                           for a, s in sorted(scores.items())],
        }), encoding="utf-8")
    return tmp


@pytest.fixture
def run_dir(tmp_path):
    return tmp_path


def archived(db, tmp: Path):
    repository.create_run(db, run_id=RUN, slug=RUN, premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    return archive_run(db, RUN, tmp)


def attempts(db):
    return [dict(r) for r in db.execute(
        "SELECT attempt, aggregate, verdict, promoted FROM attempts "
        "WHERE run_id = ? ORDER BY attempt", (RUN,))]


def test_prose_alone_stops_a_chapter_that_is_perfect_otherwise(db, run_dir):
    """The whole point of SPEC-006, exercised rather than assumed."""
    build(run_dir, {1: 5})
    (run_dir / "chapters" / "ch01.md").unlink(missing_ok=True)
    archived(db, run_dir)

    rows = attempts(db)
    assert len(rows) == 1
    assert rows[0]["aggregate"] == 5, "the minimum must be the prose score"
    assert rows[0]["verdict"] == "retry"
    assert rows[0]["promoted"] == 0, "it did not pass, so it did not ship"


def test_a_chapter_the_redraft_rescued_on_prose_is_promoted(db, run_dir):
    build(run_dir, {1: 5, 2: 9})
    (run_dir / "chapters" / "ch01.md").write_text("# Chapter 1 — A\n\nDraft 2.\n",
                                                  encoding="utf-8")
    archived(db, run_dir)

    rows = attempts(db)
    assert [r["aggregate"] for r in rows] == [5, 9]
    assert [r["promoted"] for r in rows] == [0, 1]
    assert rows[1]["verdict"] == "accept"


def test_the_archive_keeps_six_scores_an_attempt(db, run_dir):
    build(run_dir, {1: 5, 2: 9})
    archived(db, run_dir)
    for row in db.execute("SELECT id FROM attempts WHERE run_id = ?", (RUN,)):
        got = {r["characteristic"] for r in db.execute(
            "SELECT characteristic FROM scores WHERE attempt_id = ?", (row["id"],))}
        assert got == set(CHARACTERISTICS)


def test_an_unusable_prose_verdict_does_not_let_a_chapter_through(db, run_dir):
    """The rule that once returned 10 and passed a draft, applied to the newest
    and least reliable critic — the one most likely to return something
    unparseable."""
    build(run_dir, {1: None})
    (run_dir / "critiques" / "ch01.prose.json").write_text(json.dumps({
        "critic": "prose", "chapter": 1, "drafts": 1,
        "iterations": [{"iteration": 1, "score": None, "findings": []}],
    }), encoding="utf-8")
    (run_dir / "chapters" / "ch01.md").unlink(missing_ok=True)
    archived(db, run_dir)

    row = attempts(db)[0]
    assert row["aggregate"] == 10, "the minimum over the five that answered"
    assert row["verdict"] == "retry", "a gate short a critic is weaker, not passing"
    assert row["promoted"] == 0

    score = db.execute(
        "SELECT score FROM scores s JOIN attempts a ON a.id = s.attempt_id "
        "WHERE a.run_id = ? AND s.characteristic = 'prose'", (RUN,)).fetchone()
    assert score["score"] is None, "never 0 and never 10"


def test_a_prose_stop_is_conformant_not_a_breach(db, run_dir):
    """A chapter correctly stopped by the new characteristic must not read as
    the run disobeying its own gate."""
    build(run_dir, {1: 5, 2: 9})
    (run_dir / "chapters" / "ch01.md").write_text("# Chapter 1 — A\n\nDraft 2.\n",
                                                  encoding="utf-8")
    archived(db, run_dir)
    assert conformance.summary(db, RUN)["verdict"] == "conformant"


def test_promoting_a_chapter_that_failed_prose_is_a_breach(db, run_dir):
    """And the audit has to see it. A chapter shipped at 5 on prose is exactly
    the outcome G6 promises cannot happen, arriving through the newest door."""
    build(run_dir, {1: 5})
    (run_dir / "chapters" / "ch01.md").write_text("# Chapter 1 — A\n\nDraft 1.\n",
                                                  encoding="utf-8")
    archived(db, run_dir)

    breaches = conformance.audit(db, RUN)
    assert any(b.rule == "promoted below the threshold" for b in breaches), breaches
