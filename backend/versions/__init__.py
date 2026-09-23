"""The `versions` table: which copies of a novel exist, and where each came from.

Nothing here renders or regenerates anything — this is the archive half, kept
apart from `backend.publish.pdf` so the rendering can be tested without a
database and the bookkeeping without a novel.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from backend.commons.db import repository
from backend.commons.db.connection import tx

#: `v3` — a version's directory under `dist/`.
VERSION_DIR = re.compile(r"^v(\d+)$")


def next_number(conn: sqlite3.Connection, run_id: str, dist: Path) -> int:
    """The number the next publication takes.

    It is the highest of the archive *and* the directories on disk, plus one,
    and the two are asked separately because they can legitimately disagree: a
    regeneration the gate halted leaves `dist/v2/` behind and writes no row.
    Allocating from the table alone would hand v2 to the next attempt, which
    then collides with the halted workspace — or worse, publishes into it.
    """
    highest = conn.execute(
        "SELECT MAX(n) FROM versions WHERE run_id = ?", (run_id,)).fetchone()[0] or 0
    if dist.is_dir():
        for child in dist.iterdir():
            match = VERSION_DIR.match(child.name)
            if child.is_dir() and match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def record(conn: sqlite3.Connection, run_id: str, *, n: int, parent: int | None,
           reason: str) -> None:
    """One row per published version. Written last, after the files are on disk:
    a row pointing at a directory that does not exist is a version the panel
    offers and the reader cannot open."""
    with tx(conn):
        conn.execute(
            "INSERT INTO versions (run_id, n, parent, reason, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, n, parent, reason, repository.now()))


def published(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """Every version of this run, oldest first."""
    return [dict(row) for row in conn.execute(
        "SELECT n, parent, reason, created_at FROM versions "
        "WHERE run_id = ? ORDER BY n", (run_id,))]
