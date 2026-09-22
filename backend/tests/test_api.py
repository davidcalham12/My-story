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


def test_health_says_whether_it_is_replaying_or_orchestrating(client):
    """A panel showing costs from a replayed stream would be lying about money."""
    body = client.get("/api/health").json()
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


# ------------------------------------------------------- PLAN-007 6.4


def test_every_stream_line_is_in_events_with_a_dense_seq(client, db):
    """FR-RNR-3 / AC-20: the stream is the record. Every parsed line of the
    recording is a row, in order, with the raw line as its payload."""
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)
    parsed = [l for l in FIXTURE_LINES if l.strip()]
    rows = db.execute("SELECT seq, type, payload FROM events WHERE run_id = ? ORDER BY seq",
                      (run_id,)).fetchall()
    assert len(rows) == len(parsed)
    assert [r["seq"] for r in rows] == list(range(1, len(parsed) + 1))
    for r, line in zip(rows, parsed):
        assert r["payload"] == line.strip()
        assert r["type"] == json.loads(line).get("type", "unknown")


# ------------------------------------------------------- PLAN-007 6.7


def _frames(client, run_id: str, last_event_id: str | None = None):
    """Every SSE frame with its `id:`, `event:` and parsed `data:`."""
    headers = {"Last-Event-ID": last_event_id} if last_event_id is not None else {}
    frames, current = [], {"id": None, "event": None}
    with client.stream("GET", f"/api/runs/{run_id}/events", headers=headers) as response:
        assert response.status_code == 200
        for line in response.iter_lines():
            if line.startswith("id: "):
                current["id"] = int(line[4:])
            elif line.startswith("event: "):
                current["event"] = line[7:]
            elif line.startswith("data: "):
                frames.append((current["id"], current["event"], json.loads(line[6:])))
                if current["event"] == "done":
                    break
                current = {"id": None, "event": None}
    return frames


class _BlockingProcess:
    """A process that produces two lines and then waits to be stopped — the
    only way to test a halt that must arrive *during* a run against a replay
    that otherwise finishes in milliseconds."""

    def __init__(self):
        import threading
        self.released = threading.Event()
        self.stopped = False
        self.skipped: list[str] = []

    def start(self):
        return None

    def lines(self):
        for raw in ('{"type": "system", "subtype": "init"}',
                    '{"type": "assistant", "message": {"content": [{"type": "text", "text": "FLOW-1"}]}}'):
            yield raw, json.loads(raw)
        self.released.wait(timeout=10)

    def events(self):
        for _, e in self.lines():
            yield e

    def stop(self):
        self.stopped = True
        self.released.set()

    @property
    def returncode(self):
        return None

    def stderr_text(self):
        return ""


def test_halt_stops_the_process_and_marks_halted_user(db, tmp_path):
    """AC-18. The user's halt goes through the same _finish path the watchers
    use: archive, warnings, and the sentinel that frees every follower."""
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path, use_recorded_stream=True)
    service = RunService(db, settings)
    fake = _BlockingProcess()
    service._process = lambda *a, **k: fake  # the seam the recorded stream uses
    created = service.start(PREMISE, "tiny", "")
    run_id = created["id"]
    import time
    for _ in range(100):
        if service._live and service._live.seq >= 2:
            break
        time.sleep(0.02)
    assert service._live.seq == 2, "the process produced its two lines and is now blocked"

    service.halt(run_id)
    for _ in range(100):
        if service._live.done:
            break
        time.sleep(0.02)
    assert fake.stopped
    run = service.get(run_id)
    assert run["halted"] == "user"
    assert "user" in run["halted_detail"]
    assert service._live.result == "halted: user"


def test_halt_keeps_what_was_persisted_readable(db, tmp_path):
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path, use_recorded_stream=True)
    service = RunService(db, settings)
    fake = _BlockingProcess()
    service._process = lambda *a, **k: fake
    run_id = service.start(PREMISE, "tiny", "")["id"]
    import time
    for _ in range(100):
        if service._live and service._live.seq >= 2:
            break
        time.sleep(0.02)
    service.halt(run_id)
    for _ in range(100):
        if service._live.done:
            break
        time.sleep(0.02)
    rows = db.execute("SELECT seq FROM events WHERE run_id = ? ORDER BY seq", (run_id,)).fetchall()
    assert [r["seq"] for r in rows] == [1, 2], "the two lines read before the halt are the record"
    assert service.detail(run_id)["run"]["halted"] == "user"


