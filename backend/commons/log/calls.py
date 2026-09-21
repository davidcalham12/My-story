"""One row per model call.

v1's version of this understated the bill by a factor of eight, because it
recorded one total with no input/output split and knew nothing of the
orchestrator's own turns. Here the orchestrator is code, so every token that
reaches a model is in this table.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CallRow:
    run_id: str
    stage: str
    agent: str
    model: str            # the full id, never the family word: `opus` matches no rate
    ts: str               # a real clock reading, never an estimate
    chapter: int | None = None
    attempt: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    provenance: str = "measured"
    tokens_reserved: int | None = None
    in_flight_at_dispatch: int | None = None
    wait_ms: int | None = None
    duration_ms: int | None = None
    note: str | None = None


def write_call(conn: sqlite3.Connection, row: CallRow) -> int:
    data = asdict(row)
    columns = ", ".join(data)
    placeholders = ", ".join(f":{k}" for k in data)
    cur = conn.execute(f"INSERT INTO calls ({columns}) VALUES ({placeholders})", data)
    return int(cur.lastrowid)
