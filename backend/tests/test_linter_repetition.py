"""SPEC-EXAM-005 O1: a prose linter for restated sentences and verbal tics.

Report-only. It exists because the judge, reading the finished book, found a
sentence in chapter 5 said twice in a row with contradictory light, and every
per-chapter critic had passed the chapter. Running it changes no score.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.linters import repetition

CH05 = (Path(__file__).resolve().parents[2] / "output" / "the-other-side-of-the-hill"
        / "chapters" / "ch05.md")

RESTATED = (
    "They stepped out into the light. There was a stream, silver in the failing "
    "light, and fields that descended to a stone house with a wall around it. There "
    "was a stream, silver in the afternoon sun, and fields that went down toward a "
    "stone house with a wall around it. The house was small."
)

CLEAN = (
    "The boy climbed the hill before breakfast. His dog followed, stopping at every "
    "gate. At the top the wind smelled of thyme and salt. Below, the village was "
    "already awake, and somebody was baking bread."
)


def test_a_sentence_restated_next_to_itself_is_flagged():
    found = repetition.restated(RESTATED)
    assert len(found) == 1
    first, second, score = found[0]
    assert "failing light" in first and "afternoon sun" in second
    assert score >= repetition.THRESHOLD


def test_clean_prose_reports_nothing():
    assert repetition.restated(CLEAN) == []
    assert repetition.tics(CLEAN) == []


def test_a_phrase_leaned_on_is_a_tic():
    text = " ".join(["He felt a small smile begin."] * 4 + ["The end came quietly."])
    assert any(phrase == "a small smile" for phrase, _ in repetition.tics(text))


def test_the_linter_never_writes(tmp_path):
    chapter = tmp_path / "ch01.md"
    chapter.write_text(RESTATED, encoding="utf-8")
    before = chapter.read_bytes()
    report = repetition.lint(chapter)
    assert chapter.read_bytes() == before
    assert report["restated"] and report["file"].endswith("ch01.md")


@pytest.mark.skipif(not CH05.is_file(), reason="the example novel is not in this checkout")
def test_it_finds_what_the_judge_found_in_chapter_5():
    found = repetition.restated(CH05.read_text(encoding="utf-8"))
    assert any("failing light" in a and "afternoon sun" in b for a, b, _ in found)
