"""Every per-version validator of docs/spec.md §2, into `validations`, at once.

    python -m backend.publish.record_all output/<slug> [version]

`evals/results.md` is a pivot of this table, so a validator that leaves no row
is a column nobody can tell from "passed". The ones that cannot run here still
write their row: value NULL and a justification that starts "not run: <reason>".
Absent, never 0.

`judge_rubric` is not here: it is the judge agent's verdict and arrives by its
own route (`router_judge`). `tla_harness` runs in development, not per version.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

from backend.brief import domain as brief_domain
from backend.chapters import names
from backend.policy import forbidden
from backend.publish import mandatory, validations


def _run_id(conn: sqlite3.Connection, run_dir: Path) -> str:
    row = conn.execute("SELECT id FROM runs WHERE id = ? OR slug = ? "
                       "ORDER BY id = ? DESC LIMIT 1",
                       (run_dir.name, run_dir.name, run_dir.name)).fetchone()
    if row is None:
        raise LookupError(f"no run for {run_dir.name!r} in this database")
    return row[0]


def _chapters(run_dir: Path) -> list[tuple[str, str]]:
    """The promoted chapters, `chNN.md` only — never an attempt."""
    return [(p.stem, p.read_text(encoding="utf-8"))
            for p in sorted((run_dir / "chapters").glob("ch[0-9][0-9].md"))]


def _words(text: str) -> int:
    body = [line for line in text.splitlines() if not line.startswith("# ")]
    return len(" ".join(body).split())


def record_version(conn: sqlite3.Connection, run_dir: Path, version: int = 1) -> None:
    run_id = _run_id(conn, run_dir)
    chapters = _chapters(run_dir)

    def put(validator: str, kind: str, rows) -> None:
        validations.record(conn, run_id=run_id, version=version,
                           validator=validator, kind=kind, rows=rows)

    # schema_brief — FLOW-0 on the brief this run was filling, if any.
    brief_id = conn.execute("SELECT brief_id FROM runs WHERE id = ?",
                            (run_id,)).fetchone()
    brief_id = brief_id[0] if brief_id and "brief_id" in brief_id.keys() else None
    if brief_id is None:
        put("schema_brief", "a", [(None, None, "no brief: run started from a premise")])
    else:
        payload = conn.execute("SELECT payload FROM briefs WHERE id = ?",
                               (brief_id,)).fetchone()
        verdict = brief_domain.check(json.loads(payload[0])) if payload else None
        put("schema_brief", "a", [(None, "pass" if verdict and verdict.status == "ok"
                                   else "fail",
                                   f"FLOW-0: {verdict.status if verdict else 'brief missing'}")])

    # schema_role_output — every critique file parses as JSON.
    critiques = sorted((run_dir / "critiques").glob("*.json"))
    ok = []
    for path in critiques:
        try:
            json.loads(path.read_text(encoding="utf-8"))
            ok.append(path.name)
        except (ValueError, UnicodeDecodeError):
            pass
    bad = [p.name for p in critiques if p.name not in ok]
    put("schema_role_output", "a",
        [(None, f"{len(ok)}/{len(critiques)}" if critiques else None,
          ("unparsed: " + ", ".join(bad)) if bad else
          ("all parse" if critiques else "not run: no critique files"))])

    # chapter_length — one row per promoted chapter, in words.
    snap = run_dir / "config.snapshot.json"
    band = (json.loads(snap.read_text(encoding="utf-8"))["novel"]["words_per_chapter"]
            if snap.is_file() else None)
    put("chapter_length", "a",
        [(stem, str(n := _words(text)),
          (None if band is None else
           "in band" if band["min"] <= n <= band["max"] else
           f"outside {band['min']}-{band['max']}"))
         for stem, text in chapters] or [(None, None, "not run: no promoted chapter")])

    # forbidden_words — hits across the promoted chapters.
    terms = forbidden.terms(conn)
    hits = [(stem, h) for stem, text in chapters for h in forbidden.check(text, terms)]
    put("forbidden_words", "a",
        [(None, str(len(hits)) if chapters else None,
          "; ".join(f"{s}: {h.quote!r} ({h.level})" for s, h in hits) or
          ("none" if chapters else "not run: no promoted chapter"))])

    # canonical_names — near-misses of a canonical name.
    cast = run_dir / "bible" / "characters.md"
    if cast.is_file() and chapters:
        cast_md = cast.read_text(encoding="utf-8")
        suspects = [(stem, s) for stem, text in chapters for s in names.check(text, cast_md)]
        put("canonical_names", "a",
            [(None, str(len(suspects)),
              "; ".join(f"{st}: {s}" for st, s in suspects) or "none")])
    else:
        put("canonical_names", "a", [(None, None, "not run: no cast or no chapter")])

    # mandatory_facts — its own module decides and writes.
    mandatory.record(conn, run_id=run_id, version=version,
                     coverage=mandatory.check(conn, run_id=run_id, version_id=version))

    # What cannot run here, said so.
    put("visual_check", "a",
        [(None, None, "not run: manual Playwright MCP session (docs/browser-mcp.md)")])
    put("human_review", "b", [(None, None, "not run: pending the owner's reading")])
    put("lean_chronology", "c",
        [(None, None, "not run: elan unavailable" if shutil.which("elan") is None
          else "not run: lake build not wired")])


def main(argv: list[str]) -> int:
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect

    run_dir = Path(argv[0])
    version = int(argv[1]) if len(argv) > 1 else 1
    conn = connect(load_settings().db_path)
    record_version(conn, run_dir, version)
    for row in validations.for_version(conn, _run_id(conn, run_dir), version):
        print(row["validator"], row["criterion"] or "", row["value"], sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
