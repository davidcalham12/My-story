"""G1 — the writer never receives a previous chapter's prose.

These tests read the TYPE, not an instance. They fail when the class gains a
field, at the moment somebody writes it, rather than the first time a run happens
to fill it.
"""

from dataclasses import fields

import pytest

from backend.commons.context.packets import (
    PROSE_FIELD_NAMES,
    CriticPacket,
    WriterPacket,
    carries_prose_field,
)


def test_writer_packet_has_no_prose_field():
    assert carries_prose_field(WriterPacket) == []


def test_writer_packet_fields_are_the_expected_set():
    """A closed list, so an addition is a deliberate decision and not a drift.

    If this fails because a field was added on purpose, the guarantee in
    docs/verification.md G1 has to be re-read before the list is updated - which
    is exactly the pause this test exists to create.
    """
    got = {f.name for f in fields(WriterPacket)}
    expected = {
        "agent", "model", "premise", "tone",
        "world", "characters", "timeline", "mysteries",
        "outline_entry", "rolling_summary", "canonical_names",
        "chapter", "title", "target_words", "band",
        "previous_draft", "sheet",
    }
    assert got == expected


def test_previous_draft_is_this_chapter_not_another():
    """The one field that holds prose holds the writer's OWN rejected draft.

    The policy forbids a *previous chapter's* prose. Handing back findings
    without the text they quote is what once made redrafts come back worse than
    what they replaced.
    """
    packet = WriterPacket(
        agent="chapter-writer", model="m", premise="p", tone="t",
        chapter=4, previous_draft="my own rejected attempt at chapter 4",
    )
    rendered = packet.render()
    assert "rejected draft of this chapter" in rendered.lower()
    assert "chapter 4" in rendered.lower()


def test_packet_is_frozen():
    packet = WriterPacket(agent="w", model="m", premise="p", tone="t")
    with pytest.raises(Exception):
        packet.world = "mutated"  # type: ignore[misc]


def test_critic_packet_says_when_its_reference_is_partial():
    """A rule not retrieved is a violation nobody looked for, so a critic given
    fragments must be told they are fragments."""
    whole = CriticPacket(agent="science-critic", model="m", premise="p", tone="t",
                         draft="d", reference="all the rules", reference_is_complete=True)
    part = CriticPacket(agent="continuity-critic", model="m", premise="p", tone="t",
                        draft="d", reference="some bible", reference_is_complete=False)
    assert "retrieved fragments" not in whole.render()
    assert "retrieved fragments" in part.render()


def test_prose_field_names_is_not_empty():
    """The guard list itself must have content, or the G1 test passes vacuously."""
    assert len(PROSE_FIELD_NAMES) >= 5
