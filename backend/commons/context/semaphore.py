"""The concurrent token ceiling.

**The limit is on tokens IN FLIGHT AT ONE INSTANT, not per call.** The
distinction is the whole reason this file exists: the five critics run in
parallel, so five calls of 30,000 tokens each satisfy any per-call limit while
putting 150,000 in the air. A per-call limit survives only as a consequence —
no single call may reserve more than the total capacity.

A reservation is worst case: prompt tokens plus `max_tokens`, because
`max_tokens` bounds a reply nobody can predict. A semaphore sized by an assumed
reply is one that a single long answer walks straight through, and a ceiling
that can be exceeded is not a ceiling.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


class ContextCeilingExceeded(Exception):
    """A single reservation larger than the total capacity.

    Rejected *before* waiting. Waiting for capacity that can never exist is a
    deadlock wearing the costume of patience; this is an error of the run
    (`halted: context`), and it means something upstream broke — the Bible grew,
    the summary did not cap, retrieval returned too much. Trimming to fit would
    hide exactly that, besides silently weakening the one thing that must stay
    predictable from chapter to chapter.
    """


@dataclass(frozen=True)
class Reservation:
    """What one call held, and what it cost to get it."""

    tokens: int
    in_flight_at_dispatch: int
    wait_ms: int


class TokenSemaphore:
    """Capacity in tokens, acquired and released around every model call."""

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._in_flight = 0
        self._lock = threading.Condition()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight

    def acquire(self, tokens: int) -> Reservation:
        """Take `tokens` from the pool, waiting if the pool is short.

        **Waiting is never a failure.** A critic that waited two seconds for room
        produced the same verdict it would have produced immediately; the wait is
        the price of the ceiling and it is recorded (`wait_ms`) rather than
        avoided. What is a failure is asking for more than the pool can ever
        hold, and that is checked first.
        """
        if tokens > self._capacity:
            raise ContextCeilingExceeded(
                f"reservation of {tokens:,} tokens exceeds the total capacity of "
                f"{self._capacity:,}; this is a run error, not a wait"
            )
        started = time.monotonic()
        with self._lock:
            while self._in_flight + tokens > self._capacity:
                self._lock.wait()
            at_dispatch = self._in_flight
            self._in_flight += tokens
        return Reservation(
            tokens=tokens,
            in_flight_at_dispatch=at_dispatch,
            wait_ms=int((time.monotonic() - started) * 1000),
        )

    def release(self, reservation: Reservation) -> None:
        with self._lock:
            self._in_flight -= reservation.tokens
            self._lock.notify_all()

    class _Held:
        def __init__(self, sem: "TokenSemaphore", reservation: Reservation):
            self.sem, self.reservation = sem, reservation

        def __enter__(self) -> Reservation:
            return self.reservation

        def __exit__(self, *exc) -> None:
            self.sem.release(self.reservation)

    def hold(self, tokens: int) -> "_Held":
        """`with semaphore.hold(n) as reservation:` — released even on error."""
        return TokenSemaphore._Held(self, self.acquire(tokens))
