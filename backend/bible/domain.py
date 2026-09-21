"""Checking the Bible before anything is written from it."""

from __future__ import annotations

import re


def count_words(text: str) -> int:
    return len(text.split())


def rules_bullets(world: str) -> list[str]:
    """The bullets under `## Rules`, and nowhere else.

    The world critic reads from under that heading alone, so a constraint written
    anywhere else is never enforced. Nothing downstream can recover a missing
    rules section, which is why FLOW-1 checks it before FLOW-2 begins.
    """
    match = re.search(r"^##\s*Rules\s*$(.*?)(?=^##\s|\Z)", world, re.M | re.S)
    if not match:
        return []
    return [ln.strip() for ln in match.group(1).splitlines() if re.match(r"\s*-\s+", ln)]


def check_world(world: str, *, min_words: int, max_words: int, min_rules: int) -> list[str]:
    """What is wrong with this world document, in plain words.

    An agent's report about itself is not evidence: one worldbuilder said it had
    written ~870 words and `wc -w` counted 948. So the orchestrator measures.
    """
    problems = []
    words = count_words(world)
    if not (min_words <= words <= max_words):
        problems.append(f"it is {words} words and the band is {min_words}-{max_words}")
    bullets = len(rules_bullets(world))
    if bullets < min_rules:
        problems.append(
            f'it has {bullets} bullets under "## Rules" and the minimum is {min_rules}'
        )
    return problems


def canonical_names(characters: str) -> tuple[str, ...]:
    """The names every later packet carries and the continuity critic checks."""
    return tuple(m.group(1) for m in re.finditer(r"^\s*-\s+\*\*(.+?)\*\*", characters, re.M))
