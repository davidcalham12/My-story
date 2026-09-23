"""A reader changes one fact, and only the chapters that used it are written again.

    python -m backend.versions.change <slug> --fact <id> --to "<text>"

This is the exam's AC-7 and the reason the Story Bible knows which chapter uses
which fact: without `fact_usage` a one-word change costs a whole novel, and a
whole novel through the gate is a novel that can fail it somewhere it had
already passed.

**Three things this module is built around, each a failure it refuses to have:**

1. *The regeneration never touches the run's own chapters.* Everything it
   writes goes under `dist/v<n>/`, the version's own workspace, allocated before
   a single word is asked for. `chapters/chNN.md` — the prose the gate accepted
   for v1 — is read, never written. So "v1 is intact" is not a promise this code
   keeps; it is a place this code cannot reach.
2. *A halted regeneration publishes nothing.* The gate runs as it always runs
   and may refuse a chapter (docs/spec.md §7 accepts this gap). One refusal and
   the version is abandoned: no `novel.html`, no `versions` row, the workspace
   left on disk as the evidence of what was tried.
3. *A fact no chapter uses is refused.* `fact_usage` returning nothing means
   either the fact is unused or the usage was never recorded, and both answers
   forbid regenerating anything. Regenerating everything "to be safe" would be
   the absent-is-zero mistake in its most expensive form.

The model call itself lives behind `dispatch`, which is injected. Nothing in the
test suite crosses that boundary and nothing in it costs money.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from backend.commons.config.settings import load_settings
from backend.publish import pdf
from backend.publish.pdf import Change

import backend.versions as versions_repo


def impacted(conn: sqlite3.Connection, fact_id: str) -> tuple[int, ...]:
    """The chapters `fact_usage` says this fact reached, in order.

    `fact_usage` arrives with migration 010 (phase E3). Until it does, or if a
    run predates it, this is an empty answer — which the caller refuses to act
    on rather than reading as "no chapter needs changing".
    """
    try:
        rows = conn.execute(
            "SELECT DISTINCT chapter FROM fact_usage WHERE fact_id = ? "
            "ORDER BY chapter", (fact_id,)).fetchall()
    except sqlite3.OperationalError:
        return ()
    return tuple(int(r[0]) for r in rows)


def dispatch(run_dir: Path, workspace: Path, chapters: tuple[int, ...],
             fact_id: str, to: str) -> dict[int, bool]:
    """The boundary. `claude -p` rewrites the named chapters and the gate judges.

    **Not called anywhere in the test suite**, by design: it is the only part of
    a reader change that needs a model, and the recorded stream does not cover
    the reader-change prompt. Everything on either side of it is tested; this is
    demonstrated once, in `docs/iterations.md` (E8).

    The contract, which the tests hold a stand-in to: write each named chapter
    to `<workspace>/chapters/chNN.md` and return the gate's verdict per chapter.
    """
    prompt = (f"Rewrite chapters {', '.join(str(c) for c in chapters)} of the "
              f"novel in {run_dir} so that fact {fact_id} now reads: {to}\n"
              f"Write each chapter to {workspace / 'chapters'} and run the "
              f"ordinary gate on it.")
    raise NotImplementedError(
        "the reader change dispatches Claude Code and is demonstrated, not "
        "tested (PLAN-001 E6). The prompt is built and the workspace is ready:\n"
        + prompt)


def _run_id(conn: sqlite3.Connection, slug: str) -> str | None:
    row = conn.execute("SELECT id FROM runs WHERE slug = ?", (slug,)).fetchone()
    return row[0] if row else None


def main(argv: list[str], *, conn: sqlite3.Connection | None = None,
         output_dir: Path | None = None, regenerate=dispatch) -> int:
    parser = argparse.ArgumentParser(prog="backend.versions.change")
    parser.add_argument("slug")
    parser.add_argument("--fact", required=True)
    parser.add_argument("--to", required=True)
    args = parser.parse_args(argv[1:])

    if conn is None:  # pragma: no cover - the CLI's own wiring
        from backend.commons.db.connection import connect
        from backend.commons.db.migrate import migrate

        settings = load_settings()
        conn = connect(settings.db_path)
        migrate(conn)
        output_dir = output_dir or settings.output_dir
    output_dir = Path(output_dir or load_settings().output_dir)

    run_id = _run_id(conn, args.slug)
    if run_id is None:
        print(f"change: no run with slug {args.slug!r}", file=sys.stderr)
        return 2
    run_dir = output_dir / args.slug
    if not (run_dir / "chapters").is_dir():
        print(f"change: {run_dir} has no chapters to change", file=sys.stderr)
        return 2

    chapters = impacted(conn, args.fact)
    if not chapters:
        # Absent is never zero. "No rows" here means unused *or* unrecorded, and
        # neither is a licence to rewrite the book.
        print(f"change: REFUSED — no chapter is recorded as using fact "
              f"{args.fact!r}. Either it is unused, or `fact_usage` was never "
              f"filled for this run; both mean there is nothing to regenerate "
              f"and nothing to guess.", file=sys.stderr)
        return 1

    parent = versions_repo.published(conn, run_id)
    if not parent:
        print(f"change: REFUSED — {args.slug} has no published version to "
              f"change. Publish v1 first.", file=sys.stderr)
        return 1
    parent_n = parent[-1]["n"]

    n = versions_repo.next_number(conn, run_id, run_dir / "dist")
    workspace = run_dir / "dist" / f"v{n}"
    workspace.mkdir(parents=True, exist_ok=False)

    verdicts = regenerate(run_dir, workspace, chapters, args.fact, args.to)
    refused = sorted(c for c, accepted in verdicts.items() if not accepted)
    if refused or set(chapters) - set(verdicts):
        # The accepted gap, behaving as the spec says it will. Nothing is
        # published: the reader keeps the novel they have.
        print(json.dumps({
            "slug": args.slug, "fact": args.fact, "chapters": list(chapters),
            "halted": "gate", "refused": refused,
            "unjudged": sorted(set(chapters) - set(verdicts)),
            "published": False, "workspace": str(workspace),
            "note": f"v{parent_n} is untouched",
        }, indent=2))
        print(f"change: halted: gate — chapters {refused or 'missing'} did not "
              f"pass; v{parent_n} stands", file=sys.stderr)
        return 1

    change = Change(fact_id=args.fact, to=args.to, chapters=chapters,
                    parent=parent_n)
    published = pdf.publish(conn, run_dir, run_id,
                            reason=f"reader change to fact {args.fact}",
                            change=change, chapters_from=workspace, n=n)
    print(json.dumps({
        "slug": args.slug, "fact": args.fact, "chapters": list(chapters),
        "version": published, "parent": parent_n,
        "html": str(run_dir / "dist" / f"v{published}" / "novel.html"),
        "published": True,
    }, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
