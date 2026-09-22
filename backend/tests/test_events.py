"""PLAN-007 6.2 — the stream itself is the record (SPEC-007 FR-RNR-3, AC-20).

Until this table existed the database held what the stream *revealed* — stages,
calls, scores — and not the stream. A run is judged by the gate it ran, and
reconstructing which gate that was from the scores produced a category error
twice in one afternoon (migration 008). The raw lines end that.
"""

import json

import pytest

from backend.commons.db import repository as repo
from backend.commons.db.migrate import migrate


@pytest.fixture
def run(db):
    repo.create_run(db, run_id="r1", slug="s1", premise="A premise long enough.",
                    profile="tiny", tone=None, snapshot={})
    return "r1"


def test_migration_009_creates_events_with_seq_per_run(db, run):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(events)")}
    assert cols == {"run_id", "seq", "ts", "type", "payload"}
    repo.append_event(db, run, seq=1, type="system", payload='{"type": "system"}')
    repo.append_event(db, run, seq=2, type="assistant", payload='{"type": "assistant"}')
    # The same seq twice on one run is a bug in the writer, not a second event.
    with pytest.raises(Exception):
        repo.append_event(db, run, seq=2, type="assistant", payload="{}")


def test_seq_is_dense_and_monotonic_within_a_run(db, run):
    for i in range(1, 6):
        repo.append_event(db, run, seq=i, type="assistant", payload=json.dumps({"i": i}))
    rows = repo.events_after(db, run, 0)
    assert [r["seq"] for r in rows] == [1, 2, 3, 4, 5]
    assert [r["seq"] for r in repo.events_after(db, run, 3)] == [4, 5]
    assert repo.events_after(db, run, 5) == []


def test_payload_is_the_untouched_line(db, run):
    """Not re-serialised: key order, spacing and unknown fields survive, so what
    is stored is what `claude -p` wrote and nothing this reader understood."""
    raw = '{"type":"system","subtype":"init",  "odd_field": [1, 2,3]}'
    repo.append_event(db, run, seq=1, type="system", payload=raw)
    assert repo.events_after(db, run, 0)[0]["payload"] == raw


def test_migrating_twice_applies_009_once(db):
    assert migrate(db) == [], "a second migrate() on a migrated database applies nothing"
    applied = {r["name"] for r in db.execute("SELECT name FROM schema_migrations")}
    assert "009_events.sql" in applied
