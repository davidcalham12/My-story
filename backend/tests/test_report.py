"""Is this run sound? One command, for a person.

Fourteen instruments exist and a day was spent finding what each is for. A person
should not have to remember any of them to ask whether a run is sound.

The tests that matter here are about **what the report refuses to say**: an
unarchived run is `unchecked` and not sound, and the exit code says nothing about
a run nobody checked — because an exit code cannot say "passed" without lying
when nothing looked.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.report import build

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"


def run(*args: str):
    return subprocess.run([sys.executable, "-m", "backend.report", *args],
                          capture_output=True, text=True, cwd=ROOT)


def test_it_reads_a_real_finished_run():
    out = build(OUTPUT / "lighthouse-keeper-ledger")
    assert out["chapters_in_the_book"] == [1, 2, 3]
    assert out["cost"]["total_usd"] == pytest.approx(18.82, abs=0.01)
    assert out["cost"]["provenance"] == "measured"


def test_a_run_with_no_cost_reports_absent_not_zero(tmp_path):
    (tmp_path / "chapters").mkdir()
    out = build(tmp_path)
    assert out["cost"]["total_usd"] is None
    assert out["cost"]["provenance"] == "absent"


def test_a_run_nothing_archived_is_unchecked_not_sound(tmp_path):
    """The distinction the report exists to keep.

    A run nobody recomputed the gate for has not passed. Reporting it as
    conformant would be the absent-read-as-clean mistake at the top of the
    summary a person actually reads.
    """
    (tmp_path / "chapters").mkdir()
    out = build(tmp_path, db=None)
    assert out["gate"]["verdict"] == "unchecked"
    assert "why" in out["gate"]


def test_the_exit_code_is_non_zero_only_for_a_breach():
    """An unchecked run exits 0 with `unchecked` on the screen: it has not
    failed, and it has not passed, and an exit code cannot say the second."""
    result = run(str(OUTPUT / "lighthouse-keeper-ledger"), "no-such.db")
    assert result.returncode == 0
    assert json.loads(result.stdout)["gate"]["verdict"] == "unchecked"


def test_it_always_says_what_it_did_not_check():
    """A report that lists only what it verified reads as a clean bill of health.

    Three of the ten quality dimensions are not approached by anything here, and
    the report has to say so or it overstates itself by omission — the same rule
    the prose report follows.
    """
    out = build(OUTPUT / "lighthouse-keeper-ledger")
    assert out["unchecked"]
    assert any("worth reading" in item for item in out["unchecked"])


def test_something_that_is_not_a_run_is_refused(tmp_path):
    result = run(str(tmp_path))
    assert result.returncode == 2
    assert "does not look like a run" in result.stderr


@pytest.mark.parametrize("slug", sorted(
    p.parent.name for p in OUTPUT.glob("*/chapters") if p.is_dir()))
def test_every_run_in_the_repository_can_be_reported_on(slug):
    """Including the v1 ones, which have no cost.json, no numbered rules and no
    stated promises. A report that only works on the newest run is a report
    nobody trusts on an old one."""
    out = build(OUTPUT / slug)
    assert out["slug"] == slug
    assert "unchecked" in out
