"""The HTTP edge: starting a run, reading it back, and following it over SSE."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.commons.config.settings import Settings
from backend.main import app
from backend.runs import router as runs_router
from backend.runs.service import RunService

PREMISE = "A lighthouse keeper on Titan starts receiving her own distress calls."


@pytest.fixture
def client(db, tmp_path):
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                        use_mock_engine=True, budget_ceiling_usd=100.0)
    service = RunService(db, settings)
    # The dependency override is the cleanest seam FastAPI gives you: the test
    # swaps the database and the engine without the code under test knowing.
    app.dependency_overrides[runs_router.get_service] = lambda: service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(runs_router.get_service, None)


def _wait(client, run_id: str, timeout: float = 30.0):
    """Drain the SSE stream, which ends when the run does."""
    events = []
    with client.stream("GET", f"/api/runs/{run_id}/events") as response:
        assert response.status_code == 200
        current = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                current = line[len("event: "):]
            elif line.startswith("data: "):
                events.append((current, json.loads(line[len("data: "):])))
                if current == "done":
                    break
    return events


def test_health_says_which_engine_is_running():
    """A panel showing costs from a mock run would be lying about money."""
    with TestClient(app) as c:
        body = c.get("/api/health").json()
    assert body["ok"] is True
    assert body["engine"] in ("mock", "anthropic")


def test_start_a_run_and_follow_it_to_completion(client):
    created = client.post("/api/runs", json={"premise": PREMISE, "profile": "tiny"})
    assert created.status_code == 201
    run_id = created.json()["id"]
    assert created.json()["slug"].startswith("a-lighthouse-keeper")

    events = _wait(client, run_id)
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "snapshot", "the snapshot comes first, so a reconnect is safe"
    assert kinds[-1] == "done"
    assert "progress" in kinds

    final = events[-1][1]
    assert final["result"] == "complete"
    assert final["run"]["stage"] == "complete"


def test_the_snapshot_is_built_from_the_database_not_from_memory(client):
    """The stream is a view; the database is the record. A client that missed
    every event must still be able to recover the whole state."""
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)

    body = client.get(f"/api/runs/{run_id}").json()
    assert body["run"]["stage"] == "complete"
    assert len(body["attempts"]) >= 3
    assert body["cost"]["calls"] > 10
    assert body["cost"]["provenance"] == ["estimated"]


def test_a_premise_that_is_too_short_is_refused_at_the_edge(client):
    assert client.post("/api/runs", json={"premise": "short"}).status_code == 422


def test_the_queue_is_one(client):
    """Nothing here justifies a second worker, and two runs sharing one budget
    and one semaphore would make both figures meaningless."""
    first = client.post("/api/runs", json={"premise": PREMISE})
    assert first.status_code == 201
    second = client.post("/api/runs", json={"premise": PREMISE})
    assert second.status_code in (201, 409)
    if second.status_code == 409:
        assert "queue is one" in second.json()["detail"]
    _wait(client, first.json()["id"])


def test_an_unknown_run_is_a_404(client):
    assert client.get("/api/runs/nope").status_code == 404


def test_the_run_list_includes_what_was_imported(client, db):
    """Imported runs are readable beside new ones, and marked apart."""
    from backend.commons.db.import_v1 import import_all

    import_all(db, Path(__file__).resolve().parents[2] / "output")
    rows = client.get("/api/runs").json()
    sources = {r["source"] for r in rows}
    assert "pre-loop003" in sources
