"""Persisting a run. After every stage and every attempt, never only at the end.

A background task that keeps progress in memory loses it to a restart, and a run
measured in hours will meet one. v1 wrote `state.json` only when it finished,
which is why an interrupted run left nothing anyone could read.
"""

from __future__ import annotations

import json
import sqlite3

from backend.commons.db.connection import tx


def now() -> str:
    """A real clock reading.

    v1 estimated its timestamps and a log claimed 24 minutes for a run that took
    72. A plausible number and a measured one look identical once written down,
    which is why this is a function and not a habit.
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_run(conn, *, run_id, slug, premise, profile, tone, snapshot,
               brief_id=None) -> None:
    """`brief_id` stays optional and NULL stays meaningful: a run from a bare
    premise is the demo and the stress profile, not a degraded order."""
    with tx(conn):
        conn.execute(
            "INSERT INTO runs (id, slug, premise, profile, tone, config_snapshot, "
            "stage, source, started_at, brief_id) VALUES (?,?,?,?,?,?,?, 'v2', ?,?)",
            (run_id, slug, premise, profile, tone, json.dumps(snapshot), "FLOW-1",
             now(), brief_id),
        )


def save_brief_facts(conn, run_id: str, facts) -> int:
    """What the buyer asked for, as rows the gate can count against.

    `mandatory_facts` become `mandatory` rows the publish gate checks one by
    one; the free text becomes a single `freetext` row, verbatim and whole.
    Neither is summarised or split here — a paraphrase would be a model reading
    the untrusted string, and a filter clever enough to drop brief 04's attack
    would have to be trusted not to drop the gift hidden in the same paragraph.

    `OR IGNORE` on `(run_id, source, text)`, so starting the same brief twice
    is not an error and re-running it adds nothing.
    """
    written = 0
    with tx(conn):
        for fact in facts:
            # `Fact.kind` is the brief's vocabulary ("mandatory" / "freetext");
            # the table's is the Bible's. A promise the buyer made about the
            # person the book is for is a `recipient` fact there, and the
            # translation happens here rather than by widening the CHECK, which
            # would let the two vocabularies drift into one muddle.
            # A dated memory is already the Bible's vocabulary: `chronology`.
            kind = ("freetext" if fact.source == "freetext" else
                    "chronology" if fact.kind == "chronology" else "recipient")
            cur = conn.execute(
                "INSERT OR IGNORE INTO facts (run_id, kind, text, source, mandatory) "
                "VALUES (?,?,?,?,?)",
                (run_id, kind, fact.text, fact.source, 1 if fact.mandatory else 0))
            written += cur.rowcount or 0
    return written


def set_stage(conn, run_id: str, stage: str) -> None:
    with tx(conn):
        conn.execute("UPDATE runs SET stage = ? WHERE id = ?", (stage, run_id))


def halt(conn, run_id: str, kind: str, detail: str) -> None:
    """One of gate | budget | context | interrupted. What was produced stays
    readable; that is the whole difference between halting and crashing."""
    with tx(conn):
        conn.execute(
            "UPDATE runs SET halted = ?, halted_detail = ?, finished_at = ? WHERE id = ?",
            (kind, detail, now(), run_id),
        )


def finish(conn, run_id: str) -> None:
    with tx(conn):
        conn.execute(
            "UPDATE runs SET stage = 'complete', finished_at = ? WHERE id = ?",
            (now(), run_id),
        )


def save_skill_sha(conn, run_id: str, *, at_start: str | None = None,
                   at_end: str | None = None) -> None:
    """Fingerprint the procedure a run ran under.

    `SKILL.md` is the pipeline, and it is a file anyone can edit mid-run. That
    happened: a sixth characteristic was added during an eight-chapter run, so
    its first chapters were judged by five and the rest could be judged by six.
    A run whose procedure changed underneath it is not a clean sample, and that
    has to be a recorded fact rather than something someone remembers.
    """
    if at_start is not None:
        with tx(conn):
            conn.execute("UPDATE runs SET skill_sha_at_start = ? WHERE id = ?",
                         (at_start, run_id))
    if at_end is not None:
        with tx(conn):
            conn.execute("UPDATE runs SET skill_sha_at_end = ? WHERE id = ?",
                         (at_end, run_id))


def save_cost(conn, run_id: str, *, cost_usd: float, provenance: str = "measured",
              turns=None, duration_ms=None, subagent_dispatches=None) -> None:
    """The whole run's cost, from Claude Code's `result` event. SPEC-003 A7.

    It lived only in `output/<slug>/cost.json`, so the panel showed the sum over
    `calls` instead - a reconstructed figure standing where a measured one
    existed, which is the rule G12 holds, inverted. Nullable on purpose: a run
    with no `result` has no cost, and that is absent, not zero.
    """
    with tx(conn):
        conn.execute(
            "UPDATE runs SET cost_usd = ?, cost_provenance = ?, turns = ?, "
            "duration_ms = ?, subagent_dispatches = ? WHERE id = ?",
            (float(cost_usd), provenance, turns, duration_ms, subagent_dispatches,
             run_id),
        )


def save_gate_set(conn, run_id: str, characteristics) -> None:
    """The gate this run actually ran. SPEC-006 made this necessary.

    A characteristic that did not exist when a run ran is not a critic that
    failed to answer, and the two are indistinguishable from the scores alone:
    both leave NULL. The archive can tell them apart because it sees which
    critique files exist. Everything downstream can only know it if it is
    recorded.
    """
    with tx(conn):
        conn.execute("UPDATE runs SET gate = ? WHERE id = ?",
                     (json.dumps(list(characteristics)), run_id))


def open_change(conn, run_id: str, *, n: int, kind: str, started_at: str,
                orchestrator_model: str | None = None, chapter_loop: str | None = None,
                ceiling_usd: float | None = None, ceiling_by: str | None = None,
                finished_at: str | None = None, total_usd: float | None = None,
                provenance: str | None = None, minutes: float | None = None,
                note: str | None = None) -> None:
    """One row of `changes`: what a segment of a run ran under (SPEC-EXAM-007
    §7.4). SPEC-007 writes `generate` and `continue`; the table is shared with
    SPEC-EXAM-008, whose cost columns stay NULL here — absent, never 0.

    The finished fields are here too so a segment recorded after the fact —
    the hand-written `resume` block in a `cost.json` — lands in one statement.
    """
    with tx(conn):
        conn.execute(
            "INSERT INTO changes (run_id, n, kind, started_at, finished_at, "
            "orchestrator_model, chapter_loop, ceiling_usd, ceiling_by, total_usd, "
            "provenance, minutes, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, n, kind, started_at, finished_at, orchestrator_model,
             chapter_loop, ceiling_usd, ceiling_by, total_usd, provenance, minutes,
             note))


def close_change(conn, run_id: str, n: int, *, total_usd: float | None,
                 provenance: str) -> None:
    """`total_usd` None stays NULL: a segment that reported nothing was not
    free. `minutes` is this clock's, from the row's own start to now."""
    finished = now()
    with tx(conn):
        conn.execute(
            "UPDATE changes SET finished_at = ?, total_usd = ?, provenance = ?, "
            "minutes = (julianday(?) - julianday(started_at)) * 1440.0 "
            "WHERE run_id = ? AND n = ?",
            (finished, total_usd, provenance, finished, run_id, n))


def set_trashed(conn, run_id: str, trashed: bool) -> None:
    with tx(conn):
        conn.execute("UPDATE runs SET trashed_at = ? WHERE id = ?",
                     (now() if trashed else None, run_id))


def reopen(conn, run_id: str) -> None:
    """The halt a continuation resumes past stops being the run's state. It
    stays in `events` and in the warnings; the row says running."""
    with tx(conn):
        conn.execute("UPDATE runs SET halted = NULL, halted_detail = NULL, "
                     "finished_at = NULL WHERE id = ?", (run_id,))


def append_event(conn, run_id: str, *, seq: int, type: str, payload: str,
                 unit: str | None = None) -> None:
    """One raw stream line, before anything is derived from it (FR-RNR-3).

    Its own transaction, and the first write for every line: a crash between
    this row and the stage it implies loses the derivation, never the evidence.
    """
    with tx(conn):
        conn.execute(
            "INSERT INTO events (run_id, seq, ts, type, payload, unit) "
            "VALUES (?,?,?,?,?,?)",
            (run_id, seq, now(), type or "unknown", payload, unit),
        )


def events_after(conn, run_id: str, seq: int) -> list[dict]:
    """Rows with a `seq` strictly greater than the one given — what a client that
    sends `Last-Event-ID: seq` has not seen."""
    rows = conn.execute(
        "SELECT seq, ts, type, payload, unit FROM events WHERE run_id = ? AND seq > ? "
        "ORDER BY seq", (run_id, seq),
    ).fetchall()
    return [dict(r) for r in rows]


def save_orchestrator_context(conn, run_id: str, *, turns: int, largest: int,
                              over_ceiling: int) -> None:
    """What the orchestrator's own turns measured, written once at the end."""
    with tx(conn):
        conn.execute(
            "UPDATE runs SET orchestrator_turns = ?, largest_orchestrator_turn = ?, "
            "orchestrator_turns_over_ceiling = ? WHERE id = ?",
            (turns, largest, over_ceiling, run_id),
        )


