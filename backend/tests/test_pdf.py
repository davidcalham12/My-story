"""PLAN-001 E6 — the reader's PDF, and what a reader's change does to it.

The HTML is a pure function of the archive and the files on disk: string in,
string out. That is why this file needs no browser — and it is the reason the
split exists at all. A renderer that launches Chromium is testable only where
Chromium is installed, which is neither CI nor a machine where the browser
download was still running when this was written.

So: **the HTML is the tested part, the print is the demonstrated part** (AC-6 is
D + I). Everything below is T.

Migration 010 (phase E3) brings `characters`, `places` and `fact_usage`. It is
being written in another worktree while this one is, so the stand-in schema
below is created inside the tests from the shapes `docs/spec.md` §1 documents.
E6 owns no foreign key into any of them.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from pathlib import Path

import pytest

from backend.commons.db import repository
from backend.publish import pdf
from backend.publish.pdf import Chapter, Change, Entry, Novel, Sheet

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "output" / "lighthouse-keeper-ledger"

STANDIN = ""   # retired at integration: migration 010 (E3) ships
# `characters`, `places` and `fact_usage`.

TITLES = ["The Seventh Step", "A Hand Not Mine", "The Drowned Page"]


def _novel(**over) -> Novel:
    """A three-chapter novel, as `build_html` wants it: no disk, no database."""
    base = dict(
        title="Sallowmere Reach",
        version=1,
        dedication="For Ada, who counts the steps.",
        synopsis="A keeper writes the drowned into a book that cannot be struck out.",
        chapters=[Chapter(n=i, title=t, body=f"Body of chapter {i}.")
                  for i, t in enumerate(TITLES, 1)],
        sheet=Sheet(
            characters=[Entry("Ada Rowe", "keeper of the Corbie Light", 1),
                        Entry("Thomas Creed", "Commissioner", 1),
                        Entry("Walter Byrd", "the keeper before her", 2)],
            places=[Entry("The Corbie Light", "lighthouse", 1)],
        ),
        change=None,
    )
    return Novel(**{**base, **over})


@pytest.fixture
def run(db, tmp_path):
    """A finished three-chapter run: files on disk, rows in the archive."""
    db.executescript(STANDIN)
    repository.create_run(db, run_id="r1", slug="gift", premise="A keeper.",
                          profile="tiny", tone=None, snapshot="{}")
    run_dir = tmp_path / "gift"
    (run_dir / "chapters").mkdir(parents=True)
    (run_dir / "dist").mkdir()
    for i, title in enumerate(TITLES, 1):
        (run_dir / "chapters" / f"ch{i:02d}.md").write_text(
            f"# Chapter {i} — {title}\n\nBody of chapter {i}, café.\n",
            encoding="utf-8")
    (run_dir / "dist" / "book.md").write_text(
        "# Sallowmere Reach\n\n*A NovaForge novel*\n", encoding="utf-8")
    (run_dir / "synopsis.md").write_text("A keeper writes the drowned in.\n",
                                         encoding="utf-8")
    (run_dir / "dedication.md").write_text("For Ada, who counts the steps.\n",
                                           encoding="utf-8")
    (run_dir / "state.json").write_text(json.dumps({"slug": "gift"}),
                                        encoding="utf-8")
    # Migration 010 points every story-bible table at runs(id); this fixture
    # already has its run, so it only needs the fact the usage rows name.
    db.execute("INSERT INTO facts (id, run_id, kind, text, source) "
               "VALUES (201, 'r1', 'recipient', 'The dog is called Bruno.', 'brief')")
    db.executemany(
        "INSERT INTO characters (run_id, canonical_name, role, first_chapter) "
        "VALUES (?, ?, ?, ?)",
        [("r1", "Ada Rowe", "keeper", 1), ("r1", "Walter Byrd", "keeper before", 2)])
    db.execute("INSERT INTO places (run_id, canonical_name, note, first_chapter) "
               "VALUES (?, ?, ?, ?)", ("r1", "The Corbie Light", "a lighthouse", 1))
    db.executemany("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) "
                   "VALUES (?, ?, ?, ?)", [(201, 1, 2, "Bruno"), (201, 1, 3, "Bruno")])
    return run_dir


# ------------------------------------------------------------ the migration


def test_migration_012_creates_the_versions_table(db):
    columns = {r["name"] for r in db.execute("PRAGMA table_info(versions)")}
    assert columns == {"run_id", "n", "parent", "reason", "created_at"}


def test_a_version_after_the_first_must_name_the_one_it_came_from(db):
    """A v2 with no parent is a version whose provenance was lost, and the
    "what changed" page is written from exactly that link."""
    repository.create_run(db, run_id="r1", slug="gift", premise="p",
                          profile="tiny", tone=None, snapshot="{}")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO versions (run_id, n, parent, reason, created_at) "
                   "VALUES ('r1', 2, NULL, 'change', '2026-09-23T00:00:00Z')")


# ------------------------------------------------------------ the HTML


def test_the_cover_carries_the_title_and_the_dedication():
    html = pdf.build_html(_novel())
    cover = html[html.index('id="cover"'):html.index('id="index"')]
    assert "Sallowmere Reach" in cover
    assert "For Ada, who counts the steps." in cover


def test_the_index_has_one_anchor_per_chapter_and_every_one_of_them_lands():
    html = pdf.build_html(_novel())
    index = html[html.index('id="index"'):html.index('id="sheet"')]
    pointed = re.findall(r'href="#chapter-(\d+)"', index)
    assert pointed == ["1", "2", "3"], pointed
    present = set(re.findall(r'id="chapter-(\d+)"', html))
    assert set(pointed) <= present, f"the index points at nothing: {set(pointed) - present}"


def test_the_sheet_links_each_character_to_the_chapter_it_first_appears_in():
    html = pdf.build_html(_novel())
    sheet = html[html.index('id="sheet"'):html.index('id="chapter-1"')]
    assert 'href="#chapter-2"' in sheet and "Walter Byrd" in sheet
    for name in ("Ada Rowe", "Thomas Creed", "The Corbie Light"):
        assert name in sheet
    assert len(re.findall(r'href="#chapter-\d+"', sheet)) == 4


def test_a_first_chapter_nobody_recorded_is_said_and_never_linked_to_chapter_zero():
    """Absent is never zero. A character whose first chapter was never worked
    out must not be silently filed under chapter 1 — a reader would follow the
    link and find the wrong scene, and nothing on the page would say so."""
    novel = _novel(sheet=Sheet(characters=[Entry("Nell Harker", "widow", None)],
                               places=[]))
    html = pdf.build_html(novel)
    sheet = html[html.index('id="sheet"'):html.index('id="chapter-1"')]
    assert 'href="#chapter-0"' not in sheet
    assert 'href="#chapter-1"' not in sheet
    assert "not recorded" in sheet


def test_a_sheet_whose_tables_do_not_exist_yet_says_so_rather_than_showing_none():
    """`None` is "migration 010 has not run here", `[]` is "it ran and found
    nobody". Rendering both as an empty list is how a broken ingest ships
    looking like a novel with no characters in it."""
    html = pdf.build_html(_novel(sheet=Sheet(characters=None, places=None)))
    sheet = html[html.index('id="sheet"'):html.index('id="chapter-1"')]
    assert "not recorded" in sheet


def test_the_prose_is_escaped_and_the_accents_survive():
    novel = _novel(chapters=[Chapter(1, "Café & <Ledger>",
                                     'She wrote <script>alert("x")</script>, naïve.')])
    html = pdf.build_html(novel)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "naïve" in html and "Café &amp; &lt;Ledger&gt;" in html


def test_emphasis_is_the_only_markdown_that_survives_the_conversion():
    novel = _novel(chapters=[Chapter(1, "T", "The *Marigold* stands **twice**.\n\nSecond.")])
    html = pdf.build_html(novel)
    assert "<em>Marigold</em>" in html and "<strong>twice</strong>" in html
    assert html.count("<p>") >= 2


def test_the_what_changed_page_comes_first_and_links_to_the_chapters_that_moved():
    novel = _novel(version=2,
                   change=Change(fact_id="201", to="The dog is called Nala.",
                                 chapters=(2, 3), parent=1))
    html = pdf.build_html(novel)
    assert html.index('id="what-changed"') < html.index('id="cover"')
    changed = html[html.index('id="what-changed"'):html.index('id="cover"')]
    assert re.findall(r'href="#chapter-(\d+)"', changed) == ["2", "3"]
    assert "Nala" in changed


# ------------------------------------------------------------ publishing


def test_publishing_writes_the_html_and_exactly_one_versions_row(db, run):
    n = pdf.publish(db, run, "r1", reason="first publication")
    assert n == 1
    html = run / "dist" / "v1" / "novel.html"
    assert html.is_file()
    assert "Sallowmere Reach" in html.read_text(encoding="utf-8")
    rows = db.execute("SELECT n, parent, reason FROM versions WHERE run_id = 'r1'").fetchall()
    assert [tuple(r) for r in rows] == [(1, None, "first publication")]


def test_v2_keeps_v1s_files(db, run):
    pdf.publish(db, run, "r1", reason="first publication")
    before = (run / "dist" / "v1" / "novel.html").read_text(encoding="utf-8")
    (run / "chapters" / "ch02.md").write_text("# Chapter 2 — Rewritten\n\nNala.\n",
                                              encoding="utf-8")
    n = pdf.publish(db, run, "r1", reason="reader change",
                    change=Change("201", "Nala", (2,), parent=1))
    assert n == 2
    assert (run / "dist" / "v2" / "novel.html").is_file()
    assert (run / "dist" / "v1" / "novel.html").read_text(encoding="utf-8") == before
    assert db.execute("SELECT parent FROM versions WHERE run_id='r1' AND n=2").fetchone()[0] == 1


def test_a_published_version_can_never_be_written_over(db, run):
    """The structural half of "v1 is never touched": the only document this
    module writes is `dist/v<n>/novel.html`, and it is opened with mode `"x"` —
    an exclusive create in the filesystem, not a check this code could race or
    forget. A second publication of v1 raises rather than replacing what a
    reader already has."""
    pdf.publish(db, run, "r1", reason="first publication")
    with pytest.raises(FileExistsError):
        pdf.write_version(run, _novel(version=1))


# ------------------------------------------------------------ the browser half


def test_printing_without_playwright_names_the_command_that_installs_it(monkeypatch, tmp_path):
    """The failure this exists for: `ModuleNotFoundError: playwright` at the end
    of a ten-chapter run, with nothing saying what to install."""
    def missing():
        raise ImportError("No module named 'playwright'")

    monkeypatch.setattr(pdf, "_playwright", missing)
    with pytest.raises(RuntimeError) as exc:
        pdf.print_pdf(tmp_path / "novel.html", tmp_path / "novel.pdf")
    assert "pip install playwright" in str(exc.value)
    assert "install chromium" in str(exc.value)


# ------------------------------------------------------------ the reader change


def test_the_change_regenerates_only_the_chapters_fact_usage_names(db, run):
    from backend.versions import change as change_mod

    assert change_mod.impacted(db, "201") == (2, 3)


def test_a_fact_no_chapter_uses_is_refused_rather_than_regenerating_everything(db, run):
    """v1 is published first, so the refusal can only come from the empty
    `fact_usage` answer — and `_never_called` proves nothing was regenerated."""
    from backend.versions import change as change_mod

    pdf.publish(db, run, "r1", reason="first publication")
    assert change_mod.impacted(db, "f-unused") == ()
    code = change_mod.main(["change", "gift", "--fact", "f-unused", "--to", "x"],
                           output_dir=run.parent, conn=db,
                           regenerate=_never_called)
    assert code == 1
    assert not (run / "dist" / "v2").exists()


def _never_called(*args, **kwargs):  # pragma: no cover - the point is that it is not
    raise AssertionError("the dispatch boundary was crossed in a test")


def _rewrites(run_dir, workspace, chapters, fact_id, to):
    """A stand-in for the `claude -p` dispatch: writes the chapters it was asked
    for into the version's own workspace, and reports the gate accepted them."""
    (workspace / "chapters").mkdir(parents=True, exist_ok=True)
    for n in chapters:
        (workspace / "chapters" / f"ch{n:02d}.md").write_text(
            f"# Chapter {n} — Rewritten\n\n{to}\n", encoding="utf-8")
    return {n: True for n in chapters}


