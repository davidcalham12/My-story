"""The Story Bible over HTTP — SPEC-EXAM-002 §B.4, §5 "Ask for a change".

Four reads, no writes. The page that asks for a change needs to show, *before
anything is spent*, which chapters the change would reach; the reading page
needs the character and place sheet with each entry's first chapter to link to.

Every route takes a run id and a fact id and **no filesystem path** — the pin in
`test_api_contract` exists because an artefact served by path is a traversal
surface, and nothing here opens a file.

Mounted under the same `/api/runs` prefix as `backend/runs/router.py` and
sharing its `get_service` dependency, so there is one connection and one place
that decides which database an app talks to.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from backend.runs.router import get_service

router = APIRouter()


def _conn(svc) -> sqlite3.Connection:
    return svc.conn


def _run_or_404(conn: sqlite3.Connection, run_id: str) -> None:
    if not conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no run {run_id}")


#: What `fact_usage` is and is not, carried on the answer rather than left in a
#: document nobody opens. A page that shows "3 chapters affected" as a fact
#: rather than as a floor will promise a reader something this cannot do.
MATCHING = ("chapters whose promoted prose contains the fact's words or a "
            "canonical name; a paraphrase is missed and reported as unused, "
            "never invented as used (docs/spec.md §7)")


@router.get("/{run_id}/facts")
def facts(run_id: str, version: int = 1, svc=Depends(get_service)) -> list[dict]:
    """Every fact of the run, with the chapters recorded against it.

    `chapters` is `[]` for a fact nothing has been recorded for — and that is a
    fact with no usage rows, not a fact used in chapter zero.
    """
    conn = _conn(svc)
    _run_or_404(conn, run_id)
    rows = conn.execute(
        "SELECT f.id, f.kind, f.text, f.source, f.mandatory, u.chapter "
        "FROM facts f LEFT JOIN fact_usage u "
        "  ON u.fact_id = f.id AND u.version_id = ? "
        "WHERE f.run_id = ? ORDER BY f.id, u.chapter", (version, run_id))

    out: dict[int, dict] = {}
    for row in rows:
        fact = out.setdefault(row["id"], {
            "id": row["id"], "kind": row["kind"], "text": row["text"],
            "source": row["source"], "mandatory": bool(row["mandatory"]),
            "chapters": [],
        })
        if row["chapter"] is not None:
            fact["chapters"].append(row["chapter"])
    return list(out.values())


@router.get("/{run_id}/facts/{fact_id}/impact")
def impact(run_id: str, fact_id: int, version: int = 1,
           svc=Depends(get_service)) -> dict:
    """The chapters a change to this fact would have to rewrite.

    A fact that does not exist is a **404**, never an empty list. "This change
    touches nothing" is the most expensive wrong answer this endpoint can give:
    it is the one on which a reader approves a change that silently rewrites
    nothing, or nothing at all gets regenerated and the PDF still says the old
    thing.
    """
    conn = _conn(svc)
    _run_or_404(conn, run_id)
    fact = conn.execute("SELECT * FROM facts WHERE id = ? AND run_id = ?",
                        (fact_id, run_id)).fetchone()
    if fact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"no fact {fact_id} in run {run_id}")
    chapters = [r["chapter"] for r in conn.execute(
        "SELECT DISTINCT chapter FROM fact_usage WHERE fact_id = ? AND "
        "version_id = ? ORDER BY chapter", (fact_id, version))]
    return {
        "fact_id": fact_id, "text": fact["text"], "kind": fact["kind"],
        "source": fact["source"], "mandatory": bool(fact["mandatory"]),
        "version": version, "chapters": chapters,
        # False, always, and sent on every answer so the page cannot present
        # this list as the complete one.
        "exact": False, "matching": MATCHING,
    }


@router.get("/{run_id}/bible/characters")
def characters(run_id: str, svc=Depends(get_service)) -> list[dict]:
    conn = _conn(svc)
    _run_or_404(conn, run_id)
    return [dict(r) for r in conn.execute(
        "SELECT canonical_name, role, birth_date, first_chapter FROM characters "
        "WHERE run_id = ? ORDER BY first_chapter IS NULL, first_chapter, "
        "canonical_name", (run_id,))]


@router.get("/{run_id}/bible/places")
def places(run_id: str, svc=Depends(get_service)) -> list[dict]:
    conn = _conn(svc)
    _run_or_404(conn, run_id)
    return [dict(r) for r in conn.execute(
        "SELECT canonical_name, note, first_chapter FROM places "
        "WHERE run_id = ? ORDER BY first_chapter IS NULL, first_chapter, "
        "canonical_name", (run_id,))]