def test_halt_on_an_unknown_or_finished_run_is_404_or_409(client):
    assert client.post("/api/runs/nope/halt").status_code == 404
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)
    response = client.post(f"/api/runs/{run_id}/halt")
    assert response.status_code == 409
    assert client.get(f"/api/runs/{run_id}").json()["run"]["halted"] is None, "a finished run is not re-marked"


def test_a_run_left_running_is_marked_halted_process_on_startup(db, tmp_path):
    """AC-19 / FR-RUN-7. A server restarted mid-run used to leave the row
    `running` forever, and the panel showed a run that was still going."""
    from backend.commons.db import repository as repo
    repo.create_run(db, run_id="orphan", slug="orphan-slug", premise=PREMISE,
                    profile="tiny", tone=None, snapshot={})
    repo.set_stage(db, "orphan", "FLOW-4")
    repo.create_run(db, run_id="finished", slug="finished-slug", premise=PREMISE,
                    profile="tiny", tone=None, snapshot={})
    repo.finish(db, "finished")
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, source, started_at) "
               "VALUES ('imported','imported-slug','p','tiny','{}','FLOW-6','pre-loop003','then')")

    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path, use_recorded_stream=True)
    swept = RunService(db, settings).sweep_orphans()

    assert swept == ["orphan"]
    orphan = db.execute("SELECT halted, halted_detail, finished_at FROM runs WHERE id = 'orphan'").fetchone()
    assert orphan["halted"] == "process"
    assert "startup" in orphan["halted_detail"]
    assert orphan["finished_at"] is not None
    assert db.execute("SELECT halted FROM runs WHERE id = 'finished'").fetchone()["halted"] is None
    assert db.execute("SELECT halted FROM runs WHERE id = 'imported'").fetchone()["halted"] is None, \
        "an imported run with no finished_at is history, not an orphan"


def test_sse_id_field_is_the_persisted_seq(client, db):
    """AC-20: every live frame says which stream line produced it."""
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    frames = _frames(client, run_id)
    progress = [(i, d) for i, e, d in frames if e == "progress"]
    assert progress, "the replay produces progress frames"
    ids = [i for i, _ in progress]
    assert all(isinstance(i, int) for i in ids)
    assert ids == sorted(ids)
    last = db.execute("SELECT MAX(seq) AS n FROM events WHERE run_id = ?", (run_id,)).fetchone()["n"]
    assert ids[-1] == last


def test_last_event_id_replays_from_the_next_seq_then_goes_live(client, db):
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)
    last = db.execute("SELECT MAX(seq) AS n FROM events WHERE run_id = ?", (run_id,)).fetchone()["n"]
    frames = _frames(client, run_id, last_event_id=str(last - 2))
    kinds = [e for _, e, _ in frames]
    assert kinds[0] == "snapshot", "a reconnect still gets the state first"
    replayed = [(i, d) for i, e, d in frames if e == "line"]
    assert [i for i, _ in replayed] == [last - 1, last]
    for i, d in replayed:
        assert d["seq"] == i and json.loads(d["payload"])["type"] == d["type"]
    assert kinds[-1] == "done", "the run is over, so after the replay the stream ends"


def test_last_event_id_beyond_the_end_yields_only_done(client, db):
    run_id = client.post("/api/runs", json={"premise": PREMISE}).json()["id"]
    _wait(client, run_id)
    frames = _frames(client, run_id, last_event_id="999999")
    assert [e for _, e, _ in frames] == ["snapshot", "done"]


# ------------------------------------------------------- PLAN-007 6.11


def test_health_reports_db_and_the_number_of_migrations_applied(client, db):
    """FR-HLT-1: DB reachable and migrations applied — as counted in the same
    database the service uses, not asserted."""
    body = client.get("/api/health").json()
    assert body["db"] is True
    applied = db.execute("SELECT COUNT(*) AS n FROM schema_migrations").fetchone()["n"]
    assert body["migrations"] == applied >= 9


def test_health_reports_sqlite_vec_and_model_availability_without_loading_the_model(client):
    """FR-HLT-1: `sqlite-vec` loadable, embeddings model present — and 'never
    probes the model': the answer for the model comes from its cache directory
    on disk, so health stays cheap and offline."""
    import sys
    body = client.get("/api/health").json()
    assert isinstance(body["sqlite_vec"], bool)
    assert body["embeddings_model"] in ("present", "absent", "unchecked")
    assert "sentence_transformers" not in sys.modules, "health must not import the model library"
