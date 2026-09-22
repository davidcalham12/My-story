"""Persisting a run. After every stage and every attempt, never only at the end.

A background task that keeps progress in memory loses it to a restart, and a run
measured in hours will meet one. v1 wrote `state.json` only when it finished,
which is why an interrupted run left nothing anyone could read.
"""

from __future__ import annotations

import json
import sqlite3

from backend.commons.db.connection import tx


def now() -> str:
    """A real clock reading.

    v1 estimated its timestamps and a log claimed 24 minutes for a run that took
    72. A plausible number and a measured one look identical once written down,
    which is why this is a function and not a habit.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_run(conn, *, run_id, slug, premise, profile, tone, snapshot) -> None:
    with tx(conn):
        conn.execute(
            "INSERT INTO runs (id, slug, premise, profile, tone, config_snapshot, "
            "stage, source, started_at) VALUES (?,?,?,?,?,?,?, 'v2', ?)",
            (run_id, slug, premise, profile, tone, json.dumps(snapshot), "FLOW-1", now()),
        )


def set_stage(conn, run_id: str, stage: str) -> None:
    with tx(conn):
        conn.execute("UPDATE runs SET stage = ? WHERE id = ?", (stage, run_id))


def halt(conn, run_id: str, kind: str, detail: str) -> None:
    """One of gate | budget | context | interrupted. What was produced stays
    readable; that is the whole difference between halting and crashing."""
    with tx(conn):
        conn.execute(
            "UPDATE runs SET halted = ?, halted_detail = ?, finished_at = ? WHERE id = ?",
            (kind, detail, now(), run_id),
        )


def finish(conn, run_id: str) -> None:
    with tx(conn):
        conn.execute(
            "UPDATE runs SET stage = 'complete', finished_at = ? WHERE id = ?",
            (now(), run_id),
        )


def warn(conn, run_id: str, kind: str, detail: str, chapter: int | None = None) -> None:
    with tx(conn):
        conn.execute(
            "INSERT INTO run_warnings (run_id, kind, detail, chapter, ts) "
            "VALUES (?,?,?,?,?)",
            (run_id, kind, detail, chapter, now()),
        )


def save_attempt(conn, *, run_id, chapter, attempt, title, draft_path, words,
                 scores, verdict, aggregate, findings, promoted=False) -> int:
    """A chapter's attempt, its five scores and its findings - one transaction.

    A crash between them leaves a run nobody can explain: scores without the
    draft they judged, or findings pointing at an attempt that was never written.
    """
    with tx(conn):
        cur = conn.execute(
            "INSERT INTO attempts (run_id, chapter, attempt, title, draft_path, words, "
            "aggregate, verdict, promoted, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, title, draft_path, words, aggregate,
             verdict, 1 if promoted else 0, now()),
        )
        attempt_id = int(cur.lastrowid)
        for characteristic, score in scores.items():
            conn.execute(
                "INSERT INTO scores (attempt_id, characteristic, score) VALUES (?,?,?)",
                (attempt_id, characteristic, score),
            )
        for f in findings:
            conn.execute(
                "INSERT INTO findings (attempt_id, characteristic, severity, kind, "
                "quote, claim, fix, reference, upheld, late) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, f.get("characteristic", "?"), f.get("severity", "medium"),
                 f.get("kind"), f.get("quote"), f.get("claim") or f.get("problem"),
                 f.get("fix"), f.get("reference"),
                 0 if f.get("upheld") is False else 1,
                 1 if f.get("late") else 0),
            )
    return attempt_id


def save_gate(conn, *, run_id, chapter, attempt, aggregate, threshold, verdict, note) -> None:
    with tx(conn):
        conn.execute(
            "INSERT INTO gate_decisions (run_id, chapter, attempt, aggregate, threshold, "
            "verdict, note, ts) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, aggregate if aggregate is not None else -1,
             threshold, verdict, note, now()),
        )


def save_sheet(conn, *, run_id, chapter, attempt, level, body, validated, lines_cited) -> None:
    with tx(conn):
        conn.execute(
            "INSERT OR REPLACE INTO sheets (run_id, chapter, attempt, level, body, "
            "validated, lines_cited, ts) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, level, body, 1 if validated else 0,
             lines_cited, now()),
        )


def save_facts(conn, run_id: str, chapter: int, facts: list[dict]) -> None:
    """The rolling summary, and the knowledge-state it feeds.

    `who` on a `knowledge` fact is what fills character_knowledge - in the SAME
    transaction, so the table cannot drift from the facts it points at.
    """
    with tx(conn):
        for fact in facts:
            kind = fact.get("kind")
            if kind not in ("event", "state-change", "knowledge", "open-question"):
                continue
            cur = conn.execute(
                "INSERT INTO summary_facts (run_id, chapter, kind, fact, who) "
                "VALUES (?,?,?,?,?)",
                (run_id, chapter, kind, str(fact.get("fact", "")), fact.get("who")),
            )
            if kind == "knowledge" and fact.get("who"):
                conn.execute(
                    "INSERT OR IGNORE INTO character_knowledge "
                    "(run_id, character, fact_id, learned_in_chapter) VALUES (?,?,?,?)",
                    (run_id, fact["who"], int(cur.lastrowid), chapter),
                )
