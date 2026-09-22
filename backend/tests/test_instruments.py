"""LOOP-003's instruments, run rather than trusted.

Both ship with `--self-test` and neither ran anywhere automatic.
`verification.md` §3.12 named them as a signal we would notice a broken
procedure by — a signal nobody was reading.

`validate-sheet` is the one that matters most: it decides whether a feedback
sheet may be sent to the writer at all, and `verification.md` §5 lists it as the
thing standing between an incomplete sheet and a redraft.

Skipped rather than failed when node is absent, because a suite that cannot run
on a machine without node is a suite people stop running.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOOP = ROOT / "specs/loops/LOOP-003"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not on PATH")


def run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(LOOP / script), "--self-test"],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_the_sheet_validator_behaves():
    result = run("validate-sheet.mjs")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout


def test_the_measurement_instrument_reproduces_the_committed_run():
    """§6.2 fixes what it must reproduce, against a run that is in the repository.

    Its SKIPs are legitimate and named: two assertions cannot run because that
    run did not keep its rejected drafts, which is the defect that made
    `keep_attempt_drafts` true. A skip that says why is evidence; a silent pass
    over the same hole would not be.
    """
    result = run("measure.mjs")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout
    assert "reproduces the committed run" in result.stdout


# ------------------------------------------------------- PLAN-007 6.9


def test_the_measurement_instrument_knows_six_characteristics():
    """SPEC-007 FR-INS-3 / AC-14. The instrument said five for a day after the
    gate had six; `prose` was invisible to it. On a five-characteristic run it
    must print `prose —` (absent), never omit the column."""
    result = subprocess.run(
        ["node", str(LOOP / "measure.mjs"), "lighthouse-keeper-ledger"],
        capture_output=True, text=True, cwd=ROOT, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "prose" in result.stdout
    assert "prose —" in result.stdout, "the run predates prose: absent, not omitted"


def test_the_measurement_self_test_names_prose_as_skipped():
    result = run("measure.mjs")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "prose" in result.stdout.lower()
    assert "SKIP" in result.stdout


SIX_SCORE_SHEET = """CHAPTER 2 — ATTEMPT 2 OF 3

SCORES FROM THE PREVIOUS ATTEMPT
  Continuity 7 · Science 8 · Outline 10 · Length 10 · Heading 10 · Prose 9
  The lowest is 7. All six must reach 8.

DO NOT TOUCH — these passed, and changing them can only cost you:
  Science · Outline · Length · Heading · Prose

OPEN — Continuity (1 finding, worst first)
  1. [medium] Timeline arithmetic
     Quote:        "Drafted 0118 ship time, nine hours out, received 1912."
     What is wrong: 0118 to 1912 is eighteen hours, not nine.
     Against what:  bible/timeline.md, Day 2 — the offer arrives eighteen hours stale.
     How it should read: flight time plus time queued at the relay must total eighteen.

RESOLVED since the last attempt:
  (none — this is the first correction)

RULE: change only the lines quoted above.
"""


def _validate(tmp_path, text: str) -> subprocess.CompletedProcess:
    sheet = tmp_path / "sheet.md"
    sheet.write_text(text, encoding="utf-8")
    return subprocess.run(["node", str(LOOP / "validate-sheet.mjs"), str(sheet)],
                          capture_output=True, text=True, cwd=ROOT, encoding="utf-8")


def test_the_sheet_validator_requires_all_six_scores(tmp_path):
    """FR-INS-2 / AC-13: a sheet is refused when any of the six is missing —
    including the sixth, which the validator did not know existed."""
    assert _validate(tmp_path, SIX_SCORE_SHEET).returncode == 0
    without_prose = SIX_SCORE_SHEET.replace(" · Prose 9", "").replace(" · Prose", "")
    refused = _validate(tmp_path, without_prose)
    assert refused.returncode != 0
    assert "Prose" in refused.stdout + refused.stderr


def test_the_shipped_template_carries_six_slots():
    template = (LOOP / "sheet_template" / "v01.md").read_text(encoding="utf-8")
    assert "Prose {p}" in template
    assert "All six must reach 8" in template
    assert "five" not in template.lower()
