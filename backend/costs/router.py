"""`GET /api/runs/{id}/costs`: one row per change, as Langfuse records it.

Langfuse first (SPEC-EXAM-008 §5), the local `changes` table behind it:

- Langfuse answers and holds the change's trace → the row is Langfuse's,
  `confirmed`, with a link to the trace;
- Langfuse is down, slow (4 s), not configured, or has not ingested the trace
  yet → the row is the local one, marked "unconfirmed in Langfuse";
- the two disagree → both figures, and the row says so. Neither is silently
  preferred.

Cached for a minute (15 s after a failure): the novel page calls this on every
load, and Langfuse is a network away. Credentials come from the environment,
through the SDK, and are never returned or put in a URL.
"""

from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Depends, HTTPException, status

from backend.costs import langfuse_read
from backend.costs import repository as costs
from backend.costs.measure import change_trace_id
from backend.runs.router import get_service
from backend.runs.service import NotFound, RunService

router = APIRouter()

OK_TTL_S, FAIL_TTL_S = 60.0, 15.0
#: Two figures closer than this are the same figure, rounded differently.
TOLERANCE_USD = 0.005
UNCONFIRMED = "unconfirmed in Langfuse"

_cache: dict[str, tuple[float, str, list | None]] = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def get_langfuse():
    """The SDK client when the environment configures one; None otherwise.
    Overridden in tests with a fake — no test opens a socket."""
    if not langfuse_read.configured():
        return None
    from langfuse import get_client

    return get_client()


def _observations(client, session_id: str) -> tuple[str, list | None]:
    """(`ok` | `unreachable` | `not configured`, the generations or None)."""
    if client is None:
        return "not configured", None
    now = time.monotonic()
    with _lock:
        held = _cache.get(session_id)
        if held and now - held[0] < (OK_TTL_S if held[1] == "ok" else FAIL_TTL_S):
            return held[1], held[2]
    try:
        found: tuple[str, list | None] = ("ok", langfuse_read.generations(client, session_id))
    except Exception:  # noqa: BLE001 - any failure is "Langfuse did not answer"
        found = ("unreachable", None)
    with _lock:
        _cache[session_id] = (now, *found)
    return found


def _same(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOLERANCE_USD


FIGURES = ("total_usd", "orchestrator_usd", "agents_usd")


def _row(run_id: str, local: dict, remote: dict | None) -> dict:
    trace = change_trace_id(run_id, local["n"])
    row = {k: local.get(k) for k in (
        "n", "kind", "label", "version", "chapters", "started_at", "finished_at",
        "minutes", "total_usd", "orchestrator_model", "orchestrator_usd", "agents_model",
        "agents_usd", "provenance", "note", "results", "unresulted", "sources")}
    row |= {"incomplete": int(local.get("unresulted") or 0),
            "no_orchestrator": costs.NO_ORCHESTRATOR in (local.get("note") or ""),
            "trace_id": trace, "trace_url": None, "disagreement": None}
    if remote is None:
        return row | {"source": "local", "confirmed": False, "status": UNCONFIRMED}
    url = langfuse_read.trace_url(remote.get("project_id"), trace)
    if all(_same(local.get(k), remote.get(k)) for k in FIGURES):
        return row | {"source": "langfuse", "confirmed": True,
                      "status": "confirmed in Langfuse", "trace_url": url}
    return row | {
        "source": "both", "confirmed": False, "trace_url": url,
        "status": "Langfuse and the local record disagree; both are shown",
        "disagreement": {
            "local": {k: local.get(k) for k in FIGURES},
            "langfuse": {k: remote.get(k) for k in FIGURES},
        }}


@router.get("/{run_id}/costs")
def run_costs(run_id: str, svc: RunService = Depends(get_service),
              client=Depends(get_langfuse)) -> dict:
    try:
        run = svc.get(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    local = costs.rows(svc.conn, run_id)
    state, observations = _observations(client, run["slug"]) if local else ("ok", [])
    remote = (langfuse_read.by_change(run_id, [r["n"] for r in local], observations)
              if observations is not None else {})
    rows = [_row(run_id, r, remote.get(r["n"])) for r in local]
    # Where they agree the figures are the same; where they disagree the local
    # one is summed and the row carries both. The source says which.
    total = costs.total(rows)
    sources = {r["source"] for r in rows if r["total_usd"] is not None}
    total["source"] = ("langfuse" if sources == {"langfuse"} else
                       "local" if sources <= {"local"} else "mixed")
    return {"run_id": run_id, "session_id": run["slug"],
            "langfuse": state if local else "not asked", "rows": rows, "total": total}
