"""What Langfuse says each change cost, read back through the v2 observations API.

The legacy GETs answer 410 for this organisation (SPEC-EXAM-008 §5), so this
asks `api.observations.get_many` — the v2 endpoint — for the novel's session,
generations only, with a short timeout. The exporter's change traces each hold
two generations, `orchestrator` and `agents`, whose `cost_details.total` is the
measured cost; that is what is read here.

Credentials are read by the SDK from the environment and never pass through
this module: nothing here builds a URL with a key in it, and an SDK error's
text is never put in a response (the router reports only "unreachable").
"""

from __future__ import annotations

import os

from backend.costs.measure import change_trace_id

#: Seconds. The novel page waits on this; a slow Langfuse costs a fallback.
TIMEOUT_S = 4
PAGE = 1000
MAX_PAGES = 5
ROLES = ("orchestrator", "agents")


def configured() -> bool:
    return all((os.environ.get(k) or "").strip() for k in
               ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"))


def _get(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _cost(obs) -> float | None:
    details = _get(obs, "cost_details") or {}
    total = _get(details, "total")
    if total is None:
        total = _get(obs, "total_cost")
    return float(total) if isinstance(total, (int, float)) else None


def generations(client, session_id: str) -> list:
    """Every generation of the session, across pages. Raises on any failure;
    the caller turns that into the local fallback."""
    out, cursor = [], None
    for _ in range(MAX_PAGES):
        kwargs = {"session_id": session_id, "type": "GENERATION", "limit": PAGE,
                  "fields": "core,basic,metadata,model,usage",
                  "request_options": {"timeout_in_seconds": TIMEOUT_S}}
        if cursor:
            kwargs["cursor"] = cursor
        page = client.api.observations.get_many(**kwargs)
        out.extend(_get(page, "data") or [])
        cursor = _get(_get(page, "meta"), "cursor")
        if not cursor:
            break
    return out


def by_change(run_id: str, change_ns: list[int], observations: list) -> dict[int, dict]:
    """The change traces Langfuse holds, by `n`: each role's model and cost."""
    wanted = {change_trace_id(run_id, n): n for n in change_ns}
    found: dict[int, dict] = {}
    for obs in observations:
        n = wanted.get(_get(obs, "trace_id"))
        name = _get(obs, "name")
        if n is None or name not in ROLES:
            continue
        entry = found.setdefault(n, {"project_id": _get(obs, "project_id")})
        entry[f"{name}_usd"] = _cost(obs)
        entry[f"{name}_model"] = _get(obs, "model")
    for entry in found.values():
        parts = [entry.get(f"{r}_usd") for r in ROLES]
        known = [p for p in parts if p is not None]
        entry["total_usd"] = float(sum(known)) if known else None
    return found


def trace_url(project_id: str | None, trace_id: str) -> str | None:
    """The trace in Langfuse's UI. The host is not a secret; no key goes in it."""
    base = (os.environ.get("LANGFUSE_BASE_URL") or "").rstrip("/")
    if not base or not project_id:
        return None
    return f"{base}/project/{project_id}/traces/{trace_id}"
