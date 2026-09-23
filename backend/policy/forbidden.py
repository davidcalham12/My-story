"""Does this text carry a term it may not carry? SPEC-EXAM-001 §1, AC-4.

Pure functions over values plus three small queries, for the reason
`chapters/domain.py` gives: a rule entangled with a run can only be exercised by
doing a run. Here a term, a text and a verdict cost a millisecond.

**Normalisation is the whole of it.** Comparing the written forms catches
nothing: a brief says `Ándres` and the chapter says `andres`, a brief says
`perro` and the chapter says `perros`, and a guardrail that reports clean on
either is worse than no guardrail, because someone will trust it. So both sides
of the comparison go through `normalise` and the table stores the result.

**A term is matched as whole words, never as a substring.** The first shape of
this check was `term in text.casefold()`, which makes `perro` fire on `perrera`
and turns a short term into a guardrail that reports prose nobody wrote wrong. A
reader who learns to skim a report has lost the report — `names.py` says the same
thing about capitalised words, and for the same reason.

**A hit is not a crash.** This returns findings; FLOW-4 puts them in the feedback
sheet as the `forbidden_words` validator, the writer redrafts, and only three
exhausted attempts end the run. Nothing here halts anything.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

#: The three levels, and the CHECK in `011_policy.sql` is the same list. They
#: have different authors: `global` is seeded by the migration, `client` comes
#: from the brief's `forbidden_terms`, `novel` is added during a run.
LEVELS = ("global", "client", "novel")

#: A word: letters and digits in any script, underscores excluded. `[^\W_]`
#: rather than `\w` so `mi_ex` reads as two words, and rather than `[a-z]` so an
#: accented letter is a letter — which is the entire subject of this module.
WORD = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class Term:
    level: str
    term: str
    normalised: str


@dataclass(frozen=True)
class Hit:
    level: str
    term: str
    #: The surface text as the chapter wrote it. The sheet's rule 3 wants a
    #: literal quote, and `andres` is not what the brief typed.
    quote: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "term": self.term, "quote": self.quote}

    def __str__(self) -> str:
        return (f"{self.quote!r} is the {self.level} forbidden term "
                f"{self.term!r}")


# --------------------------------------------------------------- the rule


def _singular(word: str) -> str:
    """A trailing `s`, and nothing cleverer.

    One rule, applied to both sides, so `perros` and `perro` meet in the middle.

    What it deliberately misses, written here rather than found later: a Spanish
    plural of a consonant stem — `flor`/`flores` — because the `es` rule that
    catches it also turns `andres` into `andr`, and the named test case in
    PLAN-001 is a name. A miss that is written down is a decision; the version
    that mangles names would have been a defect. Add the second rule with the
    brief that needs it.
    """
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def _fold(word: str) -> str:
    # NFKD splits `Á` into `A` + the combining acute, so dropping the combining
    # characters drops the accents and leaves everything else alone. NFC would
    # not: it puts the accent back.
    stripped = "".join(c for c in unicodedata.normalize("NFKD", word.casefold())
                       if not unicodedata.combining(c))
    return _singular(stripped)


def normalise(term: str) -> str:
    """The form the table stores and `check` compares. Words joined by a space,
    so a term of several words normalises the same way the text around it will."""
    return " ".join(_fold(w) for w in WORD.findall(term))


# --------------------------------------------------------------- the check


def check(text: str, terms: Iterable[Term]) -> list[Hit]:
    """Every hit, in the order a reader meets them.

    A term of several words is matched over a window of words and **not** over
    the characters between them, so `mi ex, mujer` is still `mi ex mujer`: a
    guardrail a comma defeats is not one. What does not match is a different
    sequence of the same words — `mujer de mi ex` is a different thing said, and
    the quote handed to the sheet has to be the phrase that was actually
    written, which is why it is sliced back out of the original text.
    """
    spans = [m.span() for m in WORD.finditer(text)]
    folded = [_fold(text[a:b]) for a, b in spans]

    wanted: dict[int, dict[str, Term]] = {}
    for term in terms:
        words = term.normalised.split()
        if words:                       # a term of punctuation alone matches
            wanted.setdefault(len(words), {})[term.normalised] = term

    found: list[tuple[int, Hit]] = []
    for size, by_form in wanted.items():
        for i in range(len(folded) - size + 1):
            term = by_form.get(" ".join(folded[i:i + size]))
            if term is not None:
                quote = text[spans[i][0]:spans[i + size - 1][1]]
                found.append((spans[i][0], Hit(term.level, term.term, quote)))
    return [hit for _, hit in sorted(found, key=lambda pair: pair[0])]


# --------------------------------------------------------------- the table


def terms(conn: sqlite3.Connection, levels: Iterable[str] | None = None) -> list[Term]:
    """Every term the database holds, or only the levels asked for.

    There is no run dimension in `forbidden_words` — the spec fixes its three
    columns — so a `novel` term added by one run is live for the next one in the
    same database. Say which levels you mean when that matters.
    """
    sql = "SELECT level, term, normalised FROM forbidden_words"
    params: tuple[str, ...] = ()
    if levels is not None:
        chosen = tuple(levels)
        sql += f" WHERE level IN ({','.join('?' * len(chosen))})"
        params = chosen
    return [Term(r["level"], r["term"], r["normalised"])
            for r in conn.execute(sql + " ORDER BY level, normalised", params)]


def add_term(conn: sqlite3.Connection, level: str, term: str) -> None:
    """Add one term at one level. Idempotent by normalised form.

    `INSERT OR IGNORE` because a brief re-read, or the same term entered twice
    with different accents, is not an error worth stopping a run for — and the
    row already there says the same thing.
    """
    conn.execute(
        "INSERT OR IGNORE INTO forbidden_words (level, term, normalised) "
        "VALUES (?, ?, ?)", (level, term, normalise(term)))
