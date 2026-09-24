"""Restated sentences and verbal tics — a report, never a verdict.

SPEC-EXAM-005 O1. The judge found, in the finished example novel, a sentence
said twice in a row with contradictory light ("failing light", then "afternoon
sun"); all six characteristics had passed that chapter. A reader of one chapter
at a time can miss a restatement a paragraph apart, and so can a model critic.
A word-set comparison of neighbouring sentences cannot.

**It is not wired into the gate.** Acting on what it finds would change how a
chapter is judged, which is a protected value (AGENTS.md §6) and a decision for
the owner. It reads and reports; it never writes.

    python -m backend.linters.repetition output/<slug>/chapters/ch*.md

Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

#: Share of words two nearby sentences must have in common to be one sentence
#: said twice. The ch05 pair scores 0.71; ordinary neighbouring sentences in the
#: example novel stay well under 0.4.
THRESHOLD = 0.6
#: How many sentences ahead to look. A restatement is a slip of revision, and it
#: sits next to what it restates or one sentence away.
WINDOW = 2
#: Shorter sentences repeat honestly ("He nodded.").
MIN_WORDS = 6
#: A three-word phrase used this many times in one chapter is leaned on.
TIC_MIN = 4

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘A-Z])")
_WORD = re.compile(r"[a-záéíóúñü']+", re.I)
_STOP = {
    "a", "an", "and", "the", "of", "to", "in", "on", "at", "for", "with", "as",
    "was", "is", "it", "he", "she", "they", "his", "her", "their", "that", "this",
    "had", "have", "be", "been", "but", "or", "not", "from", "by", "into", "i",
    "you", "we", "him", "them", "there", "were", "said", "so", "then", "what",
}


def _sentences(text: str) -> list[str]:
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return [s.strip() for s in _SENTENCE.split(re.sub(r"\s+", " ", body)) if s.strip()]


def _words(sentence: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(sentence)]


def restated(text: str) -> list[tuple[str, str, float]]:
    """Pairs of nearby sentences that say the same thing: (first, second, score)."""
    sentences = _sentences(text)
    found = []
    for i, first in enumerate(sentences):
        a = set(_words(first))
        if len(a) < MIN_WORDS:
            continue
        for second in sentences[i + 1:i + 1 + WINDOW]:
            b = set(_words(second))
            if len(b) < MIN_WORDS:
                continue
            score = len(a & b) / len(a | b)
            if score >= THRESHOLD:
                found.append((first, second, round(score, 2)))
    return found


def tics(text: str) -> list[tuple[str, int]]:
    """Three-word phrases used at least TIC_MIN times, ignoring all-stopword ones."""
    counts: Counter[str] = Counter()
    for sentence in _sentences(text):
        words = _words(sentence)
        for i in range(len(words) - 2):
            gram = words[i:i + 3]
            if all(w in _STOP for w in gram):
                continue
            counts[" ".join(gram)] += 1
    return [(g, n) for g, n in counts.most_common() if n >= TIC_MIN]


def lint(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    return {
        "file": str(path),
        "restated": [{"first": a, "second": b, "score": s} for a, b, s in restated(text)],
        "tics": [{"phrase": g, "count": n} for g, n in tics(text)],
    }


def main(argv: list[str]) -> int:
    reports = [lint(Path(p)) for p in argv]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
