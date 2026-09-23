"""The policy hook: forbidden words, and the audit row that says it ran.

    python .claude/hooks/policy.py output/<slug>/chapters/ch01.md

Wired in `.claude/settings.json` as a `PostToolUse` matcher on `Write` under
`output/*/chapters/`, where it is handed the event as JSON on stdin instead of
an argument. Both forms work, and the argument form is the one the tests use:
a hook nobody can run by hand is a hook nobody debugs.

**Prints JSON and exits 1 when it finds something**, like `check_prose` and
every other instrument here. Deliberately **not** exit 2, which is Claude Code's
"block this tool call and show the model the error": a forbidden term is not a
crash and does not stop the write. It comes back to the writer as a finding of
the `forbidden_words` validator through the ordinary feedback sheet, gets three
attempts like everything else, and only exhausting them ends the run as
`halted: policy`. A hook that blocked the write would leave the orchestrator
holding a draft it cannot see and no sheet to send.

**Every check writes an `audit_log` row, hit or not.** Silence would otherwise
mean both "the guardrail found nothing" and "the guardrail never ran".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.commons.config.settings import load_settings   # noqa: E402
from backend.commons.db.connection import connect           # noqa: E402
from backend.commons.db.migrate import migrate              # noqa: E402
from backend.policy import audit, forbidden                 # noqa: E402

ACTOR = "policy-hook"


def chapter_from_stdin() -> Path | None:
    """The `PostToolUse` event, which arrives as JSON on stdin.

    Defensive about its shape on purpose: a hook that raises inside Claude Code
    produces a traceback in a place nobody is reading, and the honest answer to
    "I was handed something I do not understand" is exit 2 — not a clean report.
    """
    try:
        event = json.loads(sys.stdin.read() or "{}")
        path = event.get("tool_input", {}).get("file_path")
    except (ValueError, AttributeError):
        return None
    return Path(path) if path else None


def slug_of(chapter: Path) -> str:
    """`output/<slug>/chapters/chNN.md` → `<slug>`."""
    return chapter.resolve().parent.parent.name


def is_a_chapter(path: Path) -> bool:
    """`<anything>/output/<slug>/chapters/<file>`, and nothing else.

    `.claude/settings.json` matches the **tool**, `Write`, because that is all a
    `PostToolUse` matcher can match. "Under `output/*/chapters/`" is therefore a
    condition this script applies, not one the harness applies for it — without
    it every `Write` in the session runs the guardrail over a file that is not
    prose and files an `audit_log` row against a run that does not exist.
    """
    parts = path.resolve().parts
    return len(parts) >= 4 and parts[-2] == "chapters" and parts[-4] == "output"


def run_id_for(conn, slug: str) -> str:
    """The run's id when this database has one, the slug when it does not.

    The hook fires while the run is being driven and the archive may not have
    written the row yet. An audit entry keyed by the slug is still an audit
    entry; refusing to write one because the join failed is not.
    """
    row = conn.execute("SELECT id FROM runs WHERE slug = ?", (slug,)).fetchone()
    return row["id"] if row else slug


def main(argv: list[str]) -> int:
    # The accents are the subject of this phase, so stdout says its encoding
    # rather than inheriting cp1252 from a Windows console.
    sys.stdout.reconfigure(encoding="utf-8")

    if len(argv) == 2:
        chapter = Path(argv[1])
    elif len(argv) == 1:
        chapter = chapter_from_stdin()
    else:
        print(f"usage: {argv[0]} <chapter.md>", file=sys.stderr)
        return 2

    if chapter is None:
        print("policy: no file_path in the hook event and none on the command "
              "line", file=sys.stderr)
        return 2
    if not chapter.is_file():
        # A missing file is not a clean chapter.
        print(f"policy: no such file: {chapter}", file=sys.stderr)
        return 2

    if not is_a_chapter(chapter):
        print(json.dumps({"hook": "policy", "validator": "forbidden_words",
                          "file": str(chapter), "verdict": "skipped",
                          "why": "not under output/<slug>/chapters/"}, indent=2))
        return 0

    slug = slug_of(chapter)
    text = chapter.read_text(encoding="utf-8")

    conn = connect(load_settings().db_path)
    try:
        # A hook may be the first thing to touch a fresh database — the global
        # seed lives in a migration, so an unmigrated database is a guardrail
        # with no terms, which reports clean on everything.
        migrate(conn)
        hits = forbidden.check(text, forbidden.terms(conn))
        run_id = run_id_for(conn, slug)
        audit.record(conn, run_id=run_id, actor=ACTOR,
                     decision="hit" if hits else "clean",
                     detail=json.dumps({"chapter": chapter.name,
                                        "hits": [h.as_dict() for h in hits]},
                                       ensure_ascii=False))
    finally:
        conn.close()

    print(json.dumps({
        "hook": "policy",
        "validator": "forbidden_words",
        "run": slug,
        "file": str(chapter),
        "verdict": "hit" if hits else "clean",
        "hits": [h.as_dict() for h in hits],
        "audit_log": "written",
    }, indent=2, ensure_ascii=False))

    if hits:
        print(f"policy: {len(hits)} forbidden term(s) in {chapter.name}. Each is "
              f"quoted; put them in the sheet as findings of forbidden_words.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
