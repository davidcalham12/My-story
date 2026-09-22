import pytest

from backend.commons.config.loader import resolve
from backend.commons.db.migrate import migrate


def test_migrations_run_once(db):
    assert migrate(db) == [], "already applied by the fixture"


def test_migrations_created_every_table(db):
    tables = {r["name"] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    for expected in ("runs", "attempts", "scores", "findings", "gate_decisions",
                     "sheets", "calls", "summary_facts", "character_knowledge",
                     "chunks", "run_completeness", "run_warnings", "events"):
        assert expected in tables


def test_score_must_be_in_range(db):
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('r','s','p','tiny','{}','FLOW-1','now')")
    db.execute("INSERT INTO attempts (run_id, chapter, attempt, draft_path, words, ts) "
               "VALUES ('r',1,1,'p.md',100,'now')")
    with pytest.raises(Exception):
        db.execute("INSERT INTO scores (attempt_id, characteristic, score) "
                   "VALUES (1,'continuity',11)")


def test_unscored_critic_is_null_not_zero(db):
    """A critic with no usable verdict is EXCLUDED, never counted as a pass.

    This once returned 10, which meant a malformed reply silently passed a draft.
    NULL is the only honest value: 10 invents an approval and 0 invents a
    rejection.
    """
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('r','s','p','tiny','{}','FLOW-4','now')")
    db.execute("INSERT INTO attempts (run_id, chapter, attempt, draft_path, words, ts) "
               "VALUES ('r',1,1,'p.md',100,'now')")
    db.execute("INSERT INTO scores (attempt_id, characteristic, score, note) "
               "VALUES (1,'science',NULL,'no usable verdict')")
    row = db.execute("SELECT score FROM scores WHERE characteristic='science'").fetchone()
    assert row["score"] is None


def test_profiles_scale_the_bible():
    """A three-chapter run and a thirty-four-chapter novel must not receive the
    same canon. That inheritance is what an incoherent short run was made of."""
    tiny, full = resolve("tiny"), resolve("full")
    assert tiny["novel"]["chapters"] == 3
    assert full["novel"]["chapters"] == 34
    assert tiny["bible"]["characters"]["max"] < full["bible"]["characters"]["max"]


def test_tone_is_not_decided_by_the_config():
    """No agent declares a genre; it is read off the premise."""
    assert resolve("tiny")["novel"]["tone"] is None


def test_the_ceiling_is_config_not_a_literal():
    """Still config, still 100,000 — but under Annex C it is enforced in two
    layers rather than reserved in advance. See docs/verification.md G2."""
    assert resolve("tiny")["context"]["max_concurrent_tokens"] == 100_000


def test_the_memory_layers_that_do_not_run_are_declared_as_such(db):
    """`verification.md` §3.15 and `architecture.md` §5.1.

    `summary.py` projects a rolling summary from typed facts and `search`
    indexes canon into `chunks`. Both are written, tested and **called by
    nothing**: `save_facts` has no caller, and no run has populated either
    table.

    Neither is a defect. The document describing them as live was, and this
    test exists so the day one of them is switched on, the documentation has to
    move with it.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    callers = []
    for path in (root / "backend").rglob("*.py"):
        if "__pycache__" in path.parts or path.name.startswith("test_"):
            continue
        if path.name in {"repository.py", "summary.py", "search.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "save_facts" in text or "summary.project" in text:
            callers.append(path.name)
    assert not callers, (
        f"{callers} now uses the structured-fact layer. architecture.md §5.1 and "
        f"verification.md §3.15 say it does not run — update them."
    )

    for claim in ("summary_facts", "chunks"):
        assert db.execute(f"SELECT COUNT(*) AS n FROM {claim}").fetchone()["n"] == 0
