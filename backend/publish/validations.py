"""Writing and reading the `validations` table. One writer, on purpose.

`judge_rubric` and `mandatory_facts` are the first two validators to store here
and there are nine more in docs/spec.md §2. Each of them writing its own INSERT
is how the `attempts` rows ended up with three spellings of the same verdict —
so the delete-then-insert, the timestamp and the row shape live here once, and a
validator supplies only what is its own.
"""

from __future__ import annotations

import sqlite3

from backend.commons.db.connection import tx
from backend.commons.db.repository import now


def record(conn: sqlite3.Connection, *, run_id: str, version: int, validator: str,
           kind: str, rows: list[tuple[str | None, str | None, str | None]]) -> None:
    """Replace this validator's verdict on this version. `rows` is
    `(criterion, value, justification)`.

    **Replace, not append.** A validator is re-run when a version is rebuilt and
    when a reader change rewrites chapters, and two verdicts under one
    (run, version, validator) make the pivot AC-8 asks for ambiguous: the report
    would have to pick one, and picking the newest silently is how a stale
    figure survives the thing that was supposed to supersede it. The whole
    replacement is one transaction so a crash cannot leave a version with no
    verdict at all where it had one before.
    """
    ts = now()
    with tx(conn):
        conn.execute(
            "DELETE FROM validations WHERE run_id = ? AND version = ? AND validator = ?",
            (run_id, version, validator),
        )
        conn.executemany(
            "INSERT INTO validations (run_id, version, validator, kind, criterion, "
            "value, justification, ts) VALUES (?,?,?,?,?,?,?,?)",
            [(run_id, version, validator, kind, criterion, value, justification, ts)
             for criterion, value, justification in rows],
        )


def for_version(conn: sqlite3.Connection, run_id: str, version: int,
                validator: str | None = None) -> list[dict]:
    """Every validator's rows for one version, or one validator's.

    Ordered by validator and then by criterion — the single-row validators
    first, since their `criterion` is NULL — so `evals/results.md` comes out in
    the same order twice running. A report whose row order depends on insertion
    order shows a diff every time it is regenerated, and then nobody reads the
    diffs.
    """
    sql = ("SELECT validator, kind, criterion, value, justification, ts FROM validations "
           "WHERE run_id = ? AND version = ?")
    params: list = [run_id, version]
    if validator is not None:
        sql += " AND validator = ?"
        params.append(validator)
    sql += " ORDER BY validator, criterion IS NULL DESC, criterion"
    return [dict(row) for row in conn.execute(sql, params)]
