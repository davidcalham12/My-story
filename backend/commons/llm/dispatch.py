"""The single path from an agent to a model.

Everything the architecture promises meets here. A call cannot happen without
being counted against the semaphore, projected against the budget, and written to
the log — not because a procedure says so, but because there is nowhere else to
call from.

`docs/verification.md` G2 records the honest weak point: nothing stops a feature
importing `anthropic` and building its own client. Until an import-boundary test
exists, this rests on review, and it is the weakest link in both guarantees.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.commons.budget.ceiling import Budget
from backend.commons.context.semaphore import TokenSemaphore
from backend.commons.context.tokens import TokenCounter
from backend.commons.llm.engine import Engine, Reply
from backend.commons.log.calls import CallRow, write_call


def now() -> str:
    """A real clock reading.

    v1 estimated its timestamps and a log claimed 24 minutes for a run that took
    72. A plausible number and a measured one look identical once written down,
    which is why this is a function and not a habit.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Dispatcher:
    """Holds the four things a call must pass through."""

    engine: Engine
    semaphore: TokenSemaphore
    budget: Budget
    counter: TokenCounter
    conn: sqlite3.Connection
    run_id: str
    # SQLite takes one writer. The critics run in parallel and each records its
    # own row, so the writes are serialised here rather than left to chance.
    _write_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def call(
        self,
        *,
        stage: str,
        agent: str,
        model: str,
        prompt: str,
        max_tokens: int,
        chapter: int | None = None,
        attempt: int | None = None,
        note: str | None = None,
    ) -> Reply:
        """One model call, through every guard, recorded.

        Order matters and is not arbitrary:

        1. **Count** the prompt. Never estimate — the semaphore's whole value
           rests on this number being right, and an estimate running low turns a
           100,000 ceiling into a 120,000 one, silently.
        2. **Project** the worst case against the budget and raise *before*
           spending. A ceiling checked afterwards is a receipt.
        3. **Reserve** from the semaphore, waiting if the pool is short.
        4. Call.
        5. **Record** the actual cost, which is exact rather than bounded, and
           write the row.

        The reservation is released even if the call raises, because `hold` is a
        context manager: a failed call that never gave its tokens back would
        shrink the pool for the rest of the run.
        """
        input_tokens = self.counter.count(prompt)
        reservation_size = input_tokens + max_tokens

        # Before the call, not after. `BudgetExceeded` propagates and the run
        # halts with `halted: budget`; the attempt in flight is kept, because it
        # is already paid for.
        self.budget.check(model, input_tokens, max_tokens)

        with self.semaphore.hold(reservation_size) as reservation:
            reply = self.engine.complete(
                prompt, model=model, max_tokens=max_tokens,
                agent=agent, chapter=chapter, attempt=attempt,
            )

        cost = self.budget.record(model, reply.input_tokens, reply.output_tokens)

        with self._write_lock:
            write_call(
                self.conn,
                CallRow(
                    run_id=self.run_id,
                    stage=stage,
                    agent=agent,
                    model=model,
                    ts=now(),
                    chapter=chapter,
                    attempt=attempt,
                    input_tokens=reply.input_tokens,
                    output_tokens=reply.output_tokens,
                    cost_usd=cost,
                    provenance=reply.provenance,
                    tokens_reserved=reservation.tokens,
                    in_flight_at_dispatch=reservation.in_flight_at_dispatch,
                    wait_ms=reservation.wait_ms,
                    duration_ms=reply.duration_ms,
                    note=note,
                ),
            )
        return reply
