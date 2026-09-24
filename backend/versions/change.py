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
    import shutil as _shutil

    from backend.commons.config.settings import load_settings as _settings
    from backend.commons.db.connection import connect
    from backend.commons.runner.process import RunProcess
    from backend.publish import personalise
    from backend.runs.conductor import Unit, prompt_for

    settings = _settings()
    conn = connect(settings.db_path)
    fact = conn.execute("SELECT text FROM facts WHERE id = ?", (fact_id,)).fetchone()
    old = fact[0] if fact else ""
    run = conn.execute("SELECT brief_id FROM runs WHERE slug = ?", (run_dir.name,)).fetchone()
    alias = personalise.alias_for(conn, run[0] if run else None)
    prepare_workspace(run_dir, workspace, chapters, old=old, to=to)

    verdicts: dict[int, bool] = {}
    for n in chapters:
        prompt = (prompt_for(Unit("chapter", n), slug=run_dir.name, run_dir=workspace)
                  + f"\nReader change: wherever the Bible or the outline once said "
                    f"{(old or fact_id)!r}, it now says {to!r}. "
                    f"Write the chapter so it holds.\n")
        # NOVAFORGE_CHANGE_PROCEDURE_REV: run the change on the procedure the
        # book was written with, not the current one (owner, 2026-09-24).
        import os as _os
        if _os.environ.get("NOVAFORGE_CHANGE_PROCEDURE_REV"):
            prompt = pin_procedure(workspace, _os.environ["NOVAFORGE_CHANGE_PROCEDURE_REV"],
                                   prompt)
        process = RunProcess.for_prompt(prompt=prompt, cwd=settings.repo_root,
                                        max_budget_usd=15.0)
        process.start()
        for _ in process.lines():
            pass
        promoted = workspace / "chapters" / f"ch{n:02d}.md"
        verdicts[n] = promoted.is_file()
        if promoted.is_file() and alias:
            # The same mechanical step as v1 (owner's decision B): the model
            # wrote the token, code puts the alias in its place.
            _shutil.copyfile(promoted, promoted.with_name(f"ch{n:02d}.anon.md"))
            text = promoted.read_text(encoding="utf-8")
            promoted.write_text(text.replace(personalise.TOKEN, alias),
                                encoding="utf-8", newline="\n")
    return verdicts


PROCEDURE = ".claude/skills/storymaker/units/chapter.md"
SKILL = ".claude/skills/storymaker/SKILL.md"


def pin_procedure(workspace: Path, rev: str, prompt: str) -> str:
    """Write the chapter procedure and the skill of revision `rev` into
    `<workspace>/procedure/`, and point the prompt at those copies."""
    import subprocess

    from backend.commons.config.settings import load_settings as _settings

    root = _settings().repo_root
    target = workspace / "procedure"
    target.mkdir(parents=True, exist_ok=True)

    def show(path: str) -> str:
        return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=root, check=True,
                              capture_output=True, text=True, encoding="utf-8").stdout

    (target / "SKILL.md").write_text(show(SKILL), encoding="utf-8", newline="\n")
    (target / "chapter.md").write_text(
        show(PROCEDURE).replace(SKILL, str(target / "SKILL.md")),
        encoding="utf-8", newline="\n")
    return prompt.replace(PROCEDURE, str(target / "chapter.md"))


def prepare_workspace(run_dir: Path, workspace: Path, chapters: tuple[int, ...],
                      *, old: str, to: str) -> None:
    """What the chapter unit rewrites from: the anonymised Bible and outline with
    the fact changed, the config, the state and the summaries before each named
    chapter. Never v1's prose — the writer is never given an earlier chapter's
    prose, and a rewrite is no exception."""
    import shutil as _shutil

    def anon(path: Path) -> Path:
        twin = path.with_name(f"{path.stem}.anon{path.suffix}")
        return twin if twin.is_file() else path

    def changed(path: Path) -> str:
        body = anon(path).read_text(encoding="utf-8")
        return body.replace(old, to) if old else body

    (workspace / "bible").mkdir(parents=True, exist_ok=True)
    for sub in ("chapters", "critiques", "logs"):
        (workspace / sub).mkdir(exist_ok=True)
    for src in sorted((run_dir / "bible").glob("*.md")):
        if not src.stem.endswith(".anon"):
            (workspace / "bible" / src.name).write_text(
                changed(src), encoding="utf-8", newline="\n")
    if (run_dir / "outline.md").is_file():
        (workspace / "outline.md").write_text(
            changed(run_dir / "outline.md"), encoding="utf-8", newline="\n")
    for name in ("config.snapshot.json", "state.json"):
        if (run_dir / name).is_file():
            _shutil.copyfile(run_dir / name, workspace / name)
    for n in chapters:
        summary = run_dir / "chapters" / f"ch{n - 1:02d}.summary.md"
        if summary.is_file():
            _shutil.copyfile(summary, workspace / "chapters" / summary.name)


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
