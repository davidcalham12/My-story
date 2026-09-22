"""Promoting a chapter into the book — by a script that can refuse.

    python -m backend.chapters.promote output/<slug> 3

`verification.md` §3.1 said the gate's obedience was a procedure with no earlier
signal than reading the book. The conformance audit gave it a signal; **this is
the next step, which is making the correct path the easy one.**

On the eight-chapter run, chapter 3 scored `continuity` 5 and was copied to
`ch03.md` anyway — no third attempt, no patch, no halt. Writing that file was a
one-line copy, and nothing stood between the copy and the book.

Now something does. This reads the chapter's own critique files, computes the
aggregate the way the gate computes it, asks `decide`, and **writes
`chNN.md` only on `accept`**. Anything else prints the refusal and exits non-zero
with the file untouched.

**What this is not.** It is not a guarantee: the orchestrator holds `Write` and
always will, because it writes every other file in the run. A determined or
careless orchestrator can still copy a draft by hand, and `conformance.audit`
exists for exactly that. What this removes is the *easy* way to do it — the
version where nothing says no.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from backend.chapters.domain import CHARACTERISTICS, decide


def _scores(run_dir: Path, chapter: int, attempt: int) -> tuple[dict, tuple[str, ...]]:
    """This attempt's scores, and the gate this run actually ran.

    A characteristic with a critique file and no usable verdict is `None` — a
    gate one critic short. One with no file at all is not in the gate: it did not
    exist for this run. Those are opposite facts and only the file tells them
    apart.
    """
    scores: dict[str, int | None] = {}
    gate: list[str] = []
    for characteristic in CHARACTERISTICS:
        path = run_dir / "critiques" / f"ch{chapter:02d}.{characteristic}.json"
        if not path.is_file():
            continue
        gate.append(characteristic)
        raw = json.loads(path.read_text(encoding="utf-8"))
        scores[characteristic] = None
        for iteration in raw.get("iterations") or []:
            if isinstance(iteration, dict) and int(iteration.get("iteration") or 0) == attempt:
                value = iteration.get("score")
                scores[characteristic] = (int(value)
                                          if isinstance(value, (int, float)) else None)
    return scores, tuple(gate)


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(f"usage: {argv[0]} <run_dir> <chapter> [attempt]", file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    chapter = int(argv[2])
    drafts = sorted(int(p.stem.split("attempt")[1])
                    for p in (run_dir / "chapters").glob(f"ch{chapter:02d}.attempt*.md"))
    if not drafts:
        print(f"promote: no drafts for chapter {chapter}", file=sys.stderr)
        return 2
    attempt = int(argv[3]) if len(argv) == 4 else drafts[-1]

    scores, gate = _scores(run_dir, chapter, attempt)
    if not gate:
        # No critique files at all. Promoting here would put a chapter in the
        # book that nothing judged, which is worse than one that failed.
        print(f"promote: REFUSED — chapter {chapter} has no critiques; nothing "
              f"has judged this draft", file=sys.stderr)
        return 1

    usable = [s for s in scores.values() if s is not None]
    aggregate = min(usable) if usable else None
    complete = len(usable) == len(gate)
    decision = decide(aggregate=aggregate if complete else None, attempt=attempt)

    report = {
        "chapter": chapter, "attempt": attempt, "scores": scores,
        "gate": list(gate), "aggregate": aggregate,
        "action": decision.action, "why": decision.why,
    }

    if decision.action != "accept":
        print(json.dumps({**report, "promoted": False}, indent=2))
        print(f"promote: REFUSED — {decision.why}", file=sys.stderr)
        return 1

    source = run_dir / "chapters" / f"ch{chapter:02d}.attempt{attempt}.md"
    shutil.copyfile(source, run_dir / "chapters" / f"ch{chapter:02d}.md")
    print(json.dumps({**report, "promoted": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
