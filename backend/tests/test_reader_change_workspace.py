"""The reader change's workspace: what the chapter unit is given to rewrite from.

Only the preparation is tested; the `claude -p` call is demonstrated (E8).
"""

from __future__ import annotations

from backend.versions import change


def _run_dir(tmp_path):
    d = tmp_path / "gift"
    for sub in ("bible", "chapters"):
        (d / sub).mkdir(parents=True)
    (d / "bible" / "world.md").write_text("Alias has the cardboard observatory.\n", encoding="utf-8")
    (d / "bible" / "world.anon.md").write_text("[NOMBRE_ANONIMIZADO] has the cardboard observatory.\n", encoding="utf-8")
    (d / "outline.md").write_text("Alias; the cardboard observatory\n", encoding="utf-8")
    (d / "outline.anon.md").write_text("[NOMBRE_ANONIMIZADO]; the cardboard observatory\n", encoding="utf-8")
    (d / "config.snapshot.json").write_text("{}", encoding="utf-8")
    (d / "state.json").write_text("{}", encoding="utf-8")
    (d / "chapters" / "ch02.summary.md").write_text("summary two", encoding="utf-8")
    (d / "chapters" / "ch03.md").write_text("v1 prose", encoding="utf-8")
    return d


def test_the_workspace_carries_the_change_and_never_the_name(tmp_path):
    d = _run_dir(tmp_path)
    ws = d / "dist" / "v2"
    ws.mkdir(parents=True)
    change.prepare_workspace(d, ws, (3,), old="the cardboard observatory",
                             to="the wooden treehouse")
    world = (ws / "bible" / "world.md").read_text(encoding="utf-8")
    assert "the wooden treehouse" in world and "cardboard" not in world
    assert "[NOMBRE_ANONIMIZADO]" in world, "the model is given the anonymised Bible"
    assert "the wooden treehouse" in (ws / "outline.md").read_text(encoding="utf-8")
    assert (ws / "chapters" / "ch02.summary.md").is_file()
    assert not (ws / "chapters" / "ch03.md").exists(), "v1's prose is not handed over"
    assert not (ws / "bible" / "world.anon.md").exists()


def test_a_pinned_procedure_is_written_into_the_workspace(tmp_path):
    """The demo runs on the system the book was written with (owner, 2026-09-24):
    the chapter procedure and the skill are taken from a named revision, and the
    prompt points at the pinned copies."""
    ws = tmp_path / "v3"
    ws.mkdir()
    prompt = change.pin_procedure(ws, "c35fdc9^",
                                  "procedure: .claude/skills/storymaker/units/chapter.md\n")
    pinned = ws / "procedure" / "chapter.md"
    assert pinned.is_file() and (ws / "procedure" / "SKILL.md").is_file()
    assert "bible-critic" not in pinned.read_text(encoding="utf-8")
    assert str(pinned) in prompt and "units/chapter.md" not in prompt
    assert str(ws / "procedure" / "SKILL.md") in pinned.read_text(encoding="utf-8")


# ------------------------------------------- the model, and why a change stopped


def test_a_reader_change_runs_on_the_profiles_orchestrator_model():
    """The novel's snapshot predates `models.orchestrator`; the change takes the
    model its profile says NOW, so exam runs on sonnet, not the CLI default."""
    assert change.orchestrator_model("exam") == "sonnet"
    process = change.unit_process("prompt", model="sonnet", max_budget_usd=12.5)
    assert process.command[process.command.index("--model") + 1] == "sonnet"
    assert process.command[process.command.index("--max-budget-usd") + 1] == "12.5"


def test_a_cut_by_the_org_limit_is_budget_not_gate():
    limit = {"type": "result", "is_error": True, "subtype": "success",
             "result": "You've hit your org's monthly spend limit · run /usage-credits"}
    assert change.cut_reason([limit]) == "budget"
    assert change.cut_reason([{"type": "result", "subtype": "error_max_budget_usd",
                               "is_error": True}]) == "budget"
    assert change.cut_reason([{"type": "result", "is_error": True,
                               "result": "API Error: 529 overloaded"}]) == "api"
    assert change.cut_reason([{"type": "result", "is_error": False,
                               "result": "done"}]) is None


def test_main_reports_a_cut_unit_as_budget(db, tmp_path, capsys):
    from backend.commons.db import repository
    repository.create_run(db, run_id="r1", slug="gift", premise="p", profile="exam",
                          tone=None, snapshot="{}")
    d = tmp_path / "gift"
    (d / "chapters").mkdir(parents=True)
    with db:
        db.execute("INSERT INTO facts (id, run_id, kind, text, source) VALUES "
                   "(1, 'r1', 'recipient', 'the cardboard observatory', 'brief')")
        db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) "
                   "VALUES (1, 1, 3, 'x')")
        db.execute("INSERT INTO versions (run_id, n, parent, reason, created_at) "
                   "VALUES ('r1', 1, NULL, 'first', 't')")

    def cut(*a, **k):
        raise change.UnitCut("budget", 3)

    rc = change.main(["change", "gift", "--fact", "1", "--to", "x"], conn=db,
                     output_dir=tmp_path, regenerate=cut)
    out = capsys.readouterr()
    assert rc == 1 and '"halted": "budget"' in out.out and "gate" not in out.err


