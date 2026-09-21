"""The only path to a model.

Every model call in this system goes through an `Engine`. That is what makes the
semaphore and the budget guarantees rather than habits: a feature cannot send a
prompt without being counted, reserved and charged, because there is nowhere else
to send it from.

`verification.md` G2 records the weak point honestly: nothing enforces this at
import time. A feature *could* construct its own client. Until an import-boundary
test exists, this rests on review.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    # How the token figures were obtained. `measured` from the API, `estimated`
    # from a counter. Never absent-as-zero.
    provenance: str = "measured"


class Engine(Protocol):
    name: str

    def complete(self, prompt: str, *, model: str, max_tokens: int) -> Reply: ...


# --------------------------------------------------------------------- mock


@dataclass
class Plan:
    """What a test wants to happen, said explicitly.

    Not a seed. The tests that matter are specific — *a chapter that fails
    `outline` twice then passes*, *one that can never pass* — and a seed gives
    random failure, which tests nothing in particular. With a plan,
    `patch_then_halt` has a test that says exactly what provoked the halt.

    `fail` names the model critics that should return a low score for a given
    (chapter, attempt). It does NOT control `length` or `chatter`: those are real
    code and compute over the text the mock actually produced. Scripting the two
    characteristics that reproduce would be not testing them.
    """

    fail: dict[tuple[int, int], list[str]] = field(default_factory=dict)
    # Chapters whose draft should come back outside the word band, or without the
    # heading, so the two arithmetic characteristics run on real text.
    out_of_band: set[int] = field(default_factory=set)
    headingless: set[int] = field(default_factory=set)

    def failures_for(self, chapter: int, attempt: int) -> list[str]:
        return list(self.fail.get((chapter, attempt), []))


class MockEngine:
    """A deterministic engine that respects the premise.

    v1's mock ignored the premise, which is why it never demonstrated anything:
    artefacts that mention nothing from the brief cannot show that the pipeline
    carried the brief through. This one seeds every reply with terms from the
    premise, so a test can assert the premise survived six stages.

    Deterministic, so a test that fails, fails the same way tomorrow.
    """

    name = "mock"

    def __init__(self, plan: Plan | None = None, counter=None):
        from backend.commons.context.tokens import DeterministicCounter

        self.plan = plan or Plan()
        self.counter = counter or DeterministicCounter()
        self.calls: list[str] = []

    def complete(self, prompt: str, *, model: str, max_tokens: int) -> Reply:
        started = time.monotonic()
        self.calls.append(prompt)
        text = self._respond(prompt)
        return Reply(
            text=text,
            input_tokens=self.counter.count(prompt),
            output_tokens=self.counter.count(text),
            duration_ms=int((time.monotonic() - started) * 1000),
            provenance="estimated",  # a counter, not an API: say so
        )

    # -- response shaping ------------------------------------------------

    @staticmethod
    def _terms(prompt: str, n: int = 6) -> list[str]:
        """Content words from the premise line, so replies carry the brief."""
        for line in prompt.splitlines():
            if "remise" in line:
                words = [w.strip(".,;:\"'") for w in line.split()]
                return [w for w in words if len(w) > 4][:n]
        return []

    def _respond(self, prompt: str) -> str:
        if "Return JSON only" in prompt:
            return self._critic_reply(prompt)
        if "# Chapter" in prompt or "You are writing chapter" in prompt:
            return self._chapter(prompt)
        return self._document(prompt)

    def _document(self, prompt: str) -> str:
        terms = self._terms(prompt) or ["the", "premise"]
        body = " ".join(terms)
        return (
            f"# Generated from the premise\n\n{body}.\n\n"
            "## Factions\n\n- **A Faction** - wants one thing, gets it one way\n"
            "- **Another** - wants the opposite\n\n"
            "## Means\n\n- **A means** - what the plot turns on\n\n"
            "## Rules\n\n"
            "- A rule a scene could break\n- A second rule\n"
            "- A third rule\n- A fourth rule\n\n"
            "## Texture\n\nWhat it feels like from inside.\n"
        )

    def _chapter(self, prompt: str) -> str:
        chapter = self._chapter_number(prompt)
        terms = self._terms(prompt) or ["premise"]
        heading = "" if chapter in self.plan.headingless else f"# Chapter {chapter}\n\n"
        sentences = 4 if chapter in self.plan.out_of_band else 120
        body = " ".join(f"{terms[i % len(terms)]} happened." for i in range(sentences))
        return heading + body

    @staticmethod
    def _chapter_number(prompt: str) -> int:
        import re

        m = re.search(r"chapter (\d+)", prompt, re.I)
        return int(m.group(1)) if m else 1

    def _critic_reply(self, prompt: str) -> str:
        import json
        import re

        chapter = self._chapter_number(prompt)
        attempt = 1
        m = re.search(r"ATTEMPT (\d+)", prompt)
        if m:
            attempt = int(m.group(1))
        which = "continuity"
        for name in ("continuity", "science", "outline"):
            if name in prompt.lower():
                which = name
                break
        failing = which in self.plan.failures_for(chapter, attempt)
        return json.dumps(
            {
                "score": 4 if failing else 10,
                "findings": (
                    [{
                        "kind": f"{which}-defect",
                        "severity": "high",
                        "quote": "happened.",
                        "claim": f"{which} was planned to fail on chapter "
                                 f"{chapter} attempt {attempt}",
                        "fix": "make it not do that",
                    }]
                    if failing else []
                ),
                "notes": [f"{which} judged chapter {chapter}, attempt {attempt}"],
            }
        )


# ------------------------------------------------------------------ real


class AnthropicEngine:
    """The real engine, behind the flag. Credentials from the environment only."""

    name = "anthropic"

    def __init__(self, api_key: str):
        import anthropic  # imported here so the mock needs no dependency

        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str, *, model: str, max_tokens: int) -> Reply:
        started = time.monotonic()
        message = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        return Reply(
            text=text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            duration_ms=int((time.monotonic() - started) * 1000),
            provenance="measured",
        )
