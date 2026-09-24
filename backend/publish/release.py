"""The first publication: v1, printed, with every validator's row.

    python -m backend.publish.release output/<slug>
    python -m backend.publish.release output/<slug> --next "<reason>"

Until this existed only a reader change called `pdf.publish`, so a finished run
had no way to become `dist/v1/novel.pdf`. This is that way, and nothing more:
personalise, render v1, print it, record the validators of docs/spec.md §2 against it.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from backend.chapters import fact_usage
from backend import versions as versions_repo
from backend.bible import ingest
from backend.publish import pdf, personalise, record_all


class AlreadyReleased(Exception):
    """v1 exists. A later version is a reader change, never a second v1."""


def ensure_bible_rows(conn: sqlite3.Connection, run_dir: Path) -> None:
    """Ingest the Story Bible if nothing did.

    The ingest belongs to the conductor's cast unit; a novel written by the
    single orchestrator (the approved fallback) never ran it, and published
    with no characters and no places for *Read* to show. Run on the
    personalised files, so the rows carry the names the reader sees.
    """
    run_id = record_all._run_id(conn, run_dir)
    if conn.execute("SELECT 1 FROM characters WHERE run_id = ?", (run_id,)).fetchone():
        return
    ingest.ingest(conn, run_dir)


def release(conn: sqlite3.Connection, run_dir: Path) -> int:
    run_id = record_all._run_id(conn, run_dir)
    if conn.execute("SELECT 1 FROM versions WHERE run_id = ?", (run_id,)).fetchone():
        raise AlreadyReleased(f"{run_dir.name} already has a published version")
    return _publish(conn, run_dir, run_id, reason="first publication")


def release_next(conn: sqlite3.Connection, run_dir: Path, *, reason: str) -> int:
    """The run's own chapters, grown since the last version, as the next one.

    For a run resumed after v1 was published (spec §8, the owner's decision on
    run 02412b7fe29e): the completed book is v2, and v1 stays as it was — a
    version's files are written with an exclusive create and never again.
    """
    return _publish(conn, run_dir, record_all._run_id(conn, run_dir), reason=reason)


def _publish(conn: sqlite3.Connection, run_dir: Path, run_id: str, *, reason: str) -> int:
    # Personalised first, so fact usage, the validators and the PDF all read
    # the text the reader gets (owner's decision B, 2026-09-24).
    personalise.personalise(conn, run_dir)
    ensure_bible_rows(conn, run_dir)
    n = versions_repo.next_number(conn, run_id, run_dir / "dist")
    for chapter in sorted((run_dir / "chapters").glob("ch[0-9][0-9].md")):
        fact_usage.record(conn, run_dir, int(chapter.stem[2:]), version_id=n)
    pdf.publish(conn, run_dir, run_id, reason=reason, n=n,
                parent=n - 1 if n > 1 else None)
    html = run_dir / "dist" / f"v{n}" / "novel.html"
    pdf.print_pdf(html, html.with_name("novel.pdf"))
    record_all.record_version(conn, run_dir, n)
    return n


def main(argv: list[str]) -> int:
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect

    run_dir = Path(argv[0]).resolve()   # the browser needs a file URI
    conn = connect(load_settings().db_path)
    n = (release_next(conn, run_dir, reason=argv[2]) if argv[1:2] == ["--next"]
         else release(conn, run_dir))
    print(run_dir / "dist" / f"v{n}" / "novel.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
