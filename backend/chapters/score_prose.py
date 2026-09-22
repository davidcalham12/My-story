"""`prose`, scored by a script rather than by the orchestrator. SPEC-006.

    echo '{"major": 2, "minor": 3}' \
      | python -m backend.chapters.score_prose <chapter.md> [characters.md]

SPEC-006 left the orchestrator holding one piece of arithmetic: run the
mechanical check, read its count, take the critic's two counts, and work out
`10 − 3·mechanical − 2·major − 1·minor`. That is three numbers copied by hand
into a formula, at the moment a chapter's fate is being decided.

**`AGENTS.md` §5: if a script will do, it is a script.** This one does both
halves — it runs the mechanical check itself, so the count cannot be
miscopied, and it applies the formula, so the formula cannot be misremembered.
The orchestrator supplies only what it alone knows: how many findings the critic
raised **and quoted**.

It returns the mechanical defects alongside the score, because the writer needs
them quoted in the sheet and a score with no findings behind it is a number
nobody can act on.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.chapters.domain import score_prose
from backend.chapters.names import check as check_names
from backend.chapters.prose import find


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <chapter.md> [characters.md]  (counts on stdin)",
              file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.is_file():
        print(f"score_prose: no such file: {path}", file=sys.stderr)
        return 2

    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("expected a JSON object")
        major = int(payload.get("major", 0))
        minor = int(payload.get("minor", 0))
    except (ValueError, TypeError) as exc:
        # A scoring script that guesses when it cannot read its input produces a
        # number nothing stands behind, and the orchestrator would use it.
        print(f'score_prose: cannot read the counts ({exc}). Expected '
              f'{{"major": <int>, "minor": <int>}} on stdin', file=sys.stderr)
        return 2
    if major < 0 or minor < 0:
        print("score_prose: counts cannot be negative", file=sys.stderr)
        return 2

    draft = path.read_text(encoding="utf-8")
    defects = [{"kind": d.kind, "quote": d.quote, "claim": d.claim}
               for d in find(draft)]

    if len(argv) == 3:
        bible = Path(argv[2])
        if not bible.is_file():
            print(f"score_prose: no such file: {bible}", file=sys.stderr)
            return 2
        defects.extend({"kind": "name-one-letter-out", "quote": s.written,
                        "claim": str(s)}
                       for s in check_names(draft, bible.read_text(encoding="utf-8")))

    mechanical = len(defects)
    score = score_prose(mechanical=mechanical, major=major, minor=minor)

    print(json.dumps({
        "characteristic": "prose",
        "score": score,
        "mechanical": mechanical,
        "major": major,
        "minor": minor,
        "why": f"10 − 3×{mechanical} − 2×{major} − 1×{minor} = {score}"
               + (" (floored at 0)" if 10 - 3 * mechanical - 2 * major - minor < 0
                  else ""),
        # Quoted, because the writer is told to change only what was quoted and
        # these count against the chapter like any other finding.
        "mechanical_defects": defects,
        "not_checked": [
            "whether a fact stated here contradicts one stated elsewhere",
            "anything the critic did not raise and quote",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
