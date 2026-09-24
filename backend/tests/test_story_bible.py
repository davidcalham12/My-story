"""The Story Bible in SQLite — PLAN-001-exam E3, `docs/spec.md` §1, §4 AC-3.

Until now the Bible was four Markdown files and nothing could ask it a question.
"Which chapters would change if this fact changed" was a `grep` a person ran by
hand, and the answer was as good as their patience. These tests hold the tables,
the ingest that fills them from the Markdown the agents already write, and the
usage rows a promoted chapter leaves behind.

They also hold the **limit** `docs/spec.md` §7 declares: `fact_usage` is string
matching, not meaning. A paraphrased fact must come back **uncovered**, never
invented as covered, and there is a test below that fails if that ever reverses.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.bible import router as bible_router
from backend.bible.ingest import ingest
from backend.chapters.fact_usage import record
from backend.runs.router import get_service

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "output" / "lighthouse-keeper-ledger"
RUN_ID = RUN_DIR.name


@pytest.fixture
def run(db):
    """The real run's row, so the Bible's rows have a run to hang off.

    Every run-scoped table in this database references `runs(id)`; a Bible
    ingested against a run that does not exist would be orphan rows nobody could
    find again.
    """
    db.execute(
        "INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
        "started_at) VALUES (?,?,?,?,?,?,?)",
        (RUN_ID, RUN_ID, "a keeper's ledger", "tiny", "{}", "complete",
         "2026-09-22T15:53:55Z"),
    )
    return db


# --------------------------------------------------------------------------
# The migration


def test_migration_010_creates_the_story_bible_tables(db):
    names = {r["name"] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"facts", "fact_usage", "characters", "places", "chronology",
            "chronology_participants"} <= names


def test_010_is_recorded_as_applied(db):
    applied = {r["name"] for r in db.execute("SELECT name FROM schema_migrations")}
    assert "010_story_bible.sql" in applied


def test_a_fact_from_an_unnamed_source_is_refused(run):
    """`source` is the closed list the spec names, because `mandatory_facts`
    selects on it: a typo'd `source` would silently exempt a mandatory fact."""
    with pytest.raises(sqlite3.IntegrityError):
        run.execute(
            "INSERT INTO facts (run_id, kind, text, source) VALUES (?,?,?,?)",
            (RUN_ID, "rule", "the light shows two flashes", "somewhere"))


def test_mandatory_is_a_flag_not_a_number(run):
    with pytest.raises(sqlite3.IntegrityError):
        run.execute(
            "INSERT INTO facts (run_id, kind, text, source, mandatory) "
            "VALUES (?,?,?,?,?)",
            (RUN_ID, "rule", "the light shows two flashes", "world", 2))


def test_a_usage_row_cannot_name_chapter_zero(run):
    """Chapters are one-based everywhere in this repository. A 0 here is the
    shape a missing chapter number takes when nobody checks."""
    run.execute("INSERT INTO facts (id, run_id, kind, text, source) "
                "VALUES (1,?,?,?,?)", (RUN_ID, "rule", "a rule", "world"))
    with pytest.raises(sqlite3.IntegrityError):
        run.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, "
                    "matched) VALUES (1, 1, 0, 'x')")


def test_fact_usage_has_no_foreign_key_on_version(run):
    """`versions` is E6's table and does not exist yet. The column is a plain
    INTEGER on purpose; a foreign key here would make this migration wait for
    one it does not need."""
    keys = list(run.execute("PRAGMA foreign_key_list(fact_usage)"))
    assert {r["table"] for r in keys} == {"facts"}


# --------------------------------------------------------------------------
# Ingest, on the Bible a real run actually wrote


