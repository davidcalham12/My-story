"""HTTP over `validations`. Two reads, no writes.

SPEC-EXAM-002 §B.4 names both routes and B.5 AC-7 says what the Quality screen
does with them: the judge's six criteria **with their justifications**, and the
validators table for a version. Two routes rather than one because they answer
different questions — "how was this book judged" and "what ran against it" —
and a screen that asks for the second should not have to know the first one's
shape.

Nothing here takes a filesystem path. `test_no_route_takes_a_path_and_reads_a_file`
pins that for the whole app, and these routes are addressed by run id and
version number for the same reason every other route is.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from backend.publish import judge, validations
from backend.runs.router import get_service

router = APIRouter()


def get_conn(svc=Depends(get_service)) -> sqlite3.Connection:
    """The app's one connection, reached through the dependency `main.py`
    already overrides.

    Declaring a second provider here would mean a second override to remember
    at startup, and the one that gets forgotten is the one that opens a second
    connection to the same SQLite file — which is where the single-writer rule
    in `commons/db/connection.py` stops being true.
    """
    return svc.conn


@router.get("/{run_id}/versions/{n}/judge")
def judge_rubric(run_id: str, n: int, conn=Depends(get_conn)) -> dict:
    """AC-9's payload: six scores, six justifications, the mean and what it
    covers.

    404 when the judge never ran on this version. Not an empty rubric: a screen
    rendering six dashes for "no judge ran" is indistinguishable from one
    rendering six dashes for "the judge answered nothing", and those are the two
    outcomes AC-9 exists to tell apart.
    """
    found = judge.read(conn, run_id, n)
    if found is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no {judge.VALIDATOR} verdict for run {run_id} version {n}")
    return found


@router.get("/{run_id}/versions/{n}/validations")
def validations_for(run_id: str, n: int, conn=Depends(get_conn)) -> list[dict]:
    """Every validator's rows for this version, as stored.

    Deliberately untransformed, and deliberately not filtered to the ones that
    passed: `evals/results.md` is a pivot of exactly these rows, and a route
    that reshaped them would be a second reading of the table that drifts from
    the report's.
    """
    return validations.for_version(conn, run_id, n)
