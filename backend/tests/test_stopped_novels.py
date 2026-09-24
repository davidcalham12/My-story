"""SPEC-EXAM-007: a stopped novel can be continued, or put in the bin and restored.

Nothing here talks to a model. The resume tests build the **real** `RunProcess`
argv — that is what AC-1 and AC-2 pin — and hand the conductor a fake process
in its place, so no `claude` is ever launched.
"""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.commons.config import loader
from backend.commons.config.settings import Settings
from backend.commons.db import repository as repo
from backend.commons.runner.process import RunProcess
from backend.main import app
from backend.runs import conductor as C
from backend.runs import router as runs_router
from backend.runs import service as S
from backend.runs.service import Refused, RunService

from backend.tests.test_conductor import FakeProcess, result_line, turn

SLUG = "a-stopped-novel"
RUN_ID = "r007"


def _svc(db, tmp_path, **over) -> RunService:
    return RunService(db, Settings(db_path=tmp_path / "x.db", output_dir=tmp_path,
                                   use_recorded_stream=False, **over))


def _snapshot(**over) -> dict:
    """What a run started before today was snapshotted with: the orchestrator
    on the CLI's default (null), which for every stopped run today was Opus."""
    cfg = loader.resolve("tiny")
    cfg["models"] = {"orchestrator": None}
    cfg.update(over)
    return cfg


