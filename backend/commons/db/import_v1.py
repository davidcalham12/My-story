"""Importing the eight runs from the previous implementation.

D22 makes this the schema's first real test, and it is a hard one: the eight runs
carry **three** critique shapes, **eight** different chapter schemas and **five**
different critic sets, and three of them wrote no gate rows at all.

The rule that governs every decision here: **import what is common and record
what was missing.** Normalising a gap away fabricates a past that did not happen
— a run that never wrote gate rows must not end up resembling one whose gate
passed everything first time. Every imported run therefore carries a completeness
record, and the interface says "not recorded" rather than zero.

They are marked `pre-loop003` and **excluded from LOOP-003's statistics**: a pass
rate computed over runs judged by three characteristics does not measure what it
claims. Evidence, not sample.

This importer does **not** backfill `knowledge` facts from their prose summaries.
That would be invented data wearing the appearance of measurement.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.commons.db.connection import tx

#: The five a v1 run could possibly have carried. **Not** `domain.CHARACTERISTICS`,
#: which gained `prose` in SPEC-006: recording an imported attempt as missing a
#: critic that did not exist when it ran would file a gap that is not one.
CHARACTERISTICS = ("continuity", "science", "outline", "length", "chatter")


@dataclass
class ImportReport:
    slug: str
    chapters: int
    attempts: int
    calls: int
    gate_rows: int
    missing: dict[str, str]


def _iterations(raw: Any) -> list[dict]:
    """A critique file, in whichever of three shapes its run happened to write.

    The shape was never specified, so each run chose one. Being strict about a
    contract nobody stated is not rigour — it is how a reader once called
    `.iterations` on a bare array and took an entire interface down.
    """
    if isinstance(raw, list):
        return [it for it in raw if isinstance(it, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("iterations"), list):
            return [it for it in raw["iterations"] if isinstance(it, dict)]
        if isinstance(raw.get("score"), (int, float)):
            return [raw]
    return []


def _int(value: Any, default: int | None = None) -> int | None:
    """Whatever a v1 run wrote, as an integer or as nothing.

    The STRICT tables caught this on the first import: some runs wrote
    `iteration` as a string. Coercing here rather than loosening the column is
    the right direction - the schema keeps telling the truth about its types, and
    the mess stays in the importer where the mess came from.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _log_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "logs" / "agents.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue  # a partial log from an interrupted run is still worth reading
    return rows


def _full_model_id(short: str | None) -> str | None:
    """`opus` is not a model id and matches no rate.

    Four v1 runs wrote the family word, so every one of them priced at nothing —
    which reads as "this run was free" rather than "the name did not match the
    price list". Folded here, and only where exactly one model of that family is
    priced.
    """
    if not short:
        return None
    table = {"opus": "claude-opus-5", "sonnet": "claude-sonnet-5",
             "haiku": "claude-haiku-4-5"}
    return table.get(short.strip().lower(), short)


