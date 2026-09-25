"""The Langfuse export, held against the five things it is bought for.

AC-10 asks for one session per novel, a trace per version, spans per agent call,
the validators' scores, the run's measured cost and the prompts as versions. Four
of those are shape and one of them is a measurement, and the measurement is the
one that can be wrong quietly: a characteristic nobody scored, sent as 0, becomes
a judgement in a dashboard that cannot tell it from one a critic actually made.
That is the same defect `test_absent_is_not_zero.py` guards inside the panel,
arriving here by a different door — the export is the only place where this
project's numbers leave the machine, so it is the last door.

The client is faked rather than mocked: a small recorder with the four methods
the exporter calls. It exists so these tests assert on *what was asked for* and
never on a network, which is also the reason the whole file runs at $0 and with
no credentials in the environment.
"""

from __future__ import annotations

import json
import socket
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from tools.export_to_langfuse import collect, main, plan, send

ROOT = Path(__file__).resolve().parents[2]

CHARACTERISTICS = ("continuity", "science", "outline", "length", "chatter", "prose")
JUDGE_CRITERIA = ("continuity", "tone", "narrative_arc", "character_coherence",
                  "pacing", "natural_personalisation")


class FakeObservation:
    """What one span was asked to be, and what was hung under it."""

    def __init__(self, recorder, parent, kwargs):
        self.id = f"obs-{len(recorder.observations)}"
        self.parent = parent
        self.kwargs = kwargs
        self.ended = False
        recorder.observations.append(self)
        self._recorder = recorder

    def start_observation(self, **kwargs):
        return FakeObservation(self._recorder, self, kwargs)

    def update(self, **kwargs):
        self.kwargs.update(kwargs)

    def end(self):
        self.ended = True


class FakeClient:
    """The four calls the exporter makes, recorded instead of sent.

    `session` stands in for `propagate_attributes`, which in SDK v4 is a module
    function and a context manager rather than a method — the one part of the
    surface that cannot be substituted by handing over a different object.
    """

    def __init__(self):
        self.sessions: list[str] = []
        self.observations: list[FakeObservation] = []
        self.scores: list[dict] = []
        self.prompts: list[dict] = []
        self.flushes = 0
        self.tags: list = []

    @contextmanager
    def session(self, *, session_id, tags=None):
        self.sessions.append(session_id)
        self.tags.append(tags)
        yield

    def start_observation(self, **kwargs):
        return FakeObservation(self, None, kwargs)

    def create_score(self, **kwargs):
        self.scores.append(kwargs)

    def create_prompt(self, **kwargs):
        self.prompts.append(kwargs)

    def flush(self):
        self.flushes += 1

    # -- the questions the tests ask of it --------------------------------
    @property
    def traces(self) -> list[FakeObservation]:
        return [o for o in self.observations if o.parent is None]

    def spans(self, as_type: str) -> list[FakeObservation]:
        return [o for o in self.observations
                if o.parent is not None and o.kwargs.get("as_type") == as_type]

    def score(self, name: str) -> dict | None:
        found = [s for s in self.scores if s["name"] == name]
        assert len(found) <= 1, f"{name} was scored {len(found)} times"
        return found[0] if found else None


# ---------------------------------------------------------------------------
# A run, seeded small enough to write the expected scores out by hand.
# ---------------------------------------------------------------------------

def workspace(tmp_path: Path, *, slug="demo", cost: dict | None = None) -> Path:
    ws = tmp_path / slug
    (ws / "logs").mkdir(parents=True)
    (ws / "state.json").write_text(
        json.dumps({"slug": slug, "premise": "a keeper's ledger",
                    "profile": "tiny", "stage": "complete"}),
        encoding="utf-8")
    (ws / "logs" / "agents.jsonl").write_text("", encoding="utf-8")
    if cost is not None:
        (ws / "cost.json").write_text(json.dumps(cost), encoding="utf-8")
    return ws


