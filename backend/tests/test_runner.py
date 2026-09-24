"""The runner: launching Claude Code, reading its stream, and stopping it.

Everything here runs against a **real recorded stream** from a real run, at $0.
That split is the deal Annex C makes: the runner, the parser, the persistence,
the SSE and both watchers are testable exhaustively; the procedure in `SKILL.md`
is not testable for free at all, and pretending otherwise would be the more
comfortable lie.
"""

import json
from pathlib import Path

import pytest

from backend.commons.runner.process import (
    ALLOWED_TOOLS,
    ReplayProcess,
    RunProcess,
    build_prompt,
)
from backend.commons.runner.watch import (
    BudgetWatcher,
    ContextWatcher,
    State,
    WatchTripped,
    apply,
    context_size,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "recorded-run.stream.jsonl"


def replay() -> State:
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    state = State()
    for event in process.events():
        state = apply(state, event)
    return state


# ------------------------------------------------------- launching it right


def test_the_prompt_carries_only_what_it_should():
    """`premise:`, `profile:`, optionally `tone:`. The procedure lives in
    SKILL.md; restating it here would be a second source of truth."""
    prompt = build_prompt("A lighthouse keeper on Titan.", "tiny", "procedural")
    assert "premise: A lighthouse keeper on Titan." in prompt
    assert "profile: tiny" in prompt
    assert "tone: procedural" in prompt
    assert "SKILL.md" in prompt


def test_an_empty_tone_is_omitted_rather_than_sent_blank():
    """Empty means: read the genre off the premise. Sending `tone:` with nothing
    after it would be an instruction to write in no genre."""
    assert "tone:" not in build_prompt("A premise long enough.", "tiny", "  ")


def test_the_command_carries_the_flags_that_were_learned_the_hard_way():
    run = RunProcess.for_run(premise="p", profile="tiny", tone="", cwd=Path("."))
    command = run.command
    # stream-json exits 1 without --verbose, and no events appear at all.
    assert "--verbose" in command
    assert command[command.index("--output-format") + 1] == "stream-json"
    # --restricted breaks --agent: Claude Code falls back to its built-in agents
    # and refuses the project's own. The tools: line in each agent file is the
    # boundary, and it is a better one.
    assert "--restricted" not in command
    # The subagent tool is `Agent`; `Task` is the older spelling. Allowing only
    # the wrong one produces a run that quietly dispatches nothing.
    assert "Agent" in ALLOWED_TOOLS and "Task" in ALLOWED_TOOLS
    # Retrieval runs through the orchestrator, not through a critic's tool list.
    assert "Bash(python *)" in ALLOWED_TOOLS


def test_the_prompt_is_never_an_argument():
    """Passing a task as an argument with shell=True on Windows was command
    injection, and it shipped for about an hour."""
    run = RunProcess.for_run(premise="; rm -rf /", profile="tiny", tone="",
                             cwd=Path("."))
    assert all("rm -rf" not in part for part in run.command)
    assert "rm -rf" in run.prompt


# --------------------------------------------------------- reading it right


def test_the_slug_is_learned_from_the_paths_the_run_writes():
    """Claude Code derives the slug from the premise itself, so the launcher
    cannot know it in advance. A guessed slug opens the wrong novel, or none."""
    assert replay().slug == "night-dispatcher-recovered-climber"


def test_subagent_dispatches_are_counted_by_name():
    state = replay()
    assert len(state.dispatched) >= 10
    assert "chapter-writer" in state.dispatched
    assert "continuity-critic" in state.dispatched


def test_the_whole_run_cost_comes_from_the_result_event():
    """The figure v1 could not see. Its absence is why a $6.21 estimate stood in
    for $49.33 — the difference being the orchestrator's own turns, which this
    number includes."""
    state = replay()
    assert state.finished is True
    assert state.total_cost_usd == pytest.approx(19.00, abs=0.5)
    assert state.turns and state.turns > 100


def test_an_unfamiliar_shape_never_raises():
    """The stream belongs to someone else and may grow shapes this reader has
    never seen. One real event carries `message` as a plain string."""
    state = State()
    for event in ({"type": "nonsense"}, {"type": "assistant", "message": "a string"},
                  {"type": "assistant", "message": {"content": "not a list"}},
                  {}):
        state = apply(state, event)
    assert state.slug is None


# -------------------------------------------------------------- the ceiling


def test_context_size_counts_the_cache_not_just_the_input():
    """**`input_tokens` alone is nearly always 2.** Almost the whole context
    arrives cached, so a watcher reading only that field reports two-token calls
    and never trips — a ceiling that cannot be exceeded because it is measuring
    the wrong thing. Found by replaying a real run."""
    usage = {"input_tokens": 2, "cache_creation_input_tokens": 45_839,
             "cache_read_input_tokens": 0, "output_tokens": 1}
    assert context_size(usage) == 45_841


def test_the_orchestrators_own_turns_are_recorded_and_never_fatal():
    """Across two real runs the orchestrator's turns ran at a median of 147,000
    and a peak of 642,000 tokens. Halting on those would halt every run inside a
    minute — the 100,000 ceiling was never the orchestrator's budget."""
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    watcher = ContextWatcher(ceiling=100_000)
    for event in process.events():
        watcher.observe_event(event)  # must not raise
    assert watcher.orchestrator_turns > 10
    assert watcher.largest_orchestrator_turn > 100_000


def test_an_oversized_subagent_packet_halts_the_run():
    """The check that will fire the day those figures populate. It costs nothing
    to have waiting."""
    watcher = ContextWatcher(ceiling=100_000)
    with pytest.raises(WatchTripped) as trip:
        watcher.observe_event({
            "type": "system", "subtype": "task_progress",
            "subagent_type": "chapter-writer",
            "usage": {"input_tokens": 120_000},
        })
    assert trip.value.kind == "context"
    assert "chapter-writer" in trip.value.detail


def test_context_size_reads_total_tokens_when_the_input_fields_are_absent():
    """SPEC-010 W2. Every `task_progress` event carries
    `usage: {total_tokens, tool_uses, duration_ms}` — none of the three input
    fields `context_size` summed. Three real runs were read as "no packet data"
    because of a key name."""
    assert context_size({"total_tokens": 13921, "tool_uses": 1, "duration_ms": 93451}) == 13921


def test_context_size_prefers_the_input_fields_when_they_exist():
    """The orchestrator's own turns carry the three fields; their sum is the
    context, and `total_tokens` (if present) would double-count output."""
    usage = {"input_tokens": 2, "cache_creation_input_tokens": 45_839,
             "cache_read_input_tokens": 0, "output_tokens": 1, "total_tokens": 99_999}
    assert context_size(usage) == 45_841


def test_the_fixture_packet_is_measured_not_absent():
    """Replaces `test_unreported_packets_are_absent_rather_than_zero`, whose
    claim — that the recording's packets read empty — was the key-name mistake
    itself. The fixture carries one packet, worldbuilder's, 13,921 tokens."""
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    watcher = ContextWatcher(ceiling=100_000)
    for event in process.events():
        watcher.observe_event(event)
    assert watcher.packets_measured == 1
    assert watcher.largest_packet == 13921
    assert watcher.by_agent["worldbuilder"] == 13921
    assert watcher.packet_series_provenance == "measured"


def test_an_empty_usage_is_still_absent_never_zero():
    """The old test's real point, kept for the case it was about: a
    `task_progress` whose `usage` is empty reports nothing, not a tiny packet."""
    watcher = ContextWatcher(ceiling=100_000)
    watcher.observe_event({"type": "system", "subtype": "task_progress",
                           "subagent_type": "chapter-writer", "usage": {}})
    assert watcher.packets_measured == 0
    assert watcher.packet_series_provenance == "absent"


# --------------------------------------------------------------- the budget


def test_the_budget_stops_the_run_when_the_reported_cost_crosses_it():
    watcher = BudgetWatcher(ceiling_usd=5.0, pricing={"models": {}})
    state = State(total_cost_usd=19.0)
    with pytest.raises(WatchTripped) as trip:
        watcher.observe(state)
    assert trip.value.kind == "budget"


def test_the_budget_prices_tokens_at_the_worst_rate_on_file():
    """A ceiling that under-estimates is not a ceiling."""
    pricing = {"models": {"a": {"input_per_mtok": 1, "output_per_mtok": 25},
                          "b": {"input_per_mtok": 1, "output_per_mtok": 5}}}
    watcher = BudgetWatcher(ceiling_usd=1000.0, pricing=pricing)
    watcher.observe(State(input_tokens=1_000_000, output_tokens=0))
    assert watcher.spent_usd == pytest.approx(25.0)


def test_a_unit_stopped_before_it_reported_still_counts_against_the_ceiling():
    """The hole the conductor opened, and the reason the ceiling takes a max.

    A unit the context watcher stops is killed mid-turn and sends no `result`,
    so nobody reports its cost. A ceiling reading only the reported sum would
    forget that unit's spending for the rest of the run. The token estimate
    still carries it, so the larger of the two wins.
    """
    pricing = {"models": {"a": {"input_per_mtok": 1, "output_per_mtok": 30}}}
    watcher = BudgetWatcher(ceiling_usd=1000.0, pricing=pricing)

    # One unit finished and billed $2; a second burned two million tokens and
    # was killed before it could say so.
    watcher.observe(State(total_cost_usd=2.0,
                          input_tokens=1_000_000, output_tokens=1_000_000))

    assert watcher.spent_usd == pytest.approx(60.0),         "the reported $2 must not erase the tokens nobody billed for"


def test_the_reported_total_still_wins_when_it_is_the_larger():
    """It usually is: the bill includes the subagents and these tokens are the
    orchestrator's alone. The maximum is a floor under the ceiling, not a
    different way of pricing the run."""
    pricing = {"models": {"a": {"input_per_mtok": 1, "output_per_mtok": 30}}}
    watcher = BudgetWatcher(ceiling_usd=1000.0, pricing=pricing)

    watcher.observe(State(total_cost_usd=40.0, input_tokens=1000, output_tokens=1000))

    assert watcher.spent_usd == pytest.approx(40.0)


def test_stopping_the_replay_ends_the_stream():
    """A watcher that trips must actually be able to end the process."""
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    seen = 0
    for _ in process.events():
        seen += 1
        if seen == 3:
            process.stop()
    assert seen <= 4


# ------------------------------------------------- PLAN-007 6.1: the switches


def test_a_line_that_is_not_json_is_kept_as_skipped_not_silently_dropped(tmp_path):
    """SPEC-007 FR-RNR-2 / AC-2: a malformed line is *logged* and skipped. The
    parser used to `continue` and forget; a stream that quietly loses lines is
    indistinguishable from one that never had them."""
    fixture = tmp_path / "stream.jsonl"
    fixture.write_text(
        '{"type": "system", "subtype": "init"}\n'
        'this is not json\n'
        '{"type": "result", "total_cost_usd": 0.01, "num_turns": 1}\n',
        encoding="utf-8",
    )
    process = ReplayProcess(fixture=fixture)
    process.start()
    events = list(process.events())
    assert [e["type"] for e in events] == ["system", "result"]
    assert process.skipped == ["this is not json"]


# ------------------------------------------------------- PLAN-007 6.4


def test_argv_carries_max_budget_usd_from_the_ceiling_it_is_given():
    """FR-BUD-1 / AC-21: the CLI has `--max-budget-usd`; it is the first line of
    defence and the watcher is the second. Same figure in both, or the two
    disagree about what the ceiling is."""
    run = RunProcess.for_run(premise="p", profile="tiny", tone="", cwd=Path("."),
                             max_budget_usd=12.5)
    i = run.command.index("--max-budget-usd")
    assert run.command[i + 1] == "12.5"
    assert "p" not in run.command, "the prompt is still on stdin"


def test_lines_yield_the_raw_line_beside_the_event():
    """What goes into `events.payload` is the line as written, not a
    re-serialisation of what this reader understood of it (AC-20)."""
    process = ReplayProcess(fixture=FIXTURE)
    process.start()
    pairs = list(process.lines())
    assert pairs, "the fixture has lines"
    for raw, event in pairs:
        assert isinstance(raw, str) and isinstance(event, dict)
        assert json.loads(raw) == event
    assert [e for _, e in pairs] == list(ReplayProcess(fixture=FIXTURE).events())


def test_the_watcher_knows_every_agent_file():
    """The set said 'the nine'. There are ten, and a dispatch to the tenth was
    'worth noticing rather than assuming' by a set that had never heard of it."""
    from backend.commons.runner.watch import AGENTS
    on_disk = {p.stem for p in (Path(__file__).resolve().parents[2] / ".claude" / "agents").glob("*.md")}
    assert AGENTS == on_disk, sorted(AGENTS ^ on_disk)


# ------------------------------------------------------- PLAN-011 11.2 (SPEC-011 W2)


def test_argv_carries_the_orchestrator_model_when_the_config_sets_one():
    run = RunProcess.for_run(premise="p", profile="tiny", tone="", cwd=Path("."), model="haiku")
    i = run.command.index("--model")
    assert run.command[i + 1] == "haiku"
    assert i > run.command.index("--allowedTools"), "after the tool list, so the list stays contiguous"
    assert "p" not in run.command, "the prompt is still on stdin"


def test_argv_carries_no_model_flag_when_the_config_leaves_it_null():
    run = RunProcess.for_run(premise="p", profile="tiny", tone="", cwd=Path("."), model=None)
    assert "--model" not in run.command
    default = RunProcess.for_run(premise="p", profile="tiny", tone="", cwd=Path("."))
    assert "--model" not in default.command


def test_the_orchestrator_model_is_read_from_the_resolved_config_not_a_literal(db, tmp_path):
    """SPEC-011 W2 / C6: `models.orchestrator` in novel.config.json, null by
    default (the CLI's own default); a profile overlay wins."""
    from backend.commons.config import loader
    from backend.commons.config.settings import Settings
    from backend.runs.service import RunService
    base = loader.resolve("tiny")
    assert "models" in base and base["models"]["orchestrator"] is None, "the knob exists and is null by default"
    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path, use_recorded_stream=False))
    assert "--model" not in svc._process("A premise long enough.", "tiny", "", base).command
    overlaid = {**base, "models": {**base["models"], "orchestrator": "haiku"}}
    cmd = svc._process("A premise long enough.", "tiny", "", overlaid).command
    assert cmd[cmd.index("--model") + 1] == "haiku"


