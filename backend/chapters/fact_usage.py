"""Which facts a promoted chapter actually used — PLAN-001-exam E3.

    python -m backend.chapters.fact_usage output/<slug> 3 [version]

Run from FLOW-4's "Record it", after `promote` has written `chNN.md`. Drafts
that were rejected are not recorded: the book is what shipped, and a fact used
only by a draft nobody kept is not used.

**The limit, stated first because everything downstream rests on it.** This is
**string matching of canonical names and fact text against the chapter prose.
It is not semantic.** A fact the chapter states in other words — "the boat was
logged the better part of a day before she ever left the quay" against a Bible
that says "nineteen hours after the line that records her passing" — is **not
found**, and is reported *uncovered*.

That is the trade `docs/spec.md` §7 accepts, and the direction of the error is
the whole of the argument. The failure is always the same one: a covered fact
reported uncovered. **A fact is never invented as covered.** `mandatory_facts`
then over-reports at the publish gate, a person reads the chapter and sees the
paraphrase, and the cost is a minute of their attention. The opposite error —
a fact reported covered that the prose never carries — would be a gift novel
delivered without the thing the buyer asked for, and nothing downstream could
catch it.

**Why this is not an agent** (AGENTS.md §5, "code before agent"). A model asked
"which of these facts did you use" would find the paraphrase, and would also
agree it used facts it did not: it has every incentive to say yes and no way to
be checked. A model gives class **D**; this gives class **T**, and the reader
change in AC-7 regenerates real chapters from its answer.

Where the matching works well is where it matters most: the brief's facts are
short and literal — a recipient's name, a dog called Nala, a street — and those
are the facts `mandatory = 1` marks and the buyer paid for.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from backend.bible.ingest import name_needles
from backend.commons.db.connection import tx


@dataclass(frozen=True)
class Usage:
    fact_id: int
    kind: str
    matched: str


def promoted_text(run_dir: Path, chapter: int) -> str | None:
    """`chNN.md` — the file `promote` writes and only on `accept`.

    None when it does not exist. A chapter that was never promoted has no usage,
    which is not the same as a chapter that used nothing, and the caller has to
    be able to tell them apart.
    """
    path = run_dir / "chapters" / f"ch{chapter:02d}.md"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def needles_for(kind: str, text: str) -> list[str]:
    """What to look for in the prose, for a fact of this kind.

    - a **character** fact is looked for by the canonical name and its parts:
      a chapter says *Ada* far more often than *Ada Rowe*.
    - a **place** fact is looked for by the whole name only. `Corbie Light`
      split into parts would match *the Light* in every paragraph of a
      lighthouse novel, and a place marked used everywhere is a place whose
      usage says nothing.
    - everything else is looked for **verbatim**. A rule or a mystery is a
      paragraph, and a paragraph never appears in prose word for word — those
      facts are therefore reported uncovered unless the chapter quotes them.
      That is the declared limit, not an oversight.
    """
    head = text.split(" — ")[0].strip()
    if kind == "character":
        return name_needles(head)
    if kind == "place":
        return [head]
    return [text.strip()]


def _found(needle: str, prose: str) -> bool:
    """Word boundaries, case-insensitively. Without the boundaries `Ada` is
    found inside `adamant`, and a chapter would credit a character who is not
    in it."""
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", prose, re.I) is not None


def record(conn: sqlite3.Connection, run_dir: Path, chapter: int,
           version_id: int = 1, run_id: str | None = None) -> list[Usage]:
    """Record what chapter `chapter` of version `version_id` uses.

    `version_id` defaults to 1 — the first published version — because FLOW-4
    writes the first version and knows no other number. E6's reader change
    passes the new version explicitly; the rows of version 1 stay where they
    are, which is what "`dist/v1/` is untouched" (AC-7) means in the archive.
    """
    # `run_id` is named by a caller reading a version workspace (dist/v<n>/),
    # whose directory name is no run's.
    run_id = run_id or run_dir.name
    # A v2 run's id is not its slug; resolve it the way the ingest does, or a
    # v2 run finds no facts and every mandatory one reads uncovered.
    if not conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
        by_slug = conn.execute("SELECT id FROM runs WHERE slug = ?", (run_id,)).fetchone()
        if by_slug:
            run_id = by_slug[0]
    prose = promoted_text(run_dir, chapter)
    if prose is None:
        raise FileNotFoundError(
            f"chapters/ch{chapter:02d}.md does not exist in {run_dir}; only a "
            f"promoted chapter has usage")

    facts = conn.execute(
        "SELECT id, kind, text FROM facts WHERE run_id = ?", (run_id,)).fetchall()

    used: list[Usage] = []
    for fact in facts:
        hit = next((n for n in needles_for(fact["kind"], fact["text"])
                    if _found(n, prose)), None)
        if hit is not None:
            used.append(Usage(fact["id"], fact["kind"], hit))

    with tx(conn):
        # The chapter is re-recorded whole after a redraft. A row left over from
        # a draft that named a character the accepted one dropped would send the
        # reader change to rewrite a chapter that no longer mentions the fact.
        conn.execute(
            "DELETE FROM fact_usage WHERE version_id = ? AND chapter = ? AND "
            "fact_id IN (SELECT id FROM facts WHERE run_id = ?)",
            (version_id, chapter, run_id))
        for usage in used:
            conn.execute(
                "INSERT INTO fact_usage (fact_id, version_id, chapter, matched) "
                "VALUES (?,?,?,?)",
                (usage.fact_id, version_id, chapter, usage.matched))

        # The sheet links each name to the chapter it is first met in. Earliest
        # wins, and a chapter recorded out of order must be able to move it back.
        by_id = {f["id"]: f["text"] for f in facts}
        for table, kind in (("characters", "character"), ("places", "place")):
            named = [by_id[u.fact_id].split(" — ")[0].strip()
                     for u in used if u.kind == kind]
            if not named:
                continue
            conn.execute(
                f"UPDATE {table} SET first_chapter = ? WHERE run_id = ? AND "
                f"(first_chapter IS NULL OR first_chapter > ?) AND "
                f"canonical_name IN ({','.join('?' * len(named))})",
                (chapter, run_id, chapter, *named))
    return used


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(f"usage: {argv[0]} <run_dir> <chapter> [version]", file=sys.stderr)
        return 2

    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate

    run_dir, chapter = Path(argv[1]), int(argv[2])
    version_id = int(argv[3]) if len(argv) == 4 else 1
    conn = connect(load_settings().db_path)
    migrate(conn)

    total = conn.execute("SELECT COUNT(*) FROM facts WHERE run_id = ?",
                         (run_dir.name,)).fetchone()[0]
    if not total:
        print(f"fact_usage: no facts for {run_dir.name}; run "
              f"`python -m backend.bible.ingest {run_dir}` first", file=sys.stderr)
        return 1
    try:
        used = record(conn, run_dir, chapter, version_id)
    except FileNotFoundError as exc:
        print(f"fact_usage: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "run": run_dir.name, "version": version_id, "chapter": chapter,
        "facts": total, "used": len(used),
        # Named, not counted: the point of the number is the facts it leaves out,
        # and "17 of 23" tells a reader nothing about which six to go and look at.
        "matched": [{"fact_id": u.fact_id, "kind": u.kind, "on": u.matched}
                    for u in used],
        "uncovered_are_not_absent": (
            "a fact this chapter states in other words is matched by nothing "
            "here and counted as unused; see the module docstring"),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