def test_ingest_reads_the_real_bible(run):
    report = ingest(run, RUN_DIR)

    characters = list(run.execute(
        "SELECT * FROM characters WHERE run_id = ?", (RUN_ID,)))
    assert len(characters) >= 3, [dict(r) for r in characters]
    assert "Ada Rowe" in {r["canonical_name"] for r in characters}

    chronology = list(run.execute(
        "SELECT * FROM chronology WHERE run_id = ? ORDER BY seq", (RUN_ID,)))
    assert len(chronology) >= 4, [dict(r) for r in chronology]

    mysteries = list(run.execute(
        "SELECT text FROM facts WHERE run_id = ? AND source = 'mysteries'",
        (RUN_ID,)))
    assert mysteries, "mysteries.md produced no facts"

    assert report.characters == len(characters)
    assert report.chronology == len(chronology)


def test_ingest_records_the_role_it_read_and_no_birth_date_it_did_not(run):
    """`birth_date` is NULL here because this Bible states none. Absent is not a
    date, and the sheet must be able to tell the two apart."""
    ingest(run, RUN_DIR)
    ada = run.execute(
        "SELECT * FROM characters WHERE run_id = ? AND canonical_name = 'Ada Rowe'",
        (RUN_ID,)).fetchone()
    assert "keeper of the Corbie Light" in ada["role"]
    assert ada["birth_date"] is None
    assert ada["first_chapter"] is None  # no chapter has been recorded yet


def test_ingest_ties_the_timeline_to_the_people_in_it(run):
    ingest(run, RUN_DIR)
    who = {r["canonical_name"] for r in run.execute(
        "SELECT DISTINCT canonical_name FROM chronology_participants")}
    assert {"Ada Rowe", "Walter Byrd"} <= who


def test_ingest_reads_the_chapter_a_timeline_row_pins_itself_to(run):
    ingest(run, RUN_DIR)
    pinned = {r["excludes_after"] for r in run.execute(
        "SELECT excludes_after FROM chronology WHERE excludes_after IS NOT NULL")}
    assert {1, 2, 3} <= pinned
    # The backstory rows name no chapter, and must not be given one.
    assert run.execute("SELECT COUNT(*) FROM chronology "
                       "WHERE excludes_after IS NULL").fetchone()[0] > 0


def test_ingest_runs_twice_without_doubling_the_bible(run):
    """FLOW-2 may be re-run after a correction to `characters.md`. A second
    ingest that doubled every row would make `impact` count each chapter twice.
    """
    first = ingest(run, RUN_DIR)
    second = ingest(run, RUN_DIR)
    assert (second.facts, second.characters, second.chronology) == \
           (first.facts, first.characters, first.chronology)


def test_ingest_names_the_places_the_world_sets_itself_in(run):
    ingest(run, RUN_DIR)
    places = {r["canonical_name"] for r in run.execute(
        "SELECT canonical_name FROM places WHERE run_id = ?", (RUN_ID,))}
    assert "Sallowmere Reach" in places, sorted(places)


# --------------------------------------------------------------------------
# fact_usage — string matching, and honest about it


def test_fact_usage_for_chapter_one_names_the_characters_in_it(run):
    ingest(run, RUN_DIR)
    record(run, RUN_DIR, 1)

    used = {r["text"] for r in run.execute(
        "SELECT f.text FROM fact_usage u JOIN facts f ON f.id = u.fact_id "
        "WHERE u.chapter = 1 AND f.kind = 'character'")}
    named = {name for name in ("Ada Rowe", "Thomas Creed", "Nell Harker",
                               "Walter Byrd")
             if any(name in text for text in used)}
    assert named == {"Ada Rowe", "Thomas Creed", "Nell Harker"}, named


def test_a_chapter_nobody_recorded_has_no_rows_rather_than_a_zero(run):
    ingest(run, RUN_DIR)
    record(run, RUN_DIR, 1)
    assert run.execute(
        "SELECT COUNT(*) FROM fact_usage WHERE chapter = 3").fetchone()[0] == 0