# ------------------------- a change that does not arrive is not a change (§8)

OLD, NEW = "the cardboard observatory", "the wooden treehouse observatory"


def test_arrival_needs_the_new_text_and_no_variant_of_the_old():
    assert change.arrival(f"He climbed into {NEW} at dusk.", new=NEW, old=OLD) is None
    assert "missing" in change.arrival("He climbed the hill.", new=NEW, old=OLD)
    both = f"He left {NEW} and the Cardboard Observatories behind."
    assert "still" in change.arrival(both, new=NEW, old=OLD)


def test_the_workspace_replaces_the_old_texts_variants(tmp_path):
    d = _run_dir(tmp_path)
    (d / "bible" / "characters.md").write_text(
        "Marcos, a builder of cardboard observatories. The Cardboard Observatory.\n",
        encoding="utf-8")
    ws = d / "dist" / "v2"; ws.mkdir(parents=True)
    change.prepare_workspace(d, ws, (3,), old=OLD, to=NEW)
    text = (ws / "bible" / "characters.md").read_text(encoding="utf-8").lower()
    assert "cardboard" not in text and "wooden treehouse observator" in text


def _published_run(db, tmp_path):
    from backend.commons.db import repository
    repository.create_run(db, run_id="r1", slug="gift", premise="p", profile="exam",
                          tone=None, snapshot="{}")
    d = tmp_path / "gift"
    (d / "chapters").mkdir(parents=True)
    with db:
        db.execute("INSERT INTO facts (id, run_id, kind, text, source) VALUES "
                   "(1, 'r1', 'recipient', ?, 'brief')", (OLD,))
        db.execute("INSERT INTO fact_usage (fact_id, version_id, chapter, matched) "
                   "VALUES (1, 1, 3, 'x')")
        db.execute("INSERT INTO versions (run_id, n, parent, reason, created_at) "
                   "VALUES ('r1', 1, NULL, 'first', 't')")
    return d


def test_a_promoted_chapter_without_the_new_fact_is_not_published(db, tmp_path, capsys):
    d = _published_run(db, tmp_path)

    def promotes_without_the_fact(run_dir, ws, chapters, fact, to):
        (ws / "chapters").mkdir(parents=True, exist_ok=True)
        (ws / "chapters" / "ch03.md").write_text("# Chapter 3\n\nNo observatory here.\n",
                                                 encoding="utf-8")
        return {3: True}

    rc = change.main(["change", "gift", "--fact", "1", "--to", NEW], conn=db,
                     output_dir=tmp_path, regenerate=promotes_without_the_fact)
    out = capsys.readouterr().out
    assert rc == 1 and '"halted": "fact"' in out
    assert not (d / "dist" / "v2" / "chapters" / "ch03.md").exists()
    assert list((d / "dist" / "v2" / "chapters").glob("ch03.rejected-*.md"))


def test_redo_reuses_the_workspace_and_sets_the_old_chapter_aside(db, tmp_path):
    d = _published_run(db, tmp_path)
    ws = d / "dist" / "v2"
    (ws / "chapters").mkdir(parents=True)
    (ws / "chapters" / "ch03.md").write_text("old promoted", encoding="utf-8")
    (ws / "chapters" / "ch03.attempt1.md").write_text("old draft", encoding="utf-8")
    seen = {}

    def redo(run_dir, workspace, chapters, fact, to):
        seen["ws"], seen["chapters"] = workspace, chapters
        assert not (workspace / "chapters" / "ch03.attempt1.md").exists()
        (workspace / "chapters" / "ch03.md").write_text(f"# Chapter 3\n\n{NEW}.\n",
                                                        encoding="utf-8")
        return {3: True}

    rc = change.main(["change", "gift", "--fact", "1", "--to", NEW, "--workspace", "v2",
                      "--only", "3"], conn=db, output_dir=tmp_path, regenerate=redo)
    assert seen == {"ws": ws, "chapters": (3,)}
    assert any(p.is_dir() for p in (ws / "chapters").glob("_redo-*"))
    assert rc == 0 and (ws / "novel.html").is_file()


def test_another_cardboard_object_is_not_the_old_fact():
    """ch10 of v3 keeps 'the cardboard telescope', a different object: the old
    fact is the phrase, not the word."""
    text = f"She raised the cardboard telescope toward {NEW}."
    assert change.arrival(text, new=NEW, old=OLD) is None
