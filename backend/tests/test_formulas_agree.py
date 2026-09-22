"""One formula, written in four places, checked against the code that runs it.

`prose = 10 − 3·mechanical − 2·major − 1·minor` now appears in `domain.py`, in
`SKILL.md`, in the critic's own prompt and in SPEC-006. `outline`'s formula
appears in three. **Every one of those is a copy, and copies drift** — it is the
defect this suite has been finding all day, and adding a characteristic created
four fresh instances of it in an afternoon.

A drifted formula here is not cosmetic. The orchestrator computes the score from
what `SKILL.md` says; the archive and every statistic recompute it from
`domain.py`. If the two disagree, a chapter is scored by one rule and judged by
another, and the gate rows in the database describe a gate that did not run.

**A**, not T: it parses coefficients out of prose. It holds while the formulas
are written the way they are written, and they are written plainly on purpose.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.chapters.domain import score_outline, score_prose

ROOT = Path(__file__).resolve().parents[2]

WHERE_PROSE = [
    ".claude/skills/novaforge/SKILL.md",
    ".claude/agents/prose-critic.md",
    "specs/SPEC-006-prose-characteristic.md",
]

#: `10 − 3·mechanical − 2·major − 1·minor`, in either kind of minus sign.
PROSE = re.compile(
    r"prose\s*=\s*10\s*[−-]\s*(\d+)·mechanical\s*[−-]\s*(\d+)·major\s*[−-]\s*(\d+)·minor")


def coefficients(path: str) -> tuple[int, int, int]:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = PROSE.search(text)
    assert match, f"{path} no longer states the prose formula in a readable form"
    return tuple(int(g) for g in match.groups())


def test_the_formula_is_found_in_every_place_it_is_written():
    for path in WHERE_PROSE:
        assert coefficients(path)


@pytest.mark.parametrize("path", WHERE_PROSE)
def test_each_written_formula_computes_what_the_code_computes(path):
    """Not "the text matches" — the text, executed, matches.

    Comparing strings would pass on a formula written identically and wrongly.
    This runs the documented coefficients over the same inputs as the function
    and compares the answers.
    """
    a, b, c = coefficients(path)
    for mechanical in range(0, 4):
        for major in range(0, 4):
            for minor in range(0, 4):
                documented = max(0, 10 - a * mechanical - b * major - c * minor)
                actual = score_prose(mechanical=mechanical, major=major, minor=minor)
                assert documented == actual, (
                    f"{path} says {documented} for "
                    f"({mechanical}, {major}, {minor}); the code says {actual}"
                )


def test_the_mechanical_term_is_the_heaviest_everywhere_it_is_written():
    """It is the only certain term, and the weighting is the argument.

    A document that swapped the coefficients would still look like a formula,
    and would quietly say that a model's reading of a paragraph costs more than
    a repeated sentence.
    """
    for path in WHERE_PROSE:
        a, b, c = coefficients(path)
        assert a > b > c, f"{path}: {a}, {b}, {c}"


OUTLINE = re.compile(r"10\s*[−-]\s*(\d+)\s*(?:·|per )missing")


def test_the_outline_formula_in_the_skill_matches_the_code():
    """The older instance of the same hazard, and it predates today."""
    text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    match = re.search(r"`10 − 3` per missing beat", text)
    assert match, "architecture.md no longer states the outline penalty"
    assert score_outline(missing=1, out_of_order=0) == 7
    assert score_outline(missing=0, out_of_order=1) == 9
    assert score_outline(missing=4, out_of_order=0) == 0, "floored at 0"


# ------------------------------------------- one home per constant

def test_the_gate_constants_are_written_once_in_python():
    """The threshold was in four places and the attempt limit in three.

    Both are on `AGENTS.md` §6's never-touched-without-a-spec list, which is an
    argument for each having exactly one home. A bare literal in a second module
    is how a spec-protected number gets changed by an edit nobody reviews.
    """
    offenders = []
    for path in sorted((ROOT / "backend").rglob("*.py")):
        if path.name.startswith("test_") or "__pycache__" in path.parts:
            continue
        if path == ROOT / "backend/chapters/domain.py":
            continue  # the one home
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"^\s*(THRESHOLD|MAX_ATTEMPTS)\w*\s*=\s*\d+\s*$", line):
                offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
            if re.search(r"max_attempts(: int)?\s*=\s*\d+", line):
                offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, offenders


def test_the_constants_the_config_owns_match_it():
    import json

    from backend.chapters.domain import MAX_ATTEMPTS_DEFAULT, THRESHOLD_DEFAULT

    config = json.loads((ROOT / "config/novel.config.json").read_text(encoding="utf-8"))
    gate = config["quality_gate"]
    assert THRESHOLD_DEFAULT == gate["threshold"]
    # Three attempts is one draft plus two revisions, and the config counts
    # revisions. The arithmetic is the only thing tying the two numbers together.
    assert MAX_ATTEMPTS_DEFAULT == gate["max_revisions"] + 1
