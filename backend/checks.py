"""Every check a stage owes, in one command.

    python -m backend.checks FLOW-3 output/<slug>
    python -m backend.checks FLOW-4 output/<slug> 4

Seven instruments now stand between a run and a defect, each with its own
invocation, each remembered at its own moment. **Remembering is what has failed
here, repeatedly** — a chapter promoted at 5, a cap exceeded five times, a
verdict written in a vocabulary the database rejects. Every one of those was a
step nobody forgot on purpose.

So the orchestrator remembers one thing per stage instead of seven, and *this*
file is where the mapping lives. Adding a check means adding it here, which is
also the only way it becomes something the procedure cannot skip by accident.

**It never blocks.** It reports, per check, with the exit code saying whether
anything failed — because the decisions belong to `decide` and `promote`, which
are called at their own moments and can refuse. A checker that also gated would
be a second place the gate lives, and this repository has spent a day on what
that costs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

#: stage -> the checks it owes, as argv tails. `{chapter}` is filled in.
BY_STAGE: dict[str, list[tuple[str, list[str]]]] = {
    # The Bible exists. Before anything cites a rule or promises an answer.
    "FLOW-2": [
        ("rules resolve", ["backend.chapters.check_rules", "{run}"]),
        ("promises name chapters", ["backend.chapters.check_promises", "{run}"]),
    ],
    # The outline exists and the audit is about to read it.
    "FLOW-3": [
        ("rules resolve", ["backend.chapters.check_rules", "{run}"]),
        ("promises are reachable", ["backend.chapters.check_promises", "{run}"]),
    ],
    # A chapter has been written and summarised.
    "FLOW-4": [
        ("prose defects", ["backend.chapters.check_prose",
                           "{run}/chapters/ch{chapter:02d}.md",
                           "{run}/bible/characters.md"]),
        ("summary within its cap", ["backend.chapters.check_summary",
                                    "{run}", "{chapter}"]),
        ("promises still reachable", ["backend.chapters.check_promises", "{run}"]),
    ],
    # The book is about to be assembled.
    # The book, not a chapter. Everything above reads one chapter at a time, and
    # a sentence repeated in chapters 2 and 7 is invisible to every one of them.
    # One shipped: the Bible quoted a character's line verbatim as a sample of
    # how he speaks, and two chapters five apart used it word for word.
    "FLOW-6": [
        ("the assembled book repeats nothing",
         ["backend.chapters.check_prose", "{run}/dist/book.md"]),
        ("every promise landed in a chapter that exists",
         ["backend.chapters.check_promises", "{run}"]),
        ("summaries within their cap", ["backend.chapters.check_summary", "{run}"]),
        # SPEC-007 §8 point 2: every call has a timestamp, and the log says
        # which were measured and which derived. Reported, never refused.
        ("call log timestamps parse, in order, with their provenance",
         ["backend.chapters.check_log", "{run}"]),
    ],
}


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(f"usage: {argv[0]} <stage> <run_dir> [chapter]", file=sys.stderr)
        print(f"stages: {', '.join(sorted(BY_STAGE))}", file=sys.stderr)
        return 2

    stage, run_dir = argv[1], argv[2]
    chapter = int(argv[3]) if len(argv) == 4 else None

    if stage not in BY_STAGE:
        # Not "nothing to do". An unknown stage means the caller believes in a
        # check that does not exist, and answering "all clear" would confirm it.
        print(f"checks: no checks registered for {stage!r}. "
              f"Known: {', '.join(sorted(BY_STAGE))}", file=sys.stderr)
        return 2

    wanted = BY_STAGE[stage]
    if chapter is None and any("{chapter" in part
                               for _, parts in wanted for part in parts):
        print(f"checks: {stage} needs a chapter number", file=sys.stderr)
        return 2

    results = []
    worst = 0
    for name, parts in wanted:
        args = [p.format(run=run_dir, chapter=chapter) for p in parts]
        proc = subprocess.run([sys.executable, "-m", *args],
                              capture_output=True, text=True)
        try:
            detail = json.loads(proc.stdout) if proc.stdout.strip() else None
        except json.JSONDecodeError:
            detail = None
        results.append({
            "check": name,
            "ok": proc.returncode == 0,
            "exit": proc.returncode,
            "detail": detail,
            "stderr": proc.stderr.strip() or None,
        })
        worst = max(worst, proc.returncode)

    failed = [r["check"] for r in results if not r["ok"]]
    print(json.dumps({
        "stage": stage,
        "chapter": chapter,
        "ran": [r["check"] for r in results],
        "failed": failed,
        "results": results,
        "note": "this reports; it does not gate. `decide` and `promote` are the "
                "only things that refuse, and they are called at their own "
                "moments.",
    }, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