def _make_run(db, tmp_path, *, halted=("context", "x"), snapshot=None,
              upto: int = 0, stage="FLOW-4", run_id=RUN_ID, slug=SLUG,
              spent: float | None = 5.0) -> Path:
    """A run on disk with its Bible and outline done and `upto` chapters
    promoted, and `spent` measured by its first segment (None: not measured)."""
    repo.create_run(db, run_id=run_id, slug=slug, premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=snapshot or _snapshot())
    repo.set_stage(db, run_id, stage)
    if spent is not None:
        repo.save_cost(db, run_id, cost_usd=spent, provenance="measured")
    if halted:
        repo.halt(db, run_id, *halted)
    run_dir = tmp_path / slug
    for unit in C.units_for(snapshot or _snapshot()):
        if unit.key == "chapter" and unit.chapter > upto:
            continue
        if unit.key == "finish":
            continue
        for rel in unit.outputs:
            (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (run_dir / rel).write_text(f"{unit.name}: {rel}\n", encoding="utf-8")
    return run_dir


def _complete(run_dir: Path, cfg: dict) -> None:
    for unit in C.units_for(cfg):
        for rel in unit.outputs:
            (run_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (run_dir / rel).write_text("x", encoding="utf-8")


@pytest.fixture
def argv(monkeypatch, tmp_path):
    """Every `claude -p` the conductor would launch: its real argv recorded, a
    fake process started in its place that writes the unit's outputs."""
    launched: list[dict] = []
    real = RunProcess.for_prompt.__func__

    def for_prompt(cls, *, prompt, cwd, max_budget_usd=None, model=None, **kw):
        process = real(cls, prompt=prompt, cwd=cwd, max_budget_usd=max_budget_usd,
                       model=model, **kw)
        unit = next(l.split(": ", 1)[1] for l in prompt.splitlines() if l.startswith("unit: "))
        run_dir = Path(next(l.split(": ", 1)[1] for l in prompt.splitlines()
                            if l.startswith("run directory: ")))
        outputs = [l.strip() for l in prompt.split("Outputs this unit owes:")[1].splitlines() if l.strip()]
        launched.append({"unit": unit, "command": process.command})
        return FakeProcess([turn(900), result_line()],
                           writes={rel: f"{unit} wrote this\n" for rel in outputs},
                           run_dir=run_dir)

    monkeypatch.setattr(RunProcess, "for_prompt", classmethod(for_prompt))
    return launched


def _flag(command: list[str], name: str) -> str | None:
    return command[command.index(name) + 1] if name in command else None


# ------------------------------------------------------------------ AC-1


def test_a_continued_run_launches_with_the_profiles_current_orchestrator(db, tmp_path, argv):
    """The snapshot says null (the CLI default: Opus, the expensive one). The
    profile says sonnet today. The continuation runs on the profile's."""
    _make_run(db, tmp_path, upto=1)
    before = db.execute("SELECT config_snapshot FROM runs WHERE id = ?", (RUN_ID,)).fetchone()[0]

    _svc(db, tmp_path).resume(RUN_ID, _wait=True)

    assert argv, "nothing was launched"
    assert all(_flag(a["command"], "--model") == "sonnet" for a in argv), \
        [a["command"] for a in argv]
    after = db.execute("SELECT config_snapshot FROM runs WHERE id = ?", (RUN_ID,)).fetchone()[0]
    assert after == before, "the snapshot is not rewritten"
    assert json.loads(after)["models"]["orchestrator"] is None


def test_the_continuation_is_recorded_as_a_segment(db, tmp_path, argv):
    _make_run(db, tmp_path, upto=1)

    _svc(db, tmp_path).resume(RUN_ID, _wait=True)

    rows = [dict(r) for r in db.execute(
        "SELECT * FROM changes WHERE run_id = ? ORDER BY n", (RUN_ID,))]
    assert [r["n"] for r in rows] == [1, 2], "the original launch is segment one"
    assert [r["kind"] for r in rows] == ["generate", "continue"]
    seg = rows[-1]
    assert seg["orchestrator_model"] == "sonnet"
    assert seg["chapter_loop"] == "claude"
    assert seg["ceiling_usd"] == pytest.approx(25.0), "tiny's 25, fresh for this segment (§8)"
    assert seg["ceiling_by"] == "profile"
    assert seg["started_at"] and seg["finished_at"]
    # Two units at $0.40 each (chapters 2, 3) and the finish.
    assert seg["total_usd"] == pytest.approx(1.20)
    assert seg["provenance"] == "measured"
    assert seg["minutes"] is not None and seg["minutes"] >= 0, "this clock's, from its own start"
    # SPEC-EXAM-008's cost split is not measured here: absent, never 0.
    assert seg["orchestrator_usd"] is None and seg["agents_usd"] is None
    assert rows[0]["orchestrator_model"] is None, "segment one ran on what the snapshot said"


def test_the_original_launch_is_segment_one(db, tmp_path):
    svc = RunService(db, Settings(db_path=Path(":memory:"), output_dir=tmp_path,
                                  use_recorded_stream=True, budget_ceiling_usd=1000.0))
    svc._execute = lambda *a, **k: None          # no thread work: the row is the point
    created = svc.start("A lighthouse keeper on Titan hears her own calls.", "tiny", "")

    row = db.execute("SELECT * FROM changes WHERE run_id = ?", (created["id"],)).fetchone()
    assert row["n"] == 1
    assert row["kind"] == "generate"
    assert row["orchestrator_model"] == "sonnet"
    assert row["ceiling_by"] == "profile"
    assert row["total_usd"] is None, "not finished: absent, never 0"


def test_the_hand_made_resume_block_becomes_segment_two(db, tmp_path, argv):
    """The example novel's `cost.json` carries its first run and a resume that
    was recorded by hand (spec §8). Those are its segments one and two. Its
    budget is the exam profile's (60, so the per-novel cap is 120 > 74.20)."""
    exam = _snapshot(budget={"max_cost_usd": 60.0, "max_calls": 500,
                             "novel_ceiling_multiple": 2})
    run_dir = _make_run(db, tmp_path, upto=2, halted=None, stage="complete",
                        snapshot=exam)
    (run_dir / "cost.json").write_text(json.dumps({
        "total_cost_usd": 74.2047088, "provenance": "measured",
        "first_run_usd": 53.174548899999984,
        "resume": {"total_cost_usd": 21.0301599, "turns": 193,
                   "duration_ms": 3043542, "provenance": "measured"},
    }), encoding="utf-8")
    svc = _svc(db, tmp_path)

    svc.resume(RUN_ID, _wait=True)

    rows = [dict(r) for r in db.execute(
        "SELECT n, kind, total_usd, provenance, started_at, note FROM changes "
        "WHERE run_id = ? ORDER BY n", (RUN_ID,))]
    assert [r["n"] for r in rows] == [1, 2, 3]
    assert [r["kind"] for r in rows] == ["generate", "continue", "continue"]
    assert rows[0]["total_usd"] == pytest.approx(53.1745489)
    assert rows[1]["total_usd"] == pytest.approx(21.0301599)
    assert "hand-made" in rows[1]["note"], "a start time nobody recorded is said to be one"
    # The run's total now counts all three segments.
    total = json.loads((run_dir / "cost.json").read_text(encoding="utf-8"))["total_cost_usd"]
    assert total == pytest.approx(74.2047088 + rows[2]["total_usd"])


# ------------------------------------------------------------------ AC-2


@pytest.mark.parametrize("halted,spent", [
    (("budget", "spent $25.80 against a ceiling of $25.00"), 25.8),
    (("budget", "spent $25.80"), None),
    (("user", "halted by the user"), 10.0),
    (("user", "halted by the user"), 25.0),
    (("user", "halted by the user"), None),
    (None, 5.0),
])
def test_every_continuation_gets_the_profiles_ceiling_fresh(db, tmp_path, argv, halted, spent):
    """§8: Continue never asks for a figure. Whatever stopped the novel — its
    budget included — and whether its spend was measured or not, the segment
    runs under the profile's ceiling, fresh, recorded as the profile's."""
    _make_run(db, tmp_path, halted=halted, upto=3, spent=spent,
              stage="FLOW-4" if halted else "complete")

    out = _svc(db, tmp_path).resume(RUN_ID, _wait=True)

    assert [a["unit"] for a in argv] == ["finish"]
    assert float(_flag(argv[0]["command"], "--max-budget-usd")) == pytest.approx(25.0)
    assert out["ceiling_usd"] == pytest.approx(25.0) and out["ceiling_by"] == "profile"
    seg = db.execute("SELECT kind, ceiling_usd, ceiling_by FROM changes "
                     "WHERE run_id = ? ORDER BY n DESC", (RUN_ID,)).fetchone()
    assert seg["kind"] == "continue"
    assert seg["ceiling_usd"] == pytest.approx(25.0)
    assert seg["ceiling_by"] == "profile"


def test_continue_is_refused_once_the_novel_has_spent_its_per_novel_cap(db, tmp_path, argv):
    """SR-05, the owner's choice (2026-09-24, "Tope automático por novela"):
    no figure is asked, but a novel that has spent budget.novel_ceiling_multiple
    x its profile's ceiling (2 x 25 = 50 here) is not continued again, and the
    reason says so. Nothing is launched."""
    _make_run(db, tmp_path, halted=("budget", "spent $50.10"), upto=3, spent=50.1)

    with pytest.raises(Refused, match="50"):
        _svc(db, tmp_path).resume(RUN_ID, _wait=True)
    assert argv == []


def test_just_under_the_per_novel_cap_continues(db, tmp_path, argv):
    _make_run(db, tmp_path, halted=("budget", "spent $49"), upto=3, spent=49.0)

    _svc(db, tmp_path).resume(RUN_ID, _wait=True)
    assert argv


def test_novaforge_budget_still_lowers_the_continuations_ceiling(db, tmp_path, argv):
    _make_run(db, tmp_path, halted=("budget", "spent $25.80"), upto=3, spent=25.8)

    _svc(db, tmp_path, budget_ceiling_usd=7.0).resume(RUN_ID, _wait=True)

    assert float(_flag(argv[0]["command"], "--max-budget-usd")) == pytest.approx(7.0)


def test_continue_takes_no_figure(db, tmp_path):
    """No figure is asked for, so none can be passed: not to the service, not in
    the standing the panel reads, and there is no refusal that wants one."""
    import inspect
    assert "ceiling_usd" not in inspect.signature(RunService.resume).parameters
    assert not hasattr(S, "CeilingRequired")

    _make_run(db, tmp_path, halted=("budget", "spent $25.80"), upto=1, spent=None)
    standing = _svc(db, tmp_path).get(RUN_ID)
    assert "asks_for_figure" not in standing and "figure_reason" not in standing
    assert standing["ceiling_usd"] == pytest.approx(25.0), "shown as information"
    assert standing["spent_usd"] is None, "absent, never 0"


def test_the_resume_route_takes_no_body(db, tmp_path, client_for, monkeypatch):
    client, svc = client_for(db, tmp_path)
    _make_run(db, tmp_path, halted=("budget", "x"), upto=1)
    calls = []
    monkeypatch.setattr(svc, "resume", lambda run_id, **kw: calls.append((run_id, kw)) or
                        {"id": run_id, "ceiling_usd": 25.0, "ceiling_by": "profile"})

    r = client.post(f"/api/runs/{RUN_ID}/resume")

    assert r.status_code == 200
    assert calls == [(RUN_ID, {})], "nothing but the run id reaches the service"


def test_error_max_budget_usd_ends_as_a_budget_halt(db, run_budget_error):
    """The CLI's own ceiling ends a unit with this subtype. Filed as `process`,
    the panel would never ask for a new ceiling."""
    outcome = run_budget_error()
    assert outcome.halted is not None
    assert outcome.halted[0] == "budget"


@pytest.fixture
def run_budget_error(db, tmp_path):
    def go():
        repo.create_run(db, run_id="rb", slug="b", premise="a premise long enough",
                        profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
        run_dir = tmp_path / "b"
        line = json.dumps({"type": "result", "subtype": "error_max_budget_usd",
                           "is_error": True, "total_cost_usd": 3.1})
        maestro = C.Conductor(
            conn=db, run_id="rb", slug="b", run_dir=run_dir, cfg=loader.resolve("tiny"),
            process_factory=lambda unit, prompt, left=None: FakeProcess(
                [turn(500), line], run_dir=run_dir))
        return maestro.run()
    return go


def test_error_max_budget_usd_on_the_single_orchestrator_is_a_budget_halt(db, tmp_path):
    from backend.commons.runner.watch import State
    from backend.runs.service import Live

    repo.create_run(db, run_id="rs", slug="s", premise="a premise long enough",
                    profile="tiny", tone=None, snapshot=loader.resolve("tiny"))
    svc = _svc(db, tmp_path)
    line = json.dumps({"type": "result", "subtype": "error_max_budget_usd",
                       "is_error": True, "total_cost_usd": 3.1})
    svc._process = lambda *a, **k: FakeProcess([line], run_dir=tmp_path)
    svc._execute_single(Live(run_id="rs"), "p", "tiny", "", loader.resolve("tiny"))

    assert db.execute("SELECT halted FROM runs WHERE id='rs'").fetchone()["halted"] == "budget"


# ------------------------------------------------------------------ AC-3


def test_promoted_chapters_are_not_redone(db, tmp_path, argv):
    run_dir = _make_run(db, tmp_path, upto=2)
    ch01 = (run_dir / "chapters" / "ch01.md").read_bytes()

    _svc(db, tmp_path).resume(RUN_ID, _wait=True)

    assert [a["unit"] for a in argv] == ["chapter 3", "finish"]
    assert (run_dir / "chapters" / "ch01.md").read_bytes() == ch01


# ------------------------------------------------------------------ AC-5


def test_stopped_means_units_missing_not_stage(db, tmp_path, argv):
    """The example novel stopped itself at 8/10 with `stage = complete`. A rule
    by stage would never offer "Continuar" there."""
    _make_run(db, tmp_path, upto=2, halted=None, stage="complete")
    repo.finish(db, RUN_ID)
    svc = _svc(db, tmp_path)

    standing = svc.get(RUN_ID)
    assert standing["stopped"] is True
    assert standing["resume_from"] == "chapter 3"
    assert standing["resume_stage"] == "FLOW-4"

    svc.resume(RUN_ID, _wait=True)
    assert argv[0]["unit"] == "chapter 3"


def test_resume_refuses_a_complete_run_and_a_second_live_one(db, tmp_path, argv):
    run_dir = _make_run(db, tmp_path, upto=3)
    _complete(run_dir, _snapshot())
    svc = _svc(db, tmp_path)
    with pytest.raises(S.NotLive, match="complete"):
        svc.resume(RUN_ID, _wait=True)

    _make_run(db, tmp_path, run_id="other", slug="other-novel", upto=1)
    svc._live = S.Live(run_id="someone-else")
    with pytest.raises(S.AlreadyRunning, match="in flight"):
        svc.resume("other", _wait=True)
    assert argv == []


def test_the_refusals_reach_the_panel_with_their_reasons(db, tmp_path, client_for):
    client, svc = client_for(db, tmp_path)
    run_dir = _make_run(db, tmp_path, upto=3)
    _complete(run_dir, _snapshot())
    r = client.post(f"/api/runs/{RUN_ID}/resume", json={})
    assert r.status_code == 409 and "complete" in r.json()["detail"]

    _make_run(db, tmp_path, run_id="b1", slug="budget-novel", halted=("budget", "x"))
    svc._live = S.Live(run_id="b1")
    r = client.post("/api/runs/b1/trash")
    assert r.status_code == 409 and "live" in r.json()["detail"]


def test_trash_refuses_only_a_live_run(db, tmp_path):
    run_dir = _make_run(db, tmp_path, upto=3)
    svc = _svc(db, tmp_path)
    svc._live = S.Live(run_id=RUN_ID)
    with pytest.raises(S.Refused, match="live"):
        svc.trash(RUN_ID)
    assert run_dir.is_dir()


def test_a_complete_novel_goes_to_the_bin_and_comes_back(db, tmp_path, client_for):
    """§8.3: every novel can be binned, the complete ones too. Only its
    `output/<slug>/` moves; the PDFs already copied to `ejemplos/` stay."""
    client, _ = client_for(db, tmp_path)
    run_dir = _make_run(db, tmp_path, upto=3, halted=None, stage="complete")
    _complete(run_dir, _snapshot())
    ejemplos = tmp_path / "ejemplos"
    ejemplos.mkdir()
    (ejemplos / "a-stopped-novel-v1.pdf").write_bytes(b"%PDF-1.7 v1")
    before, pdfs = _tree(run_dir), _tree(ejemplos)

    r = client.post(f"/api/runs/{RUN_ID}/trash")

    assert r.status_code == 200, r.text
    assert not run_dir.exists()
    assert _tree(tmp_path / "_papelera" / SLUG) == before
    assert _tree(ejemplos) == pdfs, "ejemplos/ is not touched"
    assert [x["id"] for x in client.get("/api/runs?trashed=true").json()] == [RUN_ID]

    assert client.post(f"/api/runs/{RUN_ID}/restore").status_code == 200
    assert _tree(run_dir) == before
    assert _tree(ejemplos) == pdfs


def test_the_100k_refusal_is_estimated_and_only_for_the_unit_that_halted(db, tmp_path, argv):
    """With `chapter_loop = claude` the packet cannot be measured before launch:
    the floor a fresh orchestrator carries (~48,800) plus bytes/4 of what the
    unit declares it reads. Refused only when that estimate is over and the
    unit is the one that halted."""
    run_dir = _make_run(db, tmp_path, upto=0, halted=("context", "chapter 1: a turn of 104,000"))
    (run_dir / "outline.md").write_text("x" * 220_000, encoding="utf-8")  # ~55,000 tokens
    svc = _svc(db, tmp_path)

    with pytest.raises(S.Refused, match="estimated"):
        svc.resume(RUN_ID, _wait=True)
    assert argv == []
    assert svc.get(RUN_ID)["context_refusal"] and "estimated" in svc.get(RUN_ID)["context_refusal"]

    # A halt on a different unit: the estimate alone does not refuse.
    repo.halt(db, RUN_ID, "context", "outline-audit: a turn of 104,000")
    svc.resume(RUN_ID, _wait=True)
    assert argv and argv[0]["unit"] == "chapter 1"


def test_the_estimate_is_the_floor_plus_a_quarter_of_the_bytes(tmp_path):
    unit = [u for u in C.units_for(loader.resolve("tiny")) if u.chapter == 2][0]
    (tmp_path / "outline.md").write_text("x" * 4000, encoding="utf-8")
    assert "outline.md" in unit.inputs
    assert C.estimate_packet(unit, tmp_path) == C.STARTUP_FLOOR + 1000


# ------------------------------------------------------------------ AC-4


def _tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_trash_and_restore_are_byte_identical(db, tmp_path):
    run_dir = _make_run(db, tmp_path, upto=1)
    (run_dir / "logs").mkdir(exist_ok=True)
    (run_dir / "logs" / "blob.bin").write_bytes(bytes(range(256)) * 10)
    (run_dir / "chapters" / "ch01.md").write_text("Él dijo: «ñ»\r\n", encoding="utf-8")
    before = _tree(run_dir)
    svc = _svc(db, tmp_path)

    svc.trash(RUN_ID)

    binned = tmp_path / "_papelera" / SLUG
    assert not run_dir.exists()
    assert _tree(binned) == before
    assert db.execute("SELECT trashed_at FROM runs WHERE id = ?", (RUN_ID,)).fetchone()[0]

    svc.restore(RUN_ID)

    assert not binned.exists()
    assert _tree(run_dir) == before
    assert db.execute("SELECT trashed_at FROM runs WHERE id = ?", (RUN_ID,)).fetchone()[0] is None


def test_the_library_hides_binned_runs_and_the_bin_lists_them(db, tmp_path, client_for):
    client, _ = client_for(db, tmp_path)
    _make_run(db, tmp_path, run_id="keep", slug="keep-me", upto=1)
    _make_run(db, tmp_path, run_id="bin", slug="bin-me", upto=1)

    assert client.post("/api/runs/bin/trash").status_code == 200

    library = client.get("/api/runs").json()
    assert [r["id"] for r in library] == ["keep"]
    binned = client.get("/api/runs?trashed=true").json()
    assert [r["id"] for r in binned] == ["bin"]
    assert binned[0]["trashed_at"]

    assert client.post("/api/runs/bin/restore").status_code == 200
    assert sorted(r["id"] for r in client.get("/api/runs").json()) == ["bin", "keep"]
    assert client.get("/api/runs?trashed=true").json() == []


def test_restore_refuses_when_the_directory_exists_again(db, tmp_path):
    run_dir = _make_run(db, tmp_path, upto=1)
    svc = _svc(db, tmp_path)
    svc.trash(RUN_ID)
    run_dir.mkdir()                               # someone made it again

    with pytest.raises(S.Refused, match="already exists"):
        svc.restore(RUN_ID)
    assert (tmp_path / "_papelera" / SLUG).is_dir(), "nothing moved"


def test_a_locked_directory_is_a_readable_error(db, tmp_path, monkeypatch, client_for):
    client, _ = client_for(db, tmp_path)
    run_dir = _make_run(db, tmp_path, upto=1)

    def locked(src, dst):
        raise PermissionError(13, "The process cannot access the file because it "
                                  "is being used by another process", str(src))

    monkeypatch.setattr(S, "_move", locked)
    r = client.post(f"/api/runs/{RUN_ID}/trash")

    assert r.status_code == 409
    assert "open" in r.json()["detail"] and SLUG in r.json()["detail"]
    assert run_dir.is_dir()
    assert db.execute("SELECT trashed_at FROM runs WHERE id = ?", (RUN_ID,)).fetchone()[0] is None


def test_a_new_run_never_takes_a_binned_slug(db, tmp_path):
    (tmp_path / "_papelera" / "a-lighthouse").mkdir(parents=True)
    assert S.unique_slug(db, "a-lighthouse", bin_dir=tmp_path / "_papelera") == "a-lighthouse-2"


def test_a_binned_run_is_not_resumed(db, tmp_path, argv):
    _make_run(db, tmp_path, upto=1)
    svc = _svc(db, tmp_path)
    svc.trash(RUN_ID)
    with pytest.raises(S.Refused, match="bin"):
        svc.resume(RUN_ID, _wait=True)


@pytest.fixture
def client_for():
    made = []

    def make(db, tmp_path):
        svc = _svc(db, tmp_path)
        app.dependency_overrides[runs_router.get_service] = lambda: svc
        c = TestClient(app)
        made.append(c)
        return c, svc

    yield make
    app.dependency_overrides.pop(runs_router.get_service, None)
