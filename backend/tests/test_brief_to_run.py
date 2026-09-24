"""The join: an order becomes a run, and what it asked for becomes rows.

Until this existed the product had two halves that did not touch. `POST
/api/briefs` stored what the buyer ordered; `POST /api/runs` took a premise
somebody typed; no column, table or function joined them. The interview in
SPEC-EXAM-002 assumes the join, and the eval harness found its absence by
having to compose a premise itself.

What these tests hold is not that the join exists — that is one line — but
that the three things it carries land where the rest of the pipeline already
reads them, and that the one field an attacker controls does not travel as a
sentence.
"""

from __future__ import annotations

import json
import sqlite3
import uuid

import pytest

from backend.brief import domain
from backend.commons.config.settings import Settings
from backend.commons.db import repository as repo
from backend.policy import forbidden
from backend.runs.service import BriefNotReady, NotFound, RunService

EXAMPLES = domain.EXAMPLES


def brief_payload(name: str) -> dict:
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def store(db, name: str) -> str:
    """A brief in the table, the way the router puts one there."""
    parsed = domain.parse(brief_payload(name))
    brief_id = uuid.uuid4().hex[:12]
    with db:
        db.execute("INSERT INTO briefs (id, created_at, payload) VALUES (?,?,?)",
                   (brief_id, "2026-09-23T00:00:00Z",
                    json.dumps(parsed.model_dump(), ensure_ascii=False)))
    return brief_id


@pytest.fixture
def svc(db, tmp_path) -> RunService:
    service = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                      use_recorded_stream=True))
    # The join is what is on trial, not the orchestrator. Nothing is launched.
    service._execute = lambda *a, **k: None
    return service


# ------------------------------------------------------------- the premise


def test_the_premise_carries_the_order_and_not_the_free_text():
    """The one field an attacker controls never becomes a sentence.

    Brief 04 hides "IGNORE ALL PREVIOUS INSTRUCTIONS" in the free box. It
    reaches the novel as a row whose `source` says what it is worth. Putting it
    in the premise would turn it back into something the orchestrator reads,
    which is the one thing SPEC-EXAM-001 AC-2 forbids.
    """
    brief = domain.parse(brief_payload("04-adversarial"))
    line = domain.premise(brief)

    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" not in line.upper()
    assert "developer mode" not in line.lower()
    assert "system prompt" not in line.lower()
    # And the gift hidden in the same paragraph does not travel either — it is
    # a lead for a human, in the freetext row, not a promise in the premise.
    assert "tomato plants" not in line.lower()

    # It is still an order somebody could write a book from.
    assert brief.recipient.alias in line
    assert brief.genre in line
    assert "Finisterre" in line, "the memories are the book"
    assert all(f in line for f in brief.mandatory_facts)


def test_the_premise_fits_what_the_api_accepts():
    """`StartRun.premise` caps at 2000 characters, and a brief with a long cast
    and long memories is exactly how that cap gets found in production."""
    for name in ("01-hijo", "02-pareja", "04-adversarial"):
        line = domain.premise(domain.parse(brief_payload(name)))
        assert 10 <= len(line) <= 2000, (name, len(line))


# ------------------------------------------------------------- the join


def test_a_run_started_from_a_brief_remembers_which_one(svc, db):
    brief_id = store(db, "01-hijo")

    started = svc.start_from_brief(brief_id, profile="tiny")

    assert started["brief_id"] == brief_id
    row = db.execute("SELECT brief_id, premise FROM runs WHERE id = ?",
                     (started["id"],)).fetchone()
    assert row["brief_id"] == brief_id
    assert row["premise"] == domain.premise(domain.parse(brief_payload("01-hijo")))


def test_a_run_started_from_a_premise_has_no_brief_and_that_is_not_a_defect(svc, db):
    """NULL means "no brief", which is a different claim from "a brief that
    asked for nothing". The demo and the stress profile live here."""
    started = svc.start("a lighthouse keeper and the winter she stopped counting",
                        "tiny", "")

    row = db.execute("SELECT brief_id FROM runs WHERE id = ?",
                     (started["id"],)).fetchone()
    assert row["brief_id"] is None


def test_the_briefs_forbidden_terms_reach_the_table_the_validator_reads(svc, db):
    """A forbidden term that lives only in the writer's prompt is a term the
    writer sometimes still writes and nothing downstream notices.

    Level `client`, which is what 011_policy.sql reserves for a brief's own
    terms — `novel` is for a term that turns out to be forbidden during a run.
    """
    before = {t.normalised for t in forbidden.terms(db, ["client"])}
    brief_id = store(db, "04-adversarial")

    svc.start_from_brief(brief_id, profile="tiny")

    after = {t.normalised for t in forbidden.terms(db, ["client"])}
    assert after - before == {"hospital", "carmen", "cancer"}
    assert {t.level for t in forbidden.terms(db, ["client"])} == {"client"}


