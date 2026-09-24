"""SPEC-EXAM-004: one critic reads the Bible once and scores three
characteristics; the procedure dispatches two model critics, not four."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = (ROOT / ".claude" / "skills" / "storymaker" / "SKILL.md").read_text(encoding="utf-8")
CHAPTER = (ROOT / ".claude" / "skills" / "storymaker" / "units" / "chapter.md").read_text(encoding="utf-8")
AGENT = ROOT / ".claude" / "agents" / "bible-critic.md"


def test_ac1_the_agent_runs_on_haiku():
    head = AGENT.read_text(encoding="utf-8").split("---")[1]
    assert re.search(r"^model:\s*haiku\s*$", head, re.M)


def test_ac1_it_answers_with_the_three_keys():
    text = AGENT.read_text(encoding="utf-8")
    for key in ('"continuity"', '"science"', '"outline"'):
        assert key in text


def test_ac2_the_procedure_dispatches_two_model_critics():
    for doc in (SKILL, CHAPTER):
        assert "bible-critic" in doc
        for old in ("`continuity-critic`", "`science-critic`", "`outline-critic`"):
            assert old not in doc, old
    assert "four model critics" not in CHAPTER
    assert "two model critics" in CHAPTER


def test_ac3_each_key_lands_in_its_old_file_and_missing_is_unscored():
    for doc in (SKILL, CHAPTER):
        assert "critiques/chNN.<characteristic>.json" in doc or "chNN.continuity.json" in doc
        assert re.search(r"missing .*key.*unscored|key .*missing.*unscored", doc, re.I | re.S)


def test_ac4_the_watcher_knows_it():
    from backend.commons.runner.watch import AGENTS
    assert "bible-critic" in AGENTS
