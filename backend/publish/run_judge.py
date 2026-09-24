"""Run the judge on a published version and store its rubric.

    python -m backend.publish.run_judge output/<slug> <version>

`judge_rubric` (docs/spec.md §2, kind b) had a schema and a writer and nothing
that ever asked the judge. This asks it, once, with the assembled book pasted in
its prompt — the judge holds only `Glob` and cannot read a file.

**The book it reads is the anonymised one** (`chNN.anon.md` where it exists): no
model is given the recipient's name, so the judge sees the same placeholder the
writers wrote. A reply that is not a valid rubric is stored as one row, value
NULL and "not run: <why>" — absent, never 0.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from backend.publish import judge, record_all, validations


def _chapter_text(path: Path) -> str:
    anon = path.with_name(f"{path.stem}.anon{path.suffix}")
    return (anon if anon.is_file() else path).read_text(encoding="utf-8")


def prompt_for(run_dir: Path) -> str:
    state = run_dir / "state.json"
    meta = json.loads(state.read_text(encoding="utf-8")) if state.is_file() else {}
    chapters = sorted((run_dir / "chapters").glob("ch[0-9][0-9].md"))
    book = "\n\n".join(_chapter_text(p).strip() for p in chapters)
    return (f"genre and tone: {meta.get('tone') or 'as the book reads'}\n"
            f"recipient: the protagonist, written as the placeholder the book uses\n"
            f"chapters: {len(chapters)}\n\n"
            "Judge this book as your instructions say, and return only the JSON.\n\n"
            f"--- THE BOOK ---\n\n{book}\n")


def _claude(prompt: str) -> str:
    """One `claude -p --agent judge`, the prompt on stdin, never in argv."""
    done = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--agent", "judge",
         "--permission-mode", "dontAsk"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=900)
    return json.loads(done.stdout)["result"]


def _json_in(reply: str) -> str:
    """The reply's JSON object, tolerating a fence around it."""
    start, end = reply.find("{"), reply.rfind("}")
    return reply[start:end + 1] if start != -1 and end > start else reply


def run(conn: sqlite3.Connection, run_dir: Path, version: int, *, dispatch=_claude) -> bool:
    run_id = record_all._run_id(conn, run_dir)
    try:
        rubric = judge.parse(_json_in(dispatch(prompt_for(run_dir))))
    except Exception as exc:                  # any failure means: the judge did not answer
        validations.record(conn, run_id=run_id, version=version,
                           validator=judge.VALIDATOR, kind=judge.KIND,
                           rows=[(None, None, f"not run: {type(exc).__name__}: "
                                              f"{str(exc)[:200]}")])
        return False
    judge.record(conn, run_id=run_id, version=version, rubric=rubric)
    return True


def main(argv: list[str]) -> int:
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect

    conn = connect(load_settings().db_path)
    ok = run(conn, Path(argv[0]), int(argv[1]))
    for row in validations.for_version(conn, record_all._run_id(conn, Path(argv[0])),
                                       int(argv[1]), judge.VALIDATOR):
        print(row["criterion"], row["value"], sep="\t")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
