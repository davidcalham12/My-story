"""What *Read* shows beside the book: the chapters, the people, the places.

The owner opened a finished novel and found all three empty. Two causes, one
test each: no route answered `/chapters` at all, and the story-bible ingest —
the step that turns `bible/characters.md` into rows — ran only inside the
conductor's cast unit, so a novel written by the single orchestrator published
with an empty cast.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.commons.config.settings import Settings
from backend.commons.db import repository as write_repo
from backend.main import app
from backend.runs import router as runs_router
from backend.runs.service import RunService

CHARACTERS = """- **Mara Quell** — protagonist, the keeper, age 40; patient; speaks little

- **Tobias Wren** — the supply pilot, age 30; loud; speaks in jokes
"""


@pytest.fixture
def world(db, tmp_path):
    settings = Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                        use_recorded_stream=True, budget_ceiling_usd=1000.0)
    service = RunService(db, settings)
    write_repo.create_run(db, run_id="r1", slug="the-keeper", premise="a keeper of a light",
                          profile="tiny", tone=None, snapshot={"novel": {"chapters": 2}})
    run_dir = tmp_path / "the-keeper"
    (run_dir / "chapters").mkdir(parents=True)
    (run_dir / "bible").mkdir()
    (run_dir / "chapters" / "ch01.md").write_text("# Chapter 1 — The Light\n\nText.\n", encoding="utf-8")
    (run_dir / "chapters" / "ch02.md").write_text("# Chapter 2 - The Supply Boat\n\nText.\n", encoding="utf-8")
    (run_dir / "chapters" / "ch01.attempt1.md").write_text("# draft\n", encoding="utf-8")
    (run_dir / "bible" / "characters.md").write_text(CHARACTERS, encoding="utf-8")
    app.dependency_overrides[runs_router.get_service] = lambda: service
    with TestClient(app) as c:
        yield c, db, run_dir
    app.dependency_overrides.pop(runs_router.get_service, None)


def test_the_reader_lists_the_promoted_chapters_by_title(world):
    client, _, _ = world
    r = client.get("/api/runs/r1/chapters")
    assert r.status_code == 200
    assert r.json() == [{"n": 1, "title": "The Light"}, {"n": 2, "title": "The Supply Boat"}]


def test_an_unknown_run_has_no_chapters(world):
    client, _, _ = world
    assert client.get("/api/runs/nope/chapters").status_code == 404


def test_release_fills_the_cast_when_nothing_ingested_it(world):
    from backend.publish import release
    _, db, run_dir = world
    release.ensure_bible_rows(db, run_dir)
    names = {r[0] for r in db.execute("SELECT canonical_name FROM characters WHERE run_id='r1'")}
    assert {"Mara Quell", "Tobias Wren"} <= names
    # And a second call does not double them.
    release.ensure_bible_rows(db, run_dir)
    assert db.execute("SELECT COUNT(*) FROM characters WHERE run_id='r1'").fetchone()[0] == len(names)


@pytest.mark.parametrize("attempt", ["..%2F..%2Fetc", "../the-keeper", "r1%2F..%2F.."])
def test_the_run_id_never_becomes_a_path(world, attempt):
    """The folder comes from the database's slug for an exact run id; an id
    shaped like a path matches no run and reads nothing."""
    client, _, _ = world
    assert client.get(f"/api/runs/{attempt}/chapters").status_code == 404
