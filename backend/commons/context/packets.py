"""What each agent is handed. The boundary is the type.

In v1 the chapter writer was a subagent whose tool list held `Glob`, which
returns paths and cannot return contents: a previous chapter's prose was
*unreachable*. Calling the API directly gives that up, and this module is the
replacement — **what an agent cannot be handed, it cannot read.**

That is a weaker class of evidence than v1's and `docs/verification.md` G1 says
so rather than inheriting the old language. It is only true while these types
stay closed and every packet is built here, which is what the tests hold.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

# Names that would mean a packet had gained a way to carry another chapter's
# prose. Checked by a test, not by convention: this list is how the guarantee
# fails loudly if someone adds a convenient field.
PROSE_FIELD_NAMES = frozenset(
    {"prose", "previous_chapter", "previous_chapters", "chapters",
     "full_text", "manuscript", "book", "prior_prose", "earlier_chapters"}
)


@dataclass(frozen=True)
class Packet:
    """Common to every agent's context."""

    agent: str
    model: str
    premise: str
    tone: str

    def render(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


def _join(*parts: str) -> str:
    return "\n".join(p for p in parts if p)


@dataclass(frozen=True)
class WriterPacket(Packet):
    """The chapter writer's context. **The one that matters.**

    Every field here is either canon, this chapter's own commission, or a
    projection of the rolling summary. There is deliberately no field for another
    chapter's text, and `test_context.py` fails if one appears.

    `previous_draft` is not an exception. The policy forbids a *previous
    chapter's* prose; this is the writer's own rejected attempt at the chapter it
    is writing right now. Handing back findings without the text they quote is
    what once made redrafts come back worse than what they replaced.
    """

    world: str = ""
    characters: str = ""
    timeline: str = ""
    mysteries: str = ""
    outline_entry: str = ""          # THIS chapter only
    rolling_summary: str = ""        # projected from facts, never raw prose
    canonical_names: tuple[str, ...] = ()
    chapter: int = 0
    title: str = ""
    target_words: int = 0
    band: tuple[int, int] = (0, 0)
    previous_draft: str = ""         # its own, this chapter, on a redraft
    sheet: str = ""                  # the feedback sheet, on a redraft

    def render(self) -> str:
        names = ", ".join(self.canonical_names)
        return _join(
            f"You are writing chapter {self.chapter}, titled \"{self.title}\".",
            f"Tone: {self.tone}. Target {self.target_words} words; "
            f"the accepted band is {self.band[0]}-{self.band[1]}.",
            f'Open with "# Chapter {self.chapter} - {self.title}" and then prose.',
            f"Canonical names, spell exactly: {names}" if names else "",
            "",
            "The story so far - this is all you get, and it is deliberate:",
            self.rolling_summary or "(nothing; this is the first chapter)",
            "",
            "Your outline entry, this chapter only:",
            self.outline_entry,
            "",
            "The Story Bible:",
            self.world, self.characters, self.timeline, self.mysteries,
            "",
            ("--- YOUR REJECTED DRAFT OF THIS CHAPTER ---\n" + self.previous_draft)
            if self.previous_draft else "",
            self.sheet,
        )


@dataclass(frozen=True)
class CriticPacket(Packet):
    """A critic's context. What it is given decides what it can enforce.

    `science` and `outline` receive their reference material WHOLE and never
    retrieved: a rule not retrieved is a violation nobody looked for. Only
    `continuity` takes fragments, because the Bible is large and its findings are
    about specific passages.
    """

    draft: str = ""
    reference: str = ""              # whole for science/outline, fragments for continuity
    reference_is_complete: bool = True
    chapter: int = 0

    def render(self) -> str:
        return _join(
            "Judge this chapter draft. Return JSON only, no code fence.",
            "",
            "The draft:", "", self.draft, "",
            "What you judge it against"
            + ("" if self.reference_is_complete else " (retrieved fragments)")
            + ":",
            "", self.reference,
        )


@dataclass(frozen=True)
class BiblePacket(Packet):
    """worldbuilder and character-architect. The only two that produce canon."""

    instructions: str = ""
    counts: str = ""
    world: str = ""                  # character-architect receives it; worldbuilder does not
    names_rule: str = "familiar"

    def render(self) -> str:
        return _join(
            f"Premise, verbatim: {self.premise}",
            f"Tone: {self.tone}.",
            self.counts,
            f"Names: {self.names_rule}.",
            "", self.instructions,
            ("\nbible/world.md, in full:\n" + self.world) if self.world else "",
        )


@dataclass(frozen=True)
class PlainPacket(Packet):
    """plot-architect, style-editor, publisher: a body and nothing surprising."""

    body: str = ""

    def render(self) -> str:
        return _join(f"Tone: {self.tone}.", "", self.body)


def carries_prose_field(packet_type: type) -> list[str]:
    """Field names on a packet that could carry another chapter's prose.

    Used by the test that holds G1. It reads the type rather than an instance,
    so it fails when the *class* gains a field — at the moment someone writes it,
    not the first time a run happens to fill it.
    """
    return sorted(
        f.name for f in fields(packet_type) if f.name in PROSE_FIELD_NAMES
    )
