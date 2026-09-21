"""SPEC-002 — the gate.

Written before `backend/chapters/domain.py` exists and seen failing first, which
is the point of the order: a test that has never failed has not been shown to
test anything.

Every rule here was arrived at by a run that went wrong. The comments say which.
"""

import pytest

from backend.chapters import domain

BAND = (300, 550)


# ---------------------------------------------------------------- B1, B2


def test_a_chapter_passes_only_when_all_five_reach_eight():
    """`min`, so a chapter is worth what its worst characteristic is worth."""
    scores = {"continuity": 10, "science": 10, "outline": 10, "length": 10, "chatter": 10}
    assert domain.aggregate(scores).passed is True
    scores["science"] = 7
    verdict = domain.aggregate(scores)
    assert verdict.passed is False
    assert verdict.aggregate == 7
    assert verdict.worst == ["science"]


def test_an_average_does_not_pass_a_chapter():
    """Four tens and a four averages 8.8 and must still fail."""
    scores = {"continuity": 10, "science": 10, "outline": 10, "length": 10, "chatter": 4}
    assert domain.aggregate(scores).passed is False


def test_an_unusable_verdict_is_excluded_not_counted_as_a_pass():
    """This once returned 10, which meant a malformed reply SILENTLY PASSED a
    draft — the one failure a quality gate must not have. There is no honest
    substitute: 10 invents an approval and 0 invents a rejection."""
    scores = {"continuity": 10, "science": None, "outline": 10, "length": 10, "chatter": 10}
    verdict = domain.aggregate(scores)
    assert verdict.unscored == ["science"]
    assert verdict.aggregate == 10
    assert verdict.passed is False, "four critics is a weaker gate, not a passing one"
    assert "science" in verdict.note


def test_all_five_unusable_is_not_a_pass():
    verdict = domain.aggregate({k: None for k in domain.CHARACTERISTICS})
    assert verdict.passed is False
    assert verdict.aggregate is None


# -------------------------------------------------------------- B3, B4, B5


def test_length_scores_against_the_band_widened_by_tolerance():
    assert domain.score_length(420, BAND, tolerance_pct=0) == 10
    assert domain.score_length(299, BAND, tolerance_pct=0) == 0
    # 25% tolerance widens 300-550 to 225-688
    assert domain.score_length(240, BAND, tolerance_pct=25) == 10
    assert domain.score_length(700, BAND, tolerance_pct=25) == 0


def test_chatter_scores_zero_unless_the_draft_opens_with_the_heading():
    assert domain.score_chatter("# Chapter 3 — A Title\n\nProse.") == 10
    assert domain.score_chatter("Here is the chapter you asked for.\n\n# Chapter 3") == 0
    assert domain.score_chatter("") == 0


def test_outline_scores_by_the_formula_with_a_floor():
    assert domain.score_outline(missing=0, out_of_order=0) == 10
    assert domain.score_outline(missing=1, out_of_order=0) == 7
    assert domain.score_outline(missing=1, out_of_order=1) == 6
    assert domain.score_outline(missing=9, out_of_order=0) == 0, "floor, never negative"


# ---------------------------------------------------------------- B6, B7


def test_patches_apply_by_literal_match():
    draft = "The ship left at dawn. It arrived at noon."
    result = domain.apply_patches(
        draft, [{"find": "at noon", "replace": "at dusk", "why": "timeline"}]
    )
    assert "at dusk" in result.text
    assert result.applied == 1 and result.skipped == []


def test_a_find_that_does_not_match_is_skipped_and_counted():
    """Never applied approximately. An approximation silently does nothing worse
    than nothing: it does something nobody asked for."""
    draft = "The ship left at dawn."
    result = domain.apply_patches(
        draft, [{"find": "at MIDNIGHT", "replace": "at dusk", "why": "x"}]
    )
    assert result.text == draft
    assert result.applied == 0
    assert result.skipped == ["at MIDNIGHT"]


def test_nothing_the_findings_did_not_name_can_change():
    """The guardrail on the DO-NOT-TOUCH list. A writer that takes the
    opportunity to improve an approved paragraph is the commonest way a passing
    score stops passing — and here it is impossible, because the orchestrator
    applies the patches itself."""
    draft = "Sentence one. Sentence two. Sentence three."
    result = domain.apply_patches(
        draft, [{"find": "Sentence two.", "replace": "Sentence TWO.", "why": "x"}]
    )
    assert result.text == "Sentence one. Sentence TWO. Sentence three."


def test_patching_reports_when_nothing_applied():
    """The caller's cue to fall back to a full rewrite rather than burn the
    attempt on nothing."""
    result = domain.apply_patches("abc", [{"find": "zzz", "replace": "y", "why": "x"}])
    assert result.applied == 0
    assert result.nothing_applied is True


# ------------------------------------------------------------ B8, B9, B10


def _finding(**kw):
    base = {
        "characteristic": "continuity",
        "severity": "medium",
        "quote": "Drafted 0118 ship time, nine hours out, received 1912.",
        "claim": "0118 to 1912 is eighteen hours, not nine.",
        "fix": "flight plus relay time must total eighteen",
        "reference": "bible/timeline.md, Day 2",
    }
    base.update(kw)
    return base