def warn_orchestrator_context(conn, run_id: str, *, turn_tokens: int, ceiling: int) -> None:
    """The FIRST crossing, once per run.

    A warning per turn would be sixty warnings on a run that is behaving
    exactly as designed, and a warning nobody reads is worse than none
    (`domain-knowledge.md` §8.6). One row, with the figure that crossed.
    """
    with tx(conn):
        conn.execute(
            "INSERT INTO run_warnings (run_id, kind, detail, chapter, ts) "
            "SELECT ?, 'orchestrator-context', ?, NULL, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM run_warnings "
            "                  WHERE run_id = ? AND kind = 'orchestrator-context')",
            (run_id,
             f"an orchestrator turn carried {turn_tokens:,} tokens against a ceiling "
             f"of {ceiling:,}. Recorded, not halted: the ceiling is about the packets "
             f"the agents receive, and this run is free to continue.",
             now(), run_id),
        )


def warn(conn, run_id: str, kind: str, detail: str, chapter: int | None = None) -> None:
    with tx(conn):
        conn.execute(
            "INSERT INTO run_warnings (run_id, kind, detail, chapter, ts) "
            "VALUES (?,?,?,?,?)",
            (run_id, kind, detail, chapter, now()),
        )


def save_attempt(conn, *, run_id, chapter, attempt, title, draft_path, words,
                 scores, verdict, aggregate, findings, promoted=False) -> int:
    """A chapter's attempt, its five scores and its findings - one transaction.

    A crash between them leaves a run nobody can explain: scores without the
    draft they judged, or findings pointing at an attempt that was never written.
    """
    with tx(conn):
        cur = conn.execute(
            "INSERT INTO attempts (run_id, chapter, attempt, title, draft_path, words, "
            "aggregate, verdict, promoted, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, title, draft_path, words, aggregate,
             verdict, 1 if promoted else 0, now()),
        )
        attempt_id = int(cur.lastrowid)
        for characteristic, score in scores.items():
            conn.execute(
                "INSERT INTO scores (attempt_id, characteristic, score) VALUES (?,?,?)",
                (attempt_id, characteristic, score),
            )
        for f in findings:
            conn.execute(
                "INSERT INTO findings (attempt_id, characteristic, severity, kind, "
                "quote, claim, fix, reference, upheld, ruling, late) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, f.get("characteristic", "?"), f.get("severity", "medium"),
                 f.get("kind"), f.get("quote"), f.get("claim") or f.get("problem"),
                 f.get("fix"), f.get("reference"),
                 0 if f.get("upheld") is False else 1,
                 # The arbitration itself, not just its outcome. "Overruled and
                 # right" and "overruled and wrong" are different events, and
                 # only the wording tells them apart.
                 f.get("ruling") or f.get("orchestrator_arbitration"),
                 1 if f.get("late") else 0),
            )
    return attempt_id