def seed(db: sqlite3.Connection, *, scores: dict | None = None) -> None:
    """One run, two versions, three calls, two conductor units, one attempt.

    The timestamps are the load-bearing part: a call is assigned to the version
    it was made for, and the only thing the schema offers to do that with is the
    clock. Version 1 closes at noon on the 1st, so the two calls before it are
    its, and the call on the 2nd belongs to version 2.
    """
    db.execute(
        "INSERT INTO runs (id, slug, premise, profile, tone, config_snapshot, "
        "stage, started_at) VALUES ('r1','demo','a keeper''s ledger','tiny',NULL,"
        "'{}','complete','2026-01-01T08:00:00Z')")
    db.executemany(
        "INSERT INTO versions (run_id, n, parent, reason, created_at) VALUES (?,?,?,?,?)",
        [("r1", 1, None, "first publication", "2026-01-01T12:00:00Z"),
         ("r1", 2, 1, "the recipient's dog was called Bruno", "2026-01-02T12:00:00Z")])
    db.executemany(
        "INSERT INTO calls (run_id, stage, agent, model, chapter, attempt, "
        "input_tokens, output_tokens, cost_usd, provenance, ts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [("r1", "FLOW-1", "worldbuilder", "claude-opus-5", None, None,
          1000, 200, 0.5, "measured", "2026-01-01T09:00:00Z"),
         ("r1", "FLOW-4", "chapter-writer", "claude-opus-5", 1, 1,
          2000, 900, 1.25, "measured", "2026-01-01T10:00:00Z"),
         ("r1", "FLOW-4", "chapter-writer", "claude-opus-5", 1, 1,
          None, None, None, "absent", "2026-01-02T10:00:00Z")])
    db.executemany(
        "INSERT INTO events (run_id, seq, ts, type, payload, unit) VALUES (?,?,?,?,?,?)",
        [("r1", 1, "2026-01-01T09:00:00Z", "system", "{}", "world"),
         ("r1", 2, "2026-01-01T09:30:00Z", "assistant", "{}", "world"),
         ("r1", 3, "2026-01-01T10:00:00Z", "assistant", "{}", "chapter 1"),
         # Written before the conductor existed: absent, not "the first unit".
         ("r1", 4, "2026-01-01T11:00:00Z", "result", "{}", None)])

    cur = db.execute(
        "INSERT INTO attempts (run_id, chapter, attempt, title, draft_path, words, "
        "aggregate, verdict, promoted, ts) VALUES ('r1',1,1,'The Light',"
        "'chapters/ch01.attempt1.md',1200,6,'accept',1,'2026-01-01T10:05:00Z')")
    attempt_id = int(cur.lastrowid)
    db.executemany(
        "INSERT INTO scores (attempt_id, characteristic, score) VALUES (?,?,?)",
        [(attempt_id, c, v) for c, v in (scores if scores is not None else
                                         {"continuity": 9, "science": 8, "outline": 7,
                                          "length": 10, "chatter": 6}).items()])

    judged = {"continuity": ("8", "the ledger holds"), "tone": ("7", "steady"),
              "narrative_arc": ("9", "closes"), "character_coherence": ("8", "Ada is Ada"),
              "pacing": ("6", "chapter two sags"),
              # The judge returned nothing for this one. The ROW exists — it was
              # asked — and that is a different claim from a criterion nobody ran.
              "natural_personalisation": (None, "the judge returned no score")}
    db.executemany(
        "INSERT INTO validations (run_id, version, validator, kind, criterion, value, "
        "justification, ts) VALUES (?,?,?,?,?,?,?,?)",
        [("r1", 1, "judge_rubric", "b", name, value, why, "2026-01-01T12:00:00Z")
         for name, (value, why) in judged.items()]
        + [("r1", 1, "judge_rubric", "b", "mean", "7.6", "mean over 5 of 6 criteria",
            "2026-01-01T12:00:00Z"),
           ("r1", 1, "lean_chronology", "c", None, "pass", None, "2026-01-01T12:00:00Z"),
           ("r1", 1, "chapter_length", "a", None, "1200", None, "2026-01-01T12:00:00Z")])


