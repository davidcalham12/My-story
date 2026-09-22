"""PLAN-007 6.5 — FR-BUD-4: the ceiling comes from the profile, never a literal.

Before this phase the budget watcher read `NOVAFORGE_BUDGET` (default 25) and
never looked at the profile, whose `max_cost_usd` for `tiny` was 5.0 — a figure
below the measured cost of a tiny run. Two numbers for one concept, and neither
was the one the run obeyed.
"""

from pathlib import Path

import pytest

from backend.commons.config import loader
from backend.commons.config.settings import Settings
from backend.runs.service import RunService


def _service(db, tmp_path, env_ceiling):
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                        use_recorded_stream=False, budget_ceiling_usd=env_ceiling)
    return RunService(db, settings)


def test_the_ceiling_is_the_profile_figure_when_the_env_is_unset(db, tmp_path):
    svc = _service(db, tmp_path, env_ceiling=None)
    tiny = loader.resolve("tiny")
    assert svc.ceiling_for(tiny) == tiny["budget"]["max_cost_usd"]
    stress = loader.resolve("stress")
    assert svc.ceiling_for(stress) == stress["budget"]["max_cost_usd"]
    assert svc.ceiling_for(tiny) != svc.ceiling_for(stress), "profiles differ, so must ceilings"


def test_the_env_only_lowers_the_ceiling_never_raises_it(db, tmp_path):
    tiny = loader.resolve("tiny")
    profile_figure = tiny["budget"]["max_cost_usd"]
    assert _service(db, tmp_path, env_ceiling=profile_figure / 2).ceiling_for(tiny) == profile_figure / 2
    assert _service(db, tmp_path, env_ceiling=profile_figure * 40).ceiling_for(tiny) == profile_figure


def test_the_same_figure_reaches_argv_and_the_watcher(db, tmp_path):
    """FR-BUD-1 and AC-21 together: one number, two lines of defence."""
    svc = _service(db, tmp_path, env_ceiling=None)
    tiny = loader.resolve("tiny")
    process = svc._process("A premise long enough.", "tiny", "", tiny)
    i = process.command.index("--max-budget-usd")
    assert float(process.command[i + 1]) == svc.ceiling_for(tiny)
    assert svc._budget_watcher(tiny).ceiling_usd == svc.ceiling_for(tiny)


def test_tiny_can_afford_the_run_it_was_measured_at():
    """P-1, resolved at the plan's approval: 25.0. A tiny run measured $18.82;
    a ceiling of 5.0 would halt every one of them at chapter 1."""
    assert loader.resolve("tiny")["budget"]["max_cost_usd"] == 25.0


def test_the_env_default_is_absent_not_twenty_five(monkeypatch):
    """Unset means 'the profile decides'. A default of 25 read as 'the env says
    25' and silently overrode every profile."""
    from backend.commons.config.settings import load_settings
    monkeypatch.delenv("NOVAFORGE_BUDGET", raising=False)
    assert load_settings().budget_ceiling_usd is None
    monkeypatch.setenv("NOVAFORGE_BUDGET", "7.5")
    assert load_settings().budget_ceiling_usd == pytest.approx(7.5)