def import_run(conn: sqlite3.Connection, run_dir: Path) -> ImportReport:
    slug = run_dir.name
    state = _read_json(run_dir / "state.json") or {}
    snapshot = _read_json(run_dir / "config.snapshot.json") or {}
    rows = _log_rows(run_dir)
    gate_rows = [r for r in rows if r.get("event") == "gate_decision"]
    calls = [r for r in rows if r.get("agent")]

    stamps = sorted(r["ts"] for r in rows if r.get("ts"))
    started = stamps[0] if stamps else datetime.now(timezone.utc).isoformat()

    missing: dict[str, str] = {}
    if not gate_rows:
        missing["gate_decisions"] = (
            "the run wrote no gate_decision rows; its gate history, if any, is "
            "only in critiques/chNN.gate.json"
        )
    if not any(c.get("duration_ms") for c in calls):
        missing["duration_ms"] = "no call recorded how long it took"
    if not any(c.get("tokens") for c in calls):
        missing["tokens"] = "no call recorded token usage"

    critique_dir = run_dir / "critiques"
    present = set()
    if critique_dir.exists():
        for f in critique_dir.glob("ch*.json"):
            name = f.name.split(".", 1)[1].removesuffix(".json")
            if name in CHARACTERISTICS:
                present.add(name)
    for absent in set(CHARACTERISTICS) - present:
        missing[f"critic:{absent}"] = "this run had no such characteristic"

    with tx(conn):
        conn.execute(
            "INSERT INTO runs (id, slug, premise, profile, tone, config_snapshot, "
            "stage, source, started_at, finished_at) "
            "VALUES (?,?,?,?,?,?,?,'pre-loop003',?,?)",
            (
                slug, slug,
                state.get("premise") or "(not recorded)",
                state.get("profile") or "unknown",
                (snapshot.get("novel") or {}).get("tone"),
                json.dumps(snapshot),
                state.get("stage") or "unknown",
                started,
                stamps[-1] if stamps else None,
            ),
        )
        for field, note in missing.items():
            conn.execute(
                "INSERT INTO run_completeness (run_id, field, state, note) "
                "VALUES (?,?,'absent',?)",
                (slug, field, note),
            )
        for field in ("premise", "state.json"):
            conn.execute(
                "INSERT INTO run_completeness (run_id, field, state, note) "
                "VALUES (?,?,?,NULL)",
                (slug, field, "present" if state else "absent"),
            )

        attempts = _import_chapters(conn, slug, run_dir, state)
        _import_calls(conn, slug, calls)
        for row in gate_rows:
            conn.execute(
                "INSERT INTO gate_decisions (run_id, chapter, attempt, aggregate, "
                "threshold, verdict, note, ts) VALUES (?,?,?,?,?,?,?,?)",
                (
                    slug, _int(row.get("chapter"), 0), _int(row.get("iteration"), 1),
                    _int(row.get("aggregate"), 0), _int(row.get("threshold"), 8),
                    str(row.get("verdict") or "unknown"), row.get("note"),
                    row.get("ts") or started,
                ),
            )

    return ImportReport(
        slug=slug,
        chapters=len(state.get("chapters") or []),
        attempts=attempts,
        calls=len(calls),
        gate_rows=len(gate_rows),
        missing=missing,
    )


def _import_chapters(conn, slug: str, run_dir: Path, state: dict) -> int:
    """One attempt row per attempt the run left evidence of.

    The eight runs use eight different chapter schemas - `drafts` here,
    `attempts` there, `accepted_iteration` or `passed_at` or neither - so every
    field is read defensively and an absent one stays absent.
    """
    chapters = state.get("chapters") or []
    written = 0
    for entry in chapters:
        n = entry.get("n")
        if not isinstance(n, int):
            continue
        count = _int(entry.get("drafts") or entry.get("attempts"), 1) or 1
        accepted = _int(
            entry.get("accepted_iteration") or entry.get("accepted_attempt")
            or entry.get("passed_at"), count) or count
        for k in range(1, count + 1):
            draft = f"chapters/ch{n:02d}.attempt{k}.md"
            if not (run_dir / draft).exists():
                # Most v1 runs kept only the accepted draft. That is exactly the
                # evidence loss that made "the writer changed only what was
                # cited" unmeasurable, and it is recorded rather than faked.
                draft = f"chapters/ch{n:02d}.md" if k == accepted else "(not kept)"
            cur = conn.execute(
                "INSERT INTO attempts (run_id, chapter, attempt, title, draft_path, "
                "words, aggregate, verdict, promoted, ts) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    slug, n, k, entry.get("title"), draft,
                    _int(entry.get("words"), 0),
                    _int(entry.get("best_aggregate") or entry.get("aggregate")),
                    "accept" if k == accepted else "retry",
                    1 if k == accepted else 0,
                    state.get("finished_at") or "unknown",
                ),
            )
            written += 1
            _import_scores(conn, int(cur.lastrowid), run_dir, n, k)
    return written