def test_a_reader_change_publishes_v2_from_the_regenerated_chapters(db, run):
    from backend.versions import change as change_mod

    pdf.publish(db, run, "r1", reason="first publication")
    code = change_mod.main(["change", "gift", "--fact", "201",
                            "--to", "The dog is called Nala."],
                           output_dir=run.parent, conn=db, regenerate=_rewrites)
    assert code == 0
    html = (run / "dist" / "v2" / "novel.html").read_text(encoding="utf-8")
    chapter2 = html[html.index('id="chapter-2"'):html.index('id="chapter-3"')]
    assert "Nala" in chapter2, "v2 shipped the old chapter 2 under a change page"
    assert "Rewritten" in chapter2
    assert "Body of chapter 1" in html, "chapter 1 was not touched and must still ship"
    assert (run / "chapters" / "ch02.md").read_text(encoding="utf-8").startswith(
        "# Chapter 2 — A Hand Not Mine"), "the run's own chapters were written over"
    assert db.execute("SELECT COUNT(*) FROM versions WHERE run_id='r1'").fetchone()[0] == 2


def test_a_halted_regeneration_publishes_nothing_and_leaves_v1_intact(db, run):
    """The gap `docs/spec.md` §7 accepts: the regeneration runs the ordinary
    gate and may fail it. What must not happen is a half-changed novel on the
    shelf under the version number a reader already has."""
    from backend.versions import change as change_mod

    pdf.publish(db, run, "r1", reason="first publication")
    before = (run / "dist" / "v1" / "novel.html").read_text(encoding="utf-8")

    def halts(run_dir, workspace, chapters, fact_id, to):
        _rewrites(run_dir, workspace, chapters, fact_id, to)
        return {2: True, 3: False}  # chapter 3 never passed the gate

    code = change_mod.main(["change", "gift", "--fact", "201", "--to", "Nala"],
                           output_dir=run.parent, conn=db, regenerate=halts)
    assert code == 1
    assert db.execute("SELECT COUNT(*) FROM versions WHERE run_id='r1'").fetchone()[0] == 1
    assert not (run / "dist" / "v2" / "novel.html").exists()
    assert (run / "dist" / "v1" / "novel.html").read_text(encoding="utf-8") == before
    assert (run / "chapters" / "ch02.md").read_text(encoding="utf-8").startswith(
        "# Chapter 2 — A Hand Not Mine"), "the accepted chapters were rewritten in place"