def test_a_paraphrased_fact_is_missed_and_never_invented_as_covered(run):
    """The limit `docs/spec.md` §7 declares, held as a test.

    The Bible says the *Marigold* was entered "nineteen hours after the line
    that records her passing". A fact that says the same thing in other words is
    **not** found, and the failure direction is the safe one: uncovered when it
    was in fact covered, never covered when it was not.
    """
    ingest(run, RUN_DIR)
    run.execute(
        "INSERT INTO facts (id, run_id, kind, text, source, mandatory) "
        "VALUES (9001,?,?,?,?,1)",
        (RUN_ID, "recipient", "the boat was logged the better part of a day "
                              "before she ever left the quay", "brief"))
    record(run, RUN_DIR, 2)
    assert run.execute(
        "SELECT COUNT(*) FROM fact_usage WHERE fact_id = 9001").fetchone()[0] == 0


def test_a_literal_brief_fact_is_found_in_the_prose(run):
    """The other half of the same claim: matching works where the words match,
    which is the case `mandatory_facts` was built for — a brief's facts are
    short and literal ("the dog is called Nala")."""
    ingest(run, RUN_DIR)
    run.execute(
        "INSERT INTO facts (id, run_id, kind, text, source, mandatory) "
        "VALUES (9002,?,?,?,?,1)",
        (RUN_ID, "recipient", "the seventh step", "brief"))
    record(run, RUN_DIR, 1)
    row = run.execute(
        "SELECT * FROM fact_usage WHERE fact_id = 9002").fetchone()
    assert row["chapter"] == 1
    assert row["matched"] == "the seventh step"


def test_recording_a_chapter_twice_keeps_one_row_per_fact(run):
    ingest(run, RUN_DIR)
    record(run, RUN_DIR, 1)
    record(run, RUN_DIR, 1)
    rows = run.execute(
        "SELECT fact_id, COUNT(*) c FROM fact_usage WHERE chapter = 1 "
        "GROUP BY fact_id HAVING c > 1").fetchall()
    assert not rows, [dict(r) for r in rows]


def test_recording_a_chapter_sets_the_first_chapter_a_character_appears_in(run):
    ingest(run, RUN_DIR)
    record(run, RUN_DIR, 2)
    record(run, RUN_DIR, 1)
    first = {r["canonical_name"]: r["first_chapter"] for r in run.execute(
        "SELECT canonical_name, first_chapter FROM characters WHERE run_id = ?",
        (RUN_ID,))}
    assert first["Thomas Creed"] == 1   # chapter 1 only
    assert first["Walter Byrd"] == 2    # chapter 2 only — and not 1
    assert first["Ada Rowe"] == 1       # both chapters: the earlier one wins


# --------------------------------------------------------------------------
# The HTTP surface (SPEC-EXAM-002 §B.4)


@pytest.fixture
def client(run):
    """Mounted on an app of its own: `backend/main.py` is another phase's file
    and its route list is pinned by `test_api_contract`."""
    ingest(run, RUN_DIR)
    record(run, RUN_DIR, 1)
    app = FastAPI()
    app.include_router(bible_router.router, prefix="/api/runs")
    app.dependency_overrides[get_service] = lambda: SimpleNamespace(conn=run)
    with TestClient(app) as c:
        yield c


def test_facts_lists_each_fact_with_the_chapters_that_use_it(client):
    body = client.get(f"/api/runs/{RUN_ID}/facts").json()
    assert body
    ada = next(f for f in body if f["kind"] == "character"
               and "Ada Rowe" in f["text"])
    assert ada["chapters"] == [1]
    assert ada["source"] == "characters"
    walter = next(f for f in body if f["kind"] == "character"
                  and "Walter Byrd" in f["text"])
    assert walter["chapters"] == []


def test_impact_is_the_chapters_a_change_to_this_fact_would_reach(client):
    body = client.get(f"/api/runs/{RUN_ID}/facts").json()
    ada = next(f for f in body if "Ada Rowe" in f["text"])
    impact = client.get(f"/api/runs/{RUN_ID}/facts/{ada['id']}/impact").json()
    assert impact["chapters"] == [1]
    assert impact["exact"] is False  # string matching; §7 says so out loud


