"""The library says what a novel's book holds, in the list itself.

The owner saw "Ready to read" on novels that had stopped with a one-chapter v1
(8834d0ab189a, halted budget; 8ab6c57af9f6, halted user): the card was drawn,
then a per-run request for its versions arrived and flipped it. `GET /api/runs`
now carries what the card needs — the chapters in the latest published version
and the chapters the run planned — so the panel asks nothing per run.
"""

import pytest
from fastapi.testclient import TestClient

from backend import versions as versions_repo
from backend.main import app
from backend.runs import router as runs_router

from backend.tests.test_stopped_novels import RUN_ID, _make_run, _snapshot, _svc


def _publish(db, run_dir, n: int, chapters: int) -> None:
    """A version as `publish` leaves it: its HTML, then its row."""
    out = run_dir / "dist" / f"v{n}"
    out.mkdir(parents=True)
    sections = "\n".join(f'<section id="chapter-{c}">\n<h1>Chapter {c}</h1>\n</section>'
                         for c in range(1, chapters + 1))
    (out / "novel.html").write_text(
        f'<html><body><section id="index"><a href="#chapter-1">1</a></section>\n{sections}'
        "</body></html>", encoding="utf-8")
    versions_repo.record(db, RUN_ID, n=n, parent=None if n == 1 else n - 1, reason="test")


@pytest.fixture
def client(db, tmp_path):
    svc = _svc(db, tmp_path)
    app.dependency_overrides[runs_router.get_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.pop(runs_router.get_service, None)


def test_a_stopped_run_with_a_partial_book_says_how_much_of_it_there_is(db, tmp_path, client):
    run_dir = _make_run(db, tmp_path, halted=("budget", "spent $25.80"), upto=1)
    _publish(db, run_dir, 1, chapters=1)

    [row] = client.get("/api/runs").json()

    assert row["published_chapters"] == 1
    assert row["chapters_planned"] == _snapshot()["novel"]["chapters"] == 3
    assert row["published_versions"] == [1]


def test_the_latest_version_is_the_one_counted(db, tmp_path, client):
    run_dir = _make_run(db, tmp_path, halted=None, upto=3, stage="complete")
    _publish(db, run_dir, 1, chapters=2)
    _publish(db, run_dir, 2, chapters=3)

    [row] = client.get("/api/runs").json()

    assert row["published_chapters"] == 3
    assert row["published_versions"] == [1, 2]


def test_nothing_published_is_null_never_zero(db, tmp_path, client):
    _make_run(db, tmp_path, halted=("user", "halted by the user"), upto=1)

    [row] = client.get("/api/runs").json()

    assert row["published_chapters"] is None
    assert row["published_versions"] == []
    assert row["chapters_planned"] == 3


def test_the_run_page_gets_the_same_fields(db, tmp_path, client):
    run_dir = _make_run(db, tmp_path, halted=("user", "halted by the user"), upto=1)
    _publish(db, run_dir, 1, chapters=1)

    run = client.get(f"/api/runs/{RUN_ID}").json()["run"]

    assert (run["published_chapters"], run["chapters_planned"]) == (1, 3)
