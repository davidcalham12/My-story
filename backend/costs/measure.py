"""The measured figures of one `result` event, split by role. Pure: no I/O.

Every Claude Code process ends with one `result` event. It carries
`total_cost_usd`, `duration_ms` and `modelUsage` — the cost per model — and all
three are Claude Code's own accounting: **measured**. `minutes` below is
`duration_ms / 60000`, the process's own clock, not a wall clock around it.

**Orchestrator versus agents is decided by role, not by model family**
(SPEC-EXAM-008 §8.3). The orchestrator is the process's main model; every other
entry in `modelUsage` is an agent it dispatched. The main model is, in order:

1. the `model` of the stream's `system/init` event — what the process actually
   ran on, already resolved from `--model`;
2. the `--model` the process was launched with (an alias such as `sonnet`);
3. the model of its first top-level assistant message (`parent_tool_use_id`
   null — a subagent's turn is not the main model's).

A process with no main model (the Python loop's agent processes) has no
orchestrator: every model in it is an agent.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def change_trace_id(run_id: str, n: int) -> str:
    """The Langfuse trace id of change `n` of a run: the SDK's own seeded
    derivation (`sha256(seed)[:16]`), so the exporter and the reader agree
    without either asking the other."""
    return hashlib.sha256(f"{run_id}|change{n}".encode("utf-8")).digest()[:16].hex()


@dataclass(frozen=True)
class Measured:
    total_usd: float | None
    duration_ms: int | None
    orchestrator_model: str | None
    orchestrator_usd: float | None
    agents_model: str | None
    agents_usd: float | None
    #: False when the result carried no `modelUsage` for a non-zero total: the
    #: split is absent, never guessed.
    split: bool

    @property
    def minutes(self) -> float | None:
        return None if self.duration_ms is None else self.duration_ms / 60_000


def _bare(name: str) -> str:
    """`claude-opus-5[1m]` → `claude-opus-5`: the context-window suffix is not
    part of which model it is."""
    return name.split("[", 1)[0].strip().lower()


def is_main(key: str, entry: dict, main: str | None) -> bool:
    if not main:
        return False
    want = _bare(main)
    names = {_bare(key)}
    if isinstance(entry, dict) and entry.get("canonicalModel"):
        names.add(_bare(str(entry["canonicalModel"])))
    if want in names:
        return True
    # An alias from `--model` (`sonnet`, `opus`, `haiku`) names a family.
    return "-" not in want and any(want in n for n in names)


def _number(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def split(result: dict, main_model: str | None) -> Measured:
    total = _number(result.get("total_cost_usd"))
    ms = result.get("duration_ms")
    ms = int(ms) if isinstance(ms, (int, float)) and not isinstance(ms, bool) else None
    usage = result.get("modelUsage") if isinstance(result.get("modelUsage"), dict) else {}

    if not usage:
        # Nothing to split. A process that cost exactly 0 split into 0 and 0
        # truly; any other total has no split, and inventing one is the error
        # this project keeps not making.
        zero = total == 0
        return Measured(total, ms, None, 0.0 if zero else None, None,
                        0.0 if zero else None, split=zero)

    orch_models, orch_usd, agent_models, agent_usd = [], 0.0, [], 0.0
    for key, entry in usage.items():
        cost = _number((entry or {}).get("costUSD")) or 0.0
        if is_main(key, entry or {}, main_model):
            orch_models.append(key)
            orch_usd += cost
        else:
            agent_models.append(key)
            agent_usd += cost
    return Measured(
        total_usd=total, duration_ms=ms,
        orchestrator_model=", ".join(orch_models) or None,
        orchestrator_usd=orch_usd if orch_models else None,
        agents_model=", ".join(agent_models) or None,
        agents_usd=agent_usd if agent_models else (0.0 if orch_models else None),
        split=True)


class Meter:
    """Folds one or more processes' streams, a `Measured` per `result`.

    Counts the processes it saw start (`system/init`) and the results that
    arrived, so a process that ended without one can be counted as absent.
    """

    def __init__(self, configured: str | None = None):
        self.configured = configured
        self.processes = 0
        self.results = 0
        self._init: str | None = None
        self._first_turn: str | None = None

    def main_model(self) -> str | None:
        return self._init or self.configured or self._first_turn

    def observe(self, event: dict) -> Measured | None:
        if not isinstance(event, dict):
            return None
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":
            self.processes += 1
            self._init = event.get("model") or None
            self._first_turn = None
            return None
        if kind == "assistant" and self._first_turn is None \
                and event.get("parent_tool_use_id") is None:
            message = event.get("message")
            if isinstance(message, dict) and message.get("model"):
                self._first_turn = str(message["model"])
            return None
        if kind != "result":
            return None
        self.results += 1
        # A stream with no init (a fake, an old recording) still had a process.
        self.processes = max(self.processes, self.results)
        measured = split(event, self.main_model())
        self._init = self._first_turn = None
        return measured

    @property
    def unresulted(self) -> int:
        return max(self.processes - self.results, 0)
