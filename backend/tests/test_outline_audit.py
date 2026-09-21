"""Phase 6 — the FLOW-3 outline audit.

The open problem D25 brought into v1: a chapter can be impossible as
commissioned, and no amount of redrafting saves it. A run halted at chapter 3
after three attempts and the patch, and the writer had done nothing wrong — the
beat commissioned an event the world's rules did not admit.

Measured against a real outline, the audit costs $0.07-$0.13 and found two
defects the full five-critic gate missed across three attempts and a patch.
"""

from pathlib import Path

import pytest

from backend.commons.budget.ceiling import Budget
from backend.commons.config.loader import load_pricing
from backend.commons.context.semaphore import TokenSemaphore
from backend.commons.context.tokens import DeterministicCounter
from backend.commons.db import repository as repo
from backend.commons.llm.dispatch import Dispatcher
from backend.commons.llm.engine import MockEngine, Plan
from backend.outline.domain import beats, split_entries, titles
from backend.runs.orchestrator import Orchestrator

PREMISE = "A night-shift dispatcher logs a call from a climber already recovered."


def _orchestrator(db, tmp_path, plan=None):
    repo.create_run(db, run_id="r1", slug="night", premise=PREMISE,
                    profile="tiny", tone="procedural", snapshot={})
    return Orchestrator(
        conn=db,
        dispatcher=Dispatcher(
            engine=MockEngine(plan or Plan()),
            semaphore=TokenSemaphore(100_000),
            budget=Budget(ceiling_usd=100.0, pricing=load_pricing()),
            counter=DeterministicCounter(), conn=db, run_id="r1",
        ),
        run_id="r1", slug="night", premise=PREMISE, profile="tiny",
        tone="procedural", workspace=tmp_path / "night",
    )


def test_the_audit_runs_before_any_chapter_exists(db, tmp_path):
    """Cheap in an outline, expensive in a chapter. It must happen at FLOW-3."""
    orchestrator = _orchestrator(db, tmp_path)
    orchestrator.flow1_world()
    orchestrator.flow2_characters()
    orchestrator.flow3_outline()

    assert (tmp_path / "night" / "critiques" / "outline.audit.json").exists()
    assert not (tmp_path / "night" / "chapters").exists(), "no chapter yet"


def test_the_audit_is_recorded_against_the_run(db, tmp_path):
    orchestrator = _orchestrator(db, tmp_path)
    orchestrator.flow1_world()
    orchestrator.flow2_characters()
    orchestrator.flow3_outline()
    row = db.execute(
        "SELECT COUNT(*) AS n FROM calls WHERE stage = 'FLOW-3' "
        "AND agent = 'science-critic'"
    ).fetchone()
    assert row["n"] == 1


def test_a_failed_audit_becomes_a_visible_warning(db, tmp_path):
    """An impossible commission must be seen before FLOW-4 spends three attempts
    proving it cannot be written."""
    # chapter 0 is the audit's slot; the plan fails it there.
    orchestrator = _orchestrator(db, tmp_path, Plan(fail={(0, 1): ["science"]}))
    orchestrator.flow1_world()
    orchestrator.flow2_characters()
    orchestrator.flow3_outline()

    warnings = db.execute(
        "SELECT kind, detail FROM run_warnings WHERE kind = 'outline-audit'"
    ).fetchall()
    assert warnings, "the audit's findings reach the run record"


def test_beats_are_numbered_so_a_critic_can_name_the_missing_one(db, tmp_path):
    """An unnumbered list gives the outline critic nothing to name, and a critic
    that cannot name what is missing cannot write the replacement the third
    attempt depends on."""
    orchestrator = _orchestrator(db, tmp_path)
    orchestrator.flow1_world()
    orchestrator.flow2_characters()
    orchestrator.flow3_outline()

    entries = orchestrator.entries
    assert len(entries) == 3
    for entry in entries:
        assert len(beats(entry)) >= 3


def test_the_split_refuses_a_malformed_outline():
    """`### Chapter N - Title` exactly. A chapter writer handed nothing writes
    nothing, so the orchestrator redispatches rather than drafting from an empty
    entry."""
    with pytest.raises(ValueError, match="exactly"):
        split_entries("**Chapter 1: Wrong shape**\n\nSome prose.", 1)


def test_the_split_reads_a_real_v1_outline():
    """The format is not hypothetical: it is what eight runs produced."""
    path = (Path(__file__).resolve().parents[2] / "output"
            / "ice-station-water-recycler-surplus" / "outline.md")
    text = path.read_text(encoding="utf-8")
    entries = split_entries(text, 8)
    assert len(entries) == 8
    assert len(titles(text)) == 8
    assert len(beats(entries[0])) >= 3
