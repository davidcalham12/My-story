"""SPEC-EXAM-006: the chapter loop in Python, driven by a fake runner at $0.

No test here launches `claude` or touches the network. Every agent is a fake
process handed out by an injected runner that answers per agent name from a
script of canned replies, in the shape of Claude Code's own `result` event.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from backend.chapters import loop as L
from backend.chapters.domain import decide, validate_sheet
from backend.commons.config import loader

SENTINEL = "ZQX-SENTINEL-PROSE-OF-ANOTHER-CHAPTER"
RUN_ID = "run-loop"
SLUG = "loop-fixture"

HEADING = "# Chapter 2 — The Second Morning"
BODY = (
    "Nell Harker opened the shutters before the gulls had finished their argument. "
    "The lamp room smelled of paraffin and cold brass.\n\n"
    "Below the rocks a grey boat rode the swell without hurry. "
    "She counted the oars twice and wrote the number in the ledger.\n\n"
    "Tom Reyes climbed the stair carrying bread and a question he would not ask. "
    "Outside, the tide turned its back on the harbour."
)
DRAFT = f"{HEADING}\n\n{BODY}\n"
DUP = "She counted the oars twice and wrote the number in the ledger."
DUP_FIXED = "She counted the oars and wrote the figure down."
GRAY = "The lamp room smelled of paraffin and cold brass."
GRAY_FIXED = "The lamp room smelled of paraffin and of brass left out overnight."

OUTLINE = """# Fixture — Outline

## Acts

One act.

### Chapter 1 — The First Night
- **Beats**:
  1. Nell lights the lamp.

### Chapter 2 — The Second Morning
- **Beats**:
  1. Nell counts the oars of a grey boat.
  2. Tom brings bread and does not ask.
- **Ends on**: the tide turning.

### Chapter 3 — The Third Day
- **Beats**:
  1. The boat returns.