def exported(db, ws) -> FakeClient:
    client = FakeClient()
    send(plan(collect(ws, db)), client, session_scope=client.session)
    return client


# ---------------------------------------------------------------------------


def test_one_session_one_trace_per_version_and_a_span_per_call_and_per_unit(db, tmp_path):
    """The shape AC-10 names, in one assertion each.

    A novel is now several orchestrators end to end (016_event_unit.sql), so the
    unit spans are not decoration: without them a trace of forty calls says
    nothing about which of the six processes was alive when each was made.
    """
    seed(db)
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 18.82,
                                                    "provenance": "measured"}))

    assert client.sessions == ["demo"]
    assert [t.kwargs["name"] for t in client.traces] == ["demo v1", "demo v2"]
    # Distinct trace ids, so version 2's scores cannot land on version 1.
    assert len({t.kwargs["trace_context"]["trace_id"] for t in client.traces}) == 2

    assert len(client.spans("generation")) == 3          # one per call
    assert sorted(s.kwargs["name"] for s in client.spans("span")) == [
        "unit:chapter 1", "unit:world"]                  # one per events.unit

    # The call made after version 1 was published belongs to version 2.
    by_trace: dict[str, list[str]] = {}
    for span in client.spans("generation"):
        by_trace.setdefault(span.parent.kwargs["name"], []).append(
            span.kwargs["metadata"]["ts"])
    assert by_trace["demo v2"] == ["2026-01-02T10:00:00Z"]

    assert client.flushes == 1


def test_the_scores_are_exactly_the_ones_the_database_holds(db, tmp_path):
    seed(db)
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 18.82,
                                                    "provenance": "measured"}))

    assert {s["name"] for s in client.scores} == {
        "gate.continuity", "gate.science", "gate.outline", "gate.length", "gate.chatter",
        *(f"judge_rubric.{c}" for c in JUDGE_CRITERIA if c != "natural_personalisation"),
        "judge_rubric.natural_personalisation", "judge_rubric.mean",
        "lean_chronology", "chapter_length",
    }
    assert client.score("gate.continuity")["value"] == 9.0
    assert client.score("judge_rubric.mean")["value"] == 7.6
    # The validators do not share a scale (013_validations.sql) and must not be
    # forced onto one: `pass` is a verdict, not a 1.
    assert client.score("lean_chronology")["value"] == "pass"
    assert client.score("lean_chronology")["data_type"] == "CATEGORICAL"
    # A justification is what makes a kind-b score checkable; it travels with it.
    assert "the ledger holds" in client.score("judge_rubric.continuity")["comment"]
    # The gate's verdict is scored against the span that wrote the draft, not
    # against the run, so "which draft scored 6" has an answer.
    assert client.score("gate.chatter")["observation_id"] is not None


def test_a_characteristic_nobody_scored_produces_no_score_row(db, tmp_path):
    """`prose` has no row at all; `science` has a row whose score is NULL.

    The two are different facts — the critic did not exist, and the critic
    answered nothing (006_prose_characteristic.sql) — and neither of them is a
    zero. Sending either as 0 publishes a rejection nobody made.
    """
    seed(db, scores={"continuity": 9, "science": None, "outline": 7,
                     "length": 10, "chatter": 6})
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 1.0,
                                                    "provenance": "measured"}))

    assert client.score("gate.prose") is None
    assert client.score("gate.science") is None
    assert client.score("gate.continuity")["value"] == 9.0
    assert not [s for s in client.scores if s["value"] == 0]


def test_a_run_with_no_measured_cost_exports_the_absence_not_a_zero(db, tmp_path):
    """No `result` event means no cost. The trace says so in words."""
    seed(db)
    client = exported(db, workspace(tmp_path))       # no cost.json, no runs.cost_usd

    for trace in client.traces:
        assert trace.kwargs["metadata"]["cost_usd"] is None
        assert trace.kwargs["metadata"]["cost_provenance"] == "absent"
        assert "no cost" in trace.kwargs["metadata"]["cost_note"]


