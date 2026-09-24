"""The book is personalised in code, at publication. No model touches this step.

The organisation's privacy policy makes the orchestrator write the recipient's
alias as a placeholder, so the Bible, the outline and the prose carry `TOKEN`
where the name goes (docs/spec.md §8, the owner's decision B, 2026-09-24). This
module reads the alias from the stored brief and puts it in the token's place,
before the validators run and before the PDF is printed, so both read the text
the reader gets.

Privacy by design as a side effect: the models never see the recipient's name.

What it rewrites: the promoted chapters (`chNN.md`), `bible/*.md`, `outline.md`
and `synopsis.md`, each kept first as `<stem>.anon<ext>` — the text the gate
approved, unchanged — and the run's rows in the Story Bible tables. Attempts
and summaries are records of what the models wrote and are left as they are.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.commons.db.connection import tx

TOKEN = "[NOMBRE_ANONIMIZADO]"
TABLES = ("facts", "characters", "places", "chronology")
SKIP_COLUMNS = {"id", "run_id", "kind", "source"}


def _run(conn: sqlite3.Connection, run_dir: Path):
    return conn.execute("SELECT id, brief_id FROM runs WHERE id = ? OR slug = ? "
                        "ORDER BY id = ? DESC LIMIT 1",
                        (run_dir.name, run_dir.name, run_dir.name)).fetchone()


def alias_for(conn: sqlite3.Connection, brief_id: str | None) -> str | None:
    if not brief_id:
        return None
    row = conn.execute("SELECT payload FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    if row is None:
        return None
    return (json.loads(row[0]).get("recipient") or {}).get("alias") or None


def _files(run_dir: Path) -> list[Path]:
    files = sorted((run_dir / "chapters").glob("ch[0-9][0-9].md"))
    files += sorted((run_dir / "bible").glob("*.md"))
    files += [p for p in (run_dir / "outline.md", run_dir / "synopsis.md") if p.is_file()]
    return [p for p in files if not p.stem.endswith(".anon")]


def personalise(conn: sqlite3.Connection, run_dir: Path) -> int:
    """Replace the token with the brief's alias. Returns files + rows changed.

    Idempotent: a second call finds no token and changes nothing, and the
    `.anon` copy is written only once, so it always holds the approved text.
    """
    run = _run(conn, run_dir)
    alias = alias_for(conn, run[1]) if run else None
    if alias is None:
        return 0

    changed = 0
    for path in _files(run_dir):
        text = path.read_text(encoding="utf-8")
        if TOKEN not in text:
            continue
        keep = path.with_name(f"{path.stem}.anon{path.suffix}")
        if not keep.exists():
            keep.write_text(text, encoding="utf-8", newline="\n")
        path.write_text(text.replace(TOKEN, alias), encoding="utf-8", newline="\n")
        changed += 1

    with tx(conn):
        for table in TABLES:
            columns = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")
                       if c[2].upper() == "TEXT" and c[1] not in SKIP_COLUMNS]
            for column in columns:
                cur = conn.execute(
                    f"UPDATE OR IGNORE {table} SET {column} = REPLACE({column}, ?, ?) "
                    f"WHERE run_id = ? AND {column} LIKE ?",
                    (TOKEN, alias, run[0], f"%{TOKEN}%"))
                changed += cur.rowcount or 0
    return changed
