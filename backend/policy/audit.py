"""The audit log of policy decisions. SPEC-EXAM-001 §1, AC-4.

Every check writes a row, hit or not. A log that holds only hits cannot tell
"the policy ran and found nothing" from "the policy never ran" — and an auditor
asking whether the guardrail was in force on chapter 7 gets the same silence for
both. That is the absent-read-as-zero mistake in the one place where the whole
value of the record is that it is complete.

It is deliberately not a general event log: `events` (009) already holds the
stream, and this table answers one question — what did the policy decide, about
which run, and when.
"""

from __future__ import annotations

import sqlite3

from backend.commons.db.connection import tx
from backend.commons.db.repository import now


def record(conn: sqlite3.Connection, *, run_id: str, actor: str, decision: str,
           detail: str, langfuse_trace_id: str | None = None) -> None:
    """One decision. `decision` is 'hit', 'clean' or 'override' — the CHECK in
    `011_policy.sql` is the same three, so a typo is a failure and not a row
    nobody will ever query.

    `ts` comes from `repository.now()` and not from an argument: a log whose
    timestamps a caller can supply is a log that eventually carries a plausible
    time instead of a measured one, which is exactly what that function exists
    to stop.
    """
    with tx(conn):
        conn.execute(
            "INSERT INTO audit_log (run_id, ts, actor, decision, detail, "
            "langfuse_trace_id) VALUES (?,?,?,?,?,?)",
            (run_id, now(), actor, decision, detail, langfuse_trace_id))


def entries(conn: sqlite3.Connection, run_id: str | None = None) -> list[sqlite3.Row]:
    """The log, oldest first. Every run, or one."""
    if run_id is None:
        return list(conn.execute("SELECT * FROM audit_log ORDER BY ts, rowid"))
    return list(conn.execute(
        "SELECT * FROM audit_log WHERE run_id = ? ORDER BY ts, rowid", (run_id,)))
