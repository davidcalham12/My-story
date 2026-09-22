"""The mechanical prose check, as a script the orchestrator runs. SPEC-005.

    python -m backend.chapters.check_prose output/<slug>/chapters/ch01.md

Prints a JSON report and exits 0 whether or not it found anything. **It reports;
it does not gate.** The five characteristics are fixed by `AGENTS.md` §6 and a
sixth is not added by a script quietly acquiring a veto.

What the orchestrator does with a defect is FLOW-4's business: a duplicated
sentence is a literal substitution like any other finding, and it belongs in the
sheet with its quote, which is exactly the shape redraft rule 2 needs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.chapters.prose import report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <chapter.md>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        # A missing file is not a clean chapter. Answering "clean" here would be
        # the absent-read-as-zero mistake in its most expensive form.
        print(f"check_prose: no such file: {path}", file=sys.stderr)
        return 2
    print(json.dumps(report(path.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
