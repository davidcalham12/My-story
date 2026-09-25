"""SPEC-EXAM-008 AC-4: `GET /api/runs/{id}/costs` reads Langfuse, falls back to
the local table, and shows both figures when they disagree.

The Langfuse client is a fake with the one call the endpoint makes —
`api.observations.get_many`, the v2 endpoint — so nothing here opens a socket.
The credentials in the environment are dummies, and the test checks they never
appear in a response.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.commons.config.settings import Settings
from backend.commons.db import repository as repo
from backend.costs import router as costs_router
from backend.costs.measure import change_trace_id
from backend.main import app
from backend.runs import router as runs_router
from backend.runs.service import RunService

RUN_ID = "r1"
SLUG = "the-other-side-of-the-hill"
PK, SK = "pk-lf-dummy-000000000000", "sk-lf-dummy-111111111111"


def seed(db) -> None:
    repo.create_run(db, run_id=RUN_ID, slug=SLUG, premise="a premise long enough",
                    profile="exam", tone=None, snapshot={})
    db.executemany(
        "INSERT INTO changes (run_id, n, kind, version, chapters, label, started_at, "
        "finished_at, total_usd, minutes, orchestrator_model, orchestrator_usd, "
        "agents_model, agents_usd, provenance, results, unresulted, sources, note) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(RUN_ID, 1, "generate", None, None, None, "2026-09-24T15:24:29Z", None,
          53.1745489, 118.6, "claude-opus-5[1m]", 48.7945489, "claude-haiku-4-5-20251001",
          4.38, "measured", 1, 0, '["events seq 2038"]', None),
         (RUN_ID, 2, "continue", None, None, None, "2026-09-24T17:41:17Z", None,
          21.0301599, 50.7, "claude-opus-5[1m]", 19.3387, "claude-haiku-4-5-20251001",
          1.6914599, "measured", 1, 0, '["logs/resume.stream.jsonl"]', None),
         (RUN_ID, 3, "reader_change", None, "[3]", "dist/_aborted-change-1",
          "2026-09-24T19:00:00Z", None, None, None, None, None, None, None, "absent",
          0, 0, "[]", "no stream was kept")])
    db.commit()


def gen(n: int, name: str, usd: float, model: str) -> SimpleNamespace:
    return SimpleNamespace(trace_id=change_trace_id(RUN_ID, n), name=name, model=model,
                           total_cost=usd, cost_details={"total": usd},
                           project_id="proj-1", type="GENERATION",
                           metadata={"change_n": n, "role": name, "provenance": "measured"})


class FakeObservations:
    def __init__(self, data=None, fail: Exception | None = None):
        self.data, self.fail, self.calls = data or [], fail, []

    def get_many(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise self.fail
        return SimpleNamespace(data=self.data, meta=SimpleNamespace(cursor=None))


def fake_client(observations: FakeObservations):
    return SimpleNamespace(api=SimpleNamespace(observations=observations))


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", PK)
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", SK)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.example")
    seed(db)
    svc = RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                  use_recorded_stream=True))
    app.dependency_overrides[runs_router.get_service] = lambda: svc
    costs_router.clear_cache()
    yield TestClient(app)
    app.dependency_overrides.pop(costs_router.get_langfuse, None)
    costs_router.clear_cache()


def use(observations: FakeObservations | None) -> None:
    app.dependency_overrides[costs_router.get_langfuse] = (
        lambda: fake_client(observations) if observations is not None else None)


ALL_CONFIRMED = [gen(1, "orchestrator", 48.7945489, "claude-opus-5[1m]"),
                 gen(1, "agents", 4.38, "claude-haiku-4-5-20251001"),
                 gen(2, "orchestrator", 19.3387, "claude-opus-5[1m]"),
                 gen(2, "agents", 1.6914599, "claude-haiku-4-5-20251001")]


def test_rows_come_from_langfuse_when_it_answers(client):
    obs = FakeObservations(ALL_CONFIRMED)
    use(obs)
    body = client.get(f"/api/runs/{RUN_ID}/costs").json()

    assert body["langfuse"] == "ok"
    call = obs.calls[0]
    assert call["session_id"] == SLUG and call["type"] == "GENERATION"
    assert call["request_options"]["timeout_in_seconds"] <= 5, "a short timeout"
    rows = {r["n"]: r for r in body["rows"]}
    assert rows[1]["source"] == "langfuse" and rows[1]["confirmed"] is True
    assert rows[1]["total_usd"] == pytest.approx(53.1745489)
    assert rows[1]["orchestrator_usd"] == pytest.approx(48.7945489)
    assert rows[1]["trace_id"] == change_trace_id(RUN_ID, 1)
    assert rows[1]["trace_url"] == (f"https://cloud.langfuse.example/project/proj-1/"
                                    f"traces/{change_trace_id(RUN_ID, 1)}")
    assert rows[1]["minutes"] == pytest.approx(118.6)
    assert body["total"]["usd"] == pytest.approx(74.2047088)
    assert body["total"]["absent"] == 1, "the demo with no stream is counted, not added as 0"


def test_langfuse_down_gives_the_local_rows_marked_unconfirmed(client):
    use(FakeObservations(fail=TimeoutError("read timed out")))
    body = client.get(f"/api/runs/{RUN_ID}/costs").json()

    assert body["langfuse"] == "unreachable"
    for row in body["rows"]:
        assert row["source"] == "local" and row["confirmed"] is False
        assert row["status"] == "unconfirmed in Langfuse"
        assert row["trace_url"] is None
    rows = {r["n"]: r for r in body["rows"]}
    assert rows[2]["total_usd"] == pytest.approx(21.0301599)
    assert rows[3]["total_usd"] is None, "absent stays absent"


def test_a_change_langfuse_has_not_ingested_yet_is_local_and_unconfirmed(client):
    use(FakeObservations(ALL_CONFIRMED[:2]))
    rows = {r["n"]: r for r in client.get(f"/api/runs/{RUN_ID}/costs").json()["rows"]}
    assert rows[1]["source"] == "langfuse"
    assert rows[2]["source"] == "local" and rows[2]["status"] == "unconfirmed in Langfuse"


def test_on_disagreement_both_figures_are_returned(client):
    wrong = [gen(1, "orchestrator", 40.0, "claude-opus-5[1m]"),
             gen(1, "agents", 4.38, "claude-haiku-4-5-20251001")]
    use(FakeObservations(wrong))
    row = next(r for r in client.get(f"/api/runs/{RUN_ID}/costs").json()["rows"]
               if r["n"] == 1)
    assert row["source"] == "both"
    assert row["disagreement"]["local"]["total_usd"] == pytest.approx(53.1745489)
    assert row["disagreement"]["langfuse"]["total_usd"] == pytest.approx(44.38)
    assert "disagree" in row["status"]


def test_not_configured_is_local(client):
    use(None)
    body = client.get(f"/api/runs/{RUN_ID}/costs").json()
    assert body["langfuse"] == "not configured"
    assert {r["source"] for r in body["rows"]} == {"local"}


def test_the_answer_is_cached_between_page_loads(client):
    obs = FakeObservations(ALL_CONFIRMED)
    use(obs)
    client.get(f"/api/runs/{RUN_ID}/costs")
    client.get(f"/api/runs/{RUN_ID}/costs")
    assert len(obs.calls) == 1


def test_credentials_never_leave_in_the_response(client):
    use(FakeObservations(ALL_CONFIRMED))
    text = client.get(f"/api/runs/{RUN_ID}/costs").text
    assert PK not in text and SK not in text
    use(FakeObservations(fail=RuntimeError(f"401 for {PK}:{SK}")))
    costs_router.clear_cache()
    text = client.get(f"/api/runs/{RUN_ID}/costs").text
    assert PK not in text and SK not in text


def test_an_unknown_run_is_404(client):
    use(None)
    assert client.get("/api/runs/nope/costs").status_code == 404


def test_the_library_card_carries_the_novels_total_with_provenance(client):
    use(None)
    run = next(r for r in client.get("/api/runs").json() if r["id"] == RUN_ID)
    total = run["cost_total"]
    assert total["usd"] == pytest.approx(74.2047088)
    assert total["provenance"] == "measured" and total["absent"] == 1
    assert total["source"] == "local"
