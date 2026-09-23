"""HTTP in. Translates requests to arguments and results to responses.

Three routes, and the first one exists so the third is never needed twice: the
panel asks `/check` on every keystroke it likes, free, and only posts the brief
once the answer is `ok`.
"""

from __future__ import annotations

import json
import sqlite3
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, status

from backend.brief import domain
from backend.brief.models import Brief
from backend.commons.db.connection import tx
from backend.commons.db.repository import now

router = APIRouter()

_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    """The database, opened once, overridden in tests.

    It resolves its own connection rather than taking one from `main.py` so
    that wiring this phase in is an import and an `include_router` and nothing
    else — the app is assembled by hand, one phase at a time, and a seam that
    needs a third line is a seam someone forgets.
    """
    global _conn
    if _conn is None:
        from backend.commons.config.settings import load_settings
        from backend.commons.db.connection import connect
        from backend.commons.db.migrate import migrate

        _conn = connect(load_settings().db_path)
        migrate(_conn)  # the same function the tests run, so the schemas cannot drift
    return _conn


# The body is taken as a raw dict on both POSTs, deliberately. FastAPI would
# reject an unknown key with its own 422 and its own shape, and what the buyer
# needs back is *our* answer — the questions to ask and the pair that cannot
# stand — which only `domain.check` can produce.


@router.post("/check", response_model=domain.CheckResult)
def check(payload: dict = Body(...)) -> domain.CheckResult:
    """What is missing and what contradicts, without spending anything.

    Always 200, including for a brief that fails: a half-filled form is the
    normal state of a conversation, not an error in a request.
    """
    return domain.check(payload)


@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: dict = Body(...), conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Accept a brief, or refuse it with the reason.

    422 rather than 201 for anything but `ok`, because the run that follows
    costs money and a stored-but-unusable brief is an order nobody can fill.
    The refusal carries the whole `CheckResult`: the panel shows the questions
    from it and never has to ask twice.
    """
    result = domain.check(payload)
    if result.status != "ok":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, result.model_dump())

    brief: Brief = domain.parse(payload)
    brief_id = uuid.uuid4().hex[:12]
    with tx(conn):
        # `brief.model_dump()` and not the body: what is stored is what the
        # model accepted, so the eval file's envelope — and anything else a
        # client hoped to keep — does not survive the trip.
        conn.execute(
            "INSERT INTO briefs (id, created_at, payload) VALUES (?,?,?)",
            (brief_id, now(), json.dumps(brief.model_dump(), ensure_ascii=False)),
        )
    return {"id": brief_id}


@router.get("/examples")
def examples() -> list[dict]:
    """The five committed briefs, three of which do not pass on purpose."""
    return domain.examples()