def test_the_measured_total_travels_with_its_provenance(db, tmp_path):
    seed(db)
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 18.824992,
                                                    "provenance": "measured"}))
    metadata = client.traces[0].kwargs["metadata"]
    assert metadata["cost_usd"] == pytest.approx(18.824992)
    assert metadata["cost_provenance"] == "measured"
    assert "cost.json" in metadata["cost_source"]


def test_every_agent_prompt_is_registered_as_a_version(db, tmp_path):
    """"Which prompt wrote this chapter" is answerable only if the prompt is an
    object with versions, and `.claude/agents/*.md` is where they live."""
    seed(db)
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 1.0,
                                                    "provenance": "measured"}))
    names = {p["name"] for p in client.prompts}
    assert {"chapter-writer", "judge", "continuity-critic"} <= names
    assert all(p["labels"] == ["production"] for p in client.prompts)
    assert all(p["prompt"].strip() for p in client.prompts)


def test_a_key_shaped_string_in_a_note_never_leaves_the_machine(db, tmp_path):
    seed(db)
    db.execute("UPDATE calls SET note = ? WHERE agent = 'worldbuilder'",
               ("retried after sk-ant-abcdefghijklmnop was rejected",))
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 1.0,
                                                    "provenance": "measured"}))
    notes = [s.kwargs["metadata"].get("note") for s in client.spans("generation")]
    assert "[REDACTED]" in " ".join(n for n in notes if n)
    assert "sk-ant-abcdefghijklmnop" not in json.dumps(
        [s.kwargs for s in client.observations], default=str)


def test_a_run_that_was_never_archived_is_scored_from_its_own_log(tmp_path):
    """The gate's verdicts are in `logs/agents.jsonl` too, and for a directory
    the archive never saw they are the only copy.

    Reading them is what keeps AC-10 true of the runs that already exist: eight
    of the fourteen in `output/` predate the database, and an export that scored
    none of them would show an empty dashboard beside a real novel.
    """
    ws = workspace(tmp_path, cost={"total_cost_usd": 2.0, "provenance": "measured"})
    (ws / "logs" / "agents.jsonl").write_text("\n".join(json.dumps(row) for row in [
        {"event": "agent_call", "stage": "FLOW-4", "agent": "chapter-writer",
         "chapter": 1, "iteration": 1, "model": "claude-opus-5", "tokens": 9000,
         "ts": "2026-01-01T10:00:00Z"},
        # Five characteristics. `prose` did not exist when this run ran.
        {"event": "gate_decision", "chapter": 1, "iteration": 1, "aggregate": 7,
         "threshold": 8, "verdict": "retry", "ts": "2026-01-01T10:05:00Z",
         "scores": {"length": 10, "chatter": 10, "continuity": 7, "science": 10,
                    "outline": 10}},
    ]) + "\n", encoding="utf-8")

    client = FakeClient()
    send(plan(collect(ws, None)), client, session_scope=client.session)

    assert client.score("gate.continuity")["value"] == 7.0
    assert client.score("gate.prose") is None
    # And on the span that wrote the draft it judged, not on the run.
    assert client.score("gate.length")["observation_id"] is not None


