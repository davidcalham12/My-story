"""Promises made to the reader, and whether the book owes them anywhere.

    python -m backend.chapters.check_promises output/<slug>

`bible/mysteries.md` is the only part of the Story Bible that states a commitment
about **when**: each question says which chapter plants it and which chapter
lands it. A promise planted and never paid is the ontology's foreshadowing
failure, and it is **the one literary defect a script can reach** — but only
because the Bible names the chapters.

Of eleven runs, one wrote those lines. The other ten hold promises nothing can
check, in four different formats. `character-architect` now states the shape.

**What this cannot do**, and it is most of the question: it cannot tell whether
the landing actually happens in the prose. It reads a commitment and checks it is
coherent and reachable. A chapter that says nothing about a mystery it was
supposed to land will pass this and fail a reader — that is `continuity`'s
territory at best and a human's at worst.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

QUESTION = re.compile(r"^\s*-\s+\*\*(.+?)\*\*\s*$", re.M)
PLANTED = re.compile(r"Planted:\s*Chapter\s*(\d+)", re.I)
LANDS = re.compile(r"Lands?:\s*Chapter\s*(\d+)", re.I)


def promises(mysteries_md: str) -> list[dict]:
    """One entry per question, with the chapters it names, if any."""
    out = []
    starts = [m.start() for m in QUESTION.finditer(mysteries_md)]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(mysteries_md)
        block = mysteries_md[start:end]
        planted = PLANTED.search(block)
        lands = LANDS.search(block)
        out.append({
            "question": QUESTION.match(block.lstrip("\n")).group(1)
            if QUESTION.match(block.lstrip("\n")) else block.strip()[:80],
            "planted": int(planted.group(1)) if planted else None,
            "lands": int(lands.group(1)) if lands else None,
        })
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    path = run_dir / "bible/mysteries.md"
    if not path.is_file():
        print(f"check_promises: no {path}", file=sys.stderr)
        return 2

    found = promises(path.read_text(encoding="utf-8"))
    written = sorted(int(p.stem[2:4])
                     for p in (run_dir / "chapters").glob("ch[0-9][0-9].md"))
    planned = max(written) if written else 0

    unstated = [p for p in found if p["planted"] is None or p["lands"] is None]
    backwards = [p for p in found
                 if p["planted"] and p["lands"] and p["lands"] < p["planted"]]
    beyond = [p for p in found
              if p["lands"] and planned and p["lands"] > planned]
    unwritten = [p for p in found
                 if p["lands"] and written and p["lands"] not in written]

    problems = {
        "no chapters named": unstated,
        "lands before it is planted": backwards,
        "lands past the last chapter": beyond,
        "lands in a chapter the run never wrote": unwritten,
    }
    problems = {k: v for k, v in problems.items() if v}

    print(json.dumps({
        # Three states. A file whose promises name no chapters is not a book
        # that kept them — it is one where the question cannot be asked.
        "status": ("unstated" if unstated and len(unstated) == len(found)
                   else "problems" if problems else "coherent"),
        "promises": found,
        "chapters_written": written,
        "problems": {k: [p["question"] for p in v] for k, v in problems.items()},
        "not_checked": "whether the landing actually happens in the prose. This "
                       "reads a commitment; it does not read the chapter.",
    }, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
