"""Read online, download on request (owner, 2026-09-24).

The PDF route used to answer with `Content-Disposition: attachment`, so opening
a finished novel downloaded a file instead of showing a book. Now the book is
read in the page from the version's own HTML, the PDF opens inline, and a
download happens only when the reader presses the button that asks for one.
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


@pytest.fixture
def client(db, tmp_path):
    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                                  use_recorded_stream=True))
    write_repo.create_run(db, run_id="r1", slug="the-keeper", premise="a keeper of a light",
                          profile="tiny", tone=None, snapshot={"novel": {"chapters": 1}})
    v1 = tmp_path / "the-keeper" / "dist" / "v1"
    v1.mkdir(parents=True)
    (v1 / "novel.html").write_text("<html><body><h1>The Keeper</h1></body></html>", encoding="utf-8")
    (v1 / "novel.pdf").write_bytes(b"%PDF-1.4 fake")
    app.dependency_overrides[runs_router.get_service] = lambda: svc
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(runs_router.get_service, None)


def test_the_book_is_served_to_read_in_the_page(client):
    r = client.get("/api/runs/r1/versions/1/html")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "The Keeper" in r.text
    assert "attachment" not in r.headers.get("content-disposition", "")


def test_the_pdf_opens_inline_unless_a_download_is_asked_for(client):
    inline = client.get("/api/runs/r1/versions/1/pdf")
    assert inline.headers["content-disposition"].startswith("inline")
    download = client.get("/api/runs/r1/versions/1/pdf?download=true")
    assert download.headers["content-disposition"].startswith("attachment")


def test_a_version_with_no_html_is_a_404_not_an_empty_page(client):
    assert client.get("/api/runs/r1/versions/2/html").status_code == 404
    assert client.get("/api/runs/nope/versions/1/html").status_code == 404


def test_the_download_is_named_after_the_book(client, tmp_path):
    """Owner, 2026-09-24: every download was called novel-v1.pdf."""
    outline = "# The Keeper: Light / Dark? — Outline" + chr(10)
    (tmp_path / "the-keeper" / "outline.md").write_text(outline, encoding="utf-8")
    r = client.get("/api/runs/r1/versions/1/pdf?download=true")
    # Starlette sends a non-plain name as RFC 5987 `filename*=utf-8''...`.
    from urllib.parse import unquote
    cd = unquote(r.headers["content-disposition"])
    assert "The Keeper" in cd and "v1" in cd
    # Characters a file system refuses never reach the name.
    assert "/" not in cd.split("filename", 1)[1] and "?" not in cd.split("filename", 1)[1]
