"""A book's title, from what the pipeline wrote — never the slug as it stands.

Shared by the publisher (the PDF's cover) and the runs list (the panel), so
the reader and the buyer see one title. Standard library only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_SMALL = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")
_OUTLINE = re.compile(r"^\s*(?:Outline\s*[—–-]\s*)?(.+?)(?:\s*[—–-]\s*Outline)?\s*$", re.I)


def humanise(slug: str) -> str:
    """`the-other-side-of-the-hill` → `The Other Side of the Hill`."""
    words = [w for w in re.split(r"[-_\s]+", slug) if w]
    return " ".join(w if (i and w in _SMALL) else w[:1].upper() + w[1:]
                    for i, w in enumerate(words))


def _heading(path: Path) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def title_of(run_dir: Path) -> str:
    book = _heading(run_dir / "dist" / "book.md")
    if book:
        return book
    state = run_dir / "state.json"
    slug = run_dir.name
    if state.is_file():
        data = json.loads(state.read_text(encoding="utf-8"))
        if data.get("title"):
            return str(data["title"])
        slug = str(data.get("slug") or slug)
    outline = _heading(run_dir / "outline.md")
    if outline:
        match = _OUTLINE.match(outline)
        name = match.group(1).strip() if match else outline
        # An outline headed with a slug has named nothing.
        if name and not _SLUG.fullmatch(name):
            return name
    return humanise(slug)