def save_gate(conn, *, run_id, chapter, attempt, aggregate, threshold, verdict, note) -> None:
    with tx(conn):
        conn.execute(
            "INSERT INTO gate_decisions (run_id, chapter, attempt, aggregate, threshold, "
            "verdict, note, ts) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, aggregate if aggregate is not None else -1,
             threshold, verdict, note, now()),
        )


def save_sheet(conn, *, run_id, chapter, attempt, level, body, validated, lines_cited) -> None:
    with tx(conn):
        conn.execute(
            "INSERT OR REPLACE INTO sheets (run_id, chapter, attempt, level, body, "
            "validated, lines_cited, ts) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, chapter, attempt, level, body, 1 if validated else 0,
             lines_cited, now()),
        )


def save_facts(conn, run_id: str, chapter: int, facts: list[dict]) -> None:
    """The rolling summary, and the knowledge-state it feeds.

    `who` on a `knowledge` fact is what fills character_knowledge - in the SAME
    transaction, so the table cannot drift from the facts it points at.
    """
    with tx(conn):
        for fact in facts:
            kind = fact.get("kind")
            if kind not in ("event", "state-change", "knowledge", "open-question"):
                continue
            cur = conn.execute(
                "INSERT INTO summary_facts (run_id, chapter, kind, fact, who) "
                "VALUES (?,?,?,?,?)",
                (run_id, chapter, kind, str(fact.get("fact", "")), fact.get("who")),
            )
            if kind == "knowledge" and fact.get("who"):
                conn.execute(
                    "INSERT OR IGNORE INTO character_knowledge "
                    "(run_id, character, fact_id, learned_in_chapter) VALUES (?,?,?,?)",
                    (run_id, fact["who"], int(cur.lastrowid), chapter),
                )
