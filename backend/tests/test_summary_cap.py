"""The rolling summary against its cap, measured on the runs that exist.

The project's central architectural claim is that chapter thirty-four's prompt is
the same size as chapter one's. The Bible is fixed and the outline entry is one
chapter's; **the rolling summary is the only part that can grow with the book**,
and `context.max_summary_words` is the only thing stopping it.

Nothing was checking it, and it was being exceeded.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"


def run(run_dir: Path, chapter: int | None = None):
    args = [sys.executable, "-m", "backend.chapters.check_summary", str(run_dir)]
    if chapter is not None:
        args.append(str(chapter))
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)


def runs_with_summaries() -> list[str]:
    return sorted({p.parent.parent.name
                   for p in OUTPUT.glob("*/chapters/ch*.summary.md")
                   if (p.parent.parent / "config.snapshot.json").is_file()})


def test_there_is_something_to_measure():
    assert runs_with_summaries()


def test_a_summary_within_its_cap_passes(tmp_path):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "config.snapshot.json").write_text(
        json.dumps({"context": {"max_summary_words": 10}}), encoding="utf-8")
    (tmp_path / "chapters" / "ch01.summary.md").write_text(
        "one two three four five", encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["over"] == 0


def test_a_summary_over_its_cap_is_reported_with_the_overshoot(tmp_path):
    (tmp_path / "chapters").mkdir()
    (tmp_path / "config.snapshot.json").write_text(
        json.dumps({"context": {"max_summary_words": 4}}), encoding="utf-8")
    (tmp_path / "chapters" / "ch01.summary.md").write_text(
        "one two three four five six", encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["over"] == 1
    assert out["summaries"][0]["over_by"] == 2
    assert out["worst_overshoot_pct"] == 50


def test_it_reads_the_cap_the_run_had_not_the_one_in_the_config_today(tmp_path):
    """A run is judged by the numbers it ran with.

    Reading the live config would measure a finished run against a cap it never
    had — the same category error as judging a five-characteristic run by six.
    """
    (tmp_path / "chapters").mkdir()
    (tmp_path / "config.snapshot.json").write_text(
        json.dumps({"context": {"max_summary_words": 999}}), encoding="utf-8")
    (tmp_path / "chapters" / "ch01.summary.md").write_text("a b c", encoding="utf-8")
    assert json.loads(run(tmp_path).stdout)["cap"] == 999


def test_a_missing_cap_is_refused_not_treated_as_unlimited(tmp_path):
    """Absent is not permission."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "config.snapshot.json").write_text("{}", encoding="utf-8")
    (tmp_path / "chapters" / "ch01.summary.md").write_text("a b c", encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 2
    assert "nothing can be checked" in result.stderr


@pytest.mark.parametrize("slug", runs_with_summaries())
def test_what_the_real_runs_actually_did(slug):
    """The measurement, recorded as a test so it cannot quietly get worse.

    `small` ran five of six summaries over a 200-word cap, the worst by 23%. The
    cap was being read as a target rather than a limit, which is what a number
    nobody measures becomes.

    **This asserts the overshoot stays bounded, not that it is zero.** Asserting
    zero would fail on runs already in the repository and teach the next reader
    to delete the test. What matters is that it is an overshoot and not a
    runaway: a summary at twice its cap would mean the flat curve is gone.
    """
    out = json.loads(run(OUTPUT / slug).stdout)
    assert out["worst_overshoot_pct"] < 50, (
        f"{slug}: a summary more than half again over its cap is no longer "
        f"slack in the flat-cost claim — it is the claim failing"
    )
