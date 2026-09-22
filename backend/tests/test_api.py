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
    # The recorded stream stands in for `claude`. It covers the runner, the
    # parser, the persistence, the SSE and both watchers at $0.
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                        use_recorded_stream=True, budget_ceiling_usd=1000.0)
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


def test_health_says_whether_it_is_replaying_or_orchestrating():
    """A panel showing costs from a replayed stream would be lying about money."""
    with TestClient(app) as c:
        body = c.get("/api/health").json()
    assert body["ok"] is True
    assert body["orchestrator"] in ("recorded-stream", "claude-code")


def test_start_a_run_and_follow_it_to_completion(client):
    created = client.post("/api/runs", json={"premise": PREMISE, "profile": "tiny"})
    assert created.status_code == 201
    run_id = created.json()["id"]
    assert created.json()["slug"].startswith("a-lighthouse-keeper")  # the fallback

    events = _wait(client, run_id)
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "snapshot", "the snapshot comes first, so a reconnect is safe"
    assert kinds[-1] == "done"
    assert "progress" in kinds

    final = events[-1][1]
    # The recording ends with a real `result`, so the run completes.
    assert final["result"] == "complete"


def test_the_snapshot_is_built_from_the_database_not_from_memory(client):
    """The stream is a view; the database is the record. A client that missed
    every event must still be able to recover the whole state."""
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)

    body = client.get(f"/api/runs/{run_id}").json()
    assert body["run"]["stage"] == "complete"
    # The slug was LEARNED from the paths the recorded run wrote, not guessed
    # from the premise this test sent.
    assert body["run"]["slug"] == "night-dispatcher-recovered-climber"


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


def test_a_failure_in_the_post_run_bookkeeping_still_ends_the_stream(client, monkeypatch):
    """Everything after the halt is bookkeeping, and every line of it was added
    after the SSE follower was written.

    **A failure in any of them used to hang every follower forever**, because the
    sentinel that ends the stream came last and never ran. A reader waiting on a
    finished run is worse than a missing figure: it looks like the run is still
    going. Found by adding one more bookkeeping step and watching the whole suite
    stop.
    """
    import backend.runs.service as service

    def explode(*args, **kwargs):
        raise RuntimeError("the archive fell over")

    monkeypatch.setattr(service.RunService, "_archive", explode)

    created = client.post("/api/runs", json={
        "premise": "A lighthouse keeper on a drowned coast keeps a ledger.",
        "profile": "tiny", "tone": ""})
    assert created.status_code == 201

    kinds = []
    with client.stream("GET", f"/api/runs/{created.json()['id']}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("event:"):
                kinds.append(line.split(":", 1)[1].strip())
            if kinds and kinds[-1] == "done":
                break
    assert kinds[-1] == "done", "the stream must end even when bookkeeping fails"


# ------------------------------------------------- PLAN-007 6.1: the switches


@pytest.fixture
def client_for(db, tmp_path):
    """A client whose recorded stream is a *modified* copy of the fixture: the
    switch is a different recording, never a change to the replay double."""
    def make(lines: list[str]):
        fixture = tmp_path / "switched.stream.jsonl"
        fixture.write_text("\n".join(lines) + "\n", encoding="utf-8")
        settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                            use_recorded_stream=True, recorded_stream=fixture,
                            budget_ceiling_usd=1000.0)
        service = RunService(db, settings)
        app.dependency_overrides[runs_router.get_service] = lambda: service
        return TestClient(app)
    yield make
    app.dependency_overrides.pop(runs_router.get_service, None)


FIXTURE_LINES = (Path(__file__).resolve().parent / "fixtures" / "recorded-run.stream.jsonl") \
    .read_text(encoding="utf-8").splitlines()


def test_a_malformed_line_becomes_a_run_warning(client_for):
    """AC-2: logged, not lost. The log here is the database — `run_warnings` —
    because the backend writes no other (PLAN-007 P-8)."""
    lines = list(FIXTURE_LINES)
    lines.insert(5, "garbage that is not json")
    with client_for(lines) as client:
        run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
        events = _wait(client, run_id)
        assert events[-1][1]["result"] == "complete"
        warnings = client.get(f"/api/runs/{run_id}").json()["warnings"]
    kinds = [w["kind"] for w in warnings]
    assert "malformed_line" in kinds
    assert any("garbage" in w["detail"] for w in warnings)


def test_a_stream_that_ends_without_result_halts_process(client_for):
    """FR-RNR-7: the orchestrator died. Everything written stays readable; the
    run is marked, not resumed."""
    lines = [l for l in FIXTURE_LINES if '"type": "result"' not in l]
    assert len(lines) == len(FIXTURE_LINES) - 1, "the fixture has exactly one result line"
    with client_for(lines) as client:
        run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
        events = _wait(client, run_id)
        assert events[-1][1]["result"] == "halted: process"
        run = client.get(f"/api/runs/{run_id}").json()["run"]
    assert run["halted"] == "process"
    assert "result" in run["halted_detail"]
