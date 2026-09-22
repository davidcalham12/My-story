"""Is this run sound? One command, for a person.

    python -m backend.report output/<slug>

Fourteen instruments now exist and a day was spent finding what each one is for.
**A person should not have to remember any of them to ask whether a run is
sound**, and until now the answer lived in six separate invocations and a
database query — which is to say, with whoever ran them.

This gathers them. It reads only what is on disk and in the archive, so it costs
nothing and can be run on a novel from months ago.

**It answers three questions in order of how much they matter:**

1. **Did the gate hold?** A chapter promoted below the threshold is the one
   outcome the system exists to prevent, and one run did it.
2. **What did it cost?** Measured from Claude Code's own `result`, or absent —
   never zero.
3. **What is unchecked?** The section that stops the rest from reading as a
   clean bill of health. A run with no archive is *unchecked*, which is not the
   same as sound, and this says so first.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from backend.chapters.check_promises import promises
from backend.chapters.check_rules import declared_rules
from backend.chapters.check_summary import cap_for
from backend.chapters.prose import find as prose_defects
from backend.runs import conformance


def _chapters(run_dir: Path) -> list[int]:
    return sorted(int(p.stem[2:4]) for p in (run_dir / "chapters").glob("ch[0-9][0-9].md"))


def _cost(run_dir: Path) -> dict:
    path = run_dir / "cost.json"
    if not path.is_file():
        # Absent, never zero. A run that reported no total and a free run are
        # different facts.
        return {"total_usd": None, "provenance": "absent",
                "why": "no cost.json: the run reported no total"}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {"total_usd": raw.get("total_cost_usd"),
            "provenance": raw.get("provenance", "measured"),
            "turns": raw.get("turns"),
            "duration_ms": raw.get("duration_ms")}


def _gate(db: Path | None, slug: str) -> dict:
    if db is None or not db.is_file():
        return {"verdict": "unchecked",
                "why": "no database given, so nothing recomputed the gate"}
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id FROM runs WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        return {"verdict": "unchecked",
                "why": f"{slug} is not in the archive; it was never archived"}
    return conformance.summary(conn, row["id"])


def build(run_dir: Path, db: Path | None = None) -> dict:
    chapters = _chapters(run_dir)
    world = run_dir / "bible/world.md"
    mysteries = run_dir / "bible/mysteries.md"

    defects = []
    for n in chapters:
        for d in prose_defects((run_dir / "chapters" / f"ch{n:02d}.md")
                               .read_text(encoding="utf-8")):
            defects.append(f"ch{n:02d}: {d}")

    cap = cap_for(run_dir)
    summaries = []
    for path in sorted((run_dir / "chapters").glob("ch*.summary.md")):
        words = len(path.read_text(encoding="utf-8").split())
        summaries.append({"summary": path.name, "words": words,
                          "over_cap": bool(cap and words > cap)})

    stated = promises(mysteries.read_text(encoding="utf-8")) if mysteries.is_file() else []
    unreachable = [p["question"] for p in stated
                   if p["lands"] and chapters and p["lands"] > max(chapters)]

    return {
        "slug": run_dir.name,
        "chapters_in_the_book": chapters,
        "gate": _gate(db, run_dir.name),
        "cost": _cost(run_dir),
        "prose_defects": defects,
        "summaries": {"cap": cap, "over": sum(1 for s in summaries if s["over_cap"]),
                      "of": len(summaries)},
        "promises": {
            "stated": len(stated),
            "naming_chapters": sum(1 for p in stated if p["planted"] and p["lands"]),
            "landing_past_the_last_chapter": unreachable,
        },
        "rules_numbered": bool(world.is_file()
                               and declared_rules(world.read_text(encoding="utf-8"))),
        "unchecked": [
            "whether the prose is any good — no characteristic reads it, and the "
            "mechanical check finds three defect kinds out of everything a reader "
            "would notice",
            "whether a promise that names a chapter is actually paid in it",
            "whether the book is worth reading",
        ],
    }


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <run_dir> [novaforge.db]", file=sys.stderr)
        return 2
    run_dir = Path(argv[1])
    if not (run_dir / "chapters").is_dir():
        print(f"report: {run_dir} does not look like a run", file=sys.stderr)
        return 2

    db = Path(argv[2]) if len(argv) == 3 else Path("novaforge.db")
    out = build(run_dir, db if db.is_file() else None)
    print(json.dumps(out, indent=2))

    # Non-zero on the one thing that matters. A run whose gate was not checked
    # exits 0 with `unchecked` on the screen: it has not failed, and it has not
    # passed either, and an exit code cannot say the second without lying.
    return 1 if out["gate"].get("verdict") == "breached" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