def test_impact_of_an_unknown_fact_is_404_not_an_empty_list(client):
    """An empty list would read as "this change touches nothing", which is the
    most dangerous wrong answer this endpoint can give."""
    assert client.get(f"/api/runs/{RUN_ID}/facts/999999/impact").status_code == 404


def test_the_sheet_lists_characters_and_places_with_their_first_chapter(client):
    characters = client.get(f"/api/runs/{RUN_ID}/bible/characters").json()
    ada = next(c for c in characters if c["canonical_name"] == "Ada Rowe")
    assert ada["first_chapter"] == 1
    walter = next(c for c in characters if c["canonical_name"] == "Walter Byrd")
    assert walter["first_chapter"] is None  # absent, not chapter 0

    places = client.get(f"/api/runs/{RUN_ID}/bible/places").json()
    assert "Sallowmere Reach" in {p["canonical_name"] for p in places}


def test_an_unknown_run_is_404_everywhere(client):
    for path in ("facts", "bible/characters", "bible/places"):
        assert client.get(f"/api/runs/no-such-run/{path}").status_code == 404


def test_ingest_finds_a_v2_run_by_its_slug_not_only_by_its_id(db, tmp_path):
    """`run_dir.name` is a run's id only for the v1 runs that were imported
    under it. A v2 run has a hex id and a slug, and the directory is named after
    the slug — so the first conductor novel ingested nothing and the whole story
    bible chain (fact_usage, mandatory_facts, Lean) had no rows to stand on.
    """
    from backend.bible import ingest
    from backend.commons.db import repository as repo

    repo.create_run(db, run_id="db2fed5bd97a", slug="leo-and-bruno-cross-the-hill",
                    premise="a premise long enough", profile="exam", tone=None, snapshot={})
    run_dir = tmp_path / "leo-and-bruno-cross-the-hill"
    (run_dir / "bible").mkdir(parents=True)
    (run_dir / "bible" / "world.md").write_text(
        "# The world\n\n## Rules\n\n- The hill hides a station.\n", encoding="utf-8")
    (run_dir / "bible" / "characters.md").write_text(
        "## Leo\n\n**Role:** the boy who asks\n", encoding="utf-8")
    (run_dir / "bible" / "timeline.md").write_text("# Timeline\n", encoding="utf-8")
    (run_dir / "bible" / "mysteries.md").write_text("# Mysteries\n", encoding="utf-8")

    ingest.ingest(db, run_dir)

    rows = db.execute("SELECT COUNT(*) FROM facts WHERE run_id = 'db2fed5bd97a'").fetchone()[0]
    assert rows > 0, "the facts belong to the run's id, which is not its directory name"


def test_usage_finds_a_v2_runs_facts_by_slug(db, tmp_path):
    """A v2 run's id is not its slug. The ingest resolves the directory name to
    the id; the usage recorder did not, so a v2 run found no facts and every
    mandatory fact came out uncovered."""
    db.execute(
        "INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
        "started_at) VALUES (?,?,?,?,?,?,?)",
        ("a1b2c3d4e5f6", "v2-slug", "p", "exam", "{}", "FLOW-4",
         "2026-09-24T00:00:00Z"))
    db.execute("INSERT INTO facts (run_id, kind, text, source, mandatory) "
               "VALUES ('a1b2c3d4e5f6', 'recipient', 'the dog is called Bruno', "
               "'brief', 1)")
    db.commit()
    run_dir = tmp_path / "v2-slug"
    (run_dir / "chapters").mkdir(parents=True)
    (run_dir / "chapters" / "ch01.md").write_text(
        "# Chapter 1\n\nAnd the dog is called Bruno, of course.\n", encoding="utf-8")
    assert record(db, run_dir, 1), "a v2 run's facts must be found by its slug"
