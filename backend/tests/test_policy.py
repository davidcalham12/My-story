"""The forbidden-words guardrail and the two hooks. PLAN-001 §E4, AC-4 and AC-5.

The tests PLAN-001 names, in the order it names them: one hit per level,
`Ándres`/`andres`, `perros`→`perro`, a hit writes an `audit_log` row, and each
hook script prints JSON and exits non-zero on a hit.

The hooks are run **as subprocesses**, the way `test_instruments.py` runs the
Node instruments, because that is how Claude Code runs them. Importing the
module and calling `main()` would test the code and not the script, and the two
differ in exactly the places that break: the interpreter, the exit code, the
encoding of stdout. This phase is about accented characters, so the last of
those is the subject and not a detail.

What these tests do NOT cover, said here rather than discovered later: whether
Claude Code fires the hooks at all. That is AC-5's **D** half — a demonstration,
wired in `.claude/settings.json`, which no test in this suite can reach.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from backend.commons.db.connection import connect
from backend.commons.db.migrate import migrate
from backend.policy import audit, forbidden

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"


# --------------------------------------------------------------- the detector


def test_the_migration_seeds_the_global_level(db):
    rows = db.execute(
        "SELECT term FROM forbidden_words WHERE level = 'global'").fetchall()
    assert len(rows) >= 3, "011_policy.sql seeds the terms no novel may carry"


def test_every_seeded_term_carries_the_normalisation_the_detector_uses(db):
    """The seed is hand-written SQL and the rule is Python; they can drift.

    A seeded row whose `normalised` was computed by a different rule than the one
    `check` compares against is a term that is in the table and cannot ever be
    hit — the worst failure this table has, because it looks configured.
    """
    for row in db.execute("SELECT term, normalised FROM forbidden_words"):
        assert row["normalised"] == forbidden.normalise(row["term"]), row["term"]


def test_the_level_is_constrained_to_three(db):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO forbidden_words (level, term, normalised) "
                   "VALUES ('whatever', 'x', 'x')")


def test_one_hit_per_level(db):
    """AC-4's first clause. A global term, a client term and a novel term."""
    forbidden.add_term(db, "client", "Ferrovial")
    forbidden.add_term(db, "novel", "Ándres")

    text = ("Lorem ipsum, said Ándres, who had once worked at Ferrovial.")
    hits = forbidden.check(text, forbidden.terms(db))

    assert {h.level for h in hits} == {"global", "client", "novel"}
    assert [h.quote for h in hits] == ["Lorem ipsum", "Ándres", "Ferrovial"]


def test_an_accent_is_not_a_disguise(db):
    """`Ándres` and `andres` are the same term, whichever side wears the accent."""
    forbidden.add_term(db, "novel", "Ándres")
    assert forbidden.check("andres llamó a la puerta", forbidden.terms(db))

    db.execute("DELETE FROM forbidden_words WHERE level = 'novel'")
    forbidden.add_term(db, "novel", "andres")
    assert forbidden.check("Ándres llamó a la puerta", forbidden.terms(db))


def test_a_plural_hits_the_singular_term(db):
    forbidden.add_term(db, "client", "perro")
    hits = forbidden.check("Los perros ladraban toda la noche.", forbidden.terms(db))
    assert [(h.term, h.quote) for h in hits] == [("perro", "perros")]


def test_a_word_that_merely_contains_the_term_is_not_a_hit(db):
    """`perro` is a word, not a substring. `perrera` is a different word.

    The first shape of this check was `term in text.casefold()`, which turns any
    short term into a guardrail that fires on prose nobody wrote wrong.
    """
    forbidden.add_term(db, "client", "perro")
    assert forbidden.check("La perrera estaba vacía.", forbidden.terms(db)) == []


def test_a_term_of_several_words_survives_the_punctuation_between_them(db):
    """A comma is not a disguise, and the order of the words is the term.

    The first version of this test asserted that `mi ex, mujer` was NOT the term
    `mi ex mujer`, and that is the wrong way round: a guardrail a comma defeats
    is a guardrail. What must not match is a different sequence of the same
    words, which is a different thing said.
    """
    forbidden.add_term(db, "client", "mi ex mujer")
    assert forbidden.check("Habló de mi ex mujer sin nombrarla.",
                           forbidden.terms(db))
    assert [h.quote for h in forbidden.check("mi ex, mujer de otro",
                                             forbidden.terms(db))] == ["mi ex, mujer"]
    assert forbidden.check("mujer de mi ex", forbidden.terms(db)) == []


# --------------------------------------------------------------- the audit log


