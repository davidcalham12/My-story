"""G1, back to being structural.

Under Annex C, Claude Code orchestrates and the nine agents are subagents again.
So the guarantee returns to what it was in v1 and to the strongest form this
project has ever had:

**The chapter writer holds `tools: Glob`. `Glob` returns paths and cannot return
contents, so a previous chapter's prose is UNREACHABLE — not merely not passed.**

That is class **A**, not **T**: the capability is absent rather than unused. The
typed `ContextPacket` that briefly replaced it was weaker, and these tests exist
so the line cannot be edited without something going red.
"""

import re
from pathlib import Path

import pytest

AGENTS = Path(__file__).resolve().parents[2] / ".claude" / "agents"

# The tool list IS the authority model. Each of these was chosen; none is
# incidental.
EXPECTED = {
    # Only these two produce the Story Bible. Everything else returns text and
    # the orchestrator writes the file.
    "worldbuilder": {"Read", "Write"},
    "character-architect": {"Read", "Write"},
    # Glob returns paths. It cannot return contents.
    "plot-architect": {"Glob"},
    "chapter-writer": {"Glob"},
    "continuity-critic": {"Glob"},
    "science-critic": {"Glob"},
    "outline-critic": {"Glob"},
    "style-editor": {"Glob"},
    "publisher": {"Glob"},
}

# Anything that can return a file's CONTENTS. The writer may hold none of them.
READERS = {"Read", "Grep", "Bash", "NotebookRead", "WebFetch", "Task", "Agent"}


def front_matter(name: str) -> dict[str, str]:
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{name}.md has no front matter"
    out = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def tools_of(name: str) -> set[str]:
    raw = front_matter(name).get("tools", "")
    return {t.strip() for t in raw.split(",") if t.strip()}


def test_every_agent_file_exists():
    for name in EXPECTED:
        assert (AGENTS / f"{name}.md").exists(), name


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_the_tool_list_is_exactly_what_was_chosen(name):
    assert tools_of(name) == EXPECTED[name]


def test_the_chapter_writer_cannot_read_anything():
    """The project's central claim, as a property of a capability.

    If this fails, the guarantee in docs/verification.md G1 has changed class and
    the document has to change with it — not the other way round.
    """
    assert tools_of("chapter-writer") & READERS == set()


def test_no_critic_can_read_a_file():
    """A critic that could fetch its own context would hold exactly the
    capability the writer is denied. Retrieval reaches them because the
    ORCHESTRATOR runs the search and pastes the fragments in."""
    for name in ("continuity-critic", "science-critic", "outline-critic"):
        assert tools_of(name) & READERS == set(), name


def test_only_two_agents_can_write():
    writers = {name for name in EXPECTED if "Write" in tools_of(name)}
    assert writers == {"worldbuilder", "character-architect"}


def test_no_agent_declares_a_genre():
    """All nine once opened by calling themselves hard science fiction, and a
    premise about a pop star trying quesadillas came back with factions and a
    bandwidth budget."""
    for name in EXPECTED:
        body = (AGENTS / f"{name}.md").read_text(encoding="utf-8").lower()
        opener = body.split("---", 2)[-1].strip()[:400]
        assert "for a hard-scifi novel" not in opener, name


def test_every_agent_names_its_model():
    for name in EXPECTED:
        assert front_matter(name).get("model") in ("opus", "sonnet"), name
