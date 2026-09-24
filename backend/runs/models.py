"""The shapes at the edge. Pydantic only here; the service never sees them."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class StartRun(BaseModel):
    """Either a premise, or the id of a brief that already passed FLOW-0.

    Exactly one. A request carrying both is a request with two ideas of what
    the book is about, and picking one silently is how a buyer gets a novel
    for somebody else's father.
    """

    premise: str | None = Field(default=None, min_length=10, max_length=2000)
    brief_id: str | None = None
    profile: str = "tiny"
    # Empty means: read the genre off the premise. No agent declares one, and a
    # default here would put the welded genre back where it was. Ignored when
    # `brief_id` is given: the brief's own tone is the buyer's answer.
    tone: str = ""
    # How many chapters the buyer asked for, with a brief. Absent: the profile
    # decides. Bounded by the profile in the service, where its budget is known.
    chapters: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def one_of(self) -> "StartRun":
        if bool(self.premise) == bool(self.brief_id):
            raise ValueError("give either premise or brief_id, and not both")
        return self


class RunCreated(BaseModel):
    id: str
    slug: str


class RunSummary(BaseModel):
    id: str
    slug: str
    premise: str
    profile: str
    tone: str | None
    stage: str
    halted: str | None
    halted_detail: str | None
    source: str
    started_at: str
    finished_at: str | None


class ChapterScore(BaseModel):
    chapter: int
    attempt: int
    aggregate: int | None
    verdict: str | None
    promoted: bool
    scores: dict[str, int | None]


class Cost(BaseModel):
    calls: int
    input_tokens: int
    output_tokens: int
    total_usd: float
    # How the figures were obtained. A mixed run says so rather than picking the
    # flattering one.
    provenance: list[str]


class ResumeRun(BaseModel):
    """SPEC-EXAM-007 §4. `ceiling_usd` is the owner's figure for this
    continuation: required when the run stopped on its budget, or when nothing
    is left of the profile's ceiling; otherwise the profile's minus the spend."""

    model_config = {"extra": "forbid"}

    ceiling_usd: float | None = Field(default=None, gt=0)
