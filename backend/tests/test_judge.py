"""PLAN-001 E5 — the judge rubric and `mandatory_facts` at the publish gate.

Two validators meet here and they fail in opposite directions.

`judge_rubric` is class **b**: a model scoring a whole book. The number it
returns is worth nothing on its own — docs/spec.md §2 says "a score 0–10 **and
a justification** per criterion" and the emphasis is the schema's whole reason
to exist. A 6 with no reason cannot be argued with, cannot be acted on, and
cannot be told apart from a 6 the judge picked to look decisive. So a criterion
that arrives without its justification is **rejected**, not stored with an empty
string beside it.

`mandatory_facts` is class **a**: arithmetic over two tables. It fails by
flattery — a fact the matcher missed reported as covered. docs/spec.md §7 fixes
the direction: "a fact paraphrased is missed and reported as uncovered, never
invented as covered", which is why this reports uncovered ids rather than a
score.

And both meet the rule docs/domain-knowledge.md §7.10 names the family of:
**absent is not zero.** A criterion the judge did not score is excluded from the
mean; a run with no mandatory facts has no fraction at all.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.commons.db import repository


# The Story Bible tables arrive with migration 010 (PLAN-001 E3), which is being
# built in a different worktree. `mandatory.py` is written against their
# documented shape and must not create them, so the stand-in lives here — in the
# test, where it is obviously a stand-in, and where migration 010 replacing it
# changes nothing this file asserts.
STAND_IN_BIBLE = ""   # retired at integration: migration 010 (E3) ships
# `facts` and `fact_usage`, so a stand-in here would test a copy of them.


def _rubric(**overrides) -> dict:
    """A complete, well-formed reply from the `judge` agent."""
    body = {
        "continuity": {"score": 9,
                       "justification": "The lighthouse keeper's limp survives all ten chapters."},
        "tone": {"score": 8,
                 "justification": "Warm throughout; chapter 6 briefly turns clinical."},
        "narrative_arc": {"score": 7,
                          "justification": "The promise of the ledger is kept, but late."},
        "character_coherence": {"score": 9,
                                "justification": "Nobody acts against what the cast sheet says."},
        "pacing": {"score": 6,
                   "justification": "Chapters 3 and 4 both spend their length on the same wait."},
        "natural_personalisation": {"score": 8,
                                    "justification": "The recipient's dog arrives as a character, not a label."},
    }
    body.update(overrides)
    return body


@pytest.fixture
def run(db):
    db.executescript(STAND_IN_BIBLE)
    repository.create_run(db, run_id="r1", slug="the-keepers-ledger", premise="p",
                          profile="exam", tone=None, snapshot="{}")
    return "r1"


# ------------------------------------------------------------------ the schema


def test_the_six_criterion_rubric_validates(run):
    from backend.publish.judge import CRITERIA, JudgeRubric

    rubric = JudgeRubric.model_validate(_rubric())

    assert CRITERIA == ("continuity", "tone", "narrative_arc",
                        "character_coherence", "pacing", "natural_personalisation")
    assert rubric.continuity.score == 9
    assert rubric.natural_personalisation.justification.startswith("The recipient's dog")
    assert rubric.scored() == {"continuity": 9, "tone": 8, "narrative_arc": 7,
                               "character_coherence": 9, "pacing": 6,
                               "natural_personalisation": 8}


def test_a_score_without_its_justification_is_rejected(run):
    """The failure this schema exists to prevent.

    Not stored with an empty justification, not stored with a placeholder: a
    rubric that cannot say why is not a rubric, and the publish gate must see it
    as malformed rather than as a set of numbers.
    """
    from backend.publish.judge import JudgeRubric

    with pytest.raises(ValidationError) as missing:
        JudgeRubric.model_validate(_rubric(pacing={"score": 6}))
    assert "justification" in str(missing.value)

    with pytest.raises(ValidationError) as blank:
        JudgeRubric.model_validate(_rubric(pacing={"score": 6, "justification": "   "}))
    assert "justification" in str(blank.value)


def test_a_criterion_the_judge_did_not_score_is_excluded_not_zeroed(run):
    """docs/domain-knowledge.md §7.10, in the place it costs the most.

    Five nines and one absence is a book the judge scored 9, on a weaker rubric.
    Counting the absence as a 0 makes it 7.5 and publishes a lie about a
    criterion nobody looked at.
    """
    from backend.publish.judge import JudgeRubric

    partial = _rubric()
    del partial["pacing"]
    rubric = JudgeRubric.model_validate(partial)

    assert rubric.pacing is None
    assert rubric.unscored() == ["pacing"]
    assert rubric.mean() == pytest.approx((9 + 8 + 7 + 9 + 8) / 5)
    assert "pacing" in rubric.note()


def test_a_rubric_with_nothing_scored_has_no_mean_at_all(run):
    from backend.publish.judge import JudgeRubric

    assert JudgeRubric.model_validate({}).mean() is None


# ----------------------------------------------------------------- the storage


def test_the_rubric_is_stored_one_row_per_criterion_with_its_justification(db, run):
    from backend.publish import judge

    judge.record(db, run_id=run, version=1,
                 rubric=judge.JudgeRubric.model_validate(_rubric()))

    rows = db.execute(
        "SELECT criterion, value, justification, kind FROM validations "
        "WHERE run_id = ? AND version = ? AND validator = 'judge_rubric' "
        "ORDER BY criterion",
        (run, 1),
    ).fetchall()
    assert {r["criterion"] for r in rows} == set(judge.CRITERIA) | {"mean"}
    assert all(r["kind"] == "b" for r in rows)
    assert all((r["justification"] or "").strip() for r in rows)
    assert dict(zip([r["criterion"] for r in rows], [r["value"] for r in rows]))["pacing"] == "6"


def test_an_unscored_criterion_stores_a_row_with_no_value_rather_than_no_row(db, run):
    """A missing row and a row with a NULL value are different claims, and only
    the second one says "the judge was asked and did not answer"."""
    from backend.publish import judge

    partial = _rubric()
    del partial["pacing"]
    judge.record(db, run_id=run, version=1,
                 rubric=judge.JudgeRubric.model_validate(partial))

    row = db.execute(
        "SELECT value, justification FROM validations WHERE run_id = ? AND version = ? "
        "AND validator = 'judge_rubric' AND criterion = 'pacing'", (run, 1)).fetchone()
    assert row is not None
    assert row["value"] is None


def test_recording_the_same_version_twice_replaces_rather_than_doubles(db, run):
    from backend.publish import judge

    for _ in range(2):
        judge.record(db, run_id=run, version=1,
                     rubric=judge.JudgeRubric.model_validate(_rubric()))
    count = db.execute(
        "SELECT COUNT(*) FROM validations WHERE validator = 'judge_rubric'").fetchone()[0]
    assert count == len(judge.CRITERIA) + 1


def test_a_kind_b_row_with_a_value_and_no_justification_is_refused_by_the_schema(db, run):
    """The rule again, one layer down. Pydantic guards the agent's reply;
    this guards everything else that can write the table."""
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO validations (run_id, version, validator, kind, criterion, "
            "value, justification, ts) VALUES (?,?,?,?,?,?,?,?)",
            (run, 1, "human_review", "b", "pacing", "6", None, "2026-09-23T00:00:00Z"))


def test_the_kind_column_admits_only_the_four_docs_spec_names(db, run):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO validations (run_id, version, validator, kind, value, ts) "
            "VALUES (?,?,?,?,?,?)", (run, 1, "invented", "e", "1", "2026-09-23T00:00:00Z"))


# --------------------------------------------------------------- mandatory facts


def _facts(db, run_id: str) -> None:
    for fid, mandatory, source in [(101, 1, "brief"), (102, 1, "brief"),
                                   (103, 1, "brief"),
                                   (104, 0, "brief"), (105, 1, "mysteries")]:
        db.execute("INSERT INTO facts (id, run_id, kind, text, source, mandatory) "
                   "VALUES (?,?,?,?,?,?)", (fid, run_id, "recipient", f"text of {fid}",
                                            source, mandatory))


def test_mandatory_facts_reports_the_uncovered_fact_by_id(db, run):
    """By id, and never as a score.

    docs/spec.md §7: the matcher is string matching, so it misses paraphrase.
    A fraction alone would say "75%" and leave a reader to find which quarter;
    the id is the thing a person can act on.
    """
    from backend.publish import mandatory

    _facts(db, run)
    for fid, chapter in [(101, 2), (103, 7)]:
        db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) VALUES (?,?,?,'verbatim')",
                   (fid, 1, chapter))
    # A non-mandatory fact and a bible fact are used too; neither is this
    # validator's business and neither may move the denominator.
    db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) VALUES (104, 1, 3, 'text of 104')")

    coverage = mandatory.check(db, run_id=run, version_id=1)

    assert coverage.uncovered == [102]
    assert coverage.covered == [101, 103]
    assert coverage.total == 3
    assert coverage.fraction == pytest.approx(2 / 3)


def test_a_fact_used_in_another_version_does_not_count_for_this_one(db, run):
    from backend.publish import mandatory

    _facts(db, run)
    db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) VALUES (101, 2, 4, 'text of 101')")

    assert mandatory.check(db, run_id=run, version_id=1).uncovered == [101, 102, 103]


def test_a_run_with_no_mandatory_facts_has_no_fraction_rather_than_a_perfect_one(db, run):
    """§7.10 once more. `0/0` is not 1.0 and it is not 0.0; there is no
    denominator, so there is no figure, and the row says so."""
    from backend.publish import mandatory

    coverage = mandatory.check(db, run_id=run, version_id=1)
    assert coverage.total == 0
    assert coverage.fraction is None

    mandatory.record(db, run_id=run, version=1, coverage=coverage)
    row = db.execute("SELECT value, justification FROM validations "
                     "WHERE validator = 'mandatory_facts'").fetchone()
    assert row["value"] is None
    assert "no fact" in row["justification"]


def test_the_uncovered_ids_reach_the_stored_row(db, run):
    from backend.publish import mandatory

    _facts(db, run)
    db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) VALUES (101, 1, 2, 'text of 101')")
    mandatory.record(db, run_id=run, version=1,
                     coverage=mandatory.check(db, run_id=run, version_id=1))

    row = db.execute("SELECT kind, value, justification FROM validations "
                     "WHERE validator = 'mandatory_facts'").fetchone()
    assert row["kind"] == "a"
    assert row["value"] == "1/3"
    assert "102" in row["justification"] and "103" in row["justification"]


# -------------------------------------------------------------------- the API


@pytest.fixture
def client(db):
    from backend.publish import router_judge
    from backend.runs import router as runs_router

    class _Service:  # the only thing the two routes need off it
        conn = db

    app = FastAPI()
    app.dependency_overrides[runs_router.get_service] = lambda: _Service()
    app.include_router(router_judge.router, prefix="/api/runs")
    return TestClient(app)


def test_the_judge_route_serves_the_six_criteria_with_their_justifications(db, run, client):
    from backend.publish import judge

    judge.record(db, run_id=run, version=1,
                 rubric=judge.JudgeRubric.model_validate(_rubric()))

    body = client.get(f"/api/runs/{run}/versions/1/judge").json()
    assert set(body["criteria"]) == set(judge.CRITERIA)
    assert body["criteria"]["pacing"] == {"score": 6, "justification":
                                          "Chapters 3 and 4 both spend their length on the same wait."}
    assert body["mean"] == pytest.approx(7.833333333333333)
    assert body["unscored"] == []


def test_the_judge_route_is_404_when_no_judge_ran_for_that_version(run, client):
    assert client.get(f"/api/runs/{run}/versions/9/judge").status_code == 404


def test_the_validations_route_serves_every_validator_of_the_version(db, run, client):
    from backend.publish import judge, mandatory

    judge.record(db, run_id=run, version=1,
                 rubric=judge.JudgeRubric.model_validate(_rubric()))
    mandatory.record(db, run_id=run, version=1,
                     coverage=mandatory.check(db, run_id=run, version_id=1))

    rows = client.get(f"/api/runs/{run}/versions/1/validations").json()
    assert {r["validator"] for r in rows} == {"judge_rubric", "mandatory_facts"}
    assert {r["kind"] for r in rows} == {"a", "b"}
    assert all(set(r) == {"validator", "kind", "criterion", "value", "justification", "ts"}
               for r in rows)


# ------------------------------------------------------------------- the agent


def test_the_judge_agent_asks_for_a_justification_per_criterion():
    """The prompt and the schema are two copies of one contract, written apart.

    An agent asked for six numbers and a schema demanding six reasons produce a
    rubric that is rejected every time, at the publish gate, after the whole
    book has been paid for.
    """
    from pathlib import Path

    from backend.publish.judge import CRITERIA

    text = (Path(__file__).resolve().parents[2] / ".claude/agents/judge.md").read_text(
        encoding="utf-8")
    for criterion in CRITERIA:
        assert criterion in text, criterion
    assert "justification" in text