def test_dry_run_needs_no_credentials_and_opens_no_socket(monkeypatch, capsys, tmp_path):
    """This is how the tests run and how a person checks the data before paying.

    The socket is stubbed rather than trusted: a `--dry-run` that quietly reached
    the network would still pass every other assertion in this file.
    """
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NOVAFORGE_DB", str(tmp_path / "absent.db"))
    monkeypatch.setattr(socket, "socket", _no_sockets)

    assert main([str(ROOT / "output" / "lighthouse-keeper-ledger"), "--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "session     lighthouse-keeper-ledger" in printed
    assert "$18.82" in printed                       # the measured total, from cost.json


def test_missing_credentials_are_reported_by_name_and_the_exit_is_non_zero(
        monkeypatch, tmp_path):
    """By name, never by value, and before anything is constructed.

    The region is the other half of this: the SDK defaults to the EU host, and a
    US project's keys against it fail with a 401 that says nothing about regions.
    """
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NOVAFORGE_DB", str(tmp_path / "absent.db"))
    monkeypatch.setattr(socket, "socket", _no_sockets)

    with pytest.raises(SystemExit) as exit_info:
        main([str(ROOT / "output" / "lighthouse-keeper-ledger")])

    message = str(exit_info.value)
    assert exit_info.value.code != 0
    assert "LANGFUSE_PUBLIC_KEY" in message and "LANGFUSE_SECRET_KEY" in message
    assert "LANGFUSE_BASE_URL" in message


def test_the_trace_id_this_tool_mints_is_the_one_the_sdk_would_mint():
    """The seed is hashed here rather than through `Langfuse.create_trace_id`, so
    that `--dry-run` owes the SDK nothing. That is only safe while the two agree.
    """
    from langfuse import Langfuse

    from tools.export_to_langfuse import trace_id

    assert trace_id("r1|v2") == Langfuse.create_trace_id(seed="r1|v2")


def _no_sockets(*args, **kwargs):
    raise AssertionError("the export opened a socket")


def test_a_call_ships_its_four_usage_figures_and_its_estimate_in_metadata(db, tmp_path):
    """usage_details carries input, output and both cache figures. The per-call
    estimate, with its input/output/cache split, moves to metadata
    (`estimated_cost_usd`): SPEC-EXAM-008 §8.4 supersedes 07fe3fb's cost_details."""
    seed(db)
    db.execute("UPDATE calls SET cache_creation_input_tokens = 300, "
               "cache_read_input_tokens = 40, cost_provenance = 'estimated' "
               "WHERE agent = 'worldbuilder'")
    client = exported(db, workspace(tmp_path, cost={"total_cost_usd": 1.0,
                                                    "provenance": "measured"}))
    span = next(s for s in client.spans("generation")
                if s.kwargs["name"].startswith("FLOW-1:worldbuilder"))
    usage = span.kwargs["usage_details"]
    assert usage["input"] == 1000 and usage["output"] == 200
    assert usage["cache_creation_input_tokens"] == 300
    assert usage["cache_read_input_tokens"] == 40
    assert "cost_details" not in span.kwargs, "an estimate never goes where Langfuse sums"
    parts = span.kwargs["metadata"]["estimated_cost_usd"]
    assert set(parts) >= {"input", "output", "cache_read_input_tokens",
                          "cache_creation_input_tokens", "total"}
    assert span.kwargs["metadata"]["cost_provenance"] == "estimated"


# ------------------------------------------------ SPEC-EXAM-008: one trace per change


def seed_changes(db) -> None:
    db.executemany(
        "INSERT INTO changes (run_id, n, kind, version, chapters, label, started_at, "
        "finished_at, total_usd, minutes, orchestrator_model, orchestrator_usd, "
        "agents_model, agents_usd, provenance, results, unresulted, sources, note) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [("r1", 1, "generate", None, None, None, "2026-01-01T08:00:00Z",
          "2026-01-01T11:00:00Z", 53.1745489, 118.6, "claude-opus-5[1m]", 48.7945489,
          "claude-haiku-4-5-20251001", 4.38, "measured", 1, 0, '["events seq 2038"]', None),
         ("r1", 2, "reader_change", 2, "[3, 10]", "dist/v2", "2026-01-02T08:00:00Z",
          "2026-01-02T09:00:00Z", 8.81, 39.0, "claude-sonnet-5", 8.04,
          "claude-haiku-4-5-20251001", 0.77, "measured", 2, 0,
          '["dist/v2/logs/ch10.stream.jsonl"]', None),
         ("r1", 3, "redo", 2, "[3]", "dist/v2 redo", "2026-01-02T10:00:00Z",
          None, None, None, None, None, None, None, "absent", 0, 1, "[]",
          "incomplete: 1 process without a result")])


