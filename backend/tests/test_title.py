"""A book's title, never its slug (owner, 2026-09-24: "que no tenga el slash").

Order of trust: the assembled manuscript's heading, the title the run recorded
in `state.json`, the outline's heading — the plot architect names the book
there — and only then the slug's own words, capitalised. Nothing is invented:
every step is a title somebody in the pipeline wrote.
"""

from __future__ import annotations

import json

from backend.commons.title import humanise, title_of


def test_the_outline_heading_names_the_book(tmp_path):
    (tmp_path / "outline.md").write_text("# The Other Side of the Hill — Outline\n\n## Acts\n", encoding="utf-8")
    assert title_of(tmp_path) == "The Other Side of the Hill"


def test_an_outline_headed_with_the_slug_is_no_title(tmp_path):
    run = tmp_path / "stone-collector-birthday-adventure"
    run.mkdir()
    (run / "outline.md").write_text("# Outline — stone-collector-birthday-adventure\n", encoding="utf-8")
    assert title_of(run) == "Stone Collector Birthday Adventure"


def test_the_recorded_title_beats_the_outline(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"slug": "x", "title": "The Key"}), encoding="utf-8")
    (tmp_path / "outline.md").write_text("# Outline — Finisterre Lighthouse Retirement\n", encoding="utf-8")
    assert title_of(tmp_path) == "The Key"


def test_the_manuscript_heading_beats_everything(tmp_path):
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "book.md").write_text("# Captain Crunch and the Hill\n", encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps({"title": "The Key"}), encoding="utf-8")
    assert title_of(tmp_path) == "Captain Crunch and the Hill"


def test_humanise_keeps_small_words_small():
    assert humanise("the-other-side-of-the-hill") == "The Other Side of the Hill"


def test_the_runs_list_carries_the_title_not_only_the_slug(db, tmp_path):
    from pathlib import Path
    from backend.commons.config.settings import Settings
    from backend.commons.db import repository as write_repo
    from backend.runs.service import RunService

    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                                  use_recorded_stream=True))
    write_repo.create_run(db, run_id="r1", slug="the-other-side-of-the-hill",
                          premise="a boy and a hill", profile="tiny", tone=None,
                          snapshot={"novel": {"chapters": 1}})
    assert svc.list()[0]["title"] == "The Other Side of the Hill"
    assert svc.get("r1")["title"] == "The Other Side of the Hill"
