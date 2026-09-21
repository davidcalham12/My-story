"""The shapes at the edge. Pydantic only here; the service never sees them."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StartRun(BaseModel):
    premise: str = Field(min_length=10, max_length=2000)
    profile: str = "tiny"
    # Empty means: read the genre off the premise. No agent declares one, and a
    # default here would put the welded genre back where it was.
    tone: str = ""


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
