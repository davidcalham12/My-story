"""PLAN-001 E2 — the brief, and the two decisions that are code's and not the
agent's (SPEC-EXAM-001 §1 row 1, §4 AC-1 and AC-2).

The `interviewer` agent extracts and asks. It decides nothing, because a model
asked "is this brief complete?" answers differently on Tuesday: the missing-field
list and the age/tone contradiction are arithmetic over a schema, and arithmetic
belongs in a script (AGENTS.md §5, *code before agent* — a script gives class
**T**, an agent **D** at best).

The third rule here is the adversarial one. Free text is what the buyer typed
into a box, so it is the one field an attacker controls; brief 04 puts "IGNORE
ALL PREVIOUS INSTRUCTIONS" in it. It must come out the other side as a row of
data with `source = freetext` and never as a value of `tone`, `genre` or
`mandatory_facts`, because those are the fields that reach a prompt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.brief import domain
from backend.brief.models import Brief

BRIEFS = Path(__file__).resolve().parents[2] / "evals" / "briefs"

#: A brief with everything the domain requires, to be broken one field at a time.
COMPLETE = {
    "occasion": "10th birthday",
    "recipient": {"alias": "Leo", "age": 10, "pronouns": "he/him",
                  "traits": ["curious"], "relationship_to_buyer": "son"},
    "memories": [{"text": "He found a fossil at Cadaqués", "date": "2024-07"}],
    "genre": "children's adventure",
    "tone": "warm, funny, a little brave",
    "length_chapters": 10,
    "forbidden_terms": [],
    "mandatory_facts": [],
    "dedication": None,
    "free_text": "",
}


def example(name: str) -> dict:
    return json.loads((BRIEFS / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ AC-1


def test_a_missing_field_returns_incomplete_with_the_question_to_ask():
    """Not "invalid" and not a refusal: a question the interviewer can read out.

    The buyer who left the tone blank is mid-conversation, not in error.
    """
    payload = dict(COMPLETE, tone=None)
    result = domain.check(payload)
    assert result.status == "incomplete"
    assert result.contradictions == []
    assert any("tone" in question for question in result.questions), result.questions


def test_an_empty_list_is_a_missing_field_and_not_an_answer():
    """`memories: []` is the shape brief 03 arrives in. A brief with no memory
    is a novel about nobody; the emptiness has to reach the buyer as a question
    rather than pass as an answered field."""
    result = domain.check(dict(COMPLETE, memories=[]))
    assert result.status == "incomplete"
    assert any("memor" in question.lower() for question in result.questions)


def test_a_complete_brief_is_ok_with_nothing_to_ask():
    result = domain.check(COMPLETE)
    assert result.status == "ok"
    assert result.questions == []
    assert result.contradictions == []


def test_age_eight_and_an_adult_tone_is_a_contradiction_naming_both_sides():
    """The one contradiction the exam asks for, and it names both halves.

    "This brief is contradictory" is useless to the person who has to fix it.
    The message carries the age and the tone that fought with it, so the answer
    is obvious without opening the JSON.
    """
    payload = dict(COMPLETE, tone="novela negra adulta")
    payload["recipient"] = dict(COMPLETE["recipient"], age=8)
    result = domain.check(payload)
    assert result.status == "contradiction"
    assert len(result.contradictions) == 1
    said = result.contradictions[0]
    assert "8" in said and "novela negra adulta" in said, said


@pytest.mark.parametrize("tone", ["novela negra adulta", "erótico", "thriller violento"])
def test_every_adult_tone_the_spec_names_contradicts_a_child(tone):
    payload = dict(COMPLETE, tone=tone)
    payload["recipient"] = dict(COMPLETE["recipient"], age=8)
    assert domain.check(payload).status == "contradiction"


def test_the_same_adult_tone_for_an_adult_is_not_a_contradiction():
    """The rule is about the pair, not about the tone. A noir for a grown-up is
    the product."""
    payload = dict(COMPLETE, tone="novela negra adulta")
    payload["recipient"] = dict(COMPLETE["recipient"], age=52)
    assert domain.check(payload).status == "ok"


def test_an_unknown_age_is_not_a_young_one():
    """Absent is never zero, and never a child either: with no age there is no
    pair to contradict, so the brief is incomplete and the interviewer asks."""
    payload = dict(COMPLETE, tone="novela negra adulta")
    payload["recipient"] = dict(COMPLETE["recipient"], age=None)
    result = domain.check(payload)
    assert result.contradictions == []
    assert result.status == "incomplete"
    assert any("age" in question.lower() for question in result.questions)


# ------------------------------------------------------------------ AC-2


def test_free_text_never_becomes_a_brief_field_only_a_freetext_fact():
    """AC-2, as a property of where the string ends up.

    The injection must be readable later — a buyer's aside often contains the
    best detail in the brief, and 04 hides "the smell of rain on the tomato
    plants" behind the attack — so it is kept, verbatim, as a fact whose
    `source` says exactly how much it is worth.
    """
    payload = example("04-adversarial.json")
    brief = domain.parse(payload)
    facts = domain.facts(brief)

    freetext = [f for f in facts if f.source == "freetext"]
    assert len(freetext) == 1
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in freetext[0].text
    assert "tomato plants" in freetext[0].text, "the real detail was thrown away with the attack"

    # And nowhere else. These are the fields that reach a prompt.
    instructions = [brief.occasion, brief.genre, brief.tone, brief.dedication,
                    *brief.mandatory_facts, *brief.forbidden_terms,
                    *(m.text for m in brief.memories), *brief.recipient.traits]
    for value in instructions:
        assert "IGNORE ALL PREVIOUS" not in (value or "").upper(), value


def test_a_fact_from_the_brief_is_not_a_fact_from_the_free_text():
    """The two sources are told apart at the moment they are made, not later.

    `mandatory_facts` was written by the buyer into a labelled field and is
    trusted enough to be checked for at the publish gate; free text was typed
    into a box. Same table, different `source`, and the validator only counts
    the first.
    """
    brief = domain.parse(example("01-hijo.json"))
    facts = domain.facts(brief)
    assert {f.source for f in facts} == {"brief", "freetext"}
    mandatory = [f for f in facts if f.source == "brief"]
    assert len(mandatory) == 3 and all(f.mandatory for f in mandatory)
    assert not any(f.mandatory for f in facts if f.source == "freetext")


def test_a_brief_with_no_free_text_produces_no_freetext_fact():
    """Absent is never zero and never an empty-string row: brief 03 and 05 leave
    the box untouched, and an empty fact would be a fact about nothing."""
    brief = domain.parse(dict(COMPLETE, free_text=""))
    assert [f for f in domain.facts(brief) if f.source == "freetext"] == []


# ------------------------------------------------- the schema itself


def test_the_schema_rejects_a_field_nobody_declared():
    """`extra="forbid"`, and the reason is the agent on the other end.

    The interviewer returns JSON. A model that invents `recipient.nickname`
    produces a brief that validates, loses the field silently, and writes a
    novel that calls the boy by the wrong name — so an unknown key is an error
    at FLOW-0, before anything is spent.
    """
    with pytest.raises(ValidationError) as exc:
        Brief(**dict(COMPLETE, nickname="Leíto"))
    assert "nickname" in str(exc.value)

    with pytest.raises(ValidationError):
        Brief(**dict(COMPLETE, recipient=dict(COMPLETE["recipient"], nickname="Leíto")))


def test_the_model_has_exactly_the_keys_the_spec_names():
    """The list is a contract with the frontend (SPEC-EXAM-002 AC-1 compares the
    form's fields with this schema) and with the interviewer's prompt. A field
    added here without those two moving is a field nobody fills."""
    assert set(Brief.model_fields) == {
        "occasion", "recipient", "memories", "genre", "tone", "length_chapters",
        "forbidden_terms", "mandatory_facts", "dedication", "free_text",
    }
    from backend.brief.models import Memory, Recipient
    assert set(Recipient.model_fields) == {
        "alias", "age", "pronouns", "traits", "relationship_to_buyer"}
    assert set(Memory.model_fields) == {"text", "date"}


def test_an_unmeasured_field_is_none_and_never_zero():
    """A brief whose age nobody asked for must not read as a newborn — the
    difference decides whether the contradiction rule fires."""
    brief = Brief()
    assert brief.recipient.age is None
    assert brief.length_chapters is None
    assert brief.memories == [] and brief.recipient.traits == []


# ---------------------------------------- the five committed briefs
# `evals/briefs/*.json` are the contract for this phase, not illustrations of
# it. Each one is named after what it is supposed to do, and this is where that
# name is held to.


@pytest.mark.parametrize("name", ["01-hijo.json", "02-pareja.json", "04-adversarial.json"])
def test_the_three_complete_briefs_pass(name):
    """04 is in this list on purpose: an adversarial brief is a *valid* brief.

    The attack is in the content of a field, not in the shape of the document,
    and a schema that rejected it would be rejecting the case the exam asks us
    to survive rather than surviving it.
    """
    result = domain.check(example(name))
    assert result.status == "ok", (result.questions, result.contradictions, result.errors)


def test_brief_03_is_both_missing_data_and_a_contradiction():
    """The case FLOW-0 exists for: nothing is spent, and the buyer is told both
    things at once — the questions to answer and the pair that cannot stand.

    Its adult marker is in `genre` ("adult noir thriller") and its `tone` is
    null, which is why the rule reads both fields and not the one AC-1's
    sentence happens to name.
    """
    result = domain.check(example("03-faltan-datos.json"))
    assert result.status == "contradiction"
    assert len(result.contradictions) == 1
    assert "8" in result.contradictions[0]
    assert "adult noir thriller" in result.contradictions[0]
    # Still asked, in the same breath. Two round trips for one fix is how a
    # buyer abandons the form.
    assert len(result.questions) == 2, result.questions
    assert any("tone" in q for q in result.questions)
    assert any("memor" in q.lower() for q in result.questions)


def test_brief_05_holds_a_field_this_contract_does_not_declare():
    """`recipient.birth_date`, and it is reported rather than swallowed.

    The five files are the contract and this one asks for a twelfth key. Two
    honest outcomes exist — widen `Recipient` or drop the key from the fixture —
    and both are the owner's to choose, so what this phase does is refuse
    silently dropping it: a birth date accepted and discarded is the temporal
    validator reading a brief that never said when the man was born.
    """
    result = domain.check(example("05-incoherencia-temporal.json"))
    assert result.status == "invalid"
    assert any("birth_date" in e for e in result.errors), result.errors


def test_brief_05_is_temporally_incoherent_and_this_phase_cannot_see_it():
    """Which is the whole reason the file exists.

    With the undeclared key removed it is a complete, contradiction-free brief:
    the memories put Iker at university three years before he was born and at
    his own wedding aged nine, and nothing in E2 looks at a date. It passes
    here, and `lean_chronology` is what it is written to fail.
    """
    payload = example("05-incoherencia-temporal.json")
    payload["recipient"] = {k: v for k, v in payload["recipient"].items()
                            if k != "birth_date"}
    assert domain.check(payload).status == "ok"


def test_the_five_briefs_are_served_whole_including_the_ones_that_fail():
    served = domain.examples()
    assert [b["id"] for b in served] == [
        "01-hijo", "02-pareja", "03-faltan-datos", "04-adversarial",
        "05-incoherencia-temporal"]
    assert all(b["purpose"] for b in served), "a brief that does not say what it is for"


def test_the_envelope_is_not_a_brief_field():
    """`id` and `purpose` belong to the eval file, not to the order. They are
    dropped on the way in, which is also why they cannot be smuggled in by a
    buyer: every other unknown key is still an error."""
    brief = domain.parse(example("01-hijo.json"))
    assert brief.recipient.alias == "Leo"
    assert not hasattr(brief, "purpose")


# --------------------------------------------------------- the edge


@pytest.fixture
def client(db):
    """The router on its own app.

    `backend/main.py` is wired by hand, one phase at a time, and the route pin
    in `test_api_contract.py` says which routes the app serves. Mounting here
    tests this module without pre-empting either.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.brief import router as brief_router

    app = FastAPI()
    app.dependency_overrides[brief_router.get_conn] = lambda: db
    app.include_router(brief_router.router, prefix="/api/briefs")
    with TestClient(app) as c:
        yield c


def test_check_answers_without_storing_anything(client, db):
    body = client.post("/api/briefs/check", json=example("03-faltan-datos.json")).json()
    assert body["status"] == "contradiction"
    assert body["questions"] and body["contradictions"]
    assert db.execute("SELECT COUNT(*) FROM briefs").fetchone()[0] == 0, (
        "a brief nobody accepted was written to the database")


def test_an_accepted_brief_is_stored_and_answers_with_its_id(client, db):
    created = client.post("/api/briefs", json=example("01-hijo.json"))
    assert created.status_code == 201
    brief_id = created.json()["id"]
    stored = db.execute("SELECT payload FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    assert json.loads(stored["payload"])["recipient"]["alias"] == "Leo"


def test_a_brief_that_did_not_pass_is_refused_with_the_questions(client, db):
    """422 and not 201: the run that would have followed costs money, and the
    frontend needs the questions in the refusal to be able to show them."""
    refused = client.post("/api/briefs", json=example("03-faltan-datos.json"))
    assert refused.status_code == 422
    detail = refused.json()["detail"]
    assert detail["status"] == "contradiction"
    assert detail["questions"] and detail["contradictions"]
    assert db.execute("SELECT COUNT(*) FROM briefs").fetchone()[0] == 0


def test_the_stored_brief_is_the_validated_one_not_the_body_that_arrived(client, db):
    """The envelope, and anything else a client hopes to keep, does not survive
    the trip: what is stored is what `Brief` accepted."""
    created = client.post("/api/briefs", json=example("04-adversarial.json"))
    stored = json.loads(db.execute(
        "SELECT payload FROM briefs WHERE id = ?", (created.json()["id"],)
    ).fetchone()["payload"])
    assert set(stored) == set(Brief.model_fields)
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in stored["free_text"]


def test_the_examples_endpoint_serves_the_five(client):
    served = client.get("/api/briefs/examples").json()
    assert len(served) == 5
    assert served[3]["id"] == "04-adversarial"


# --------------------------------------------------- migration 014


def test_the_briefs_table_exists_and_is_strict(db):
    """STRICT, so a brief whose `length_chapters` arrives as the string "ten"
    is a write that fails rather than a column that quietly holds text."""
    sql = db.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'briefs'").fetchone()["sql"]
    assert "STRICT" in sql
    db.execute("INSERT INTO briefs (id, created_at, payload) VALUES (?,?,?)",
               ("b1", "2026-09-23T00:00:00Z", '{"occasion": "birthday"}'))
    with pytest.raises(Exception):
        db.execute("INSERT INTO briefs (id, created_at, payload) VALUES (?,?,?)",
                   ("b2", "2026-09-23T00:00:00Z", "not json at all"))


# ------------------------------------------- the interviewer agent
# `test_agents_frontmatter.py` is the authority model's own test and it
# enumerates the agents it knows. Until E2's row is added there, this is where
# the eleventh agent's tool list is held — the guarantee is too central to
# arrive unguarded.


AGENT = Path(__file__).resolve().parents[2] / ".claude" / "agents" / "interviewer.md"


def _front_matter() -> dict[str, str]:
    import re

    text = AGENT.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "interviewer.md has no front matter"
    return {k.strip(): v.strip()
            for k, _, v in (line.partition(":") for line in match.group(1).splitlines())
            if k.strip()}


def test_the_interviewer_holds_glob_and_haiku():
    """`Glob` returns paths and cannot return contents. The interviewer is
    handed the buyer's words in its prompt and can reach nothing else — not the
    Bible, not a previous novel, not another buyer's brief."""
    assert _front_matter()["tools"] == "Glob"
    assert _front_matter()["model"] == "haiku"


def test_the_interviewer_cannot_read_a_file():
    tools = {t.strip() for t in _front_matter()["tools"].split(",")}
    assert tools & {"Read", "Grep", "Bash", "WebFetch", "Task", "Agent", "Write"} == set()


def test_the_interviewer_is_told_it_does_not_decide():
    """The sentence is the phase's whole design: the rules are in
    `domain.py` and an agent that believed itself the judge of completeness
    would answer differently on Tuesday."""
    body = AGENT.read_text(encoding="utf-8").lower()
    assert "you do not decide" in body
    assert "free_text" in body, "the one field it must copy and never obey"
