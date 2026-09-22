"""Canonical names, checked against the Bible. SPEC-005 §"next candidates".

`verification.md` §4 named three next things to move from judgement to code:
counting the summary's facts, detecting a heading inside a paragraph, and
**checking canonical names**. The second is done. This is the third.

The defect it looks for is narrow on purpose: a name in a chapter that is *almost*
a name in `bible/characters.md` — Nell Harker written as Nell Harper. Exactly the
kind of thing `continuity` is meant to catch and might not, because it reads for
contradiction and this reads as a typo.

**What it deliberately does not do: report every unknown capitalised word.** A
novel is full of proper nouns that are not people — ships, streets, tides, the
Corbie Light. Flagging them would bury the one signal that matters under forty
that do not, and a reader who learns to skim a report has lost the report.

**Measured before it was believed.** Over nine books and 32 chapters it found
**one** candidate, and that one was *"the Learys"* — the plural of a canonical
name, which is correct English. So the defect class this looks for has **never
occurred in anything that shipped**. That is the finding, and it is written in
`domain-knowledge.md` rather than dressed up as a catch.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

#: How alike is too alike.
#:
#: Chosen by measurement, not by taste. `Harper`/`Harker` — the defect this is
#: for — scores **0.833**, so 0.86 misses the very case it was written to catch.
#: At 0.83 it catches it, and across nine books it raises nothing that COMMON
#: does not already exclude.
SIMILARITY = 0.83

#: A canonical name as `bible/characters.md` writes it: `- **Ada Rowe** — ...`
CANONICAL = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*", re.M)

#: A capitalised word that is not opening a sentence. A sentence-initial capital
#: says nothing about whether the word is a name.
MID_SENTENCE_CAPITAL = re.compile(
    r"(?<![.!?\"'“‘]\s)(?<!^)\b([A-Z][a-z]{2,})\b", re.M)

#: English plural and possessive of a name. `the Learys` is not a misspelling of
#: `Leary`, and the first version of this check said it was.
INFLECTION = re.compile(r"(?:'s|’s|s)$")

#: Common words that are never a character's name.
#:
#: A book with a character called **Theo** makes the word **The** a near miss,
#: and the check raised it five times across the shipped chapters before this
#: existed. A short canonical name turns ordinary English into a suspect, which
#: is a property of the measure rather than of the prose.
COMMON = frozenset("""
the then they them their there these those this that than
and but for nor yet not with without within from into onto upon
her his its our your their him she who whom whose what when where why how
was were been being have has had will would shall should can could may might
one two three four five six seven eight nine ten
all any both each few more most other some such only own same too very
about above after again against below between before down during further
here once other over under until while about
""".split())


@dataclass(frozen=True)
class Suspect:
    written: str
    canonical: str

    def __str__(self) -> str:
        return (f"{self.written!r} is one letter from the canonical "
                f"{self.canonical!r}")


def canonical_names(characters_md: str) -> set[str]:
    return set(CANONICAL.findall(characters_md))


def _name_parts(names: set[str]) -> set[str]:
    """Given names and surnames separately: a chapter uses either alone."""
    return {part for name in names
            for part in re.split(r"[\s'’-]+", name)
            if len(part) >= 3}


def check(draft: str, characters_md: str) -> list[Suspect]:
    known = _name_parts(canonical_names(characters_md))
    if not known:
        return []

    suspects: list[Suspect] = []
    for token in sorted(set(MID_SENTENCE_CAPITAL.findall(draft))):
        if token in known:
            continue
        if token.lower() in COMMON:
            continue
        # `Learys` and `Leary's` are that name, not a near miss of it.
        if INFLECTION.sub("", token) in known:
            continue
        close = difflib.get_close_matches(token, known, n=1, cutoff=SIMILARITY)
        if close:
            suspects.append(Suspect(token, close[0]))
    return suspects
