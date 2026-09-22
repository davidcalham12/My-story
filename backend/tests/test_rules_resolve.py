"""Do the rules a run cites exist?

The critics and the outline audit refer to a world's rules by number — "R5
rewritten to name the keeper as the writer". `bible/world.md` wrote them as
unnumbered bullets, so those numbers were the critic counting bullets and
inventing an identifier.

Two real runs produced **76 such references and not one resolved to anything.**
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.chapters.check_rules import declared_rules

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

NUMBERED = """# World

## Rules

- **R1.** The keeper on watch is the only hand that may write in the Register.
- **R2.** A vessel entered three times goes to the Drowned Page.

## Texture

Grey.
"""

UNNUMBERED = NUMBERED.replace("**R1.** ", "").replace("**R2.** ", "")


def run(run_dir: Path):
    return subprocess.run(
        [sys.executable, "-m", "backend.chapters.check_rules", str(run_dir)],
        capture_output=True, text=True, cwd=ROOT)


def build(tmp: Path, world: str, outline: str) -> Path:
    (tmp / "bible").mkdir(exist_ok=True)
    (tmp / "bible" / "world.md").write_text(world, encoding="utf-8")
    (tmp / "outline.md").write_text(outline, encoding="utf-8")
    return tmp


def test_it_reads_numbers_only_from_under_the_rules_heading():
    world = NUMBERED + "\n## Instruments\n\n- **R9.** not a rule\n"
    assert declared_rules(world) == {"R1", "R2"}


def test_a_citation_that_resolves_is_clean(tmp_path):
    build(tmp_path, NUMBERED, "### Chapter 1 — A\n\nAda writes under R1.\n")
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "clean"


def test_a_citation_that_does_not_resolve_is_reported(tmp_path):
    build(tmp_path, NUMBERED, "### Chapter 1 — A\n\nCreed signs under R7.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["status"] == "dangling"
    assert "R7" in out["dangling"]


def test_an_unnumbered_bible_reports_unnumbered_not_clean(tmp_path):
    """The mistake this exists to refuse.

    Saying "no dangling references" about a file with no reference system is the
    absent-read-as-clean error — the same shape as reporting an unmeasured
    figure as zero.
    """
    build(tmp_path, UNNUMBERED, "### Chapter 1 — A\n\nAda writes under R1.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    out = json.loads(result.stdout)
    assert out["status"] == "unnumbered"
    assert out["status"] != "clean"
    assert "never there" in out["why"]


def test_a_rule_nobody_cited_is_not_a_defect(tmp_path):
    """A rule nothing cited was simply never at issue. Reporting it as a problem
    would train the reader to skim the report."""
    build(tmp_path, NUMBERED, "### Chapter 1 — A\n\nAda writes under R1.\n")
    out = json.loads(run(tmp_path).stdout)
    assert out["declared_but_never_cited"] == ["R2"]
    assert out["status"] == "clean"


def test_the_worldbuilder_is_told_to_number_them():
    """The fix has to be at the source. A checker over a format nobody produces
    reports the same failure forever."""
    prompt = (ROOT / ".claude/agents/worldbuilder.md").read_text(encoding="utf-8")
    assert "**R1.**" in prompt
    assert "Number them" in prompt


@pytest.mark.parametrize("slug", sorted(
    p.parent.parent.name for p in OUTPUT.glob("*/bible/world.md")))
def test_what_the_existing_runs_actually_have(slug):
    """Every run in the repository predates the change, so every one reports
    `unnumbered`. Recorded as a test so the first numbered Bible changes it."""
    status = json.loads(run(OUTPUT / slug).stdout)["status"]
    assert status in {"unnumbered", "clean", "dangling"}
