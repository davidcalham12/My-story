"""The first publication: v1, printed, with every validator's row.

    python -m backend.publish.release output/<slug>

Until this existed only a reader change called `pdf.publish`, so a finished run
had no way to become `dist/v1/novel.pdf`. This is that way, and nothing more:
personalise, render v1, print it, record the validators of docs/spec.md §2 against it.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from backend.chapters import fact_usage
from backend.publish import pdf, personalise, record_all


class AlreadyReleased(Exception):
    """v1 exists. A later version is a reader change, never a second v1."""


def release(conn: sqlite3.Connection, run_dir: Path) -> int:
    run_id = record_all._run_id(conn, run_dir)
    if conn.execute("SELECT 1 FROM versions WHERE run_id = ?", (run_id,)).fetchone():
        raise AlreadyReleased(f"{run_dir.name} already has a published version")
    # Personalised first, so fact usage, the validators and the PDF all read
    # the text the reader gets (owner's decision B, 2026-09-24).
    personalise.personalise(conn, run_dir)
    for chapter in sorted((run_dir / "chapters").glob("ch[0-9][0-9].md")):
        fact_usage.record(conn, run_dir, int(chapter.stem[2:]))
    n = pdf.publish(conn, run_dir, run_id, reason="first publication")
    html = run_dir / "dist" / f"v{n}" / "novel.html"
    pdf.print_pdf(html, html.with_name("novel.pdf"))
    record_all.record_version(conn, run_dir, n)
    return n


def main(argv: list[str]) -> int:
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect

    run_dir = Path(argv[0]).resolve()   # the browser needs a file URI
    n = release(connect(load_settings().db_path), run_dir)
    print(run_dir / "dist" / f"v{n}" / "novel.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
