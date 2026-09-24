"""One `calls` row per dispatched agent, from the Agent tool's own result.

    python -m backend.commons.log.agent_usage <run_id> [extra.stream.jsonl ...]

`task_progress` reports one blended `total_tokens` per subagent, so every row it
wrote had output NULL, and most dispatches wrote none. When a subagent finishes,
the Agent tool's `tool_use_result` carries `agentType`, `resolvedModel`,
`totalDurationMs` and a `usage` block with input, cache creation, cache read and
output separately. A row is made from that.

Tokens are **measured**. The per-call cost is **estimated** from
config/pricing.json (`cost_provenance`), never a literal here. The run's total
stays **measured**, from the `result` event, and is not the sum of these rows.

`reimport` rebuilds a run's rows from what was already recorded — the run's
`events` and any stream kept beside it (a resume launched outside the server).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.commons.config import loader
from backend.commons.db.connection import tx
from backend.commons.log.calls import CallRow, write_call
from backend.commons.runner.watch import State, apply

FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
          "output_tokens")


def from_event(event: dict) -> dict | None:
    """The usage of one finished agent call, or None for anything else."""
    if event.get("type") != "user":
        return None
    result = event.get("tool_use_result")
    if not isinstance(result, dict) or not isinstance(result.get("usage"), dict):
        return None
    if not result.get("agentType"):
        return None
    usage = result["usage"]
    return {"agent": str(result["agentType"]),
            "model": str(result.get("resolvedModel") or "claude-code-session"),
            **{k: int(usage.get(k) or 0) for k in FIELDS},
            "duration_ms": result.get("totalDurationMs")}


def _rates(model: str, pricing: dict) -> dict | None:
    models = pricing.get("models", {})
    keys = [k for k in models if model.startswith(k)]
    return models[max(keys, key=len)] if keys else None


def estimate_cost(usage: dict, pricing: dict) -> float | None:
    """Dollars for one call at the config's rates; None when the model has none."""
    rates = _rates(usage["model"], pricing)
    if rates is None or "cache_write_per_mtok" not in rates:
        return None
    return (usage["input_tokens"] * rates["input_per_mtok"]
            + usage["cache_creation_input_tokens"] * rates["cache_write_per_mtok"]
            + usage["cache_read_input_tokens"] * rates["cache_read_per_mtok"]
            + usage["output_tokens"] * rates["output_per_mtok"]) / 1_000_000


def row(run_id: str, state: State, usage: dict, pricing: dict, ts: str) -> CallRow:
    cost = estimate_cost(usage, pricing)
    return CallRow(
        run_id=run_id, stage=state.stage or "unknown", agent=usage["agent"],
        model=usage["model"], ts=ts, chapter=state.chapter, attempt=state.attempt,
        input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
        cache_creation_input_tokens=usage["cache_creation_input_tokens"],
        cache_read_input_tokens=usage["cache_read_input_tokens"],
        duration_ms=usage["duration_ms"], provenance="measured",
        cost_usd=cost, cost_provenance="estimated" if cost is not None else "absent",
        note="from the Agent tool's result: four usage figures, resolved model")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _events(conn: sqlite3.Connection, run_id: str, extra: list[Path]):
    for (payload, ts) in conn.execute(
            "SELECT payload, ts FROM events WHERE run_id = ? ORDER BY seq", (run_id,)):
        try:
            yield json.loads(payload), ts
        except ValueError:
            continue
    for path in extra:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                yield json.loads(line), None
            except ValueError:
                continue


def reimport(conn: sqlite3.Connection, run_id: str, *,
             extra_streams: list[Path] | None = None) -> int:
    """Replace the run's `calls` with one row per finished agent call found in
    its recorded events and in `extra_streams`, in that order."""
    pricing = loader.load_pricing()
    state = State()
    rows: list[CallRow] = []
    for event, ts in _events(conn, run_id, list(extra_streams or [])):
        usage = from_event(event)
        if usage is not None:
            rows.append(row(run_id, state, usage, pricing, ts or _now()))
        apply(state, event)
    with tx(conn):
        conn.execute("DELETE FROM calls WHERE run_id = ?", (run_id,))
        for r in rows:
            write_call(conn, r)
    return len(rows)


def main(argv: list[str]) -> int:
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate

    conn = connect(load_settings().db_path)
    migrate(conn)
    n = reimport(conn, argv[0], extra_streams=[Path(p) for p in argv[1:]])
    total = conn.execute("SELECT COUNT(*), SUM(cost_usd), SUM(output_tokens) FROM calls "
                         "WHERE run_id = ?", (argv[0],)).fetchone()
    print(f"{argv[0]}: {n} calls, estimated {total[1] or 0:.2f} USD, "
          f"{total[2] or 0} output tokens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
