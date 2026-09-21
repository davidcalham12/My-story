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

    def complete(self, prompt: str, *, model: str, max_tokens: int,
                 agent: str = "", chapter: int | None = None,
                 attempt: int | None = None) -> Reply: ...


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

    def complete(self, prompt: str, *, model: str, max_tokens: int,
                 agent: str = "", chapter: int | None = None,
                 attempt: int | None = None) -> Reply:
        """The mock is TOLD which agent, chapter and attempt it is answering as.

        It used to read all three out of the prompt text, and both guesses were
        wrong for the same reason: an agent's prompt file talks about the other
        agents and about chapters in general, so `outline-critic` answered as
        continuity and every critic thought it was judging chapter 3. A plan that
        names a failure could then never produce it.

        Guessing a fact the caller already knows is a bug with a long fuse.
        """
        started = time.monotonic()
        self.calls.append(prompt)
        text = self._respond(prompt, agent, chapter, attempt)
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

    def _respond(self, prompt: str, agent: str = "", chapter: int | None = None,
                 attempt: int | None = None) -> str:
        if "Return JSON only" in prompt:
            if "facts" in prompt:
                return self._facts(prompt, chapter)
            return self._critic_reply(prompt, agent, chapter, attempt)
        if "You are writing chapter" in prompt:
            return self._chapter(prompt, chapter)
        if "chapter entries" in prompt:
            return self._outline(prompt)
        if "synopsis" in prompt:
            return self._synopsis(prompt)
        if "Normalise punctuation" in prompt:
            return self._style(prompt)
        if "Characters:" in prompt:
            return self._cast(prompt)
        return self._world(prompt)

    # -- the shapes the pipeline actually parses ------------------------
    #
    # Respecting the premise is not enough on its own: a mock that returns
    # plausible prose but not the SHAPE the orchestrator splits on tests the
    # prose path and nothing else. These read the counts out of the brief they
    # were given, so the artefacts satisfy the same checks a real reply must.

    @staticmethod
    def _band(prompt: str, label: str, fallback: tuple[int, int]) -> tuple[int, int]:
        import re

        m = re.search(rf"{label}:?\s*(\d+)\s*-\s*(\d+)", prompt)
        return (int(m.group(1)), int(m.group(2))) if m else fallback

    def _world(self, prompt: str) -> str:
        terms = self._terms(prompt) or ["the", "premise"]
        low, high = self._band(prompt, "Length", (250, 450))
        rules_low, _ = self._band(prompt, r'Rules under "## Rules"', (4, 5))
        factions_low, _ = self._band(prompt, "Factions", (2, 2))
        means_low, _ = self._band(prompt, "Means entries", (2, 3))

        target = (low + high) // 2
        opening = " ".join(
            f"The {terms[i % len(terms)]} matters here and is written down."
            for i in range(max(6, target // 12))
        )
        parts = [f"# The world of {terms[0]}", "", opening, "", "## Factions", ""]
        parts += [f"- **Faction {i + 1}** - wants {terms[i % len(terms)]}, "
                  f"and gets it by holding the ledger"
                  for i in range(factions_low)]
        parts += ["", "## Means", ""]
        parts += [f"- **Means {i + 1}** - the {terms[i % len(terms)]} the plot turns on"
                  for i in range(means_low)]
        parts += ["", "## Rules", ""]
        parts += [f"- Rule {i + 1}: no {terms[i % len(terms)]} without a signature, "
                  f"and a scene could break it"
                  for i in range(rules_low)]
        parts += ["", "## Texture", "",
                  f"It smells of {terms[-1]} and sounds like a pump at night."]
        text = "\n".join(parts)

        # Pad to the band, because the orchestrator MEASURES rather than
        # believing a reply about itself - and a mock that cannot satisfy the
        # brief would send every run into a redraft loop that tests nothing.
        while len(text.split()) < low:
            text += f"\n\nA further note about {terms[0]}, recorded for the record."
        return text

    def _cast(self, prompt: str) -> str:
        terms = self._terms(prompt) or ["premise"]
        count, _ = self._band(prompt, "Characters", (3, 4))
        names = ["Nora Pike", "Sam Okoye", "Hannah Brede", "Theo Vance",
                 "Gil Marchetti", "Ada Salas", "Leo Fenn"]
        out = ["# Characters", ""]
        out += [f"- **{names[i % len(names)]}** - {terms[i % len(terms)]} keeper; "
                f"stubborn, exact" for i in range(count)]
        out += ["", "# Timeline", ""]
        out += [f"- Day {i}: something about {terms[i % len(terms)]}" for i in range(4)]
        out += ["", "# Mysteries", ""]
        out += [f"- Why the {terms[i % len(terms)]} does not add up" for i in range(2)]
        return "\n".join(out)

    def _outline(self, prompt: str) -> str:
        import re

        terms = self._terms(prompt) or ["premise"]
        m = re.search(r"exactly (\d+) chapter entries", prompt)
        count = int(m.group(1)) if m else 3
        out = ["# Outline", ""]
        for n in range(1, count + 1):
            out += [
                f"### Chapter {n} \u2014 The {terms[(n - 1) % len(terms)].title()}",
                f"- **POV:** {terms[0]}",
                f"- **Tension:** {min(9, 3 + n)}/10",
                "- **Promise advanced:** P1",
                "- **Beats:**",
                f"  1. Someone notices the {terms[(n - 1) % len(terms)]}.",
                f"  2. The number is checked and does not agree.",
                f"  3. A decision is made that cannot be taken back.",
                "- **Must establish:** the discrepancy is real",
                "",
            ]
        return "\n".join(out)

    def _synopsis(self, prompt: str) -> str:
        terms = self._terms(prompt) or ["premise"]
        body = " ".join(f"The {t} is at stake." for t in terms * 20)
        return body

    def _style(self, prompt: str) -> str:
        """Returns the chapter unchanged.

        The style pass may not change a word, and the orchestrator checks that
        with a word count. A mock that altered the text would make every run
        discard every pass, which would test the discard and nothing else.
        """
        body = prompt.split("\n\n", 1)[-1]
        return body.strip()

    def _facts(self, prompt: str, chapter: int | None = None) -> str:
        import json

        chapter = 1 if chapter is None else chapter
        terms = self._terms(prompt) or ["premise"]
        return json.dumps({"facts": [
            {"fact": f"chapter {chapter}: the {terms[0]} was measured", "kind": "event"},
            {"fact": f"the discrepancy in chapter {chapter} is now known",
             "kind": "knowledge", "who": "Nora Pike"},
            {"fact": f"what caused it, as of chapter {chapter}", "kind": "open-question"},
        ]})

    def _chapter(self, prompt: str, chapter: int | None = None) -> str:
        chapter = 1 if chapter is None else chapter
        terms = self._terms(prompt) or ["premise"]
        heading = "" if chapter in self.plan.headingless else f"# Chapter {chapter}\n\n"
        sentences = 4 if chapter in self.plan.out_of_band else 120
        body = " ".join(f"{terms[i % len(terms)]} happened." for i in range(sentences))
        return heading + body

    def _critic_reply(self, prompt: str, agent: str = "", chapter: int | None = None,
                      attempt: int | None = None) -> str:
        import json

        # `or 1` would read chapter 0 - the outline audit's slot - as missing.
        chapter = 1 if chapter is None else chapter
        attempt = 1 if attempt is None else attempt
        # The agent name is PASSED, not guessed from the text. Guessing it by
        # searching the prompt for "continuity" found the wrong critic every
        # time, because outline-critic's own prompt explains what continuity
        # checks - so every critic answered as continuity and the plan could
        # never fail the one it named.
        which = agent.replace("-critic", "") if agent else "continuity"
        if which not in ("continuity", "science", "outline"):
            which = "continuity"
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

    def complete(self, prompt: str, *, model: str, max_tokens: int,
                 agent: str = "", chapter: int | None = None,
                 attempt: int | None = None) -> Reply:
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
