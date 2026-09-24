"""The judge is run at publication and leaves its six rows, or says why not.

The model call is injected; nothing here costs money.
"""

from __future__ import annotations

import json

from backend.commons.db import repository
from backend.publish import personalise, run_judge, validations

GOOD = {c: {"score": 8, "justification": f"{c} holds."} for c in
        ("continuity", "tone", "narrative_arc", "character_coherence", "pacing",
         "natural_personalisation")}


def _run(db, tmp_path):
    repository.create_run(db, run_id="r1", slug="gift", premise="p", profile="exam",
                          tone=None, snapshot="{}")
    d = tmp_path / "gift"
    (d / "chapters").mkdir(parents=True)
    (d / "chapters" / "ch01.md").write_text("# Chapter 1\n\nLeo woke.\n", encoding="utf-8")
    (d / "chapters" / "ch01.anon.md").write_text(
        f"# Chapter 1\n\n{personalise.TOKEN} woke.\n", encoding="utf-8")
    (d / "state.json").write_text(json.dumps({"tone": "warm"}), encoding="utf-8")
    return d


def test_the_book_the_judge_reads_is_the_anonymised_one(db, tmp_path):
    seen = []
    run_judge.run(db, _run(db, tmp_path), 1,
                  dispatch=lambda p: seen.append(p) or json.dumps(GOOD))
    assert personalise.TOKEN in seen[0] and "Leo woke" not in seen[0]


def test_six_rows_and_the_mean(db, tmp_path):
    run_judge.run(db, _run(db, tmp_path), 1, dispatch=lambda p: json.dumps(GOOD))
    rows = validations.for_version(db, "r1", 1, "judge_rubric")
    assert {r["criterion"] for r in rows} >= set(GOOD)


def test_a_reply_that_is_not_a_rubric_is_recorded_as_not_run(db, tmp_path):
    run_judge.run(db, _run(db, tmp_path), 1, dispatch=lambda p: "I liked it")
    rows = validations.for_version(db, "r1", 1, "judge_rubric")
    assert len(rows) == 1 and rows[0]["value"] is None
    assert rows[0]["justification"].startswith("not run")