def test_each_change_is_one_trace_with_two_generations_carrying_measured_cost(db, tmp_path):
    from tools.export_to_langfuse import change_trace_id

    seed(db)
    seed_changes(db)
    ops = plan(collect(workspace(tmp_path), db))

    roots = {o["trace_context"]["trace_id"]: o for o in ops
             if o["op"] == "observation" and o["parent"] is None}
    first = roots[change_trace_id("r1", 1)]
    assert first["metadata"]["provenance"] == "measured"
    assert first["metadata"]["kind"] == "generate"
    assert first["metadata"]["sources"] == ["events seq 2038"]
    assert set(first["tags"]) >= {"generate"}
    change2 = roots[change_trace_id("r1", 2)]
    assert set(change2["tags"]) >= {"reader_change", "v2", "ch03", "ch10"}

    gens = [o for o in ops if o["op"] == "observation" and o["parent"] == first["key"]]
    assert sorted(g["name"] for g in gens) == ["agents", "orchestrator"]
    by = {g["name"]: g for g in gens}
    assert by["orchestrator"]["as_type"] == "generation"
    assert by["orchestrator"]["model"] == "claude-opus-5[1m]"
    assert by["orchestrator"]["cost_details"] == {"total": pytest.approx(48.7945489)}
    assert by["agents"]["cost_details"] == {"total": pytest.approx(4.38)}
    assert by["orchestrator"]["cost_details"]["total"] + by["agents"]["cost_details"]["total"]         == pytest.approx(53.1745489)


def test_measured_cost_is_only_on_the_change_generations(db, tmp_path):
    """AC-3, on the ops list: every `cost_details` in the plan is a change's
    orchestrator or agents generation, and an absent figure sends none."""
    seed(db)
    seed_changes(db)
    ops = plan(collect(workspace(tmp_path), db))
    costed = [o for o in ops if "cost_details" in o]
    assert costed and all(o["name"] in ("orchestrator", "agents") for o in costed)
    assert all(o["metadata"]["provenance"] == "measured" for o in costed)
    redo = [o for o in ops if o["op"] == "observation"
            and o.get("metadata", {}).get("change_n") == 3 and o["parent"] is not None]
    assert redo and not any("cost_details" in o for o in redo), "absent is not $0"
    total = sum(o["cost_details"]["total"] for o in costed)
    assert total == pytest.approx(53.1745489 + 8.81)


def test_the_change_traces_are_sent_in_the_session_with_their_tags(db, tmp_path):
    seed(db)
    seed_changes(db)
    client = exported(db, workspace(tmp_path))
    assert set(client.sessions) == {"demo"}
    assert any("reader_change" in (t or []) for t in client.tags)
    names = [o.kwargs["name"] for o in client.observations if o.parent is not None]
    assert names.count("orchestrator") == 3 and names.count("agents") == 3


def test_replace_deletes_the_runs_traces_and_waits_until_they_are_gone():
    """A re-export must replace, not add: SDK v4 cannot fix an observation's id,
    so the run's traces are deleted first and the export waits for the queued
    deletion to finish, or it could delete what it is about to send."""
    from tools.export_to_langfuse import purge

    class Api:
        def __init__(self):
            self.deleted, self.polls = [], 0
            self.trace = self; self.observations = self

        def delete_multiple(self, *, trace_ids):
            self.deleted.append(list(trace_ids))

        def get_many(self, *, trace_id, limit):
            self.polls += 1
            return type("R", (), {"data": [1] if self.polls < 3 else []})()

    class Client:
        api = Api()

    waited = []
    purge(Client(), ["t1"], sleep=waited.append, timeout=60)
    assert Client.api.deleted == [["t1"]] and Client.api.polls == 3 and len(waited) == 2
