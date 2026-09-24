"""Reading the stream: what happened, what it cost, and when to stop it.

Three jobs, all from the same line of JSON:

1. **Progress** — which stage, chapter, attempt and agent, inferred from the tool
   calls and the paths being written. Inferred, not counted: this is reading
   someone else's work over their shoulder, so what it reports is the last thing
   it recognised rather than a position in a plan it owns.
2. **Accounting** — real token usage per message, and the whole run's cost from
   the final `result`. Measured, not estimated.
3. **The two watchers** — budget and context. Both act *after* a call rather than
   before it, which is the honest cost of Claude Code assembling the prompts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

OUTPUT_PATH = re.compile(r"output[/\\]([^/\\]+)[/\\]")
CHAPTER_FILE = re.compile(r"ch(\d+)\.attempt(\d+)\.md")
STAGE_HINT = re.compile(r"\bFLOW-[1-6]\b")

# The ten, pinned to `.claude/agents/*.md` by `test_the_watcher_knows_every_agent_file`.
# Anything else dispatched is worth noticing rather than assuming. This set said
# "the nine" for a day after prose-critic existed.
AGENTS = {
    "worldbuilder", "character-architect", "plot-architect", "chapter-writer",
    "continuity-critic", "science-critic", "outline-critic", "prose-critic",
    "style-editor", "publisher",
    # storyMaker (SPEC-EXAM-001 §3): the interviewer at FLOW-0 and the judge at
    # the publish gate. Neither writes canon; both hold `Glob`.
    "interviewer", "judge",
    # SPEC-EXAM-004: continuity, science and outline scored in one reading.
    "bible-critic",
}


@dataclass
class State:
    """What the run is doing, as far as the stream lets anyone tell."""

    slug: str | None = None
    stage: str | None = None
    chapter: int | None = None
    attempt: int | None = None
    agent: str | None = None
    headline: str = "starting"
    dispatched: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)

    # Accounting, from `usage` on assistant messages. These are REAL numbers the
    # model reported, not a rule of thumb — the provenance is `measured`.
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    # From the `result` events, which cover the orchestrators' own turns too.
    # This is the figure v1 could not see, and its absence is why a $6.21
    # estimate stood in for $49.33.
    #
    # **Summed, not replaced.** Under one orchestrator there was one `result`
    # and the distinction did not exist. The conductor emits one per unit,
    # each carrying only its own unit's bill, so replacing meant the run's
    # total was whatever the last unit cost — and the budget ceiling read that
    # number. A thirteen-unit run had thirteen ceilings and nobody was told.
    total_cost_usd: float | None = None
    turns: int | None = None
    duration_ms: int | None = None
    #: How many `result` events arrived. Under the conductor a unit stopped
    #: mid-turn never sends one, so this is how a reader tells a complete bill
    #: from a bill with a unit-shaped hole in it.
    results: int = 0
    finished: bool = False
    error: str | None = None


def _message(event: dict) -> dict:
    """The message object, or an empty one.

    Some events carry `message` as a plain string. The stream belongs to someone
    else and may grow shapes this reader has never seen, so every access to it
    goes through here rather than assuming a dict and raising in the middle of a
    run that was going fine.
    """
    message = event.get("message")
    return message if isinstance(message, dict) else {}


def _usage(event: dict) -> dict:
    """The usage object, wherever this event keeps it.

    Two places, and they mean different things:

    - on an `assistant` message: the ORCHESTRATOR's own turn;
    - on a `system/task_progress` event: a SUBAGENT's packet, with
      `subagent_type` naming which.

    Conflating them is the mistake this function exists to prevent.
    """
    if event.get("type") == "system" and event.get("subtype") == "task_progress":
        usage = event.get("usage")
    else:
        usage = _message(event).get("usage")
    return usage if isinstance(usage, dict) else {}


def context_size(usage: dict) -> int:
    """How large a turn's context actually was.

    **`input_tokens` alone is nearly always 2.** Almost the entire context
    arrives cached, so the real figure is
    `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.

    Reading only `input_tokens` gives a watcher that reports two-token calls and
    never trips - a ceiling that cannot be exceeded because it is measuring the
    wrong thing. This was found by replaying a real run, not by reading the docs.

    **And a subagent's `task_progress` carries none of those three.** It carries
    `usage: {total_tokens, tool_uses, duration_ms}` — the subagent's whole usage,
    input and output together. For a day this function summed three absent keys,
    reported 0, and three real runs were read as "no packet data" (SPEC-010 W2).
    When the three input fields are absent, `total_tokens` is the figure: an
    upper bound on the packet, labelled as such by the caller.
    """
    if any(k in usage for k in ("input_tokens", "cache_creation_input_tokens",
                                "cache_read_input_tokens")):
        return (
            int(usage.get("input_tokens") or 0)
            + int(usage.get("cache_creation_input_tokens") or 0)
            + int(usage.get("cache_read_input_tokens") or 0)
        )
    return int(usage.get("total_tokens") or 0)


def _blocks(event: dict) -> list[dict]:
    content = _message(event).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _text(event: dict) -> str:
    return " ".join(b.get("text", "") for b in _blocks(event) if b.get("type") == "text")


def _add(running, reported):
    """Sum across units, and keep absent absent.

    A unit that reported no cost must not turn the run's total into a zero:
    zero, empty and absent are three different claims. `None + None` stays
    `None`, and a figure that arrives after nothing starts the sum.
    """
    if reported is None:
        return running
    return type(reported)(reported if running is None else running + reported)


def apply(state: State, event: dict) -> State:
    """Fold one event into the state. Never raises on an unfamiliar shape."""
    kind = event.get("type")

    if kind == "system" and event.get("subtype") == "init":
        state.headline = "Claude Code started and loaded the skill"
        return state

    if kind == "result":
        state.finished = True
        state.results += 1
        state.total_cost_usd = _add(state.total_cost_usd, event.get("total_cost_usd"))
        state.turns = _add(state.turns, event.get("num_turns"))
        state.duration_ms = _add(state.duration_ms, event.get("duration_ms"))
        if event.get("is_error"):
            state.error = str(event.get("result") or "the run reported an error")
        state.headline = "finished" if not state.error else "the run reported an error"
        return state

    if kind in ("assistant", "user"):
        usage = _usage(event)
        if usage:
            state.input_tokens += int(usage.get("input_tokens") or 0)
            state.output_tokens += int(usage.get("output_tokens") or 0)

        narration = _text(event).strip()
        if narration:
            line = next((l for l in narration.split("\n") if len(l.strip()) > 12), "")
            if line:
                state.headline = line.strip()[:160]
            stage = STAGE_HINT.search(narration)
            if stage:
                state.stage = stage.group(0)

        for block in _blocks(event):
            if block.get("type") != "tool_use":
                continue
            name = block.get("name")
            data = block.get("input") or {}

            if name in ("Agent", "Task"):
                agent = str(data.get("subagent_type") or data.get("description") or "?")
                state.agent = agent
                state.dispatched.append(agent)
                state.calls += 1
                state.headline = f"dispatched {agent}"

            elif name in ("Write", "Edit"):
                path = str(data.get("file_path") or "")
                # The slug is LEARNED from the paths the run writes. Claude Code
                # derives it from the premise itself, so the launcher cannot know
                # it in advance and must not guess: a guessed slug reads the
                # wrong novel, or none.
                found = OUTPUT_PATH.search(path)
                if found:
                    state.slug = found.group(1)
                chapter = CHAPTER_FILE.search(path)
                if chapter:
                    state.chapter = int(chapter.group(1))
                    state.attempt = int(chapter.group(2))
                short = "/".join(path.replace("\\", "/").split("/")[-2:])
                if short:
                    state.written.append(short)
                    state.headline = f"wrote {short}"

    return state


# --------------------------------------------------------------- the watchers


class WatchTripped(Exception):
    """A watcher stopped the run. Carries the halt kind it should be marked with."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


@dataclass
class BudgetWatcher:
    """The cost ceiling, enforced after the fact.

    Python no longer assembles the prompts, so it cannot project a call's cost
    before the call happens. What it can do is add up the `usage` the stream
    reports and stop the process the moment the total crosses the ceiling.

    **This is weaker than the projection it replaces and the difference has a
    name.** A projection refuses the call that would exceed; this lets that call
    happen and stops the next. The overshoot is bounded by one call rather than
    by zero, and `verification.md` records it as a stop rather than a guarantee.
    """

    ceiling_usd: float
    pricing: dict
    # The models the nine agents run on. Read from their files rather than
    # assumed, so a change there cannot silently mis-price a run.
    rate_per_token: float = 0.0
    spent_usd: float = 0.0

    def observe(self, state: State) -> None:
        # The token count, priced at the most expensive rate on file, because a
        # ceiling that under-estimates is not a ceiling. Tokens here are the
        # orchestrator's, which is the right basis: the run's bill includes
        # them and v1's estimate did not.
        worst = max(
            (m["output_per_mtok"] for m in self.pricing.get("models", {}).values()),
            default=0.0,
        ) / 1_000_000
        from_tokens = (state.input_tokens + state.output_tokens) * worst

        # **The larger of the two, never just the reported sum.** A unit the
        # context watcher stops mid-turn is killed before it sends a `result`,
        # so its cost is reported by nobody — and a ceiling that read only the
        # reported total would forget that unit's spending for the rest of the
        # run. The token estimate still carries it, so taking the maximum keeps
        # the halted unit inside the ceiling while leaving the reported figure
        # in charge whenever it is the bigger of the two, which it usually is
        # (it includes the subagents; these tokens are the orchestrator's).
        self.spent_usd = max(from_tokens, state.total_cost_usd or 0.0)

        if self.spent_usd > self.ceiling_usd:
            raise WatchTripped(
                "budget",
                f"spent ${self.spent_usd:.2f} against a ceiling of "
                f"${self.ceiling_usd:.2f}",
            )


@dataclass
class ContextWatcher:
    """The 100,000-token ceiling, and an honest account of what it can watch.

    Layer 2 of two. Layer 1 is in `SKILL.md`: the orchestrator measures each
    packet with `wc -w` before dispatching and does not send one that is too
    large. That is a **procedure**, classified Inspection, and it is also where
    the flat-context series is recorded.

    **What replaying two real runs showed, and it changes this class.**

    The ceiling is about the PACKETS THE AGENTS RECEIVE - the quantity the
    architecture claims stays flat as a book grows. It was never the
    orchestrator's own budget.

    - The orchestrator's turns run at a **median of 147,000 and a peak of
      642,000** tokens across two real runs. That is not a defect: an
      orchestrator accumulates, carrying the Bible and the drafts and the
      findings turn after turn. It is the same fact that made a $6.21 estimate
      stand in for $49.33, now visible in tokens. **Halting on it would halt
      every run inside a minute**, which is what a naive reading of this layer
      would do.
    - The subagents' packets DO have a slot in the stream - `task_progress`
      carries `subagent_type` and `usage` - but in both recordings that `usage`
      reads **zero**. So the one quantity the ceiling is actually about is, from
      the stream, **not measurable today**.

    Therefore this class does two things and claims only them:

    1. **Halts** when a subagent packet is reported above the ceiling. That is a
       real check that will fire the day those figures populate, and it costs
       nothing to have waiting.
    2. **Observes** the orchestrator's context as its own series, recorded and
       never used to halt.

    What it does NOT do is report zero as if it were a measurement. When no
    subagent usage arrives, `packets_measured` stays at 0 and the provenance of
    that series is `absent` - which is not the same as "every packet was small".
    """

    ceiling: int
    largest_packet: int = 0
    packets_measured: int = 0
    largest_orchestrator_turn: int = 0
    orchestrator_turns: int = 0
    #: Turns above the ceiling.
    turns_over_ceiling: int = 0
    #: Whether crossing it stops the run.
    #:
    #: **False under one orchestrator per novel**, which is the fallback
    #: path: that conversation carries the whole book, ran at a median of
    #: 147,000 tokens across two real runs, and halting on it would halt
    #: every novel inside a minute. The figure is counted and reported
    #: instead (docs/spec.md §8).
    #:
    #: **True under the conductor** (SPEC-EXAM-003), where each unit gets a
    #: fresh process whose context is bounded by the unit rather than by
    #: the book. There the ceiling is a real bound, and the owner requires
    #: it: no part of a run above 100,000 concurrent tokens.
    halt_on_orchestrator_turn: bool = False
    # Per agent, so "chapter 34 weighs what chapter 1 weighed" can be drawn the
    # day the figures arrive.
    by_agent: dict[str, int] = field(default_factory=dict)

    def observe_event(self, event: dict) -> None:
        usage = _usage(event)
        if not usage:
            return
        size = context_size(usage)

        if event.get("type") == "system" and event.get("subtype") == "task_progress":
            agent = str(event.get("subagent_type") or "?")
            if size <= 0:
                return  # reported but empty: absent, not zero
            self.packets_measured += 1
            self.largest_packet = max(self.largest_packet, size)
            self.by_agent[agent] = max(self.by_agent.get(agent, 0), size)
            if size > self.ceiling:
                raise WatchTripped(
                    "context",
                    f"{agent} was handed {size:,} tokens against a ceiling of "
                    f"{self.ceiling:,}",
                )
            return

        # The orchestrator's own turn. Recorded, never fatal.
        self.orchestrator_turns += 1
        self.largest_orchestrator_turn = max(self.largest_orchestrator_turn, size)
        if size > self.ceiling:
            self.turns_over_ceiling += 1
            if self.halt_on_orchestrator_turn:
                raise WatchTripped(
                    "context",
                    f"an orchestrator turn carried {size:,} tokens against a "
                    f"ceiling of {self.ceiling:,}")

    @property
    def packet_series_provenance(self) -> str:
        """`measured` when packets were reported, `absent` when they were not."""
        return "measured" if self.packets_measured else "absent"