def test_a_complete_level_one_sheet_validates():
    sheet = domain.build_sheet(
        chapter=2, attempt=2, level=1,
        scores={"continuity": 7, "science": 8, "outline": 10, "length": 10, "chatter": 10},
        findings=[_finding()], resolved=[],
    )
    assert domain.validate_sheet(sheet, level=1).ok


def test_a_sheet_shows_all_five_scores_including_the_passing_ones():
    """The writer has to know what is already right in order to leave it alone."""
    sheet = domain.build_sheet(
        chapter=2, attempt=2, level=1,
        scores={"continuity": 7, "science": 8, "outline": 10, "length": 10, "chatter": 10},
        findings=[_finding()], resolved=[],
    )
    for name in ("Continuity", "Science", "Outline", "Length", "Heading"):
        assert name in sheet
    assert "DO NOT TOUCH" in sheet


def test_a_finding_missing_a_field_fails_validation():
    """Four fields or it does not go. A sheet without the quote returns the
    writer to guessing, which is where attempt 1 already was."""
    sheet = domain.build_sheet(
        chapter=2, attempt=2, level=1,
        scores={"continuity": 7, "science": 10, "outline": 10, "length": 10, "chatter": 10},
        findings=[_finding(quote=None)], resolved=[],
    )
    report = domain.validate_sheet(sheet, level=1)
    assert not report.ok
    assert any("Quote" in p for p in report.problems)


def test_level_two_requires_a_literal_replacement_and_level_one_forbids_it():
    """On attempt 2 the writer interprets a description. On attempt 3 it does not
    interpret at all — it integrates a given text."""
    scores = {"continuity": 7, "science": 10, "outline": 10, "length": 10, "chatter": 10}
    two = domain.build_sheet(chapter=2, attempt=3, level=2, scores=scores,
                             findings=[_finding(replacement="The corrected sentence.")],
                             resolved=[])
    assert domain.validate_sheet(two, level=2).ok

    missing = domain.build_sheet(chapter=2, attempt=3, level=2, scores=scores,
                                 findings=[_finding()], resolved=[])
    assert not domain.validate_sheet(missing, level=2).ok

    one = domain.build_sheet(chapter=2, attempt=2, level=1, scores=scores,
                             findings=[_finding(replacement="nope")], resolved=[])
    assert not domain.validate_sheet(one, level=1).ok


def test_a_sheet_may_not_cite_a_previous_chapter():
    """The writer has never seen one, and this sheet is not the hole through
    which it finally does."""
    sheet = domain.build_sheet(
        chapter=3, attempt=2, level=1,
        scores={"continuity": 7, "science": 10, "outline": 10, "length": 10, "chatter": 10},
        findings=[_finding(reference="chapter 1, paragraph 4")], resolved=[],
    )
    report = domain.validate_sheet(sheet, level=1)
    assert not report.ok
    assert any("previous chapter" in p or "chapter" in p.lower() for p in report.problems)


def test_findings_are_never_trimmed():
    """A finding held back to keep the sheet short is a finding that fails again
    next attempt."""
    findings = [_finding(claim=f"problem {i}") for i in range(7)]
    sheet = domain.build_sheet(
        chapter=1, attempt=2, level=1,
        scores={"continuity": 4, "science": 10, "outline": 10, "length": 10, "chatter": 10},
        findings=findings, resolved=[],
    )
    for i in range(7):
        assert f"problem {i}" in sheet


# --------------------------------------------------------------- B11, B12


def test_the_best_draft_is_kept_not_the_last():
    """A chapter whose first attempt scored 7 and whose third scored 4 must ship
    the 7. A rewrite is not guaranteed to improve, and the gate must not assume
    it was."""
    attempts = [
        domain.AttemptResult(attempt=1, aggregate=7, passed=False),
        domain.AttemptResult(attempt=2, aggregate=5, passed=False),
        domain.AttemptResult(attempt=3, aggregate=4, passed=False),
    ]
    assert domain.best_of(attempts).attempt == 1


def test_an_accepted_draft_is_the_one_that_passed_even_if_not_the_best():
    accepted = [
        domain.AttemptResult(attempt=1, aggregate=7, passed=False),
        domain.AttemptResult(attempt=2, aggregate=9, passed=True),
    ]
    assert domain.accepted_of(accepted).attempt == 2


def test_a_late_finding_is_marked_and_does_not_block():
    """A critic raising on attempt 3 something equally present in the first draft
    is moving the goalposts. Without this rule the third-attempt guarantee does
    not exist, because something new can always appear."""
    first_draft = "The bell rang twice at noon."
    late = domain.mark_late(
        findings=[_finding(quote="The bell rang twice at noon.")],
        first_draft=first_draft,
        seen_quotes=set(),
    )
    assert late[0]["late"] is True
    assert domain.blocking(late) == [], "late findings do not block"


def test_a_finding_carried_forward_is_not_late():
    """It was raised before, so the goalposts have not moved."""
    marked = domain.mark_late(
        findings=[_finding(quote="already said")],
        first_draft="already said",
        seen_quotes={"already said"},
    )
    assert marked[0]["late"] is False
    assert len(domain.blocking(marked)) == 1


# ---------------------------------------------------------------- B13


def test_domain_imports_only_the_standard_library():
    """What makes every test above runnable with no database, server or model."""
    import ast
    import pathlib
    import sys

    source = pathlib.Path(domain.__file__).read_text(encoding="utf-8")
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    assert roots <= set(sys.stdlib_module_names), f"non-stdlib import: {roots}"
