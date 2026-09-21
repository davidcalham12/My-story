"""The cost ceiling, checked before every call.

A ceiling that warns and continues is not a ceiling. One v1 run reached $49.33
with nothing to stop it.
"""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(Exception):
    """The next call would cross the ceiling. The run halts; what it produced
    stays readable, and the attempt in flight is kept because it is already
    paid for."""


@dataclass
class Budget:
    """Worst-case projection.

    Output tokens cannot be known before the call, so the projection uses
    `max_tokens` as the bound. A ceiling computed from an *assumed* reply is
    broken by one long answer; worst case stops slightly early, which is the
    correct direction in which to be wrong. The real cost is recorded afterwards,
    so the gap between projection and spend stays visible rather than argued
    about.
    """

    ceiling_usd: float
    pricing: dict
    spent_usd: float = 0.0

    def rates(self, model: str) -> tuple[float, float]:
        entry = self.pricing.get("models", {}).get(model)
        if not entry:
            # A model with no rate is not priced at zero. Zero would let an
            # unpriced model spend without limit behind a ceiling that reads as
            # enforced.
            raise BudgetExceeded(f"no rate for model {model!r}; refusing to guess")
        return entry["input_per_mtok"] / 1e6, entry["output_per_mtok"] / 1e6

    def project(self, model: str, input_tokens: int, max_tokens: int) -> float:
        per_in, per_out = self.rates(model)
        return input_tokens * per_in + max_tokens * per_out

    def check(self, model: str, input_tokens: int, max_tokens: int) -> float:
        projected = self.project(model, input_tokens, max_tokens)
        if self.spent_usd + projected > self.ceiling_usd:
            raise BudgetExceeded(
                f"spent ${self.spent_usd:.2f}; this call projects "
                f"${projected:.2f}; ceiling is ${self.ceiling_usd:.2f}"
            )
        return projected

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """The actual cost, after the call. Exact, not bounded."""
        per_in, per_out = self.rates(model)
        cost = input_tokens * per_in + output_tokens * per_out
        self.spent_usd += cost
        return cost
