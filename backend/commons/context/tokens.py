"""Counting tokens. Counted, never estimated.

The semaphore's whole value rests on this number being right. An estimate that
runs 20% low turns a 100,000 ceiling into a 120,000 one, silently, and the
guarantee becomes a decoration that still reads as a guarantee.
"""

from __future__ import annotations

from typing import Protocol


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class DeterministicCounter:
    """The counter the mock engine uses.

    Deterministic by construction: the same text always yields the same number,
    so a test that fails, fails the same way tomorrow. It is a *model* of a
    tokenizer, not an approximation of one — the mock never talks to an API, so
    there is nothing to approximate. What it must do is be exact about itself,
    and that it is.
    """

    CHARS_PER_TOKEN = 4

    def count(self, text: str) -> int:
        # Ceiling division, so a one-character prompt costs one token rather
        # than zero. A zero-token reservation would let unbounded calls through
        # a full semaphore.
        return max(1, -(-len(text) // self.CHARS_PER_TOKEN))


class AnthropicCounter:
    """The real counter: the API's own token-counting endpoint.

    Deliberately not a local tokenizer approximating the same thing. The number
    that matters is the one the API will charge and enforce, and only the API
    knows it.
    """

    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def count(self, text: str) -> int:
        result = self._client.messages.count_tokens(
            model=self._model,
            messages=[{"role": "user", "content": text}],
        )
        return int(result.input_tokens)