## Notes for canon
"""

CONFIG = {
    "novel": {"chapters": 3, "tone": "quiet coastal mystery",
              "words_per_chapter": {"min": 50, "target": 70, "max": 90},
              "tolerance_pct": 20},
    "context": {"max_summary_words": 60, "max_concurrent_tokens": 100000},
    "quality_gate": {"threshold": 8, "max_revisions": 2},
    "budget": {"max_cost_usd": 3.0},
    "orchestration": {"chapter_loop": "python", "bible_critic": False},
}


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    run = tmp_path / SLUG
    for sub in ("bible", "chapters", "critiques", "logs"):
        (run / sub).mkdir(parents=True)
    (run / "bible" / "world.md").write_text(
        "# World\n\n## Rules\n\n- The lamp is lit at dusk.\n", encoding="utf-8")
    (run / "bible" / "characters.md").write_text(
        "# Characters\n\n- **Nell Harker** — the keeper.\n- **Tom Reyes** — the baker.\n",
        encoding="utf-8")
    (run / "bible" / "timeline.md").write_text("# Timeline\n\n- Day 1: the lamp.\n",
                                               encoding="utf-8")
    (run / "bible" / "mysteries.md").write_text("# Mysteries\n\n- M1: the boat.\n",
                                                encoding="utf-8")
    (run / "outline.md").write_text(OUTLINE, encoding="utf-8")
    (run / "config.snapshot.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    # Another chapter's prose, on disk, where a careless loop could reach it.
    for name in ("ch01.md", "ch01.attempt1.md", "ch01.attempt2.md",
                 "ch03.attempt1.md"):
        (run / "chapters" / name).write_text(
            f"# Chapter 1 — The First Night\n\n{SENTINEL} lit the lamp.\n",
            encoding="utf-8")
    (run / "chapters" / "ch01.summary.md").write_text(
        "Day 1. Nell lit the lamp and saw a grey boat. Still open: whose boat.\n",
        encoding="utf-8")
    return run


@pytest.fixture
def conn(db):
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
               "started_at, source) VALUES (?, ?, 'p', 'eval', '{}', 'FLOW-4', "
               "'2026-09-24T00:00:00Z', 'v2')", (RUN_ID, SLUG))
    db.commit()
    return db


# ------------------------------------------------------------------ the fakes


def _result(text: str, cost: float, *, error: str | None = None) -> dict:
    event = {"type": "result", "subtype": error or "success", "is_error": bool(error),
             "result": text, "total_cost_usd": cost, "duration_ms": 1200,
             "usage": {"input_tokens": 11, "cache_creation_input_tokens": 22,
                       "cache_read_input_tokens": 33, "output_tokens": 44},
             "modelUsage": {"claude-haiku-4-5-20251001": {"costUSD": cost}}}
    return event


class FakeProcess:
    """One agent process. `block` makes it wait until stopped, like a slow critic."""

    def __init__(self, call, text: str, *, cost: float = 0.05, block: bool = False,
                 raise_: Exception | None = None, error: str | None = None):
        self.call, self.text, self.cost = call, text, cost
        self.block, self.raise_, self.error = block, raise_, error
        self.started = self.stopped = self.finished = False
        self._stop = threading.Event()

    def start(self):
        self.started = True

    def lines(self):
        if self.block:
            self._stop.wait(10)
            return
        if self.raise_:
            raise self.raise_
        event = _result(self.text, self.cost, error=self.error)
        self.finished = True
        yield json.dumps(event), event

    def stop(self):
        self.stopped = True
        self._stop.set()

    @property
    def alive(self) -> bool:
        return self.started and not self.finished and not self.stopped


class FakeRunner:
    """Answers per agent name, in order. A reply is text, or a dict of options."""

    def __init__(self, script: dict[str, list], cost: float = 0.05):
        self.script = {k: list(v) for k, v in script.items()}
        self.cost = cost
        self.calls: list = []
        self.processes: list[FakeProcess] = []
        self.budgets: list[tuple[str, float | None, float]] = []

    def __call__(self, call):
        self.calls.append(call)
        # What had been spent when this one was launched: finished processes only.
        spent = sum(p.cost for p in self.processes if p.finished)
        self.budgets.append((call.agent, call.budget_usd, spent))
        replies = self.script.get(call.agent) or []
        reply = replies.pop(0) if replies else DEFAULTS[call.agent]
        opts = reply if isinstance(reply, dict) else {"text": reply}
        text = opts.get("text", "")
        proc = FakeProcess(call, text if isinstance(text, str) else json.dumps(text),
                           cost=opts.get("cost", self.cost), block=opts.get("block", False),
                           raise_=opts.get("raise"), error=opts.get("error"))
        self.processes.append(proc)
        return proc


CLEAN = json.dumps({"score": 10, "findings": []})
DEFAULTS = {
    "bible-critic": "{}",
    "chapter-writer": DRAFT,
    "continuity-critic": CLEAN,
    "science-critic": CLEAN,
    "outline-critic": json.dumps({"score": 10, "findings": [], "notes": ["10"]}),
    "prose-critic": json.dumps({"major": [], "minor": [], "notes": "clean"}),
}
SUMMARY = "Day 2. Nell counted the oars of the grey boat. Tom brought bread. Still open: whose boat."


def prose_major(*quotes: str, replacement: dict | None = None) -> str:
    items = []
    for q in quotes:
        item = {"quote": q, "claim": "the sentence does no work", "fix": "say it once"}
        if replacement and q in replacement:
            item["replacement"] = replacement[q]
        items.append(item)
    return json.dumps({"major": items, "minor": [], "notes": f"{len(items)} major"})


def run(run_dir, runner, **kw):
    kw.setdefault("loop_dir", run_dir.parent / "loop003")
    return L.run_chapter(run_dir, 2, runner=runner, **kw)


def assert_matches_decide(outcome):
    for a in outcome.attempts:
        expected = decide(aggregate=a["aggregate_for_decide"], attempt=a["attempt"],
                          patched=a["patched"], threshold=8)
        assert a["action"] == expected.action, a


# ------------------------------------------------------------------ AC-2


def test_accept_first_attempt_promotes_and_summarises(run_dir):
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY]})

    outcome = run(run_dir, runner)

    assert outcome.action == "accept" and outcome.verdict == "accept", outcome.halted
    assert (run_dir / "chapters" / "ch02.md").read_text(encoding="utf-8") == DRAFT
    assert (run_dir / "chapters" / "ch02.attempt1.md").is_file()
    assert (run_dir / "chapters" / "ch02.summary.md").read_text(encoding="utf-8").strip() == SUMMARY
    for c in ("continuity", "science", "outline", "length", "chatter", "prose"):
        raw = json.loads((run_dir / "critiques" / f"ch02.{c}.json").read_text(encoding="utf-8"))
        assert raw["critic"] == c and raw["chapter"] == 2
        assert raw["iterations"][0]["iteration"] == 1
        assert raw["iterations"][0]["score"] == 10
    agents = sorted(c.agent for c in runner.calls)
    assert agents == sorted(["chapter-writer", "continuity-critic", "science-critic",
                             "outline-critic", "prose-critic", "chapter-writer"])
    rows = [json.loads(line) for line in
            (run_dir / "logs" / "agents.jsonl").read_text(encoding="utf-8").splitlines()]
    gates = [r for r in rows if r.get("event") == "gate_decision"]
    assert len(gates) == 1 and gates[0]["verdict"] == "accept" and gates[0]["aggregate"] == 10
    assert_matches_decide(outcome)


def test_critics_are_dispatched_in_parallel(run_dir):
    """All four critics are started before any of them is read: they overlap."""
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY]})
    run(run_dir, runner)
    critics = [c.agent for c in runner.calls[1:5]]
    assert sorted(critics) == ["continuity-critic", "outline-critic", "prose-critic",
                               "science-critic"]
    assert all(c.schema for c in runner.calls[1:5]), "each critic runs with --json-schema"


def test_retry_then_accept_writes_a_valid_sheet(run_dir):
    patches = json.dumps({"patches": [{"find": DUP, "replace": DUP_FIXED, "why": "1"},
                                      {"find": GRAY, "replace": GRAY_FIXED, "why": "2"}]})
    runner = FakeRunner({
        "chapter-writer": [DRAFT, patches, SUMMARY],
        "prose-critic": [prose_major(DUP, GRAY)],
    })

    outcome = run(run_dir, runner)

    assert [a["action"] for a in outcome.attempts] == ["retry", "accept"]
    assert outcome.attempts[0]["scores"]["prose"] == 6
    second = (run_dir / "chapters" / "ch02.attempt2.md").read_text(encoding="utf-8")
    assert DUP_FIXED in second and DUP not in second
    sheet = (run_dir.parent / "loop003" / "sheets" / SLUG / "ch02.attempt2.md").read_text(
        encoding="utf-8")
    assert validate_sheet(sheet, 1).ok, validate_sheet(sheet, 1).problems
    redraft = runner.calls[5]
    assert redraft.agent == "chapter-writer"
    assert "CHAPTER 2 — ATTEMPT 2 OF 3" in redraft.packet
    assert DUP in redraft.packet, "the writer gets its own rejected draft back"
    assert (run_dir / "chapters" / "ch02.md").read_text(encoding="utf-8") == second
    assert_matches_decide(outcome)


def test_writer_patches_that_match_nothing_fall_back_to_a_full_rewrite(run_dir):
    nothing = json.dumps({"patches": [{"find": "not in the draft at all", "replace": "x"}]})
    runner = FakeRunner({
        "chapter-writer": [DRAFT, nothing, DRAFT.replace(DUP, DUP_FIXED), SUMMARY],
        "prose-critic": [prose_major(DUP, GRAY)],
    })
    outcome = run(run_dir, runner)
    assert outcome.action == "accept"
    assert [c.agent for c in runner.calls].count("chapter-writer") == 4
    assert "full rewrite" in outcome.attempts[1]["note"]


def test_third_attempt_patch_then_accept_is_patched(run_dir):
    fix = {DUP: DUP_FIXED, GRAY: GRAY_FIXED}
    runner = FakeRunner({
        "chapter-writer": [DRAFT, DRAFT, DRAFT, SUMMARY],
        "prose-critic": [prose_major(DUP, GRAY), prose_major(DUP, GRAY, replacement=fix),
                         prose_major(DUP, GRAY, replacement=fix)],
    })

    outcome = run(run_dir, runner)

    assert [a["action"] for a in outcome.attempts] == ["retry", "retry", "patch", "accept"]
    assert outcome.verdict == "patched"
    promoted = (run_dir / "chapters" / "ch02.md").read_text(encoding="utf-8")
    assert DUP_FIXED in promoted and DUP not in promoted and GRAY_FIXED in promoted
    assert (run_dir / "chapters" / "ch02.unpatched.attempt3.md").read_text(
        encoding="utf-8") == DRAFT
    prose = json.loads((run_dir / "critiques" / "ch02.prose.json").read_text(encoding="utf-8"))
    assert prose["iterations"][-1]["iteration"] == 3 and prose["iterations"][-1]["patched"] is True
    level2 = (run_dir.parent / "loop003" / "sheets" / SLUG / "ch02.attempt3.md").read_text(
        encoding="utf-8")
    assert validate_sheet(level2, 2).ok, validate_sheet(level2, 2).problems
    assert (run_dir / "chapters" / "ch02.summary.md").is_file()
    assert_matches_decide(outcome)


def test_patch_that_still_fails_halts_without_summary(run_dir):
    fix = {DUP: DUP_FIXED, GRAY: GRAY_FIXED}
    runner = FakeRunner({
        "chapter-writer": [DRAFT, DRAFT, DRAFT],
        "prose-critic": [prose_major(DUP, GRAY), prose_major(DUP, GRAY, replacement=fix),
                         prose_major(DUP, GRAY, replacement=fix),
                         prose_major(DUP_FIXED, GRAY_FIXED)],
    })

    outcome = run(run_dir, runner)

    assert outcome.action == "halt" and outcome.halted[0] == "gate"
    assert [a["action"] for a in outcome.attempts] == ["retry", "retry", "patch", "halt"]
    assert not (run_dir / "chapters" / "ch02.md").exists()
    assert not (run_dir / "chapters" / "ch02.summary.md").exists()
    assert (run_dir / "logs" / "ch02.halt.md").is_file(), "the loop writes why it stopped"
    assert_matches_decide(outcome)


def test_chatter_zero_skips_the_critics(run_dir):
    runner = FakeRunner({"chapter-writer": ["Here is the chapter you asked for.\n\n" + BODY,
                                            DRAFT, SUMMARY]})
    outcome = run(run_dir, runner)
    assert outcome.attempts[0]["scores"]["chatter"] == 0
    assert [c.agent for c in runner.calls][:2] == ["chapter-writer", "chapter-writer"]
    assert outcome.action == "accept"
    assert_matches_decide(outcome)


def test_a_finding_that_does_not_quote_the_draft_is_dropped(run_dir):
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY],
                         "prose-critic": [prose_major("a sentence this draft never had")]})
    outcome = run(run_dir, runner)
    assert outcome.attempts[0]["scores"]["prose"] == 10
    assert outcome.action == "accept"


def test_an_unusable_critic_reply_is_unscored_never_a_pass(run_dir):
    runner = FakeRunner({"chapter-writer": [DRAFT, DRAFT, DRAFT],
                         "science-critic": ["not json", "not json", "not json", "not json"]})
    outcome = run(run_dir, runner)
    assert outcome.attempts[0]["scores"]["science"] is None
    assert outcome.action == "halt"
    assert not (run_dir / "chapters" / "ch02.md").exists()


def test_a_summary_over_the_cap_is_asked_for_once_more_never_truncated(run_dir):
    long = " ".join(["word"] * 80)
    runner = FakeRunner({"chapter-writer": [DRAFT, long, long]})
    outcome = run(run_dir, runner)
    assert [c.agent for c in runner.calls].count("chapter-writer") == 3
    written = (run_dir / "chapters" / "ch02.summary.md").read_text(encoding="utf-8")
    assert len(written.split()) == 80
    assert any("over" in n for n in outcome.notes)


# ------------------------------------------------------------------ AC-3


def test_no_packet_carries_another_chapters_prose(run_dir):
    patches = json.dumps({"patches": [{"find": DUP, "replace": DUP_FIXED}]})
    runner = FakeRunner({
        "chapter-writer": [DRAFT, patches, SUMMARY],
        "prose-critic": [prose_major(DUP, GRAY)],
    })
    run(run_dir, runner)
    assert len(runner.calls) >= 10
    for call in runner.calls:
        assert SENTINEL not in call.packet, f"{call.agent} was handed another chapter's prose"
    writer = runner.calls[0].packet
    assert "Nell lit the lamp and saw a grey boat" in writer, "the rolling summary is there"
    assert "Nell counts the oars of a grey boat" in writer, "its own outline entry is there"
    assert "The boat returns" not in writer, "and no other chapter's entry"
    assert "Nell Harker" in writer and "Tom Reyes" in writer


# ------------------------------------------------------------------ AC-4


def test_packet_over_the_ceiling_is_not_dispatched(run_dir):
    (run_dir / "bible" / "world.md").write_text(
        "# World\n\n" + ("tide " * 80_000), encoding="utf-8")
    runner = FakeRunner({})

    outcome = run(run_dir, runner)

    assert runner.calls == []
    assert outcome.action == "halt" and outcome.halted[0] == "context"
    assert "100000" in outcome.halted[1].replace(",", "")
    figure = int(outcome.halted[1].split(" tokens")[0].split()[-1].replace(",", ""))
    assert figure > 100_000


# ------------------------------------------------------------------ AC-5


def test_every_call_row_has_four_figures_and_measured_cost(run_dir, conn):
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY]})
    run(run_dir, runner, conn=conn, run_id=RUN_ID)

    rows = conn.execute("SELECT * FROM calls WHERE run_id = ?", (RUN_ID,)).fetchall()
    assert len(rows) == len(runner.calls) == 6
    for r in rows:
        assert (r["input_tokens"], r["cache_creation_input_tokens"],
                r["cache_read_input_tokens"], r["output_tokens"]) == (11, 22, 33, 44)
        assert r["cost_usd"] == pytest.approx(0.05)
        assert r["provenance"] == "measured" and r["cost_provenance"] == "measured"
        assert r["model"] == "claude-haiku-4-5-20251001"
        assert r["stage"] == "FLOW-4" and r["chapter"] == 2


# ------------------------------------------------------------------ AC-5b


def test_parallel_critics_share_the_remaining_budget(run_dir):
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY]}, cost=0.05)
    outcome = run(run_dir, runner, ceiling_usd=1.00, spent_usd=0.10)

    assert outcome.action == "accept"
    rounds: dict[float, list[float]] = {}
    for agent, budget, spent in runner.budgets:
        assert budget is not None and budget > 0
        rounds.setdefault(round(spent, 6), []).append(budget)
    critics = rounds[0.05]
    assert len(critics) == 4, f"the four critics are one round: {runner.budgets}"
    assert sum(critics) <= 1.00 - 0.10 - 0.05 + 1e-9
    assert max(critics) < 1.00 - 0.10 - 0.05, "none was handed the whole remainder"
    for spent, handed in rounds.items():
        assert sum(handed) <= 1.00 - 0.10 - spent + 1e-9
    assert outcome.cost_usd == pytest.approx(0.05 * len(runner.calls))


def test_no_budget_left_halts_before_dispatch(run_dir):
    runner = FakeRunner({})
    outcome = run(run_dir, runner, ceiling_usd=1.00, spent_usd=1.00)
    assert runner.calls == []
    assert outcome.halted[0] == "budget"


def test_a_process_stopped_by_its_budget_halts_the_chapter(run_dir):
    runner = FakeRunner({"chapter-writer": [{"text": "", "error": "error_max_budget_usd"}]})
    outcome = run(run_dir, runner, ceiling_usd=1.00)
    assert outcome.halted[0] == "budget"
    assert not (run_dir / "chapters" / "ch02.md").exists()


# ------------------------------------------------------------------ AC-5c


def test_an_exception_kills_every_sibling(run_dir):
    slow = {"block": True}
    runner = FakeRunner({"chapter-writer": [DRAFT],
                         "continuity-critic": [slow], "science-critic": [slow],
                         "outline-critic": [slow],
                         "prose-critic": [{"raise": RuntimeError("the critic crashed")}]})
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="the critic crashed"):
        run(run_dir, runner)
    assert time.monotonic() - started < 5
    assert not [p for p in runner.processes if p.alive]
    assert all(p.stopped for p in runner.processes if p.block)


def test_a_halt_kills_every_sibling(run_dir):
    slow = {"block": True}
    runner = FakeRunner({"chapter-writer": [DRAFT],
                         "continuity-critic": [slow], "science-critic": [slow],
                         "outline-critic": [slow],
                         "prose-critic": [{"text": "", "error": "error_max_budget_usd"}]})
    started = time.monotonic()
    outcome = run(run_dir, runner, ceiling_usd=2.0)
    assert time.monotonic() - started < 5
    assert outcome.halted[0] == "budget"
    assert not [p for p in runner.processes if p.alive]


# ------------------------------------------------------------------ AC-5d


def test_single_and_python_is_refused_at_start(db, tmp_path, monkeypatch):
    from backend.commons.config.settings import Settings
    from backend.runs import conductor, service

    cfg = loader.resolve("eval")
    cfg["orchestration"] = {"chapter_loop": "python"}
    monkeypatch.setattr(service.loader, "resolve", lambda profile: cfg)
    svc = service.RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                          use_recorded_stream=False,
                                          single_orchestrator=True))
    launched: list = []
    svc._execute = lambda *a, **k: launched.append(a)

    with pytest.raises(service.OrchestrationRefused) as refused:
        svc.start("a premise", "eval", "")

    assert str(refused.value) == conductor.refusal(cfg, single=True)
    assert "NOVAFORGE_ORCHESTRATOR=single" in str(refused.value)
    assert "chapter_loop" in str(refused.value)
    assert launched == []
    assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_refusal_is_only_for_that_pair():
    from backend.runs.conductor import refusal

    python = {"orchestration": {"chapter_loop": "python"}}
    assert refusal(python, single=False) is None
    assert refusal({"orchestration": {"chapter_loop": "claude"}}, single=True) is None
    assert refusal({}, single=True) is None


# ------------------------------------------------------------------ AC-1 and the wiring


def test_the_switch_defaults_to_claude():
    assert loader.load_base()["orchestration"]["chapter_loop"] == "claude"
    for path in (loader.CONFIG / "profiles").glob("*.json"):
        assert L.mode(loader.resolve(path.stem)) == "claude", path.stem
    assert L.mode({}) == "claude", "a snapshot from before the switch is the old path"


def _conductor_run(tmp_path, db, cfg, chapter_loop):
    from backend.runs import conductor as C

    run_dir = tmp_path / "r"
    made: list = []

    class Proc:
        def __init__(self, unit):
            self.unit = unit

        def start(self):
            for rel in self.unit.outputs:
                (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                (run_dir / rel).write_text("x", encoding="utf-8")

        def lines(self):
            return iter(())

        def stop(self):
            pass

    def factory(unit, prompt, budget_left=None):
        made.append(unit.name)
        return Proc(unit)

    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
               "started_at, source) VALUES ('c', 'r', 'p', 'tiny', '{}', 'FLOW-1', "
               "'2026-09-24T00:00:00Z', 'v2')")
    maestro = C.Conductor(conn=db, run_id="c", slug="r", run_dir=run_dir, cfg=cfg,
                          process_factory=factory, max_budget_usd=5.0,
                          chapter_loop=chapter_loop)
    return maestro.run(), made, run_dir


def test_the_conductor_path_is_unchanged_by_default(tmp_path, db):
    cfg = loader.resolve("tiny")
    looped: list = []
    outcome, made, _ = _conductor_run(tmp_path, db, cfg,
                                      lambda n, left: looped.append(n))
    assert outcome.halted is None
    assert looped == []
    assert [m for m in made if m.startswith("chapter")] == [
        f"chapter {n}" for n in range(1, int(cfg["novel"]["chapters"]) + 1)]


def test_conductor_hands_chapter_units_to_the_loop(tmp_path, db):
    cfg = loader.resolve("tiny")
    cfg["orchestration"] = {"chapter_loop": "python"}
    looped: list = []

    def chapter_loop(n, left):
        looped.append((n, left))
        for name in (f"ch{n:02d}.md", f"ch{n:02d}.summary.md"):
            (run_dir_holder[0] / "chapters" / name).write_text("x", encoding="utf-8")
        return L.Outcome(chapter=n, action="accept", verdict="accept", cost_usd=0.5)

    run_dir_holder = [tmp_path / "r"]
    outcome, made, _ = _conductor_run(tmp_path, db, cfg, chapter_loop)

    assert outcome.halted is None
    assert not [m for m in made if m.startswith("chapter")]
    assert [n for n, _ in looped] == list(range(1, int(cfg["novel"]["chapters"]) + 1))
    lefts = [left for _, left in looped]
    assert lefts[1] == pytest.approx(lefts[0] - 0.5), "the loop's spend counts against the run"


def test_conductor_stops_on_a_loop_halt(tmp_path, db):
    cfg = loader.resolve("tiny")
    cfg["orchestration"] = {"chapter_loop": "python"}

    def chapter_loop(n, left):
        return L.Outcome(chapter=n, action="halt", verdict="halt",
                         halted=("gate", "aggregate 5 after the patch"))

    outcome, made, _ = _conductor_run(tmp_path, db, cfg, chapter_loop)
    assert outcome.halted == ("gate", "chapter 1: aggregate 5 after the patch")
    assert "finish" not in made


def test_change_dispatch_uses_the_loop_when_switched(tmp_path, monkeypatch):
    from backend.commons.config.settings import Settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate
    from backend.versions import change

    db_path = tmp_path / "x.db"
    c = connect(db_path)
    migrate(c)
    c.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, stage, "
              "started_at, source) VALUES ('r1', 'book', 'p', 'eval', '{}', 'complete', "
              "'2026-09-24T00:00:00Z', 'v2')")
    c.commit()
    c.close()
    settings = Settings(db_path=db_path, output_dir=tmp_path, repo_root=tmp_path)
    monkeypatch.setattr("backend.commons.config.settings.load_settings", lambda: settings)
    monkeypatch.setattr(change, "chapter_loop_mode", lambda profile: "python")
    monkeypatch.setattr(change, "unit_process",
                        lambda *a, **k: pytest.fail("a unit process was launched"))
    seen: list = []

    def fake_loop(workspace, n, **kw):
        seen.append((workspace, n, kw))
        (workspace / "chapters" / f"ch{n:02d}.md").write_text("new", encoding="utf-8")
        return L.Outcome(chapter=n, action="accept", verdict="accept", cost_usd=0.2)

    monkeypatch.setattr(L, "run_chapter", fake_loop)
    run_dir = tmp_path / "book"
    (run_dir / "bible").mkdir(parents=True)
    (run_dir / "chapters").mkdir()
    workspace = run_dir / "dist" / "v2"
    workspace.mkdir(parents=True)

    verdicts = change.dispatch(run_dir, workspace, (2, 3), "f1", "blue")

    assert verdicts == {2: True, 3: True}
    assert [n for _, n, _ in seen] == [2, 3]
    assert "blue" in seen[0][2]["change_note"]
    assert seen[0][2]["run_id"] == "r1"


def test_a_stop_from_outside_halts_and_kills_every_process(run_dir):
    """The operator's halt reaches the conductor, and through it the loop."""
    slow = {"block": True}
    runner = FakeRunner({"chapter-writer": [DRAFT],
                         "continuity-critic": [slow], "science-critic": [slow],
                         "outline-critic": [slow], "prose-critic": [slow]})
    stop = threading.Event()
    threading.Timer(0.2, stop.set).start()
    started = time.monotonic()
    outcome = run(run_dir, runner, stop=stop)
    assert time.monotonic() - started < 5
    assert outcome.halted[0] == "interrupted"
    assert not [p for p in runner.processes if p.alive]


def test_bible_critic_replaces_the_three_where_enabled(run_dir):
    cfg = dict(CONFIG, orchestration={"chapter_loop": "python", "bible_critic": True})
    (run_dir / "config.snapshot.json").write_text(json.dumps(cfg), encoding="utf-8")
    bible = json.dumps({"continuity": {"score": 10, "findings": []},
                        "science": {"score": 9, "findings": []},
                        "outline": {"score": 10, "findings": [], "notes": ["10"]}})
    runner = FakeRunner({"chapter-writer": [DRAFT, SUMMARY], "bible-critic": [bible]})
    outcome = run(run_dir, runner)
    agents = [c.agent for c in runner.calls]
    assert "bible-critic" in agents and "continuity-critic" not in agents
    assert outcome.attempts[0]["scores"]["science"] == 9
    assert outcome.action == "accept"
    science = json.loads((run_dir / "critiques" / "ch02.science.json").read_text(encoding="utf-8"))
    assert science["agent"] == "bible-critic"
