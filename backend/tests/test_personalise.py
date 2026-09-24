"""The book is personalised in code, at publication (owner's decision B,
2026-09-24). The models never write the recipient's alias: the organisation's
privacy policy makes the orchestrator write a placeholder instead, and a script
puts the alias from the stored brief in its place. No model touches this step.
"""

from __future__ import annotations

import json

from backend.brief import domain
from backend.commons.db import repository
from backend.publish import personalise

TOKEN = personalise.TOKEN


def _setup(db, tmp_path):
    brief = domain.parse(json.loads(
        (domain.EXAMPLES / "01-hijo.json").read_text(encoding="utf-8")))
    with db:
        db.execute("INSERT INTO briefs (id, created_at, payload) VALUES (?,?,?)",
                   ("b1", "2026-09-24T00:00:00Z", json.dumps(brief.model_dump())))
    repository.create_run(db, run_id="r1", slug="gift", premise="p", profile="exam",
                          tone=None, snapshot="{}", brief_id="b1")
    with db:
        db.execute("INSERT INTO facts (run_id, kind, text, source) VALUES "
                   "('r1', 'character', ?, 'characters')", (f"{TOKEN} — the hero",))
    d = tmp_path / "gift"
    (d / "chapters").mkdir(parents=True)
    (d / "bible").mkdir()
    (d / "chapters" / "ch01.md").write_text(f"# Chapter 1\n\n{TOKEN} woke.\n", encoding="utf-8")
    (d / "chapters" / "ch01.attempt1.md").write_text(f"{TOKEN}\n", encoding="utf-8")
    (d / "bible" / "characters.md").write_text(f"### {TOKEN}\n", encoding="utf-8")
    return d, brief.recipient.alias


def test_the_placeholder_becomes_the_briefs_alias(db, tmp_path):
    d, alias = _setup(db, tmp_path)
    assert personalise.personalise(db, d) == 3
    chapter = (d / "chapters" / "ch01.md").read_text(encoding="utf-8")
    assert TOKEN not in chapter and f"{alias} woke." in chapter
    assert alias in (d / "bible" / "characters.md").read_text(encoding="utf-8")
    fact = db.execute("SELECT text FROM facts WHERE run_id='r1'").fetchone()[0]
    assert fact.startswith(alias)


def test_the_gate_approved_text_is_kept_and_attempts_are_left_alone(db, tmp_path):
    d, _ = _setup(db, tmp_path)
    personalise.personalise(db, d)
    assert TOKEN in (d / "chapters" / "ch01.anon.md").read_text(encoding="utf-8")
    assert TOKEN in (d / "chapters" / "ch01.attempt1.md").read_text(encoding="utf-8")


def test_twice_is_once(db, tmp_path):
    d, _ = _setup(db, tmp_path)
    personalise.personalise(db, d)
    assert personalise.personalise(db, d) == 0
    assert TOKEN in (d / "chapters" / "ch01.anon.md").read_text(encoding="utf-8")


def test_no_brief_no_substitution(db, tmp_path):
    repository.create_run(db, run_id="r2", slug="bare", premise="p", profile="exam",
                          tone=None, snapshot="{}")
    d = tmp_path / "bare"
    (d / "chapters").mkdir(parents=True)
    (d / "chapters" / "ch01.md").write_text(f"{TOKEN}\n", encoding="utf-8")
    assert personalise.personalise(db, d) == 0


def test_release_prints_the_personalised_book(db, tmp_path, monkeypatch):
    from backend.publish import pdf, release

    d, alias = _setup(db, tmp_path)
    monkeypatch.setattr(pdf, "print_pdf", lambda h, p: p.write_bytes(b"%PDF") or p)
    release.release(db, d)
    html = (d / "dist" / "v1" / "novel.html").read_text(encoding="utf-8")
    assert TOKEN not in html and alias in html


def test_a_run_from_a_brief_prints_the_briefs_dedication(db, tmp_path, monkeypatch):
    """Nothing wrote `dedication.md` for a run started from a brief, so the cover
    said "no dedication" while the brief carried one."""
    from backend.publish import pdf, release

    d, _ = _setup(db, tmp_path)
    dedication = json.loads((domain.EXAMPLES / "01-hijo.json").read_text(
        encoding="utf-8"))["dedication"]
    monkeypatch.setattr(pdf, "print_pdf", lambda h, p: p.write_bytes(b"%PDF") or p)
    release.release(db, d)
    html = (d / "dist" / "v1" / "novel.html").read_text(encoding="utf-8")
    assert dedication.split(",")[0] in html