def test_a_second_attempt_after_a_halt_takes_the_next_number(db, run):
    """The halted workspace keeps its number.

    Allocating from the `versions` table alone would hand v2 to the retry, which
    then either collides with the abandoned directory or — worse — publishes
    into it and inherits half a novel nobody judged.
    """
    from backend.versions import change as change_mod

    pdf.publish(db, run, "r1", reason="first publication")
    argv = ["change", "gift", "--fact", "201", "--to", "Nala"]
    change_mod.main(argv, output_dir=run.parent, conn=db,
                    regenerate=lambda *a: (_rewrites(*a), {2: True, 3: False})[1])
    assert change_mod.main(argv, output_dir=run.parent, conn=db,
                           regenerate=_rewrites) == 0

    assert (run / "dist" / "v3" / "novel.html").is_file()
    assert not (run / "dist" / "v2" / "novel.html").exists(), \
        "the halted attempt's workspace was published over"
    assert [r[0] for r in db.execute(
        "SELECT n FROM versions WHERE run_id='r1' ORDER BY n")] == [1, 3]


# ------------------------------------------------------------ the HTTP edge


@pytest.fixture
def client(db, run):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.commons.config.settings import Settings
    from backend.publish import router_versions
    from backend.runs import router as runs_router
    from backend.runs.service import RunService

    app = FastAPI()
    app.include_router(router_versions.router, prefix="/api/runs")
    service = RunService(db, Settings(db_path=Path(":memory:"), output_dir=run.parent))
    app.dependency_overrides[runs_router.get_service] = lambda: service
    with TestClient(app) as c:
        yield c


