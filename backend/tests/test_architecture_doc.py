"""`architecture.md` is the map of the codebase, and maps go stale silently.

Its `commons/` tree named `llm/`, `context/` and `budget/` — the D2 design, none
of which survived Annex C and none of which exists. A map that no longer matches
the code is worse than no map: it sends a reader looking for a module, and when
they do not find it they stop trusting the rest of the document too.

**A**, not T. It reads the document as text and compares it against the
filesystem. It cannot tell whether the prose is right; it can tell whether the
directories it names are there.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")

#: A line inside a fenced tree: `├── runner/    launches ...`
TREE_ENTRY = re.compile(r"^[│├└─\s]*([a-z_]+)/\s{2,}", re.M)


def commons_tree() -> set[str]:
    start = DOC.index("```\ncommons/")
    end = DOC.index("```", start + 4)
    return set(TREE_ENTRY.findall(DOC[start:end]))


def test_the_tree_is_readable_at_all():
    assert len(commons_tree()) >= 4, commons_tree()


def test_every_directory_the_tree_names_exists():
    for name in sorted(commons_tree()):
        assert (ROOT / "backend/commons" / name).is_dir(), (
            f"architecture.md names commons/{name}/ and it is not there"
        )


def test_every_directory_that_exists_is_in_the_tree():
    """The other direction, which is how `runner/` went undocumented.

    A module nobody wrote down is a module nobody knows to look in — and
    `runner/` is the one that launches Claude Code.
    """
    real = {p.name for p in (ROOT / "backend/commons").iterdir()
            if p.is_dir() and not p.name.startswith(("_", "."))}
    assert real == commons_tree(), (
        f"undocumented: {sorted(real - commons_tree())}; "
        f"documented and absent: {sorted(commons_tree() - real)}"
    )


def test_the_removed_modules_are_not_described_as_present():
    """`llm/`, `context/` and `budget/` may be named in the paragraph explaining
    that they are gone. They may not be back in the tree."""
    assert not ({"llm", "context", "budget"} & commons_tree())