def test_a_hit_writes_an_audit_row(db):
    forbidden.add_term(db, "novel", "Ándres")
    hits = forbidden.check("andres estuvo aquí", forbidden.terms(db))
    audit.record(db, run_id="a-slug", actor="policy-hook",
                 decision="hit", detail=json.dumps([h.as_dict() for h in hits]))

    rows = audit.entries(db, "a-slug")
    assert len(rows) == 1
    assert rows[0]["decision"] == "hit"
    assert rows[0]["actor"] == "policy-hook"
    assert "andres" in rows[0]["detail"]
    assert rows[0]["ts"]
    # Post-hoc export (docs/spec.md §7). NULL is "not exported yet", which is
    # not the same fact as "exported with no trace".
    assert rows[0]["langfuse_trace_id"] is None


def test_the_decision_is_constrained(db):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        audit.record(db, run_id="a-slug", actor="policy-hook",
                     decision="probably fine", detail="{}")


# ------------------------------------------------------------------ the hooks


def _run_dir(tmp_path: Path, *, chapter: str, min_words: int = 1,
             max_words: int = 100_000, characters: str | None = None) -> Path:
    run = tmp_path / "output" / "a-slug"
    (run / "chapters").mkdir(parents=True)
    (run / "chapters" / "ch01.md").write_text(chapter, encoding="utf-8")
    (run / "config.snapshot.json").write_text(json.dumps({
        "novel": {"words_per_chapter": {"min": min_words, "max": max_words},
                  "tolerance_pct": 0}}), encoding="utf-8")
    if characters is not None:
        (run / "bible").mkdir()
        (run / "bible" / "characters.md").write_text(characters, encoding="utf-8")
    return run


def _db(tmp_path: Path):
    conn = connect(tmp_path / "novaforge.db")
    migrate(conn)
    return conn


def _hook(script: str, path: Path, db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "NOVAFORGE_DB": str(db_path), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, str(HOOKS / script), str(path)],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=ROOT, env=env)


def test_the_policy_hook_prints_json_and_exits_non_zero_on_a_hit(tmp_path):
    db_path = tmp_path / "novaforge.db"
    conn = _db(tmp_path)
    forbidden.add_term(conn, "novel", "Ándres")
    conn.close()

    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nandres cerró la puerta.\n")
    result = _hook("policy.py", run / "chapters" / "ch01.md", db_path)

    assert result.returncode != 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "hit"
    assert report["validator"] == "forbidden_words"
    assert [h["term"] for h in report["hits"]] == ["Ándres"]
    assert report["hits"][0]["quote"] == "andres"

    conn = connect(db_path)
    rows = audit.entries(conn, "a-slug")
    conn.close()
    assert [r["decision"] for r in rows] == ["hit"]


def test_the_policy_hook_exits_zero_on_a_clean_chapter_and_says_so(tmp_path):
    """A clean check is a row too.

    An audit log that holds only hits cannot tell "the policy ran and found
    nothing" from "the policy never ran", and the second is the one an auditor
    needs to see. Absent is never zero.
    """
    db_path = tmp_path / "novaforge.db"
    _db(tmp_path).close()

    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nLa puerta estaba abierta.\n")
    result = _hook("policy.py", run / "chapters" / "ch01.md", db_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["verdict"] == "clean"

    conn = connect(db_path)
    rows = audit.entries(conn, "a-slug")
    conn.close()
    assert [r["decision"] for r in rows] == ["clean"]


def test_the_validate_chapter_hook_exits_zero_on_a_chapter_that_is_right(tmp_path):
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nNell Harker counted the ships.\n",
                   characters="- **Nell Harker** — the keeper\n")
    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "clean"
    assert "length" in report["checked"]
    assert "canonical-names" in report["checked"]


def test_the_validate_chapter_hook_prints_json_and_exits_non_zero_on_a_defect(tmp_path):
    """A name one letter out of the Bible's — the defect `names.py` exists for."""
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nNell Harper counted the ships.\n",
                   characters="- **Nell Harker** — the keeper\n")
    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode != 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "defects"
    assert [d["kind"] for d in report["defects"]] == ["name-one-letter-out"]
    assert report["defects"][0]["quote"] == "Harper"


def test_the_validate_chapter_hook_reports_a_chapter_out_of_band(tmp_path):
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nToo short.\n", min_words=1000,
                   max_words=1500, characters="- **Nell Harker** — the keeper\n")
    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode != 0
    report = json.loads(result.stdout)
    assert [d["kind"] for d in report["defects"]] == ["length-out-of-band"]


def test_the_validate_chapter_hook_says_not_checked_rather_than_clean(tmp_path):
    """No `bible/characters.md` means the names were not checked.

    Reporting `clean` here is the absent-read-as-zero mistake in the place it
    costs most: a hook that says nothing is wrong when it looked at nothing.
    """
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nNell Harper counted.\n")
    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "clean"
    assert any("characters.md" in n for n in report["not_checked"])
    assert "canonical-names" not in report["checked"]


