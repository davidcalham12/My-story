"""Every check a stage owes, in one command.

Seven instruments stand between a run and a defect, each with its own
invocation, each remembered at its own moment. **Remembering is what has failed
here, repeatedly** — a chapter promoted at 5, a cap exceeded five times, a
verdict written in a vocabulary the database rejects. None of those was
forgotten on purpose.

So the orchestrator remembers one thing per stage, and this file is the mapping.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.checks import BY_STAGE

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"


def run(*args: str):
    return subprocess.run([sys.executable, "-m", "backend.checks", *args],
                          capture_output=True, text=True, cwd=ROOT)


def test_every_registered_check_names_a_module_that_exists():
    """A mapping to a module that is not there fails at the worst moment."""
    for stage, checks in BY_STAGE.items():
        for name, parts in checks:
            module = parts[0].replace(".", "/") + ".py"
            assert (ROOT / module).is_file(), f"{stage} / {name} -> {module}"


def test_every_instrument_is_reachable_from_some_stage():
    """An instrument nothing calls is an instrument nobody runs.

    `decide`, `promote` and `score_prose` are deliberately absent: they decide
    or need inputs only the orchestrator has, and they are called at their own
    moments. Everything else must be on a stage's list or it is dead weight
    pretending to be a check.
    """
    registered = {parts[0] for checks in BY_STAGE.values() for _, parts in checks}
    decide_at_their_own_moment = {
        "backend.chapters.decide",
        "backend.chapters.promote",
        "backend.chapters.score_prose",
    }
    on_disk = {
        f"backend.chapters.{p.stem}"
        for p in (ROOT / "backend/chapters").glob("check_*.py")
    }
    missing = on_disk - registered - decide_at_their_own_moment
    assert not missing, f"instruments no stage calls: {sorted(missing)}"


def test_a_clean_chapter_reports_nothing_failed():
    result = run("FLOW-4", str(OUTPUT / "lighthouse-keeper-ledger"), "1")
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["failed"] == []
    assert len(out["ran"]) == len(BY_STAGE["FLOW-4"])


def test_a_failing_check_is_named_and_the_exit_code_says_so():
    """The long run exceeded its summary cap; the combined command has to say
    which check failed, not merely that something did."""
    result = run("FLOW-4", str(OUTPUT / "cartographer-inconstant-valley"), "4")
    assert result.returncode == 1
    assert "summary within its cap" in json.loads(result.stdout)["failed"]


def test_an_unknown_stage_is_refused_rather_than_reported_all_clear():
    """Not "nothing to do". An unknown stage means the caller believes in a
    check that does not exist, and answering "all clear" would confirm it."""
    result = run("FLOW-9", str(OUTPUT / "lighthouse-keeper-ledger"))
    assert result.returncode == 2
    assert "no checks registered" in result.stderr


def test_a_stage_that_needs_a_chapter_says_so():
    result = run("FLOW-4", str(OUTPUT / "lighthouse-keeper-ledger"))
    assert result.returncode == 2
    assert "needs a chapter" in result.stderr


def test_it_reports_and_does_not_gate():
    """`decide` and `promote` are the only things that refuse. A checker that
    also gated would be a second place the gate lives, and this repository has
    spent a day on what that costs."""
    out = json.loads(run("FLOW-4", str(OUTPUT / "lighthouse-keeper-ledger"), "1").stdout)
    assert "does not gate" in out["note"]


@pytest.mark.parametrize("stage", sorted(BY_STAGE))
def test_the_skill_calls_the_combined_command_for_every_stage_that_has_one(stage):
    """A mapping the procedure never invokes is a list nobody reads."""
    skill = (ROOT / ".claude/skills/novaforge/SKILL.md").read_text(encoding="utf-8")
    assert f"backend.checks {stage}" in skill, stage


# ------------------------------------------------------- PLAN-007 6.12


def _log(tmp_path, rows):
    run_dir = tmp_path / "run"
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "logs" / "agents.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return run_dir


def _check_log(run_dir):
    return subprocess.run([sys.executable, "-m", "backend.chapters.check_log", str(run_dir)],
                          capture_output=True, text=True, cwd=ROOT)


def test_a_log_with_parseable_monotonic_timestamps_passes_and_reports_their_provenance(tmp_path):
    """SPEC-007 §8 point 2 / AC-16 (I): every call row has a `ts`. The check
    does not demand `measured` — a derived timestamp honestly labelled is
    provenance, not a defect — but it counts them, because 47 of 50 rows on the
    first real v2 run were `derived_from_duration`."""
    run_dir = _log(tmp_path, [
        {"ts": "2026-09-22T15:55:20Z", "ts_source": "measured", "agent": "worldbuilder"},
        {"ts": "2026-09-22T15:57:00Z", "ts_source": "derived_from_duration", "agent": "character-architect"},
        {"ts": "2026-09-22T15:57:00Z", "ts_source": "derived_from_duration", "agent": "plot-architect"},
    ])
    result = _check_log(run_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    body = json.loads(result.stdout)
    assert body["rows"] == 3 and body["monotonic"] is True
    assert body["ts_source"] == {"measured": 1, "derived_from_duration": 2}


def test_a_log_with_an_unparseable_or_backwards_timestamp_fails_and_names_the_row(tmp_path):
    run_dir = _log(tmp_path, [
        {"ts": "2026-09-22T15:55:20Z", "ts_source": "measured", "agent": "worldbuilder"},
        {"ts": "yesterday-ish", "agent": "character-architect"},
        {"ts": "2026-09-22T15:50:00Z", "ts_source": "measured", "agent": "plot-architect"},
    ])
    result = _check_log(run_dir)
    assert result.returncode == 1
    body = json.loads(result.stdout)
    assert body["monotonic"] is False
    problems = " ".join(body["problems"])
    assert "row 2" in problems and "row 3" in problems
    assert body["ts_source"].get("absent") == 1, "a row with no ts_source is counted as absent, not as measured"


def test_the_real_run_log_is_checked_at_flow_6():
    assert any(parts[0] == "backend.chapters.check_log" for _, parts in BY_STAGE["FLOW-6"])
    result = _check_log(OUTPUT / "lighthouse-keeper-ledger")
    assert result.returncode == 0, result.stdout + result.stderr
    body = json.loads(result.stdout)
    assert body["rows"] > 0 and body["ts_source"].get("derived_from_duration", 0) > 0
