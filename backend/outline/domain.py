"""Splitting the outline, and counting what a chapter was commissioned to do."""

from __future__ import annotations

import re

ENTRY = re.compile(r"^###\s+Chapter\s+\d+\s*[\u2014-]\s*(.+)$", re.M)


def split_entries(outline: str, expected: int) -> list[str]:
    """One entry per chapter.

    `### Chapter N - Title` exactly. Anything else - `**Chapter 1:**` most often -
    breaks the split, and a chapter writer handed nothing writes nothing. The
    orchestrator redispatches rather than drafting from an empty entry.
    """
    positions = [m.start() for m in ENTRY.finditer(outline)]
    if len(positions) != expected:
        raise ValueError(
            f"the outline split into {len(positions)} chapter entries, not "
            f'{expected}. The plot architect must use "### Chapter N - Title" exactly.'
        )
    bounds = positions + [len(outline)]
    return [outline[bounds[i]:bounds[i + 1]].strip() for i in range(expected)]


def titles(outline: str) -> list[str]:
    return [m.group(1).strip() for m in ENTRY.finditer(outline)]


def beats(entry: str) -> list[str]:
    """The numbered beats of one entry.

    Numbered, not bulleted: the outline critic scores them by number and reports
    "beat 3 does not happen". An unnumbered list gives it nothing to name, and a
    critic that cannot name what is missing cannot write the replacement the
    third attempt depends on.
    """
    out = []
    inside = False
    for line in entry.splitlines():
        if re.search(r"\*\*Beats:?\*\*", line):
            inside = True
            continue
        if inside:
            m = re.match(r"\s+(\d+)\.\s+(.*)", line)
            if m:
                out.append(m.group(2).strip())
            elif re.match(r"\s*-\s+\*\*", line):
                break
    return out
