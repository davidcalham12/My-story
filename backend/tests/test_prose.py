"""SPEC-005 — the part of prose quality that is arithmetic.

`verification.md` §3.9 is the project's largest gap: nobody measures the prose,
and three visible defects shipped because of it. Before proposing a sixth
characteristic — another model, another judgement, another $0.07 a chapter that
does not reproduce — `AGENTS.md` §5 requires saying why a script will not do.

For two of those three defects a script does. The tests below are that claim,
and the last one is the measurement it produced.
"""

from __future__ import annotations

import json
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
    """They have to *diverge*.

    This fixture used to be the same paragraph twice, which is a duplicated
    sentence — a different and stronger finding. It passed for the wrong reason
    until the double-charge rule below made the difference visible.
    """
    first = ("The tide came in over the causeway again that evening, slow and "
             "grey and entirely without hurry.")
    second = ("The tide came in over the causeway again that morning, and she "
              "counted the steps on the way down.")
    assert "echoed-opening" in kinds(f"# Chapter 1 — A\n\n{first}\n\n{second}\n")


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
#: Books known to repeat a sentence across chapters, with the reason.
#:
#: This assertion used to be unconditional and it was true until an eight-chapter
#: book disproved it. Keeping it unconditional would mean deleting the evidence
#: to keep the test green.
REPEATS = {
    "cartographer-inconstant-valley": (
        "the Bible gave Nat Fowler a Speaks. line inside quotation marks, and "
        "chapters 2 and 7 used it verbatim. The writer never sees prior prose, "
        "so it could not know; the Bible is the only shared channel, and a "
        "quoted line in it is a line the book will repeat."
    ),
}


@pytest.mark.parametrize("slug", [slug for slug, _ in books()])
def test_a_book_repeats_a_sentence_only_where_we_know_why(slug):
    """The defect the gate cannot see, looked for across whole books.

    **Per-chapter checking cannot see it.** `check_prose` reads one chapter and
    found nothing in all eight; the repeat is between chapter 2 and chapter 7.
    That is why `backend.checks FLOW-6` reads `dist/book.md`.
    """
    repeated = "duplicate-sentence" in kinds(dict(books())[slug])
    if slug in REPEATS:
        assert repeated, (
            f"{slug} no longer repeats — remove it from REPEATS and say what "
            f"fixed it"
        )
    else:
        assert not repeated, slug


# --------------------------------------------- scoring, as a script

def score(chapter: Path, payload: str, bible: Path | None = None):
    import subprocess, sys
    args = [sys.executable, "-m", "backend.chapters.score_prose", str(chapter)]
    if bible:
        args.append(str(bible))
    return subprocess.run(args, input=payload, capture_output=True, text=True,
                          cwd=ROOT)


def test_the_score_is_computed_by_the_script_not_the_orchestrator(tmp_path):
    """SPEC-006 left three numbers to be copied by hand into a formula, at the
    moment a chapter's fate is decided. `AGENTS.md` §5: if a script will do."""
    chapter = tmp_path / "ch01.md"
    chapter.write_text(CLEAN, encoding="utf-8")
    result = score(chapter, '{"major": 2, "minor": 3}')
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["mechanical"] == 0
    assert out["score"] == 10 - 2 * 2 - 3
    assert "10 − 3×0 − 2×2 − 1×3 = 3" in out["why"]


def test_the_mechanical_count_comes_from_the_script_not_from_the_caller(tmp_path):
    """The caller cannot inflate or hide it: it is not an input."""
    chapter = tmp_path / "ch01.md"
    chapter.write_text(
        CLEAN + "\nThe water went off the causeway at twenty past two and Ada went down behind it.\n",
        encoding="utf-8")
    out = json.loads(score(chapter, '{"major": 0, "minor": 0, "mechanical": 99}').stdout)
    assert out["mechanical"] == 1
    assert out["score"] == 7
    assert out["mechanical_defects"][0]["quote"]


def test_the_score_floors_at_zero_and_says_so(tmp_path):
    chapter = tmp_path / "ch01.md"
    chapter.write_text(CLEAN, encoding="utf-8")
    out = json.loads(score(chapter, '{"major": 9, "minor": 9}').stdout)
    assert out["score"] == 0
    assert "floored" in out["why"]


def test_unreadable_counts_are_refused_rather_than_guessed(tmp_path):
    """A scoring script that guesses produces a number nothing stands behind,
    and the orchestrator would use it."""
    chapter = tmp_path / "ch01.md"
    chapter.write_text(CLEAN, encoding="utf-8")
    result = score(chapter, "two majors")
    assert result.returncode != 0
    assert "score" not in result.stdout


def test_negative_counts_are_refused(tmp_path):
    chapter = tmp_path / "ch01.md"
    chapter.write_text(CLEAN, encoding="utf-8")
    assert score(chapter, '{"major": -1, "minor": 0}').returncode != 0


def test_one_fault_is_not_charged_twice(tmp_path):
    """A repeated paragraph is a duplicate sentence AND an echoed opening.

    Reported as both it costs six points for one fault — exactly what the critic
    is told not to do, so the script must not do it either. The duplicate is the
    stronger and more specific finding, so it is the one that stands.
    """
    para = "The water went off the causeway at twenty past two and Ada went down behind it."
    draft = f"# Chapter 1 — A\n\n{para}\n\n{para}\n"
    found = [d.kind for d in find(draft)]
    assert found.count("duplicate-sentence") == 1
    assert "echoed-opening" not in found


def test_a_genuine_echo_is_still_caught(tmp_path):
    """Suppression must be narrow: two paragraphs that open alike and then
    diverge are a real finding and not a duplicate."""
    a = ("The tide came in over the causeway again that evening, slow and grey "
         "and without hurry.")
    b = ("The tide came in over the causeway again that morning, and she counted "
         "the steps as she went.")
    assert "echoed-opening" in kinds(f"# Chapter 1 — A\n\n{a}\n\n{b}\n")
