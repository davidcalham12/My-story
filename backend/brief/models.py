"""The brief: what the buyer asked for, as a shape that can be checked.

The only description of the person the novel is for. Everything downstream —
the Bible, the outline, every chapter, the dedication on the cover — is derived
from this, so the moment to reject a malformed one is here, at FLOW-0, before a
single token is spent.

Two decisions are visible in the field list and are worth stating:

- **Every field is optional to the model and only some are required by the
  domain.** A brief arrives mid-conversation: the buyer has answered four
  questions out of nine and the interviewer needs to know which five are left.
  A model that refused the half-filled one could not produce that list, so
  `backend.brief.domain` decides what is required and this file only decides
  what is *shaped* correctly.
- **`extra="forbid"` everywhere.** The interviewer is a language model returning
  JSON. A model that invents `recipient.nickname` and has it quietly dropped
  produces a novel that calls the boy by a name nobody chose; the invented key
  is an error, loudly, at the edge.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.commons import limits

#: The eleven keys, and no twelfth. Adding one moves SPEC-EXAM-001 §1 row 1, the
#: interviewer's prompt and the frontend form (SPEC-EXAM-002 AC-1) together.
STRICT = ConfigDict(extra="forbid")

# Every string the buyer types has a ceiling (SR-11); the figures are in
# `backend.commons.limits`, one place for the brief, the run and the change.
Short = Annotated[str, StringConstraints(max_length=limits.SHORT_TEXT)]
Long = Annotated[str, StringConstraints(max_length=limits.LONG_TEXT)]


class Memory(BaseModel):
    """Something that happened, and when — if the buyer remembers when.

    `date` is absent far more often than it is present, and an absent date is
    `None`. It is never "today" and never the start of the epoch: the temporal
    validator reads these, and an invented date is an invented contradiction.
    """

    model_config = STRICT

    text: Long
    date: Short | None = None


class Recipient(BaseModel):
    """The person receiving the novel, as the novel will know them.

    `alias` and not a name: the brief travels through a model, a database and a
    PDF, and the less of a real person is in it the better. `age` is `int | None`
    for the rule in `domain`: an unknown age is unknown, not a newborn, and a
    zero here would make every brief with a blank age contradict an adult tone.
    """

    model_config = STRICT

    alias: Short | None = None
    age: int | None = None
    pronouns: Short | None = None
    # ISO date, "YYYY-MM" or "YYYY-MM-DD". Declared on the owner's order of
    # 2026-09-24 so brief 05 reaches the temporal check. `None` claims nothing.
    birth_date: Short | None = None
    traits: list[Short] = Field(default_factory=list)
    relationship_to_buyer: Short | None = None


class Brief(BaseModel):
    """What was ordered.

    `free_text` is the one field the buyer writes freely, which makes it the one
    field an attacker controls. It is carried here as data and read only by
    `domain.facts()`, which turns it into rows marked `source="freetext"`; no
    part of this system copies it into any other field. Brief 04 is the test of
    that sentence.
    """

    model_config = STRICT

    occasion: Short | None = None
    recipient: Recipient = Field(default_factory=Recipient)
    memories: list[Memory] = Field(default_factory=list)
    genre: Short | None = None
    tone: Short | None = None
    length_chapters: int | None = None
    forbidden_terms: list[Short] = Field(default_factory=list)
    mandatory_facts: list[Long] = Field(default_factory=list)
    dedication: Long | None = None
    free_text: str = Field(default="", max_length=limits.FREE_TEXT)


class Fact(BaseModel):
    """One statement the novel has to honour, with where it came from.

    `source` is the whole point. A fact the buyer typed into `mandatory_facts`
    is checked for at the publish gate (`mandatory_facts` validator, SPEC-EXAM-001
    §2); a fact scraped out of free text is a lead for a human, never a promise
    and never an instruction. Same table, different trust, told apart at the
    moment the row is made rather than guessed at afterwards.
    """

    model_config = STRICT

    text: str
    kind: str
    source: str
    mandatory: bool = False
