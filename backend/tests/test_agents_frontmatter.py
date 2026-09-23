"""G1, back to being structural.

Under Annex C, Claude Code orchestrates and the agents are subagents again.
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
    # SPEC-006. It judges the writing, so it needs the draft and nothing else —
    # the same tool list as the critics it joins.
    "prose-critic": {"Glob"},
    "style-editor": {"Glob"},
    "publisher": {"Glob"},
    # SPEC-EXAM-001 §3. FLOW-0: it extracts what the buyer said and asks for what
    # is missing. Every decision — missing field, contradiction — is code's
    # (`backend/brief/domain.py`), which is why it needs no tool but `Glob`.
    "interviewer": {"Glob"},
    # SPEC-EXAM-001 §2. The publish gate's rubric: it reads the assembled book
    # and nothing else, so it holds what the critics hold.
    "judge": {"Glob"},
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


def test_every_agent_file_exists_and_every_file_is_expected():
    """Both directions, and the second one was missing.

    Every test in this file iterated over EXPECTED, so **a new agent file was
    invisible to all of them**: one could be added holding `Read` and `Bash` and
    nothing here would go red. The authority model's own test could not see a
    new authority. SPEC-006 added the tenth agent and this is what noticed.
    """
    on_disk = {p.stem for p in AGENTS.glob("*.md")}
    assert on_disk == set(EXPECTED), (
        f"undeclared agent files: {sorted(on_disk - set(EXPECTED))}; "
        f"declared and missing: {sorted(set(EXPECTED) - on_disk)}"
    )


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
    for name in EXPECTED:
        if name.endswith("-critic"):
            assert tools_of(name) & READERS == set(), name


def test_only_two_agents_can_write():
    writers = {name for name in EXPECTED if "Write" in tools_of(name)}
    assert writers == {"worldbuilder", "character-architect"}


def test_no_agent_declares_a_genre():
    """They once all opened by calling themselves hard science fiction, and a
    premise about a pop star trying quesadillas came back with factions and a
    bandwidth budget."""
    for name in EXPECTED:
        body = (AGENTS / f"{name}.md").read_text(encoding="utf-8").lower()
        opener = body.split("---", 2)[-1].strip()[:400]
        assert "for a hard-scifi novel" not in opener, name


def test_every_agent_names_its_model():
    for name in EXPECTED:
        assert front_matter(name).get("model") in ("opus", "sonnet", "haiku"), name  # haiku since SPEC-011
