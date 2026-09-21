"""The rolling summary: structured facts, and the projection built from them.

This is the ONLY channel between chapters. Everything a later chapter knows about
an earlier one passes through here, which is what makes the writer's isolation
survivable rather than merely strict.
"""

from __future__ import annotations

import sqlite3

# Survival order when the cap bites. Never by age alone.
#
# An `open-question` dropped is a promise abandoned in silence - the failure the
# ontology calls the foreshadowing ledger, arriving quietly. So questions survive
# first, then recent state changes, then events.
PRIORITY = {"open-question": 0, "state-change": 1, "knowledge": 2, "event": 3}


def project(conn: sqlite3.Connection, run_id: str, *, cap: int) -> tuple[str, list[dict]]:
    """The summary as the writer receives it, and whatever the cap dropped.

    Returns (text, dropped). A dropped `open-question` is a run warning, not a
    halt: the cap exists to hold the context flat, not to govern the story, and
    halting because a novel opened many threads is the wrong trade. But it must
    be VISIBLE, which is what the second return value is for.
    """
    rows = [dict(r) for r in conn.execute(
        "SELECT id, chapter, kind, fact, who FROM summary_facts "
        "WHERE run_id = ? AND dropped_at_chapter IS NULL ORDER BY chapter, id",
        (run_id,),
    )]
    if len(rows) <= cap:
        return _render(rows), []

    ranked = sorted(rows, key=lambda r: (PRIORITY.get(r["kind"], 9), -r["chapter"]))
    kept = ranked[:cap]
    dropped = ranked[cap:]
    kept_in_order = [r for r in rows if r in kept]
    return _render(kept_in_order), dropped


def _render(rows: list[dict]) -> str:
    if not rows:
        return ""
    lines = []
    for r in rows:
        who = f" [{r['who']}]" if r.get("who") else ""
        lines.append(f"- (ch{r['chapter']}, {r['kind']}){who} {r['fact']}")
    return "\n".join(lines)
