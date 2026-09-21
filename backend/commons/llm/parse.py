"""Reading a critic's reply.

A critic that did not return usable JSON has not delivered a verdict. There is no
honest score to substitute: 10 invents an approval and 0 invents a rejection, and
returning 10 here once meant a malformed reply silently passed a draft. `None` is
the only truthful answer, and the gate excludes it from the minimum.
"""

from __future__ import annotations

import json
import re


def critic_reply(raw: str) -> tuple[int | None, list[dict], list[str]]:
    """Returns (score or None, findings, notes)."""
    try:
        body = re.search(r"\{[\s\S]*\}", raw)
        parsed = json.loads(body.group(0) if body else raw)
        score = parsed.get("score")
        if not isinstance(score, (int, float)):
            return None, [], ["reply carried no numeric score"]
        return (
            max(0, min(10, int(score))),
            [f for f in parsed.get("findings", []) if isinstance(f, dict)],
            [str(n) for n in parsed.get("notes", [])],
        )
    except Exception:
        return None, [], [
            "this critic did not return JSON, so it produced no verdict; it was "
            "excluded from the aggregate rather than counted as a pass"
        ]


def patches(raw: str) -> list[dict]:
    try:
        body = re.search(r"\{[\s\S]*\}", raw)
        parsed = json.loads(body.group(0) if body else raw)
        return [p for p in parsed.get("patches", []) if isinstance(p, dict)]
    except Exception:
        return []