def test_the_versions_route_lists_what_was_published(client, db, run):
    pdf.publish(db, run, "r1", reason="first publication")
    body = client.get("/api/runs/r1/versions").json()
    assert [v["n"] for v in body] == [1]
    assert body[0]["reason"] == "first publication"
    assert body[0]["pdf"] is False, "no PDF was printed; the panel must not offer one"


def test_the_pdf_route_answers_404_when_the_pdf_was_never_printed(client, db, run):
    pdf.publish(db, run, "r1", reason="first publication")
    assert client.get("/api/runs/r1/versions/1/pdf").status_code == 404


def test_the_pdf_route_serves_the_file_when_it_is_there(client, db, run):
    pdf.publish(db, run, "r1", reason="first publication")
    (run / "dist" / "v1" / "novel.pdf").write_bytes(b"%PDF-1.4 not really\n")
    response = client.get("/api/runs/r1/versions/1/pdf")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_posting_a_change_answers_with_the_chapters_it_would_regenerate(client, db, run):
    pdf.publish(db, run, "r1", reason="first publication")
    response = client.post("/api/runs/r1/changes",
                           json={"fact_id": "201", "to": "The dog is called Nala."})
    assert response.status_code == 202
    body = response.json()
    assert body["chapters"] == [2, 3] and body["version"] == 2


