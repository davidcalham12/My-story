import pytest

from backend.commons.budget.ceiling import Budget, BudgetExceeded
from backend.commons.config.loader import load_pricing
from backend.commons.llm.engine import MockEngine, Plan
from backend.commons.log.calls import CallRow, write_call


def _prompt(chapter: int, attempt: int = 1, critic: str | None = None) -> str:
    head = "Premise: a lighthouse keeper on Titan receives her own distress calls"
    if critic:
        return f"{head}\nReturn JSON only. {critic}. chapter {chapter}. ATTEMPT {attempt}"
    return f"{head}\nYou are writing chapter {chapter}"


def test_mock_respects_the_premise():
    """v1's mock ignored the premise, which is why it never demonstrated
    anything. An artefact that mentions nothing from the brief cannot show the
    pipeline carried the brief through."""
    engine = MockEngine()
    reply = engine.complete(_prompt(1), model="m", max_tokens=100)
    assert "lighthouse" in reply.text


def test_plan_drives_named_failures_only():
    engine = MockEngine(Plan(fail={(2, 1): ["outline"]}))
    failed = engine.complete(_prompt(2, 1, "outline"), model="m", max_tokens=99)
    passed = engine.complete(_prompt(2, 2, "outline"), model="m", max_tokens=99)
    other = engine.complete(_prompt(2, 1, "science"), model="m", max_tokens=99)
    assert '"score": 4' in failed.text
    assert '"score": 10' in passed.text
    assert '"score": 10' in other.text, "only the named critic fails"


def test_mock_emits_out_of_band_and_headingless_text():
    """`length` and `chatter` are real code and must run on real text. Scripting
    the two characteristics that reproduce would be not testing them."""
    engine = MockEngine(Plan(out_of_band={3}, headingless={4}))
    short = engine.complete(_prompt(3), model="m", max_tokens=99).text
    bare = engine.complete(_prompt(4), model="m", max_tokens=99).text
    assert len(short.split()) < 50
    assert not bare.startswith("# Chapter")


def test_mock_is_deterministic():
    a = MockEngine().complete(_prompt(1), model="m", max_tokens=99).text
    b = MockEngine().complete(_prompt(1), model="m", max_tokens=99).text
    assert a == b


def test_mock_reports_its_provenance_honestly():
    """A counter is not an API. `estimated`, not `measured`."""
    reply = MockEngine().complete(_prompt(1), model="m", max_tokens=99)
    assert reply.provenance == "estimated"


# ------------------------------------------------------------------ budget


def test_budget_projects_worst_case():
    """Exact input plus max_tokens. A ceiling built on an ASSUMED reply is broken
    by one long answer, and a ceiling that can be exceeded is not a ceiling."""
    budget = Budget(ceiling_usd=10.0, pricing=load_pricing())
    projected = budget.project("claude-opus-5", input_tokens=1_000_000, max_tokens=1_000_000)
    assert projected == pytest.approx(5.0 + 25.0)


def test_budget_halts_before_the_call_that_would_exceed():
    budget = Budget(ceiling_usd=1.0, pricing=load_pricing())
    with pytest.raises(BudgetExceeded):
        budget.check("claude-opus-5", input_tokens=1_000_000, max_tokens=1_000_000)
    assert budget.spent_usd == 0.0, "nothing was spent; the call never happened"


def test_budget_refuses_to_guess_a_missing_rate():
    """A model with no rate is not free. Zero would let it spend without limit
    behind a ceiling that reads as enforced."""
    budget = Budget(ceiling_usd=10.0, pricing=load_pricing())
    with pytest.raises(BudgetExceeded):
        budget.project("opus", input_tokens=10, max_tokens=10)  # the family word


def test_recorded_cost_is_exact_not_bounded():
    budget = Budget(ceiling_usd=10.0, pricing=load_pricing())
    cost = budget.record("claude-sonnet-5", input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(2.0)
    assert budget.spent_usd == pytest.approx(2.0)


# --------------------------------------------------------------------- log


def test_call_row_carries_every_field(db):
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('r','s','p','tiny','{}','FLOW-4','now')")
    write_call(db, CallRow(
        run_id="r", stage="FLOW-4", agent="continuity-critic",
        model="claude-sonnet-5", ts="2026-09-21T12:00:00Z", chapter=2, attempt=1,
        input_tokens=14_000, output_tokens=600, cost_usd=0.034,
        provenance="measured", tokens_reserved=30_000,
        in_flight_at_dispatch=60_000, wait_ms=120, duration_ms=8400,
    ))
    row = db.execute("SELECT * FROM calls").fetchone()
    assert row["input_tokens"] == 14_000 and row["output_tokens"] == 600
    assert row["tokens_reserved"] == 30_000
    assert row["in_flight_at_dispatch"] == 60_000
    assert row["wait_ms"] == 120
    assert row["provenance"] == "measured"


def test_provenance_cannot_be_invented(db):
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('r','s','p','tiny','{}','FLOW-4','now')")
    with pytest.raises(Exception):
        write_call(db, CallRow(run_id="r", stage="s", agent="a", model="m",
                               ts="now", provenance="probably-fine"))
