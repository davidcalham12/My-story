"""Promotion, by a script that can refuse.

On the eight-chapter run, chapter 3 scored `continuity` 5 and was copied to
`ch03.md` anyway. Writing that file was a one-line copy and nothing stood between
the copy and the book.

These drive the refusal on the case that actually happened, and the acceptance on
the cases beside it. The script cannot make the violation impossible — the
orchestrator holds `Write` and always will — but it removes the version where
nothing says no.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.chapters.domain import CHARACTERISTICS

ROOT = Path(__file__).resolve().parents[2]


def run(run_dir: Path, chapter: int, attempt: int | None = None):
    args = [sys.executable, "-m", "backend.chapters.promote", str(run_dir), str(chapter)]
    if attempt is not None:
        args.append(str(attempt))
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)


def build(tmp: Path, per_attempt: dict[int, dict[str, int | None]]) -> Path:
    (tmp / "chapters").mkdir(exist_ok=True)
    (tmp / "critiques").mkdir(exist_ok=True)
    for attempt in per_attempt:
        (tmp / "chapters" / f"ch03.attempt{attempt}.md").write_text(
            f"# Chapter 3 — A\n\nDraft {attempt}.\n", encoding="utf-8")
    critics = {c for scores in per_attempt.values() for c in scores}
    for critic in critics:
        (tmp / "critiques" / f"ch03.{critic}.json").write_text(json.dumps({
            "critic": critic, "chapter": 3, "drafts": len(per_attempt),
            "iterations": [{"iteration": a, "score": s.get(critic), "findings": []}
                           for a, s in sorted(per_attempt.items())],
        }), encoding="utf-8")
    return tmp


FIVE = tuple(c for c in CHARACTERISTICS if c != "prose")


def passing(**over) -> dict:
    return {**{c: 10 for c in FIVE}, **over}


def test_a_passing_chapter_is_promoted(tmp_path):
    build(tmp_path, {1: passing()})
    result = run(tmp_path, 3)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "chapters" / "ch03.md").exists()
    assert json.loads(result.stdout)["promoted"] is True


def test_the_case_that_actually_happened_is_refused(tmp_path):
    """Chapter 3: continuity 2, then 5, promoted anyway."""
    build(tmp_path, {1: passing(continuity=2), 2: passing(continuity=5)})
    result = run(tmp_path, 3)
    assert result.returncode == 1
    assert not (tmp_path / "chapters" / "ch03.md").exists(), "it wrote the file anyway"
    assert "REFUSED" in result.stderr
    assert json.loads(result.stdout)["aggregate"] == 5


def test_a_refusal_leaves_an_existing_chapter_untouched(tmp_path):
    """It must not half-promote: a refusal that truncated the previous file
    would be worse than the copy it replaced."""
    build(tmp_path, {1: passing(continuity=4)})
    book = tmp_path / "chapters" / "ch03.md"
    book.write_text("# Chapter 3 — A\n\nSomething earlier.\n", encoding="utf-8")
    assert run(tmp_path, 3).returncode == 1
    assert "Something earlier" in book.read_text(encoding="utf-8")


def test_a_chapter_nothing_judged_is_refused(tmp_path):
    """Worse than one that failed: nothing has looked at it at all."""
    (tmp_path / "chapters").mkdir()
    (tmp_path / "critiques").mkdir()
    (tmp_path / "chapters" / "ch03.attempt1.md").write_text("# Chapter 3 — A\n\nx.\n",
                                                            encoding="utf-8")
    result = run(tmp_path, 3)
    assert result.returncode == 1
    assert "no critiques" in result.stderr
    assert not (tmp_path / "chapters" / "ch03.md").exists()


def test_a_gate_one_critic_short_is_refused(tmp_path):
    """The critic ran and returned nothing usable. A weaker gate, not a passing
    one — the rule that once returned 10 and shipped a draft."""
    build(tmp_path, {1: passing(continuity=None)})
    result = run(tmp_path, 3)
    assert result.returncode == 1
    assert not (tmp_path / "chapters" / "ch03.md").exists()


def test_a_run_without_the_sixth_characteristic_can_still_promote(tmp_path):
    """Judged by the gate it ran. A characteristic with no critique file did not
    exist for this run and is not a critic that failed to answer."""
    build(tmp_path, {1: passing()})
    out = json.loads(run(tmp_path, 3).stdout)
    assert "prose" not in out["gate"]
    assert out["promoted"] is True


def test_it_promotes_the_last_draft_when_no_attempt_is_named(tmp_path):
    build(tmp_path, {1: passing(continuity=4), 2: passing()})
    out = json.loads(run(tmp_path, 3).stdout)
    assert out["attempt"] == 2
    assert "Draft 2" in (tmp_path / "chapters" / "ch03.md").read_text(encoding="utf-8")
