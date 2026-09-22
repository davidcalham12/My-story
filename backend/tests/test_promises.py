"""Promises made to the reader, and whether the book owes them anywhere.

`bible/mysteries.md` is the only part of the Bible that commits to **when**: each
question names the chapter that plants it and the chapter that lands it. A
promise planted and never paid is the ontology's foreshadowing failure, and it is
the one literary defect a script can reach — because the Bible names chapters.

**One run of eleven wrote those lines.** The other ten hold promises in four
different formats and nothing can tell whether the book kept them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.chapters.check_promises import promises

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"

STATED = """# Mysteries

- **Who are the ships the Commissioners cannot name?**
  - True: Ada copies them off the petitions.
  - Planted: Chapter 1, Nell's petition on the step.
  - Lands: Chapter 3, when Creed asks her outright.
"""


def run(run_dir: Path):
    return subprocess.run(
        [sys.executable, "-m", "backend.chapters.check_promises", str(run_dir)],
        capture_output=True, text=True, cwd=ROOT)


def build(tmp: Path, mysteries: str, chapters: int) -> Path:
    (tmp / "bible").mkdir(exist_ok=True)
    (tmp / "chapters").mkdir(exist_ok=True)
    (tmp / "bible" / "mysteries.md").write_text(mysteries, encoding="utf-8")
    for n in range(1, chapters + 1):
        (tmp / "chapters" / f"ch{n:02d}.md").write_text(f"# Chapter {n} — A\n\nx.\n",
                                                         encoding="utf-8")
    return tmp


def test_the_shape_is_parsed():
    found = promises(STATED)
    assert len(found) == 1
    assert found[0]["planted"] == 1 and found[0]["lands"] == 3


def test_a_coherent_promise_passes(tmp_path):
    build(tmp_path, STATED, 3)
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "coherent"


def test_a_promise_naming_no_chapters_is_unstated_not_kept(tmp_path):
    """The distinction the whole script exists for.

    A file whose promises name no chapters is not a book that kept them. It is
    one where the question cannot be asked — and reporting that as success is
    the absent-read-as-clean mistake in its literary form.
    """
    build(tmp_path, "# Mysteries\n\n- **Who wrote it?**\n  - True: Walter.\n", 3)
    out = json.loads(run(tmp_path).stdout)
    assert out["status"] == "unstated"
    assert out["status"] != "coherent"


def test_a_promise_landing_before_it_is_planted_is_caught(tmp_path):
    build(tmp_path, STATED.replace("Lands: Chapter 3", "Lands: Chapter 1")
                          .replace("Planted: Chapter 1", "Planted: Chapter 2"), 3)
    result = run(tmp_path)
    assert result.returncode == 1
    assert "lands before it is planted" in json.loads(result.stdout)["problems"]


def test_a_promise_landing_past_the_last_chapter_is_caught(tmp_path):
    """The foreshadowing failure, in the only form a script can see: the book
    ends before the chapter that owed the answer."""
    build(tmp_path, STATED, 2)
    result = run(tmp_path)
    assert result.returncode == 1
    assert "lands past the last chapter" in json.loads(result.stdout)["problems"]


def test_a_promise_landing_in_a_chapter_the_run_never_wrote_is_caught(tmp_path):
    build(tmp_path, STATED, 3)
    (tmp_path / "chapters" / "ch03.md").unlink()
    (tmp_path / "chapters" / "ch04.md").write_text("# Chapter 4 — A\n\nx.\n",
                                                    encoding="utf-8")
    assert run(tmp_path).returncode == 1


def test_the_report_says_what_it_cannot_read(tmp_path):
    """It reads a commitment; it does not read the chapter. A chapter that says
    nothing about a mystery it was supposed to land passes this and fails a
    reader."""
    build(tmp_path, STATED, 3)
    assert "does not read the chapter" in json.loads(run(tmp_path).stdout)["not_checked"]


def test_the_character_architect_is_told_the_shape():
    """The fix is at the source. Four runs wrote four formats because nobody
    said which — the same defect as v1's three critique shapes."""
    prompt = (ROOT / ".claude/agents/character-architect.md").read_text(encoding="utf-8")
    assert "Planted: Chapter" in prompt
    assert "Lands: Chapter" in prompt


@pytest.mark.parametrize("slug", sorted(
    p.parent.parent.name for p in OUTPUT.glob("*/bible/mysteries.md")))
def test_no_existing_run_has_an_incoherent_promise(slug):
    """Most report `unstated`, which is the finding rather than a pass.

    None is incoherent: no run promises a landing in a chapter that was never
    written. That is worth knowing, and it is a weaker statement than it looks —
    ten of them state no chapters at all, so there was nothing to contradict.
    """
    out = json.loads(run(OUTPUT / slug).stdout)
    assert out["status"] in {"coherent", "unstated"}, out["problems"]