def test_the_validate_chapter_hook_rejects_a_malformed_critique(tmp_path):
    """`schema_role_output` (docs/spec.md §2): a critique that does not conform.

    A finding with no quote is the one that matters: the sheet's rule 3 needs a
    literal quote, so a finding without one cannot be sent to the writer and
    would be dropped in silence at the moment it was needed.
    """
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nNell Harker counted.\n",
                   characters="- **Nell Harker** — the keeper\n")
    (run / "critiques").mkdir()
    (run / "critiques" / "ch01.continuity.json").write_text(json.dumps({
        "critic": "continuity", "chapter": 1,
        "iterations": [{"iteration": 1, "score": 4,
                        "findings": [{"claim": "something is wrong"}]}]}),
        encoding="utf-8")

    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode != 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert [d["kind"] for d in report["defects"]] == ["critique-schema"]
    assert "ch01.continuity.json" in report["defects"][0]["claim"]


def test_the_validate_chapter_hook_accepts_a_real_critique_file(tmp_path):
    """The models are held against a critique a real run actually wrote.

    A schema written from the docstring of the writer rather than from its
    output is a schema that rejects the eight runs in `output/`.
    """
    real = json.loads((ROOT / "output/cartographer-inconstant-valley/critiques"
                       / "ch01.continuity.json").read_text(encoding="utf-8"))
    run = _run_dir(tmp_path, chapter="# Chapter 1\n\nNell Harker counted.\n",
                   characters="- **Nell Harker** — the keeper\n")
    (run / "critiques").mkdir()
    (run / "critiques" / "ch01.continuity.json").write_text(
        json.dumps(real), encoding="utf-8")
    (run / "critiques" / "outline.audit.json").write_text(
        json.dumps({"score": 10, "findings": [], "notes": ["ok"]}), encoding="utf-8")

    result = _hook("validate-chapter.py", run / "chapters" / "ch01.md",
                   tmp_path / "novaforge.db")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "critique-schema" in json.loads(result.stdout)["checked"]


def test_both_hooks_ignore_a_write_that_is_not_a_chapter(tmp_path):
    """`.claude/settings.json` matches a TOOL, not a path.

    Claude Code's `PostToolUse` matcher selects `Write` and nothing narrower, so
    "under `output/*/chapters/`" is a condition the scripts have to apply
    themselves. Without it every `Write` in the session runs the guardrail over
    a file that is not prose, and `policy.py` writes an `audit_log` row for a run
    that does not exist — this note contains a seeded global term precisely so
    that a missing guard fails loudly rather than quietly.
    """
    note = tmp_path / "docs" / "notes.md"
    note.parent.mkdir(parents=True)
    note.write_text("lorem ipsum, a note to self", encoding="utf-8")
    _db(tmp_path).close()

    for script in ("policy.py", "validate-chapter.py"):
        result = _hook(script, note, tmp_path / "novaforge.db")
        assert result.returncode == 0, script + result.stdout + result.stderr
        assert json.loads(result.stdout)["verdict"] == "skipped", script

    conn = connect(tmp_path / "novaforge.db")
    rows = audit.entries(conn)
    conn.close()
    assert rows == [], "a file that is not a chapter is not a policy decision"


def test_the_hook_scripts_name_their_encoding():
    """`test_utf8_everywhere.py` walks `backend/` and cannot see `.claude/`.

    The hooks are the scripts that read prose with accents in it and print it
    back as JSON, so they are the last place where an inherited cp1252 should be
    allowed to decide anything. `reconfigure` is checked too: without it the
    report above is a `UnicodeEncodeError` on a Windows console the moment a
    quote carries an `Á`.

    The regex is asserted non-empty so that a rewrite which removes every
    `read_text` cannot turn this into a test that passes over nothing.
    """
    for script in ("policy.py", "validate-chapter.py"):
        source = (HOOKS / script).read_text(encoding="utf-8")
        calls = re.findall(r"\.(?:read|write)_text\([^)]*\)", source)
        assert calls, script
        for call in calls:
            assert "utf-8" in call, f"{script}: {call}"
        assert 'reconfigure(encoding="utf-8")' in source, script


def test_both_hooks_refuse_a_path_that_is_not_there(tmp_path):
    """Exit 2, like every other instrument here: a missing file is not a clean
    chapter, and the two must not share an exit code."""
    for script in ("policy.py", "validate-chapter.py"):
        result = _hook(script, tmp_path / "nowhere" / "ch01.md",
                       tmp_path / "novaforge.db")
        assert result.returncode == 2, script
