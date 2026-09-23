"""Reading runs back. SQL out, behind the service."""

from __future__ import annotations

import json
import sqlite3

from backend.commons.config import loader


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT id, slug, premise, profile, tone, stage, halted, halted_detail, "
        "source, started_at, finished_at FROM runs ORDER BY started_at DESC"
    )]


def get_run(conn: sqlite3.Connection, run_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, slug, premise, profile, tone, stage, halted, halted_detail, "
        "source, started_at, finished_at, config_snapshot FROM runs WHERE id = ?",
        (run_id,)
    ).fetchone()
    if not row:
        return None
    run = dict(row)
    # The hash of what this run ran with, computed from the stored snapshot and
    # never from today's config (FR-CFG-1). The blob itself stays out of the
    # payload; the panel reads a fingerprint, not a config file.
    snapshot = run.pop("config_snapshot")
    run["config_hash"] = loader.config_hash(json.loads(snapshot)) if snapshot else None
    return run


def attempts_with_scores(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        "SELECT id, chapter, attempt, aggregate, verdict, promoted FROM attempts "
        "WHERE run_id = ? ORDER BY chapter, attempt", (run_id,)
    )]
    for row in rows:
        row["scores"] = {
            s["characteristic"]: s["score"]
            for s in conn.execute(
                "SELECT characteristic, score FROM scores WHERE attempt_id = ?",
                (row.pop("id"),),
            )
        }
        row["promoted"] = bool(row["promoted"])
    return rows


def cost(conn: sqlite3.Connection, run_id: str) -> dict:
    """What the run cost, and how the figures were obtained.

    Imported runs carry one total with no split, graded `reconstructed`; v2 runs
    carry both halves. Mixing them into one number without saying so is how
    $6.21 came to stand in for $49.33.

    **The run's own measured total wins over the sum of the calls** (SPEC-003 A7).
    Both are here and they answer different questions: the `result` event knows
    what the whole run cost including the orchestrator's turns, and the `calls`
    rows know how it split. When the first exists, the second is a floor. Showing
    the floor as the total is a reconstructed figure standing where a measured one
    exists, and that is the failure the grades are for.

    `total_usd` is None, never 0, when nothing measured and nothing summed.
    """
    # No COALESCE on the token sums, deliberately. SUM over rows that are all
    # NULL is NULL, and NULL is the answer: every call of the first real run
    # stored `input_tokens` as NULL — honestly, because the stream's per-agent
    # packets report nothing — and a COALESCE here printed **"0 / 0" tokens for
    # a run that spent $18.82**. The database told the truth and this query
    # threw it away.
    row = conn.execute(
        "SELECT COUNT(*) AS calls, SUM(input_tokens) AS input_tokens, "
        "SUM(output_tokens) AS output_tokens, "
        "COUNT(input_tokens) AS token_rows, "
        "SUM(cost_usd) AS total_usd FROM calls WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    kinds = [r["provenance"] for r in conn.execute(
        "SELECT DISTINCT provenance FROM calls WHERE run_id = ?", (run_id,))]

    run = conn.execute(
        "SELECT cost_usd, cost_provenance, turns, duration_ms, subagent_dispatches "
        "FROM runs WHERE id = ?", (run_id,)
    ).fetchone()

    # NULL when no call reported a cost, which is not the same as $0.00.
    summed = row["total_usd"]
    measured = run["cost_usd"] if run else None
    if measured is not None:
        total, grade = measured, (run["cost_provenance"] or "measured")
    elif summed:
        total, grade = summed, "reconstructed"
    else:
        total, grade = None, "absent"

    out = dict(row)
    token_rows = out.pop("token_rows")

    return {
        **out,
        "tokens_provenance": "measured" if token_rows else "absent",
        "total_usd": total,
        "summed_from_calls_usd": summed,
        "total_provenance": grade,
        "provenance": sorted(kinds),
        "turns": run["turns"] if run else None,
        "duration_ms": run["duration_ms"] if run else None,
        "subagent_dispatches": run["subagent_dispatches"] if run else None,
    }


def orchestrator_context(conn: sqlite3.Connection, run_id: str, ceiling: int = 100_000) -> dict:
    """What the orchestrator's own turns measured — or that nobody measured.

    `provenance` is the field that matters: `absent` says no watcher ever saw
    this run, and 0 turns over the ceiling would say the opposite.
    """
    row = conn.execute(
        "SELECT orchestrator_turns, largest_orchestrator_turn, "
        "orchestrator_turns_over_ceiling FROM runs WHERE id = ?", (run_id,)
    ).fetchone()
    turns = row["orchestrator_turns"] if row else None
    return {
        "turns": turns,
        "largest_turn_tokens": row["largest_orchestrator_turn"] if row else None,
        "turns_over_ceiling": row["orchestrator_turns_over_ceiling"] if row else None,
        "ceiling": ceiling,
        "provenance": "measured" if turns is not None else "absent",
        "note": "the ceiling is about the packets the agents receive; an "
                "orchestrator turn above it is reported and never halted",
    }


def warnings(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT kind, detail, chapter, ts FROM run_warnings WHERE run_id = ? "
        "ORDER BY id", (run_id,))]


def completeness(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    """What an imported run did NOT carry. A gap reads as a gap, never a zero."""
    return [dict(r) for r in conn.execute(
        "SELECT field, state, note FROM run_completeness WHERE run_id = ? "
        "AND state != 'present' ORDER BY field", (run_id,))]