def test_no_route_of_this_module_takes_a_filesystem_path():
    """SPEC-007 FR-RD-2, held for the routes E6 adds: the PDF is reached by run
    and version number, never by a path a caller supplies."""
    from fastapi import FastAPI

    from backend.publish import router_versions

    app = FastAPI()
    app.include_router(router_versions.router, prefix="/api/runs")
    paths = set(app.openapi()["paths"])
    assert paths == {"/api/runs/{run_id}/versions",
                     "/api/runs/{run_id}/versions/{n}/pdf",
                     "/api/runs/{run_id}/changes"}, sorted(paths)
    for path in paths:
        assert "{path" not in path and "{name" not in path


# ------------------------------------------------------------ a real run


@pytest.mark.skipif(not (EXAMPLE / "dist" / "book.md").is_file(),
                    reason="the example run is not in this worktree")
def test_the_example_run_renders_into_a_book_a_reader_could_open(db, tmp_path):
    """Read against the run the exam will actually ship, copied out of
    `output/` first: nothing here writes into a finished run."""
    db.executescript(STANDIN)
    repository.create_run(db, run_id="r2", slug="lighthouse-keeper-ledger",
                          premise="p", profile="tiny", tone=None, snapshot="{}")
    run_dir = tmp_path / "lighthouse-keeper-ledger"
    shutil.copytree(EXAMPLE, run_dir)
    db.execute("INSERT INTO characters (run_id, canonical_name, role, first_chapter) "
               "VALUES ('r2', 'Ada Rowe', 'keeper', 1)")

    novel = pdf.read_novel(db, run_dir, "r2", version=1)
    assert [c.n for c in novel.chapters] == [1, 2, 3]
    assert novel.chapters[0].title == "The Seventh Step"
    html = pdf.build_html(novel)
    assert 'id="chapter-3"' in html
    assert "Ada Rowe" in html
    assert "Corbie Light" in html
