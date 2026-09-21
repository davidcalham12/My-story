"""Assembling the manuscript. In code, never by an agent."""

from __future__ import annotations


def assemble(synopsis: str, chapters: list[str], *, include_synopsis: bool = True) -> str:
    """Concatenation.

    Deliberately not a model call. Asked to join approved chapters, a model
    rewrote a sentence in the middle of text the gate had already passed -
    mechanical transformations belong in code, always.
    """
    parts = []
    if include_synopsis and synopsis.strip():
        parts.append(synopsis.strip())
    parts.extend(c.strip() for c in chapters if c.strip())
    return "\n\n".join(parts) + "\n"


def word_count(book: str) -> int:
    return len(book.split())
