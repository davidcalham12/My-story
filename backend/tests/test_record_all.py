"""Every validator of docs/spec.md §2 that runs per version leaves a row.

`evals/results.md` is a pivot of `validations`; a validator with no row there
is a column nobody can tell from "passed". A validator that cannot run writes
its row anyway, with a NULL value and "not run: <reason>" — absent, never 0.
"""

from __future__ import annotations

import json

from backend.policy import forbidden
from backend.publish import record_all, validations

PER_VERSION = {"schema_brief", "schema_role_output", "canonical_names",
               "chapter_length", "mandatory_facts", "forbidden_words",
               "visual_check", "human_review", "lean_chronology"}


def _run(db, tmp_path):
    db.execute(
        "INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
        "started_at) VALUES ('r1', 'slug1', 'p', 'eval', '{}', 'complete', "
        "'2026-09-24T00:00:00Z')")
    db.commit()
    d = tmp_path / "slug1"
    (d / "chapters").mkdir(parents=True)
    (d / "bible").mkdir()
    (d / "critiques").mkdir()
    (d / "bible" / "characters.md").write_text("# Characters\n", encoding="utf-8")
    (d / "config.snapshot.json").write_text(json.dumps(
        {"novel": {"words_per_chapter": {"min": 3, "max": 20}}}), encoding="utf-8")
    (d / "chapters" / "ch01.md").write_text("# Chapter 1\n\none two three four\n",
                                            encoding="utf-8")
    (d / "chapters" / "ch02.md").write_text("# Chapter 2\n\nthe dragon sleeps\n",
                                            encoding="utf-8")
    (d / "critiques" / "ch01.json").write_text('{"iterations": []}', encoding="utf-8")
    (d / "critiques" / "ch02.json").write_text("not json", encoding="utf-8")
    return d


def test_every_per_version_validator_leaves_a_row(db, tmp_path):
    record_all.record_version(db, _run(db, tmp_path), 1)
    names = {r["validator"] for r in validations.for_version(db, "r1", 1)}
    assert PER_VERSION <= names, PER_VERSION - names


def test_what_cannot_run_is_null_and_says_why(db, tmp_path):
    record_all.record_version(db, _run(db, tmp_path), 1)
    rows = {r["validator"]: r for r in validations.for_version(db, "r1", 1)}
    for name in ("visual_check", "human_review", "schema_brief"):
        assert rows[name]["value"] is None
        assert rows[name]["justification"].startswith(("not run", "no brief"))
    assert rows["lean_chronology"]["justification"].startswith("not run")


def test_the_arithmetic_ones_measure(db, tmp_path):
    forbidden.add_term(db, "client", "dragon")
    db.commit()
    record_all.record_version(db, _run(db, tmp_path), 1)
    rows = validations.for_version(db, "r1", 1)
    fw = next(r for r in rows if r["validator"] == "forbidden_words")
    assert fw["value"] == "1"
    lengths = {r["criterion"]: r["value"] for r in rows
               if r["validator"] == "chapter_length"}
    assert lengths == {"ch01": "4", "ch02": "3"}
    schema = next(r for r in rows if r["validator"] == "schema_role_output")
    assert schema["value"] == "1/2"
