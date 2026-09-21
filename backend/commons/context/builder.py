"""Building each agent's packet. The one place a packet is made.

G1 is only true if this is the only builder: a type with no field for prose is a
guarantee, and a second construction site that assembles prompts by hand is a
hole in it.
"""

from __future__ import annotations

from backend.commons.context.packets import (
    BiblePacket,
    CriticPacket,
    PlainPacket,
    WriterPacket,
)


def writer_packet(
    *,
    model: str,
    premise: str,
    tone: str,
    bible: dict[str, str],
    outline_entry: str,
    rolling_summary: str,
    names: tuple[str, ...],
    chapter: int,
    title: str,
    target_words: int,
    band: tuple[int, int],
    previous_draft: str = "",
    sheet: str = "",
) -> WriterPacket:
    """The writer's context.

    Note what is NOT a parameter: any other chapter's text. It cannot be passed
    because there is nothing to pass it to, which is the whole of G1.
    """
    return WriterPacket(
        agent="chapter-writer", model=model, premise=premise, tone=tone,
        world=bible.get("world", ""), characters=bible.get("characters", ""),
        timeline=bible.get("timeline", ""), mysteries=bible.get("mysteries", ""),
        outline_entry=outline_entry, rolling_summary=rolling_summary,
        canonical_names=names, chapter=chapter, title=title,
        target_words=target_words, band=band,
        previous_draft=previous_draft, sheet=sheet,
    )


def critic_packet(*, which: str, model: str, premise: str, tone: str,
                  draft: str, reference: str, complete: bool, chapter: int) -> CriticPacket:
    return CriticPacket(
        agent=f"{which}-critic", model=model, premise=premise, tone=tone,
        draft=draft, reference=reference, reference_is_complete=complete,
        chapter=chapter,
    )


def bible_packet(*, agent: str, model: str, premise: str, tone: str,
                 instructions: str, counts: str, world: str = "",
                 names_rule: str = "familiar") -> BiblePacket:
    return BiblePacket(
        agent=agent, model=model, premise=premise, tone=tone,
        instructions=instructions, counts=counts, world=world,
        names_rule=names_rule,
    )


def plain_packet(*, agent: str, model: str, premise: str, tone: str,
                 body: str) -> PlainPacket:
    return PlainPacket(agent=agent, model=model, premise=premise, tone=tone, body=body)