def _import_scores(conn, attempt_id: int, run_dir: Path, chapter: int, attempt: int) -> None:
    for characteristic in CHARACTERISTICS:
        path = run_dir / "critiques" / f"ch{chapter:02d}.{characteristic}.json"
        if not path.exists():
            continue
        for it in _iterations(_read_json(path)):
            if (it.get("iteration") or 1) != attempt:
                continue
            score = it.get("score")
            # -1 was v1's marker for "no verdict". NULL is the honest value:
            # excluded from the minimum rather than counted either way.
            if score == -1:
                score = None
            conn.execute(
                "INSERT OR IGNORE INTO scores (attempt_id, characteristic, score, note) "
                "VALUES (?,?,?,?)",
                (attempt_id, characteristic,
                 int(score) if isinstance(score, (int, float)) else None,
                 "; ".join(it.get("notes", []))[:500] or None),
            )
            for f in it.get("findings") or []:
                conn.execute(
                    "INSERT INTO findings (attempt_id, characteristic, severity, kind, "
                    "quote, claim, fix, reference, upheld) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        attempt_id, characteristic,
                        f.get("severity") or "medium", f.get("kind"),
                        f.get("quote"),
                        f.get("claim") or f.get("problem"),
                        f.get("fix"), f.get("reference"),
                        0 if f.get("upheld") is False else 1,
                    ),
                )


def _import_calls(conn, slug: str, calls: list[dict]) -> None:
    for row in calls:
        tokens = row.get("tokens")
        conn.execute(
            "INSERT INTO calls (run_id, stage, agent, model, chapter, attempt, "
            "input_tokens, output_tokens, cost_usd, provenance, duration_ms, ts, note) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                slug, row.get("stage") or "unknown", row.get("agent") or "unknown",
                _full_model_id(row.get("model")) or "unknown",
                _int(row.get("chapter")), _int(row.get("iteration")),
                # v1 recorded ONE total with no split. Splitting it here would be
                # inventing two numbers from one; both stay absent and the total
                # is kept in the note, graded `reconstructed`.
                None, None, None,
                "reconstructed" if tokens else "absent",
                _int(row.get("duration_ms")),
                row.get("ts") or "unknown",
                f"v1 total tokens: {tokens}" if tokens else None,
            ),
        )


def import_all(
    conn: sqlite3.Connection,
    output_dir: Path,
    slugs: Iterable[str] | None = None,
) -> list[ImportReport]:
    """Import the v1 runs under `output_dir`.

    **v2 writes its runs into the same directory, on purpose** — the layout is
    the same one, and a reader should not have to know which implementation
    produced a novel. So "every directory here is a v1 run" was true exactly
    until v2 produced its first one, and then it silently marked a live v2 run
    `pre-loop003` and counted it as history.

    Two ways to say which is which, and both are here:

    - pass `slugs` explicitly — what the tests do, because a test about eight
      specific historical runs should not change its answer when someone starts
      a ninth novel;
    - otherwise skip any slug the database already holds. That is airtight for a
      live run rather than merely likely: the watcher learns the slug from the
      first `output/<slug>/` path the run writes, which is the same event that
      creates the directory this loop could see. It also makes a second import a
      no-op instead of a duplicate.
    """
    if slugs is not None:
        wanted = set(slugs)
    else:
        wanted = None
        known = {
            row["slug"]
            for row in conn.execute("SELECT slug FROM runs WHERE slug IS NOT NULL")
        }

    reports = []
    for run_dir in sorted(p for p in output_dir.iterdir() if p.is_dir()):
        if not (run_dir / "state.json").exists():
            continue
        if wanted is not None:
            if run_dir.name not in wanted:
                continue
        elif run_dir.name in known:
            continue
        reports.append(import_run(conn, run_dir))
    return reports
