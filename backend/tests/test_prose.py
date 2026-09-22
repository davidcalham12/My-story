"""SPEC-005 — the part of prose quality that is arithmetic.

`verification.md` §3.9 is the project's largest gap: nobody measures the prose,
and three visible defects shipped because of it. Before proposing a sixth
characteristic — another model, another judgement, another $0.07 a chapter that
does not reproduce — `AGENTS.md` §5 requires saying why a script will not do.

For two of those three defects a script does. The tests below are that claim,
and the last one is the measurement it produced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.chapters.prose import find, report

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

CLEAN = """# Chapter 1 — The Seventh Step

The water went off the causeway at twenty past two and Ada went down behind it.

Three petitions on the seventh step, two weighted with stones and one with net.
"""


def kinds(draft: str) -> set[str]:
    return {d.kind for d in find(draft)}


def test_clean_prose_reports_nothing():
    assert find(CLEAN) == []
    assert report(CLEAN)["verdict"] == "clean"


def test_a_sentence_repeated_word_for_word_is_caught():
    """One of the three that shipped. It is equality, not taste."""
    draft = CLEAN + "\nThe water went off the causeway at twenty past two and Ada went down behind it.\n"
    assert "duplicate-sentence" in kinds(draft)


def test_repetition_survives_emphasis_and_case():
    """`*The same sentence.*` and `The same sentence.` are the same sentence."""
    draft = CLEAN + "\n*The water went off the causeway at twenty past two and ADA went down behind it.*\n"
    assert "duplicate-sentence" in kinds(draft)


def test_a_short_repeated_line_is_not_a_defect():
    """"She nodded." twice in a chapter is a style, not a defect.

    A detector that flags it trains its reader to ignore it, which costs more
    than the thing it found.
    """
    draft = CLEAN + '\n"Yes," she said.\n\nHe waited.\n\n"Yes," she said.\n'
    assert "duplicate-sentence" not in kinds(draft)


def test_the_chapter_heading_itself_is_never_a_defect():
    """Every chapter opens the same way. That is `chatter`'s business and it is
    supposed to be repetitive."""
    assert find("# Chapter 1 — A\n\n" + CLEAN.split("\n", 2)[2]) == []


def test_a_heading_glued_to_the_previous_line_is_caught():
    draft = "# Chapter 1 — A\n\nShe closed the log and went up the stair.\n# Chapter 2 — B\n\nThe next morning came in wet and late.\n"
    assert "heading-without-a-blank-line" in kinds(draft)


def test_a_heading_after_a_blank_line_is_not():
    draft = "# Chapter 1 — A\n\nShe closed the log and went up the stair.\n\n# Chapter 2 — B\n\nThe next morning came in wet and late.\n"
    assert "heading-without-a-blank-line" not in kinds(draft)


def test_two_paragraphs_opening_the_same_way_are_caught():
    para = ("The tide came in over the causeway again that evening, slow and "
            "grey and entirely without hurry, as it always had.")
    assert "echoed-opening" in kinds(f"# Chapter 1 — A\n\n{para}\n\n{para}\n")


def test_the_report_says_what_it_did_not_look_for():
    """A report listing only its checks reads as a verdict on the prose.

    It is not one. Three of the ten quality dimensions are not even approached
    here, and the report has to say so or it overstates itself by omission.
    """
    result = report(CLEAN)
    assert result["not_checked"]
    assert any("voice" in item for item in result["not_checked"])
    assert "score" not in result, "a count of mechanical defects is not a grade"


# --------------------------------------------------------------- measured

def books() -> list[tuple[str, str]]:
    return [(p.parent.parent.name, p.read_text(encoding="utf-8"))
            for p in sorted(OUTPUT.glob("*/dist/book.md"))]


def test_it_finds_something_real_in_the_shipped_books():
    """The measurement this module exists to produce.

    A detector that finds nothing has not been shown to detect anything, and
    running it over what actually shipped is the only honest way to find out.
    """
    assert books(), "no assembled books to read"
    found = {slug: find(text) for slug, text in books()}
    assert any(found.values()), "nothing found in nine books — suspect the detector"


def test_v2s_assembled_book_is_clean_where_v1s_are_not():
    """The result worth keeping, and G10 earns a reason nobody had noticed.

    Every v1 book glues each chapter heading to the previous chapter's last
    sentence: the shell concatenated with a single newline. v2 assembles in
    `publish/domain.py`, which joins with a blank line, and its book has none.

    "Assemble in code" was adopted because a model asked to concatenate
    paraphrased. It also happens to concatenate correctly.
    """
    by_slug = {slug: kinds(text) for slug, text in books()}
    v2 = by_slug.get("lighthouse-keeper-ledger")
    assert v2 is not None, "the v2 run's book is missing"
    assert "heading-without-a-blank-line" not in v2

    v1_with_the_defect = [s for s, k in by_slug.items()
                          if s != "lighthouse-keeper-ledger"
                          and "heading-without-a-blank-line" in k]
    assert len(v1_with_the_defect) >= 5, by_slug


# Parametrised by slug alone. Passing the book's text as a parameter puts the
# whole novel in the test id, and pytest exports that id in an environment
# variable Windows caps at 32,767 characters.
@pytest.mark.parametrize("slug", [slug for slug, _ in books()])
def test_no_chapter_that_passed_the_gate_repeats_a_sentence(slug):
    """The defect the gate cannot see, looked for in every book.

    It comes back clean, and that is a result rather than a formality: the
    duplicated sentence on record was in v1, before the drafts were kept, and
    nothing that has shipped since carries one.
    """
    assert "duplicate-sentence" not in kinds(dict(books())[slug]), slug
