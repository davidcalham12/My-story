"""The part of "is the prose any good" that is arithmetic. SPEC-005.

`verification.md` §3.9 is the largest gap in the project: **nobody measures the
quality of the prose**, and three visible defects shipped because of it — a
sentence duplicated verbatim, a timeline error on screen, a paragraph stating the
same fact twice. Each was kept in by redraft rule 2, *change only what was
cited*, because no finding named them and none of the five characteristics reads
prose.

The obvious move is a sixth characteristic: another model, another judgement,
another $0.07 a chapter that does not reproduce. **`AGENTS.md` §5 says to say
first why a script will not do**, and for two of those three defects a script
does perfectly well:

- a sentence repeated word for word is **equality**, not taste;
- a heading glued to the previous line is a **regex**;
- a paragraph opening with the same eight words as another is **a prefix**.

What no script here can do is the third defect — a timeline error — or anything
about voice, pacing or whether a sentence earns its place. Those stay **U**, and
this module does not pretend otherwise. It is a floor under §3.9, not a ceiling
over it.

**It reports; it does not gate.** Adding a sixth characteristic would change the
gate, which `AGENTS.md` §6 forbids without an approved SPEC naming it, and the
evidence for that decision is exactly what this is meant to produce.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A sentence has to be long enough for repetition to mean something. "She
#: nodded." twice in a chapter is a style, not a defect; forty characters of
#: identical prose is not a coincidence anyone chose.
MIN_SENTENCE_CHARS = 40

#: How much of a paragraph's opening must match another's to be worth reporting.
ECHO_WORDS = 8

SENTENCE_END = re.compile(r"(?<=[.!?])[\s ]+")
HEADING_MID_PARAGRAPH = re.compile(r"(?<=\S)\n#{1,6}\s")


@dataclass(frozen=True)
class Defect:
    kind: str
    quote: str
    claim: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.claim} — {self.quote[:80]!r}"


def _body(draft: str) -> str:
    """The prose, without the chapter heading.

    The heading is `chatter`'s business and it is legitimately repetitive.
    """
    lines = draft.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    out = []
    for block in text.split("\n"):
        stripped = block.strip()
        if not stripped or stripped.startswith(("#", ">", "|", "---")):
            continue
        out.extend(s.strip() for s in SENTENCE_END.split(stripped) if s.strip())
    return out


def _normalise(sentence: str) -> str:
    """Case, punctuation and emphasis marks removed.

    `*The Marigold stands twice.*` and `The Marigold stands twice.` are the same
    sentence appearing twice, and a comparison that says otherwise is a
    comparison nobody wanted.
    """
    return re.sub(r"[^a-z0-9 ]", "", sentence.lower()).strip()


def find(draft: str) -> list[Defect]:
    """Every mechanically detectable prose defect in one chapter."""
    text = _body(draft)
    defects: list[Defect] = []

    seen: dict[str, str] = {}
    for sentence in _sentences(text):
        if len(sentence) < MIN_SENTENCE_CHARS:
            continue
        key = _normalise(sentence)
        if not key:
            continue
        if key in seen:
            defects.append(Defect(
                "duplicate-sentence",
                sentence,
                "this sentence already appears earlier in the chapter, word for "
                "word",
            ))
        else:
            seen[key] = sentence

    for match in HEADING_MID_PARAGRAPH.finditer(text):
        line = text[match.start():match.end() + 60].strip()
        defects.append(Defect(
            "heading-without-a-blank-line",
            line,
            "a heading follows a line of prose with no blank line between them. "
            "CommonMark lets the heading interrupt the paragraph, so it usually "
            "renders; stricter converters keep it as literal text in the middle "
            "of a sentence",
        ))

    openings: dict[str, str] = {}
    for para in re.split(r"\n\s*\n", text):
        words = _normalise(para).split()
        if len(words) < ECHO_WORDS * 2:
            continue
        key = " ".join(words[:ECHO_WORDS])
        if key in openings:
            defects.append(Defect(
                "echoed-opening",
                " ".join(para.split()[:ECHO_WORDS * 2]),
                f"another paragraph opens with the same {ECHO_WORDS} words",
            ))
        else:
            openings[key] = para

    return defects


def report(draft: str) -> dict:
    """What `find` found, and — as loudly — what it cannot look for.

    A report listing only what it checks reads as a verdict on the prose. It is
    not one, and saying so is the whole reason this returns a dict rather than a
    score.
    """
    defects = find(draft)
    return {
        "defects": [{"kind": d.kind, "quote": d.quote, "claim": d.claim}
                    for d in defects],
        "checked": ["duplicate-sentence", "heading-without-a-blank-line",
                    "echoed-opening"],
        "not_checked": [
            "whether a fact stated here contradicts one stated elsewhere",
            "voice, pacing, dialogue, originality",
            "whether any sentence earns its place",
        ],
        # Never a score. A count of mechanical defects is not a quality grade,
        # and calling it one would close the question §3.9 exists to keep open.
        "verdict": "clean" if not defects else "defects",
    }