def test_the_exam_and_eval_orchestrator_runs_on_sonnet():
    """Owner, 2026-09-24 ("baja el orquestador"): cheaper and faster than the
    session model, and not Haiku — on Haiku the orchestrator stopped using the
    project's agents (docs/iterations.md). Profiles only; the base stays null."""
    from backend.commons.config import loader
    for profile in ("exam", "eval"):
        assert loader.resolve(profile)["models"]["orchestrator"] == "sonnet", profile


def test_a_real_exam_run_launches_claude_with_model_sonnet(tmp_path):
    """The profile's figure reaches argv: the novel's orchestrator ran on Opus
    because its snapshot predated models.orchestrator, not because the flag was lost."""
    from backend.commons.config import loader
    from backend.commons.config.settings import Settings
    from backend.commons.db.connection import memory
    from backend.commons.db.migrate import migrate
    from backend.runs.service import RunService

    conn = memory(); migrate(conn)
    svc = RunService(conn, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                    use_recorded_stream=False))
    process = svc._process("a premise long enough", "exam", "", loader.resolve("exam"))
    assert process.command[process.command.index("--model") + 1] == "sonnet"


def test_the_tiny_orchestrator_runs_on_sonnet():
    """Owner, 2026-09-24 (~21:00 UTC, "Sonnet"): the profile the owner launches
    from the panel does not fall back to the CLI default (Opus)."""
    from backend.commons.config import loader
    assert loader.resolve("tiny")["models"]["orchestrator"] == "sonnet"