def test_the_buyers_promises_become_mandatory_rows_and_the_free_text_does_not(svc, db):
    """The publish gate counts `mandatory` rows one by one. The free text is a
    row too, and it must never be one the gate is told to make come true."""
    brief_id = store(db, "04-adversarial")

    started = svc.start_from_brief(brief_id, profile="tiny")

    rows = db.execute(
        "SELECT kind, text, source, mandatory FROM facts WHERE run_id = ?",
        (started["id"],)).fetchall()
    promises = [r for r in rows if r["source"] == "brief"]
    freetext = [r for r in rows if r["source"] == "freetext"]

    assert len(promises) == 3 and all(r["mandatory"] == 1 for r in promises)
    assert {r["text"] for r in promises} == {
        "the Finisterre lighthouse", "the storm of 1987", "the tomatoes"}

    assert len(freetext) == 1
    assert freetext[0]["mandatory"] == 0, \
        "the gate must never be told to make an injection appear in the novel"
    assert freetext[0]["kind"] == "freetext"
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in freetext[0]["text"], \
        "kept whole: the filter that dropped the attack would drop the gift"
    assert "rain on the tomato plants" in freetext[0]["text"]


def test_starting_the_same_brief_twice_does_not_double_anything(svc, db):
    """Two runs of one order is a reprint, not a contradiction. The rows are
    per run, and within a run the insert is idempotent."""
    brief_id = store(db, "01-hijo")

    first = svc.start_from_brief(brief_id, profile="tiny")
    svc._live = None                      # the queue of one, released
    second = svc.start_from_brief(brief_id, profile="tiny")

    assert first["id"] != second["id"]
    for run in (first, second):
        count = db.execute("SELECT COUNT(*) c FROM facts WHERE run_id = ?",
                           (run["id"],)).fetchone()["c"]
        assert count == len(domain.facts(domain.parse(brief_payload("01-hijo"))))

    # And re-writing the same brief's facts onto one run adds nothing.
    added = repo.save_brief_facts(
        db, first["id"], domain.facts(domain.parse(brief_payload("01-hijo"))))
    assert added == 0


# ------------------------------------------------------------- refusals


def test_a_brief_that_is_not_there_is_a_404_not_a_run(svc):
    with pytest.raises(NotFound):
        svc.start_from_brief("nosuchbrief", profile="tiny")


def test_a_brief_that_stopped_passing_starts_nothing(svc, db):
    """Stored briefs were checked before they were stored, so this should never
    fire — which is why it is worth a test. If the schema moves under a brief
    somebody is still waiting on, the refusal is free and the run is not.
    """
    brief_id = store(db, "01-hijo")
    with db:
        payload = json.loads(db.execute(
            "SELECT payload FROM briefs WHERE id = ?", (brief_id,)).fetchone()["payload"])
        payload["tone"] = ""                       # a required field, emptied
        db.execute("UPDATE briefs SET payload = ? WHERE id = ?",
                   (json.dumps(payload), brief_id))

    with pytest.raises(BriefNotReady):
        svc.start_from_brief(brief_id, profile="tiny")

    assert db.execute("SELECT COUNT(*) c FROM runs").fetchone()["c"] == 0


# ------------------------------------------------------------- the edge


def test_the_request_takes_a_premise_or_a_brief_and_never_both():
    """Two ideas of what the book is about, and picking one silently is how a
    buyer gets a novel for somebody else's father."""
    from pydantic import ValidationError

    from backend.runs.models import StartRun

    assert StartRun(premise="a lighthouse and a long winter").brief_id is None
    assert StartRun(brief_id="abc123").premise is None

    with pytest.raises(ValidationError):
        StartRun()
    with pytest.raises(ValidationError):
        StartRun(premise="a lighthouse and a long winter", brief_id="abc123")


def test_the_column_is_nullable_so_every_run_recorded_before_today_still_reads(db):
    """A migration that made this NOT NULL would have made every existing run
    unreadable, and there are runs in this repository that are evidence."""
    cols = {r[1]: r for r in db.execute("PRAGMA table_info(runs)")}
    assert "brief_id" in cols
    assert cols["brief_id"][3] == 0, "notnull must be 0"
