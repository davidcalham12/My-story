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
