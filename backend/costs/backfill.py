"""Rebuild a run's `changes` cost figures from what is already on disk, at $0.

    python -m backend.costs.backfill output/<slug> [--run-id ID] [--dry-run]

Every figure comes from a `result` event Claude Code wrote — measured — read
from one of these records (SPEC-EXAM-008 §3 and §8.6):

    the first run and its units        `events` in the database, by run
    a resume outside the server        logs/resume.stream.jsonl
    a reader change, version N         dist/vN/logs/chNN.stream.jsonl
    a change that never published      dist/_aborted-change-K/logs/*.stream.jsonl
    a redo of chapter NN               dist/vN/chapters/_redo-<stamp>/ (what it set aside)

**A redo overwrites.** Until SPEC-EXAM-008, `dispatch` wrote
`logs/chNN.stream.jsonl` afresh for a redo, so the earlier pass's stream for
that chapter is gone; the `_redo-<stamp>` directory proves the earlier pass
happened and holds its chapter files, not its bill. That process is counted
as without a result — absent, never 0 — with a note saying why. From now on
`_set_aside` moves the stream into that directory too, and this reads it there.

**Idempotent.** A change is matched to its existing row — SPEC-EXAM-007's
`generate`/`continue` rows by kind and order, the rest by kind and `label` —
and its cost columns are reset and summed again; what 007 recorded (ceiling,
start) is kept. Rows the live recorder wrote under another label are left alone.

Never touches a network or a model. `--dry-run` works on an in-memory copy of
the database and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from backend.commons.db.connection import tx
from backend.costs import repository as costs
from backend.costs.measure import Meter

RESUME = "logs/resume.stream.jsonl"
STREAM = re.compile(r"^ch(\d{2})\.stream\.jsonl$")
CHAPTER_FILE = re.compile(r"^ch(\d{2})\.")
REDO_STAMP = re.compile(r"_redo-(\d{8}T\d{6}Z)$")

#: Notes this module writes, removed before a row is summed again.
_OWN_NOTES = ("incomplete: ", costs.SPLIT_ABSENT, costs.NO_ORCHESTRATOR,
              "no stream was kept", "the stream of ch")


@dataclass
class Planned:
    kind: str
    label: str | None = None
    version: int | None = None
    chapters: set[int] = field(default_factory=set)
    started_at: str | None = None
    #: (source, events) — one entry per stream, possibly several processes each.
    streams: list[tuple[str, list[dict]]] = field(default_factory=list)
    missing: int = 0
    notes: list[str] = field(default_factory=list)
    n: int | None = None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_stream(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _rel(path: Path, run_dir: Path) -> str:
    return path.relative_to(run_dir).as_posix()


# ------------------------------------------------------------------ the sources


def _from_events(conn, run_id: str, segments: list[dict]) -> dict[int, Planned]:
    """The run's own processes, from `events`, each to the segment it ran in.

    A line with no `unit` came from the single orchestrator — the first run,
    since a continuation always runs under the conductor — and is `generate`'s
    whatever its `ts` (a reimported stream's `ts` is the import's). A unit's
    line goes to the last generate/continue row that had started by its `ts`."""
    rows = conn.execute("SELECT seq, ts, payload, unit FROM events WHERE run_id = ? "
                        "ORDER BY seq", (run_id,)).fetchall()
    planned: dict[int, Planned] = {}

    def target(ts: str, unit) -> Planned:
        index = 0
        for i, seg in enumerate(segments):
            if unit is not None and seg["started_at"] and ts and seg["started_at"] <= ts:
                index = i
        key = segments[index]["n"] if segments else 1
        kind = segments[index]["kind"] if segments else "generate"
        return planned.setdefault(key, Planned(kind=kind, n=key if segments else None,
                                               started_at=ts))

    current: list[dict] = []
    for row in rows:
        try:
            event = json.loads(row["payload"])
        except (TypeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        current.append(event)
        if event.get("type") == "result":
            target(row["ts"], row["unit"]).streams.append(
                (f"events seq {row['seq']}", current))
            current = []
    if current and any(e.get("type") == "system" and e.get("subtype") == "init"
                       for e in current):
        # A process that started and never sent its result (eval 01).
        target(rows[-1]["ts"], rows[-1]["unit"]).streams.append(
            ("events (no result)", current))
    return planned


def _from_dist(run_dir: Path) -> list[Planned]:
    dist = run_dir / "dist"
    if not dist.is_dir():
        return []
    out: list[Planned] = []
    for workspace in sorted(p for p in dist.iterdir() if p.is_dir()):
        name = workspace.name
        version_match = re.fullmatch(r"v(\d+)", name)
        if not version_match and not name.startswith("_aborted-change-"):
            continue
        version = int(version_match.group(1)) if version_match else None
        logs = workspace / "logs"
        streams = {int(m.group(1)): p for p in (sorted(logs.iterdir()) if logs.is_dir() else [])
                   if (m := STREAM.match(p.name))}
        redos = sorted(p for p in (workspace / "chapters").glob("_redo-*") if p.is_dir()) \
            if (workspace / "chapters").is_dir() else []
        if version is not None and not streams and not redos:
            # A version the run published itself (v1 by `generate`, v2 by
            # `release --next` after a continuation): no reader change ran here.
            continue
        label = f"dist/{name}"
        started = min((p.stat().st_mtime for p in streams.values()),
                      default=workspace.stat().st_mtime)
        change = Planned(kind="reader_change", label=label, version=version,
                         started_at=_iso(started))

        redo_changes = []
        for d in redos:
            stamp = REDO_STAMP.search(d.name)
            at = (datetime.strptime(stamp.group(1), "%Y%m%dT%H%M%SZ")
                  .replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                  if stamp else _iso(d.stat().st_mtime))
            chapters = {int(m.group(1)) for p in d.iterdir()
                        if (m := CHAPTER_FILE.match(p.name))}
            redo_changes.append((d, Planned(kind="redo", label=f"{label} {d.name}",
                                            version=version, chapters=chapters,
                                            started_at=at)))

        chapters = set(streams) | {c for _, r in redo_changes for c in r.chapters}
        change.chapters = chapters
        # The first pass began before any redo of it, whatever the files' times.
        change.started_at = min([change.started_at, *(r.started_at for _, r in redo_changes)])
        for c in sorted(chapters):
            # Who wrote which stream of chapter c: the first pass, then each
            # redo in turn. Each one's stream is in the next redo's directory,
            # the last one's in logs/.
            owners = [change] + [r for _, r in redo_changes if c in r.chapters]
            places = [d for d, r in redo_changes if c in r.chapters] + [logs]
            for owner, place in zip(owners, places):
                path = place / f"ch{c:02d}.stream.jsonl"
                if path.is_file():
                    owner.streams.append((_rel(path, run_dir), _read_stream(path)))
                else:
                    owner.missing += 1
                    owner.notes.append(f"the stream of ch{c:02d} was overwritten by a "
                                       f"later redo before streams were kept")
        if not chapters:
            change.notes.append("no stream was kept for this change")
        out.append(change)
        out.extend(r for _, r in redo_changes)
    return sorted(out, key=lambda p: p.started_at or "")


def plan(conn: sqlite3.Connection, run_dir: Path, run_id: str) -> list[Planned]:
    segments = [dict(r) for r in conn.execute(
        "SELECT n, kind, started_at FROM changes WHERE run_id = ? AND kind IN "
        "('generate', 'continue') ORDER BY n", (run_id,))]
    from_events = _from_events(conn, run_id, segments)
    planned = [from_events[k] for k in sorted(from_events)]

    resume = run_dir / RESUME
    if resume.is_file():
        taken = {p.n for p in planned}
        free = [s for s in segments if s["kind"] == "continue" and s["n"] not in taken]
        state = {}
        try:
            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        planned.append(Planned(
            kind="continue", label=RESUME, n=free[0]["n"] if free else None,
            started_at=state.get("resumed_utc") or _iso(resume.stat().st_mtime),
            streams=[(RESUME, _read_stream(resume))]))
    return planned + _from_dist(run_dir)


# ------------------------------------------------------------------ writing


def _reset(conn, run_id: str, n: int) -> None:
    row = conn.execute("SELECT note FROM changes WHERE run_id = ? AND n = ?",
                       (run_id, n)).fetchone()
    note = "; ".join(p for p in (row["note"] or "").split("; ")
                     if p and not p.startswith(_OWN_NOTES)) or None
    with tx(conn):
        conn.execute(
            "UPDATE changes SET total_usd = NULL, minutes = NULL, orchestrator_usd = NULL, "
            "agents_model = NULL, agents_usd = NULL, provenance = NULL, results = 0, "
            "unresulted = 0, sources = '[]', note = ? WHERE run_id = ? AND n = ?",
            (note, run_id, n))


def _existing(conn, run_id: str, p: Planned) -> int | None:
    if p.n is not None:
        return p.n
    if p.label is None and p.kind == "generate":
        row = conn.execute("SELECT n FROM changes WHERE run_id = ? AND kind = 'generate' "
                           "ORDER BY n LIMIT 1", (run_id,)).fetchone()
        return row["n"] if row else None
    row = conn.execute("SELECT n FROM changes WHERE run_id = ? AND kind = ? AND label = ?",
                       (run_id, p.kind, p.label)).fetchone()
    return row["n"] if row else None


def rebuild(conn: sqlite3.Connection, run_dir: Path, run_id: str) -> list[dict]:
    """Write every planned change's figures; returns the run's rows."""
    for p in plan(conn, Path(run_dir), run_id):
        n = _existing(conn, run_id, p)
        if n is None:
            n = costs.open_change(conn, run_id, kind=p.kind, version=p.version,
                                  chapters=sorted(p.chapters) if p.chapters else None,
                                  label=p.label, started_at=p.started_at)
        else:
            _reset(conn, run_id, n)
        for source, events in p.streams:
            costs.record_stream(conn, run_id, n, events, meter=Meter(), source=source)
        costs.add_missing(conn, run_id, n, p.missing)
        for note in dict.fromkeys(p.notes):
            costs.add_note(conn, run_id, n, note)
        costs.finish(conn, run_id, n)
    return costs.rows(conn, run_id)


# ------------------------------------------------------------------ the CLI


def _connect() -> sqlite3.Connection:  # pragma: no cover - the CLI's own wiring
    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate

    conn = connect(load_settings().db_path)
    migrate(conn)
    return conn


def _usd(value) -> str:
    return "absent" if value is None else f"{value:.2f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.costs.backfill",
                                     description="Rebuild a run's per-change costs "
                                                 "from its streams and events, at $0.")
    parser.add_argument("run_dir", type=Path, help="output/<slug>")
    parser.add_argument("--run-id", help="the run's id; by default, looked up by slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="rebuild on an in-memory copy and print; write nothing")
    args = parser.parse_args(argv)
    if not args.run_dir.is_dir():
        print(f"backfill: {args.run_dir} is not a directory", file=sys.stderr)
        return 2

    conn = _connect()
    run_id = args.run_id
    if run_id is None:
        row = conn.execute("SELECT id FROM runs WHERE slug = ?",
                           (args.run_dir.name,)).fetchone()
        if row is None:
            print(f"backfill: no run with slug {args.run_dir.name!r}", file=sys.stderr)
            return 2
        run_id = row["id"]

    if args.dry_run:
        from backend.commons.db.connection import memory

        copy = memory()
        conn.backup(copy)
        conn = copy
    rows = rebuild(conn, args.run_dir, run_id)
    print(f"{'n':>3}  {'kind':<14}{'version':<9}{'total':>9}{'orch':>9}{'agents':>9}"
          f"{'min':>8}  provenance  label / note")
    for r in rows:
        print(f"{r['n']:>3}  {r['kind']:<14}{str(r['version'] or ''):<9}"
              f"{_usd(r['total_usd']):>9}{_usd(r['orchestrator_usd']):>9}"
              f"{_usd(r['agents_usd']):>9}"
              f"{'' if r['minutes'] is None else format(r['minutes'], '.1f'):>8}  "
              f"{(r['provenance'] or ''):<12}{r['label'] or ''} {r['note'] or ''}")
    total = costs.total(rows)
    print(f"total {_usd(total['usd'])} ({total['provenance']}); "
          f"{total['absent']} change(s) with no figure")
    if args.dry_run:
        print("dry run: nothing was written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
