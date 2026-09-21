"""The database connection, with the four settings that decide whether a small
local SQLite behaves or corrupts.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)  # we own the transactions
    conn.row_factory = sqlite3.Row                      # rows index by name
    conn.execute("PRAGMA journal_mode = WAL")           # readers do not block the writer
    conn.execute("PRAGMA foreign_keys = ON")            # OFF by default, per connection
    conn.execute("PRAGMA busy_timeout = 5000")          # wait rather than raise
    return conn


def memory() -> sqlite3.Connection:
    """A fresh database per test. WAL is unavailable in memory and unneeded."""
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """All or nothing.

    A chapter's draft, its five critique rows and its gate decision are one
    transaction: a crash between them leaves a run nobody can explain.
    """
    conn.execute("BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
