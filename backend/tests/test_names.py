"""Canonical names against the Bible — and what measuring it found.

The last of the three "next candidates" `verification.md` §4 named. The
interesting result is at the bottom: over everything that has ever shipped, the
defect this looks for has **never happened**, and the one candidate it did raise
was correct English.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.chapters.names import canonical_names, check

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

BIBLE = """# Characters — Sallowmere Reach

- **Ada Rowe** — keeper of the Corbie Light
  - Wants: the drowned boats to stand in writing.

- **Nell Harker** — Ridge household; widow of the *Marigold*'s mate
  - Wants: the *Marigold* entered a third time.
"""


def test_the_bible_is_read_at_all():
    assert canonical_names(BIBLE) == {"Ada Rowe", "Nell Harker"}


def test_a_name_one_letter_out_is_caught():
    """The defect: a typo `continuity` reads past because it is not a
    contradiction, it is a misspelling."""
    draft = "She waited while Nell Harper climbed as far as the seventh step."
    suspects = check(draft, BIBLE)
    assert [s.canonical for s in suspects] == ["Harker"]


def test_the_canonical_spelling_is_not_caught():
    draft = "She waited while Nell Harker climbed as far as the seventh step."
    assert check(draft, BIBLE) == []


def test_a_plural_or_possessive_of_a_canonical_name_is_not_a_misspelling():
    """`the Learys` is the plural of a canonical name, and correct English.

    It was the only candidate the first version of this check produced across
    nine books — a false positive, and the reason this rule exists.
    """
    for draft in ("The Rowes had kept the light for two generations.",
                  "She read Ada Rowe's hand at the top of the page.",
                  "The Harkers left petitions at every low water."):
        assert check(draft, BIBLE) == [], draft


def test_a_common_word_is_never_a_suspect():
    """A book with a character called Theo makes the word `The` a near miss.

    It did, five times across the shipped chapters, before the stoplist existed.
    A short canonical name turns ordinary English into a suspect — a property of
    the measure, not of the prose.
    """
    bible = "- **Theo Vance** — the duty controller\n"
    draft = "He read it twice. The list was short, and then they went in."
    assert check(draft, bible) == []


def test_the_threshold_catches_the_case_it_was_written_for():
    """Chosen by measurement. `Harper`/`Harker` scores 0.833, so a threshold of
    0.86 — which reads like a safely strict choice — misses the whole point."""
    from backend.chapters.names import SIMILARITY
    import difflib

    assert difflib.SequenceMatcher(None, "Harper", "Harker").ratio() >= SIMILARITY


def test_an_unrelated_proper_noun_is_not_reported():
    """A novel is full of proper nouns that are not people.

    Reporting them buries the one signal that matters under forty that do not,
    and a reader who learns to skim a report has lost the report.
    """
    draft = "The Corbie Light stood over Sallowmere Reach and the Drowned Page."
    assert check(draft, BIBLE) == []


def test_a_sentence_initial_capital_is_not_a_name():
    draft = "Harper was not here. Harker was."
    # Only the mid-sentence occurrence can be judged; a sentence-initial capital
    # says nothing about whether the word is a name.
    assert [s.written for s in check(draft, BIBLE)] == []


# --------------------------------------------------------------- measured

def runs_with_a_bible() -> list[str]:
    return sorted(p.parent.parent.name
                  for p in OUTPUT.glob("*/bible/characters.md"))


def test_there_is_something_to_measure():
    assert len(runs_with_a_bible()) >= 8


@pytest.mark.parametrize("slug", runs_with_a_bible())
def test_no_shipped_chapter_misspells_a_canonical_name(slug):
    """The measurement, and it comes back empty.

    Nine books, 32 chapters, zero misspelled canonical names. **This check has
    never fired on real work** — which is a fact worth having rather than a
    reason to delete it: it cost nothing, and the alternative was believing the
    defect was out there because it sounded likely.
    """
    run = OUTPUT / slug
    bible = (run / "bible/characters.md").read_text(encoding="utf-8")
    for chapter in sorted((run / "chapters").glob("ch[0-9][0-9].md")):
        suspects = check(chapter.read_text(encoding="utf-8"), bible)
        assert suspects == [], f"{slug}/{chapter.name}: {[str(s) for s in suspects]}"
