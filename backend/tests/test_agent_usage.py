"""One `calls` row per dispatched agent, from the Agent tool's own result.

`task_progress` carries only `total_tokens`, so every row it wrote had output
NULL and a single blended figure, and most dispatches never produced one. The
Agent tool's `tool_use_result` carries the four usage figures, the resolved
model and the duration; that is what a row is made from now. Cost per call is
`estimated` from config/pricing.json; the run's total stays `measured`.
"""

from __future__ import annotations

import json

import pytest

from backend.commons.config import loader
from backend.commons.db import repository
from backend.commons.log import agent_usage


def result_event(agent="chapter-writer", model="claude-haiku-4-5-20251001",
                 inp=10, cw=9823, cr=0, out=6078, ms=60844) -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result",
            "tool_use_id": "t1"}]},
            "tool_use_result": {"status": "completed", "agentType": agent,
                                "resolvedModel": model, "totalDurationMs": ms,
                                "totalTokens": inp + cw + cr + out,
                                "usage": {"input_tokens": inp,
                                          "cache_creation_input_tokens": cw,
                                          "cache_read_input_tokens": cr,
                                          "output_tokens": out}}}


def test_the_four_figures_the_model_and_the_duration_are_read():
    u = agent_usage.from_event(result_event())
    assert u == {"agent": "chapter-writer", "model": "claude-haiku-4-5-20251001",
                 "input_tokens": 10, "cache_creation_input_tokens": 9823,
                 "cache_read_input_tokens": 0, "output_tokens": 6078,
                 "duration_ms": 60844}


def test_anything_else_is_not_a_call():
    assert agent_usage.from_event({"type": "user", "tool_use_result": "text"}) is None
    assert agent_usage.from_event({"type": "system", "subtype": "task_progress",
                                   "usage": {"total_tokens": 5}}) is None


def test_the_cost_is_estimated_from_the_config_rates():
    rates = loader.load_pricing()["models"]["claude-haiku-4-5"]
    u = agent_usage.from_event(result_event())
    want = (10 * rates["input_per_mtok"] + 9823 * rates["cache_write_per_mtok"]
            + 0 * rates["cache_read_per_mtok"] + 6078 * rates["output_per_mtok"]) / 1e6
    assert agent_usage.estimate_cost(u, loader.load_pricing()) == pytest.approx(want)


def test_a_model_with_no_rate_has_no_cost():
    u = agent_usage.from_event(result_event(model="claude-unknown-9"))
    assert agent_usage.estimate_cost(u, loader.load_pricing()) is None


def test_reimport_rebuilds_a_runs_calls_from_its_streams(db, tmp_path):
    repository.create_run(db, run_id="r1", slug="s", premise="p", profile="exam",
                          tone=None, snapshot="{}")
    with db:
        db.execute("INSERT INTO calls (run_id, stage, agent, model, ts, input_tokens) "
                   "VALUES ('r1', 'FLOW-4', 'x', 'claude-code-session', 't', 5)")
    stream = tmp_path / "resume.stream.jsonl"
    stream.write_text("\n".join(json.dumps(e) for e in (
        {"type": "assistant", "message": {"content": [{"type": "text",
         "text": "FLOW-4 chapter 9"}]}},
        result_event(), result_event(agent="prose-critic", out=500))) + "\n",
        encoding="utf-8")
    n = agent_usage.reimport(db, "r1", extra_streams=[stream])
    rows = db.execute("SELECT agent, output_tokens, cache_creation_input_tokens, "
                      "cost_usd, cost_provenance, provenance FROM calls "
                      "WHERE run_id = 'r1' ORDER BY id").fetchall()
    assert n == 2 and [r["agent"] for r in rows] == ["chapter-writer", "prose-critic"]
    assert rows[0]["output_tokens"] == 6078 and rows[0]["cache_creation_input_tokens"] == 9823
    assert rows[0]["cost_provenance"] == "estimated" and rows[0]["provenance"] == "measured"
    assert rows[0]["cost_usd"] > 0
