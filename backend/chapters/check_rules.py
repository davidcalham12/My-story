"""Do the rules a run cites exist? SPEC-005's pattern, applied to canon.

    python -m backend.chapters.check_rules output/<slug>

The critics and the outline audit refer to a world's rules **by number** — *"R5
rewritten to name the keeper as the writer"*, *"R1 says only the keeper on watch
may write in the Register"*. `bible/world.md` wrote them as unnumbered bullets,
so those numbers were **the critic counting bullets and inventing an
identifier**.

Two real runs produced **76 such references and not one of them resolved to
anything.** A positional reference into an unnumbered list points at a different
rule the moment one is inserted or reordered, and two critics can number the same
list differently — so the arbitration record decays, silently, and nothing it
claims can be checked against the Bible.

`worldbuilder` now writes `- **R1.** ...`. This checks the citations against what
was actually declared.

**A Bible with no numbers at all reports `unnumbered`, not `clean`.** It predates
the change; nothing can be checked, and saying "no dangling references" about a
file with no references to resolve is the absent-read-as-clean mistake.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

#: `- **R1.** ...` or `**R1**` anywhere a rule declares itself.
DECLARED = re.compile(r"\*\*(R\d+)\.?\*\*")
CITED = re.compile(r"\b(R\d+)\b")


def declared_rules(world_md: str) -> set[str]:
    start = world_md.find("## Rules")
    if start == -1:
        return set()
    end = world_md.find("\n## ", start + 1)
    return set(DECLARED.findall(world_md[start:end if end != -1 else len(world_md)]))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <run_dir>", file=sys.stderr)
        return 2

    run_dir = Path(argv[1])
    world = run_dir / "bible/world.md"
    if not world.is_file():
        print(f"check_rules: no {world}", file=sys.stderr)
        return 2

    declared = declared_rules(world.read_text(encoding="utf-8"))

    citations: dict[str, list[str]] = {}
    for path in sorted(list(run_dir.glob("*.md")) + list(run_dir.glob("critiques/*.json"))):
        for rule in sorted(set(CITED.findall(path.read_text(encoding="utf-8",
                                                            errors="ignore")))):
            citations.setdefault(rule, []).append(path.name)

    if not declared:
        print(json.dumps({
            "status": "unnumbered",
            "declared": [],
            "cited": sorted(citations),
            "why": "bible/world.md declares no numbered rules, so the "
                   f"{sum(len(v) for v in citations.values())} citations in this "
                   "run resolve to nothing. This is not 'no dangling references' "
                   "— it is a reference system that was never there.",
        }, indent=2))
        return 1 if citations else 0

    dangling = {r: files for r, files in citations.items() if r not in declared}
    unused = sorted(declared - set(citations))

    print(json.dumps({
        "status": "dangling" if dangling else "clean",
        "declared": sorted(declared),
        "cited": sorted(citations),
        "dangling": dangling,
        # Not a defect. A rule nothing cited was simply never at issue.
        "declared_but_never_cited": unused,
    }, indent=2))

    if dangling:
        print(f"check_rules: {len(dangling)} rule(s) cited and never declared: "
              f"{', '.join(sorted(dangling))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
