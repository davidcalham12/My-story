"""The eval table is checked, not snapshotted.

`evals/results.md` is a file somebody reads at the exam and nobody re-derives.
A table that quietly stopped matching the code would still look like evidence,
which is the worst thing a table can do. These tests hold the two halves
together: the expectations written next to the readings, and the readings
themselves.

They cost nothing and start no run. The half of the eval that needs a novel is
`--novel`, and it is absent from this file for the same reason it is absent
from the table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.brief import domain                                    # noqa: E402
from evals import run_eval                                          # noqa: E402

IDS = ["01-hijo", "02-pareja", "03-faltan-datos", "04-adversarial",
       "05-incoherencia-temporal"]


def brief(name: str) -> dict:
    return run_eval.load(run_eval.BRIEFS / f"{name}.json")


def test_every_committed_brief_has_a_recorded_expectation():
    """A brief with no expectation is a row nobody has to defend."""
    assert sorted(run_eval.EXPECTED) == sorted(IDS)
    for name, spec in run_eval.EXPECTED.items():
        assert spec["expect_status"] in ("ok", "incomplete", "contradiction", "invalid")
        assert len(spec["why"]) > 40, f"{name}: say what the brief is for"


@pytest.mark.parametrize("name", IDS)
def test_the_table_says_what_the_code_does(name):
    """The expectation and the reading, held against each other.

    This is the test the table exists to earn. If `domain.check` changes its
    mind about a brief, the eval stops agreeing with itself here rather than in
    a printed table at the exam.
    """
    row = run_eval.flow0(brief(name))
    assert row["status"] == domain.check(brief(name)).status
    assert run_eval.verdict(row) == "as expected", row


def test_two_of_the_five_do_not_pass_and_that_is_the_point():
    """A table where every row said `ok` would prove nothing.

    Two, not three, and the arithmetic is worth stating because it is easy to
    say "three of these are written to fail" and be wrong. Three briefs pass
    FLOW-0. `03` is refused for exactly the reason it was written. `05` is
    refused for a **different** reason than the one it was written for -- an
    undeclared key -- and the temporal incoherence it exists to carry is
    invisible to this phase entirely.
    """
    statuses = {name: run_eval.flow0(brief(name))["status"] for name in IDS}
    refused = {n: s for n, s in statuses.items() if s != "ok"}

    assert set(refused) == {"03-faltan-datos", "05-incoherencia-temporal"}, statuses
    assert refused["03-faltan-datos"] == "contradiction"
    assert refused["05-incoherencia-temporal"] == "contradiction", (
        "since birth_date is declared, 05 is refused for the reason it was written")


def test_the_injection_is_a_row_and_never_an_instruction():
    """Brief 04's three questions, asked of the code rather than of a model."""
    row = run_eval.flow0(brief("04-adversarial"))

    assert row["injection_is_a_fact"] is True, "dropping it silently is not safety"
    assert row["injection_is_verbatim"] is True, "kept whole, attack and gift together"
    assert row["gift_survived"] is True, "the filter that dropped one would drop both"
    assert row["injection_is_mandatory"] is False, \
        "the publish gate must never be told to make this appear in the novel"


def test_the_premise_built_for_a_run_never_carries_the_free_text():
    """The one field an attacker controls does not reach the orchestrator.

    It reaches the novel as a `freetext` fact with its source attached, which is
    a row. Pasting it into the premise would make it a sentence the orchestrator
    reads, which is the one thing SPEC-EXAM-001 AC-2 forbids.
    """
    payload = brief("04-adversarial")
    premise = run_eval.premise_for(payload)

    assert run_eval.INJECTION.lower() not in premise.lower()
    assert "developer mode" not in premise.lower()
    assert "system prompt" not in premise.lower()
    # And it is still a usable premise rather than an empty string.
    assert payload["recipient"]["alias"] in premise
    assert payload["genre"] in premise


def test_a_brief_that_does_not_pass_flow0_cannot_start_a_run():
    """Spending money on a brief the code already refused is the bug this
    prevents; it raises before it touches the database."""
    with pytest.raises(SystemExit) as caught:
        run_eval.run_novel("03-faltan-datos")
    assert "FLOW-0" in str(caught.value)


def test_the_eval_profile_is_the_exam_pipeline_at_a_smaller_size():
    """Not `tiny`: an eval that scored continuity against a cast of three would
    not be measuring what the exam novel does."""
    from backend.commons.config import loader

    ev, exam, tiny = (loader.resolve(n) for n in ("eval", "exam", "tiny"))

    assert ev["novel"]["chapters"] == 3, "three chapters, so four briefs are affordable"
    assert ev["bible"] == exam["bible"], "the same canon the exam novel carries"
    assert ev["bible"] != tiny["bible"]
    assert ev["budget"]["max_cost_usd"] < exam["budget"]["max_cost_usd"]
    assert ev["context"]["max_concurrent_tokens"] == exam["context"]["max_concurrent_tokens"], \
        "the ceiling is the owner's requirement and does not bend for an eval"
