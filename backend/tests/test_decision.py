"""SPEC-004 — what follows an attempt, decided by arithmetic.

This was a paragraph in `SKILL.md`, read by a model at the moment a run has
spent an hour and is about to be thrown away. That is exactly when "it is only
just below" gets rationalised, and `accept_with_warnings` is what rationalising
looked like when it won.

A6 is the test that matters: every aggregate at every attempt number, asserting
that nothing below the threshold is ever accepted. It is cheap enough to be
exhaustive, so it is exhaustive.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from backend.chapters.domain import THRESHOLD_DEFAULT, decide

MAX = 3


def d(aggregate, attempt, *, patched=False, max_attempts=MAX):
    return decide(aggregate=aggregate, attempt=attempt, max_attempts=max_attempts,
                  patched=patched, threshold=THRESHOLD_DEFAULT)


def test_a_passing_attempt_is_accepted_whatever_its_number():
    for attempt in range(1, MAX + 1):
        assert d(8, attempt).action == "accept"
        assert d(10, attempt).action == "accept"


def test_a_failure_with_attempts_left_is_a_retry():
    assert d(7, 1).action == "retry"
    assert d(3, 2).action == "retry"


def test_a_failure_on_the_last_attempt_is_the_patch_never_an_acceptance():
    decision = d(7, MAX)
    assert decision.action == "patch"
    assert decision.action != "accept"


def test_a_failure_after_the_patch_halts():
    decision = d(7, MAX, patched=True)
    assert decision.action == "halt"
    assert "patch" in decision.why.lower()


def test_a_chapter_the_patch_rescued_is_accepted_and_recorded_as_patched():
    decision = d(9, MAX, patched=True)
    assert decision.action == "accept"
    assert decision.verdict == "patched", (
        "it passed, and it did not pass on its own; a reader is entitled to both"
    )


def test_an_unpatched_acceptance_is_not_recorded_as_patched():
    assert d(9, 1).verdict == "accept"


@pytest.mark.parametrize("attempt", range(1, MAX + 1))
@pytest.mark.parametrize("aggregate", range(0, THRESHOLD_DEFAULT))
@pytest.mark.parametrize("patched", [False, True])
def test_nothing_below_the_threshold_is_ever_accepted(aggregate, attempt, patched):
    """A6, exhaustive. The whole spec is this assertion."""
    assert d(aggregate, attempt, patched=patched).action != "accept"


@pytest.mark.parametrize("attempt", range(1, MAX + 1))
@pytest.mark.parametrize("patched", [False, True])
def test_no_usable_verdict_is_never_accepted(attempt, patched):
    """A7. `None` is not a low score; it is the absence of a score.

    A gate running on four characteristics is a weaker gate, not a passing one,
    and this once returned 10.
    """
    decision = d(None, attempt, patched=patched)
    assert decision.action != "accept"


def test_the_halt_is_not_reachable_before_the_patch_has_been_tried():
    """`patch_then_halt` is two words in that order.

    Halting at attempt 3 without applying the critics' own replacements would
    throw away a run that the patch might have rescued — which is what the third
    attempt's escalation costs 46,000 tokens to make possible.
    """
    for aggregate in range(0, THRESHOLD_DEFAULT):
        assert d(aggregate, MAX).action == "patch"


def test_the_decision_is_runnable_as_a_script_the_orchestrator_can_call():
    """A8. A rule the orchestrator cannot invoke is a rule it has to remember."""
    payload = json.dumps({"aggregate": 7, "attempt": 3, "patched": True})
    proc = subprocess.run(
        [sys.executable, "-m", "backend.chapters.decide"],
        input=payload, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["action"] == "halt"
    assert out["why"]


def test_the_script_refuses_a_payload_it_cannot_read_rather_than_guessing():
    proc = subprocess.run(
        [sys.executable, "-m", "backend.chapters.decide"],
        input="not json", capture_output=True, text=True,
    )
    assert proc.returncode != 0
    # A decision script that answers anyway is worse than one that fails: the
    # orchestrator would obey an answer nothing produced.
    assert "accept" not in proc.stdout
