"""Numbered SQL migrations, applied in order, recorded so they run once."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.commons.db.connection import tx

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def migrate(conn: sqlite3.Connection, folder: Path | None = None) -> list[str]:
    """Apply what has not been applied. Returns the names it ran.

    Rules that keep this honest, each learned the hard way somewhere:

    - A migration is never edited once it has run anywhere. Fix it with the next
      number; an edited migration means two databases with the same recorded
      history and different schemas.
    - Names are zero-padded so `sorted()` is the real order. `010` before `9` is
      a bug that only shows up on the tenth migration.
    - `executescript` commits implicitly before it starts, which is why the
      BEGIN below wraps the bookkeeping and not the script.
    """
    folder = folder or MIGRATIONS
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "  name TEXT PRIMARY KEY,"
        "  applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
    applied: list[str] = []
    for path in sorted(folder.glob("*.sql")):
        if path.name in done:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        with tx(conn):
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (path.name,))
        applied.append(path.name)
    return applied
