"""The fallback the owner approved (spec §8, "va", Q29) must be reachable.

In a real run `_execute` always conducted, so the single-orchestrator path —
the fallback — existed only under the recorded stream. `NOVAFORGE_ORCHESTRATOR=
single` is the switch; anything else keeps the conductor.
"""

from __future__ import annotations

from backend.commons.config import settings as settings_mod
from backend.commons.config.settings import Settings
from backend.runs.service import RunService


def _svc(db, tmp_path, single: bool) -> tuple[RunService, list[str]]:
    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=False,
                                  single_orchestrator=single))
    called: list[str] = []
    svc._execute_single = lambda *a, **k: called.append("single")
    svc._conduct = lambda *a, **k: called.append("conductor")
    svc.get = lambda run_id: {"slug": "s"}
    return svc, called


class _Live:
    run_id = "r"


def test_the_switch_takes_the_single_path(db, tmp_path):
    svc, called = _svc(db, tmp_path, single=True)
    svc._execute(_Live(), "p", "exam", "", {})
    assert called == ["single"]


def test_without_it_a_real_run_is_conducted(db, tmp_path):
    svc, called = _svc(db, tmp_path, single=False)
    svc._execute(_Live(), "p", "exam", "", {})
    assert called == ["conductor"]


def test_the_environment_sets_it(monkeypatch):
    monkeypatch.setenv("NOVAFORGE_ORCHESTRATOR", "single")
    assert settings_mod.load_settings().single_orchestrator is True
    monkeypatch.setenv("NOVAFORGE_ORCHESTRATOR", "conductor")
    assert settings_mod.load_settings().single_orchestrator is False
