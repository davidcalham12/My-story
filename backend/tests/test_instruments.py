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
