"""The rolling summary against its cap — the one number the flat curve rests on.

    python -m backend.chapters.check_summary output/<slug> 4

**The project's central architectural claim is that chapter thirty-four's prompt
is the same size as chapter one's.** The Story Bible is fixed, the outline entry
is one chapter's, and the only part that could grow with the book is the rolling
summary. `context.max_summary_words` is what stops it, and **nothing was checking
it.**

Measured, on two real runs:

| profile | cap | summaries |
|---|---|---|
| `tiny` | 120 | 108, 116, **122** |
| `small` | 200 | 192, **204**, **211**, **246**, **220**, **222** |

Five of six over on the longer run, by 2% to 23%. **The cap was being read as a
target rather than a limit** — which is what a number nobody measures becomes.

It is an overshoot, not a runaway: the figures plateau around 220 rather than
climbing with the chapter count, so the flat curve holds with about a tenth of
one component's slack. That distinction matters and is why this reports rather
than truncates. **Truncating a summary silently is worse than a long one**: what
the cap protects is a budget, and what a dropped sentence loses is the only
channel between chapters.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def cap_for(run_dir: Path) -> int | None:
    """From the run's own snapshot, not from today's config.

    A run is judged by the numbers it ran with. Reading the live config would
    measure a finished run against a cap it never had.
    """
    snapshot = run_dir / "config.snapshot.json"
    if not snapshot.is_file():
        return None
    raw = json.loads(snapshot.read_text(encoding="utf-8"))
    value = (raw.get("context") or {}).get("max_summary_words")
    return int(value) if isinstance(value, (int, float)) else None


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <run_dir> [chapter]", file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    cap = cap_for(run_dir)
    if cap is None:
        # Absent, not unlimited. A missing cap must not read as permission.
        print("check_summary: the run's snapshot states no "
              "context.max_summary_words; nothing can be checked", file=sys.stderr)
        return 2

    if len(argv) == 3:
        paths = [run_dir / "chapters" / f"ch{int(argv[2]):02d}.summary.md"]
    else:
        paths = sorted((run_dir / "chapters").glob("ch*.summary.md"))
    paths = [p for p in paths if p.is_file()]
    if not paths:
        print("check_summary: no summaries to read", file=sys.stderr)
        return 2

    rows = []
    for path in paths:
        words = len(path.read_text(encoding="utf-8").split())
        rows.append({
            "summary": path.name,
            "words": words,
            "cap": cap,
            "over_by": max(0, words - cap),
            "within": words <= cap,
        })

    over = [r for r in rows if not r["within"]]
    print(json.dumps({
        "cap": cap,
        "summaries": rows,
        "over": len(over),
        "worst_overshoot_pct": (round(100 * max(r["over_by"] for r in over) / cap)
                                if over else 0),
        "why_it_matters": "the rolling summary is the only part of a chapter's "
                          "packet that can grow with the book; the flat cost "
                          "curve is this number holding",
    }, indent=2))

    if over:
        print(f"check_summary: {len(over)} of {len(rows)} over the {cap}-word cap. "
              f"Trim the NEXT summary; do not truncate one already written — a "
              f"dropped sentence loses the only channel between chapters.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
