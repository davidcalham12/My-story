"""The mechanical prose check, as a script the orchestrator runs. SPEC-005.

    python -m backend.chapters.check_prose \n      output/<slug>/chapters/ch01.md [output/<slug>/bible/characters.md]

With the Bible's character file as a second argument it also checks canonical
names — a name one letter from one the Bible declares.

Prints a JSON report and **exits 1 when it finds something**, like every other
check here. That is not gating: nothing in the pipeline stops on it, and the
combined `backend.checks` run reports which checks failed by name. An exit code
that is always 0 makes a finding invisible to anything that aggregates — which is
how a duplicated sentence reached an assembled book while the check that could
see it reported success.

**It reports; it does not gate.** The five characteristics are fixed by `AGENTS.md` §6 and a
sixth is not added by a script quietly acquiring a veto.

What the orchestrator does with a defect is FLOW-4's business: a duplicated
sentence is a literal substitution like any other finding, and it belongs in the
sheet with its quote, which is exactly the shape redraft rule 2 needs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.chapters.names import check as check_names
from backend.chapters.prose import report


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <chapter.md> [characters.md]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        # A missing file is not a clean chapter. Answering "clean" here would be
        # the absent-read-as-zero mistake in its most expensive form.
        print(f"check_prose: no such file: {path}", file=sys.stderr)
        return 2
    draft = path.read_text(encoding="utf-8")
    result = report(draft)

    if len(argv) == 3:
        bible = Path(argv[2])
        if not bible.is_file():
            print(f"check_prose: no such file: {bible}", file=sys.stderr)
            return 2
        suspects = check_names(draft, bible.read_text(encoding="utf-8"))
        result["defects"].extend({
            "kind": "name-one-letter-out", "quote": s.written, "claim": str(s),
        } for s in suspects)
        result["checked"].append("name-one-letter-out")
        if suspects:
            result["verdict"] = "defects"
    else:
        # Not checked is not clean. Without the Bible there is nothing to compare
        # a name against, and the report says so rather than staying quiet.
        result["not_checked"].append(
            "canonical names — no characters.md was given to compare against")

    print(json.dumps(result, indent=2))
    if result["defects"]:
        print(f"check_prose: {len(result['defects'])} defect(s) in {path.name}. "
              f"Each is quoted; put them in the sheet.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
