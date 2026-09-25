"""Ship a finished run to Langfuse: one session, a trace per version, spans per
call and per conductor unit, the validators' scores, the measured cost.

**Post-hoc, deliberately.** Claude Code is the orchestrator and its turns are not
ours to hook, so there is nothing to instrument live. What there is instead is a
record — `output/<slug>/` on disk and the archive in SQLite — and a program that
reads it afterwards. Three consequences, and two of them are gains:

* **It cannot fail a run.** A live sink needs a guard so that an unreachable
  dashboard never costs a novel. Here that guarantee is structural: this runs
  after the novel exists, and the worst it can do is exit non-zero.
* **It is re-runnable.** Every trace id and every score id is derived from the
  thing it describes, so a second export overwrites rather than duplicates.
* **It is not live**, and the timestamps in the dashboard are the export's, not
  the run's. The run's own clock travels in metadata (`ts`), which is the field
  to read when comparing against anything else. Said here because a reader who
  believes the wall clock will be wrong by however long the run sat on disk.

What goes up, and where it comes from:

    session         the run's slug                       state.json / runs.slug
    trace           one per row of `versions`            versions
    trace           one per change (SPEC-EXAM-008)       changes
    generation      its orchestrator and its agents,     changes (Σ result.modelUsage)
                    with the MEASURED cost
    span            one per agent call                   calls, logs/agents.jsonl
    span            one per conductor unit               events.unit
    score           every validator's verdict            validations
    score           every attempt's characteristics      attempts + scores
    prompt version  each agent's instructions            .claude/agents/*.md
    metadata        the run's measured total             cost.json / runs.cost_usd

**Only measured cost goes in `cost_details`** (SPEC-EXAM-008 §4). Langfuse sums
`cost_details` across a session; an estimate beside a measurement makes a total
that is neither. So the change traces' two generations carry the measured cost,
and each call keeps its four token figures while its estimated cost — with the
input/output/cache split 07fe3fb put in `cost_details` — moves to metadata
(`estimated_cost_usd`).

**Absent is never zero, and this is the last place it could become one.** A
characteristic nobody scored gets no score row: `scores.score` is NULL when the
critic returned nothing usable and there is no row at all when the critic did
not exist yet (006_prose_characteristic.sql), and a 0 sent for either publishes
a rejection nobody made — into the one system whose whole purpose is to be
believed later. The same rule governs cost: a run with no `result` event has
`cost_usd: null` and a sentence saying why, never 0.0.

Credentials come from the environment only. A flag lands in shell history and in
the process table where any other local user can read it; there is no --api-key
and no --secret here, and the check below names the missing variables and never
their values.

    LANGFUSE_PUBLIC_KEY   required
    LANGFUSE_SECRET_KEY   required
    LANGFUSE_BASE_URL     required, and required for a reason: the SDK defaults
                          to the EU host, so a US project's keys against the
                          default fail with a 401 that says nothing about
                          regions. Naming it every time is cheaper than
                          diagnosing that once.

Usage:

    python tools/export_to_langfuse.py output/<slug> --dry-run
    python tools/export_to_langfuse.py output/<slug>

`--dry-run` needs no credentials, no SDK and no network: it prints what would be
sent. It is how the tests run, and how a person checks the data before spending
anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import ExitStack, contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude" / "agents"

# `python tools/export_to_langfuse.py ...` puts `tools/` on the path and not the
# repository root, so the settings import below fails with ModuleNotFoundError
# from every working directory except one. The alternative was to repeat the
# database's default path here, and a path written in two places disagrees.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: All three, and the host is not optional. See the module docstring.
REQUIRED = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")

#: Enough of a field to recognise it, not a second copy of the novel.
MAX_FIELD_CHARS = 4000

#: Key-shaped strings, scrubbed before anything leaves the machine. The pair
#: this program is itself holding is caught by literal as well as by pattern.
KEY_PATTERNS = (
    re.compile(r"\b(?:pk|sk)-lf-[A-Za-z0-9\-_]{8,}", re.I),
    re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{8,}", re.I),
)


class Scrubber:
    """Pattern-based, plus whatever keys this process is holding, as literals."""

    def __init__(self, *literals: str) -> None:
        self._literals = [s for s in literals if s and len(s) > 8]

    def __call__(self, text):
        if not isinstance(text, str):
            return text
        out = text
        for literal in self._literals:
            out = out.replace(literal, "[REDACTED]")
        for pattern in KEY_PATTERNS:
            out = pattern.sub("[REDACTED]", out)
        if len(out) > MAX_FIELD_CHARS:
            out = out[:MAX_FIELD_CHARS] + f"\n[... {len(out) - MAX_FIELD_CHARS} more characters]"
        return out


def change_trace_id(run_id: str, n: int) -> str:
    """One change's trace: the same derivation the panel's reader uses."""
    from backend.costs.measure import change_trace_id as derive

    return derive(run_id, n)


def trace_id(seed: str) -> str:
    """The SDK's own derivation, reimplemented so `--dry-run` owes it nothing.

    `Langfuse.create_trace_id(seed=...)` is `sha256(seed).digest()[:16].hex()`.
    Copying four lines buys a dry run that imports no SDK at all; the copy is
    only safe while the two agree, and a test holds them together.
    """
    return hashlib.sha256(seed.encode("utf-8")).digest()[:16].hex()


# ---------------------------------------------------------------------------
# Reading the run
# ---------------------------------------------------------------------------

def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _agent_log(path: Path) -> list[dict]:
    """`logs/agents.jsonl`, one JSON object per line.

    A malformed line is fatal rather than skipped: a log this tool silently
    drops rows from is a cost figure that is quietly too low.
    """
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            sys.exit(f"{path}:{number} is not JSON: {exc}")
    return rows


def _calls_from_db(conn, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT stage, agent, model, chapter, attempt, input_tokens, output_tokens, "
        "cache_creation_input_tokens, cache_read_input_tokens, cost_usd, "
        "cost_provenance, provenance, duration_ms, ts, note FROM calls "
        "WHERE run_id = ? ORDER BY ts, id", (run_id,)).fetchall()
    return [dict(r, source="calls") for r in rows]


def _calls_from_log(rows: list[dict]) -> list[dict]:
    """The same shape, out of the log a v1-era run left behind.

    v1 recorded ONE total with no input/output split. It stays one total —
    splitting it here would invent two numbers from one and let Langfuse price
    the invention as fact — and it is graded `reconstructed` so a reader can see
    which figures were measured and which were read back off a transcript.
    """
    out = []
    for row in rows:
        if row.get("event") != "agent_call":
            continue
        tokens = row.get("tokens")
        out.append({
            "stage": row.get("stage") or "unknown",
            "agent": row.get("agent") or "unknown",
            "model": row.get("model") or "unknown",
            "chapter": row.get("chapter"),
            "attempt": row.get("iteration"),
            "input_tokens": None, "output_tokens": None,
            "total_tokens": tokens,
            "cost_usd": None,
            "provenance": "reconstructed" if tokens else "absent",
            "duration_ms": row.get("duration_ms"),
            "ts": row.get("ts") or "unknown",
            "note": row.get("note"),
            "verdict": row.get("verdict"),
            "source": "logs/agents.jsonl",
        })
    return out


def _attempts_from_log(rows: list[dict]) -> list[dict]:
    """The gate's verdicts out of `logs/agents.jsonl`, in the shape `attempts`
    and `scores` would have given.

    Eight of the runs in `output/` were written before the database existed, and
    for those this file is the only copy of what the gate decided. The `scores`
    object carries whichever characteristics that run's gate actually had — five
    before SPEC-006 — and the ones it does not carry get no score here, for the
    same reason a NULL does: the critic did not exist, which is not a zero.
    """
    out = []
    for row in rows:
        if row.get("event") != "gate_decision":
            continue
        out.append({
            "chapter": row.get("chapter"), "attempt": row.get("iteration"),
            "ts": row.get("ts"), "verdict": row.get("verdict"),
            "aggregate": row.get("aggregate"),
            "scores": {name: {"score": value, "note": row.get("note")}
                       for name, value in (row.get("scores") or {}).items()},
        })
    return out


def _cost(workspace: Path, run: dict | None) -> dict:
    """The run's own measured total, and where it came from.

    `cost.json` is Claude Code's `result` event — the whole run, orchestrator
    turns included, which is most of it. It is preferred over anything summed
    from `calls` for the reason 005_run_cost.sql was written: a reconstructed
    figure must never stand where a measured one exists.
    """
    measured = _json(workspace / "cost.json")
    if measured.get("total_cost_usd") is not None:
        return {"usd": float(measured["total_cost_usd"]),
                "provenance": measured.get("provenance") or "measured",
                "source": "cost.json (Claude Code's own `result` event)",
                "note": "the whole run, orchestrator turns included"}
    if run and run.get("cost_usd") is not None:
        return {"usd": float(run["cost_usd"]),
                "provenance": run.get("cost_provenance") or "measured",
                "source": "runs.cost_usd",
                "note": "archived from the run's `result` event"}
    return {"usd": None, "provenance": "absent", "source": "",
            "note": "no cost was measured: this run produced no `result` event "
                    "and left no cost.json. Absent, not zero — a 0 here would "
                    "say the novel was free."}


def _prompts() -> list[dict]:
    """Each agent's instructions, as a prompt Langfuse can version.

    Registering with a name that exists adds a version rather than overwriting,
    which is the whole point: "which prompt wrote this chapter" is answerable
    only if the prompt is an object with a history.
    """
    out = []
    for path in sorted(AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        out.append({"name": path.stem, "text": text,
                    "source": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]})
    return out


class Run:
    """Everything the export needs, gathered once, from both records."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


def collect(workspace: Path, conn: sqlite3.Connection | None) -> Run:
    """Read one run out of its directory and, when it is archived, its database.

    Both, not either. The directory is the only place `cost.json` lives and the
    only record a v1-era run left; the database is the only place versions,
    units and validations exist. A run archived from disk has both and they
    agree; a run that was never archived has one, and the gaps say so rather
    than reading as zeroes.
    """
    state = _json(workspace / "state.json")
    slug = state.get("slug") or workspace.name
    log = _agent_log(workspace / "logs" / "agents.jsonl")

    run = None
    if conn is not None:
        row = conn.execute("SELECT * FROM runs WHERE slug = ? OR id = ?",
                           (slug, slug)).fetchone()
        run = dict(row) if row else None

    gaps: list[str] = []
    run_id = (run or {}).get("id") or slug
    if conn is None:
        gaps.append("no database: versions, conductor units and validations are "
                    "unavailable, and the calls come from logs/agents.jsonl")
    elif run is None:
        gaps.append(f"the database has no run with slug {slug}; this directory "
                    f"has not been archived")

    versions, units, calls, attempts, validations, changes = [], [], [], [], [], []
    if run is not None:
        try:
            from backend.costs import repository as costs
            changes = costs.rows(conn, run_id)
        except sqlite3.OperationalError:
            # A database from before SPEC-EXAM-008: no per-change traces.
            gaps.append("no `changes` table: no per-change cost traces")
        versions = [dict(r) for r in conn.execute(
            "SELECT n, parent, reason, created_at FROM versions WHERE run_id = ? "
            "ORDER BY n", (run_id,))]
        units = [dict(r) for r in conn.execute(
            "SELECT unit, MIN(seq) AS first_seq, MAX(seq) AS last_seq, "
            "MIN(ts) AS first_ts, MAX(ts) AS last_ts, COUNT(*) AS events "
            "FROM events WHERE run_id = ? AND unit IS NOT NULL "
            "GROUP BY unit ORDER BY MIN(seq)", (run_id,))]
        calls = _calls_from_db(conn, run_id)
        attempts = _attempts(conn, run_id)
        validations = [dict(r) for r in conn.execute(
            "SELECT version, validator, kind, criterion, value, justification "
            "FROM validations WHERE run_id = ? "
            "ORDER BY version, validator, criterion IS NULL DESC, criterion",
            (run_id,))]

    if not calls:
        calls = _calls_from_log(log)
    if not attempts:
        attempts = _attempts_from_log(log)
    if not versions:
        # A run with no versions still has a trace. `n` is None so nothing
        # downstream can mistake it for version 1, which is a publication that
        # happened; this is a run that never published.
        gaps.append("no rows in `versions`: one trace for the whole run")
        versions = [{"n": None, "parent": None, "reason": "", "created_at": ""}]
    if not units:
        gaps.append("no `events.unit` rows: this run predates the conductor, or "
                    "its stream was never archived")

    return Run(slug=slug, run_id=run_id, workspace=workspace,
               premise=(run or state).get("premise", ""),
               profile=(run or state).get("profile", ""),
               stage=(run or state).get("stage", ""),
               versions=versions, units=units, calls=calls, attempts=attempts,
               validations=validations, cost=_cost(workspace, run),
               prompts=_prompts(), gaps=gaps, changes=changes)


def _attempts(conn, run_id: str) -> list[dict]:
    """Every attempt with its characteristics, NULLs included.

    The NULLs are carried rather than filtered here so that the count of
    characteristics a critic failed to answer can be reported. They are dropped
    where the scores are built, which is the one place the decision matters.
    """
    rows = conn.execute(
        "SELECT a.id, a.chapter, a.attempt, a.ts, a.verdict, a.aggregate, "
        "s.characteristic, s.score, s.note FROM attempts a "
        "LEFT JOIN scores s ON s.attempt_id = a.id WHERE a.run_id = ? "
        "ORDER BY a.chapter, a.attempt, s.characteristic", (run_id,)).fetchall()
    by_id: dict[int, dict] = {}
    for row in rows:
        entry = by_id.setdefault(row["id"], {
            "chapter": row["chapter"], "attempt": row["attempt"], "ts": row["ts"],
            "verdict": row["verdict"], "aggregate": row["aggregate"], "scores": {}})
        if row["characteristic"] is not None:
            entry["scores"][row["characteristic"]] = {"score": row["score"],
                                                      "note": row["note"]}
    return list(by_id.values())


# ---------------------------------------------------------------------------
# The plan: every call that would be made, in order, as data
# ---------------------------------------------------------------------------

def _version_for(ts: str | None, versions: list[dict]) -> dict:
    """Which version a call or a unit belongs to.

    The schema offers nothing better than the clock: `calls` has no version
    column and `events` has none either, so a call belongs to the first version
    published after it was made. Work that came after the last publication —
    including anything whose `ts` is the literal "unknown" a v1 import writes —
    lands on the last version, because that is the copy it was heading for.
    """
    if len(versions) == 1:
        return versions[0]
    for version in versions:
        if ts and version["created_at"] and ts <= version["created_at"]:
            return version
    return versions[-1]


def _score_value(raw):
    """A validator's verdict, on the scale the validator actually used.

    §2's score column reads pass/fail, a count, words, a fraction, hits and six
    scores, and 013_validations.sql keeps them TEXT for exactly that reason.
    Forcing `pass` to 1.0 invents a scale; a NULL value means the validator ran
    and had no answer, which is a fact worth carrying and is not a number.
    """
    if raw is None:
        return "no answer", "CATEGORICAL"
    try:
        return float(raw), "NUMERIC"
    except (TypeError, ValueError):
        return str(raw), "CATEGORICAL"


def plan(run: Run, scrub: Scrubber | None = None) -> list[dict]:
    """Everything that would be sent, as a list of operations.

    A plan rather than a stream of calls, because it makes `--dry-run` and the
    real export the same program: one builds the list and prints it, the other
    builds the list and performs it. A dry run that took a different path
    through the code would be checking a different program.
    """
    scrub = scrub or Scrubber(*(os.environ.get(name, "") for name in REQUIRED[:2]))
    ops: list[dict] = [{"op": "session", "session_id": run.slug}]

    for prompt in run.prompts:
        ops.append({"op": "prompt", "name": prompt["name"],
                    "prompt": scrub(prompt["text"]), "labels": ["production"],
                    "config": {"source": prompt["source"], "sha256": prompt["sha256"]}})

    trace_keys: dict[object, str] = {}
    for version in run.versions:
        n = version["n"]
        key = f"trace:{n}"
        trace_keys[n] = key
        name = f"{run.slug} v{n}" if n else run.slug
        ops.append({
            "op": "observation", "key": key, "parent": None, "as_type": "chain",
            "trace_context": {"trace_id": trace_id(f"{run.run_id}|v{n}")},
            "name": name,
            "input": {"premise": scrub(run.premise)},
            "metadata": {
                "run_id": run.run_id, "slug": run.slug, "profile": run.profile,
                "stage": run.stage, "version": n, "parent_version": version["parent"],
                "version_reason": version["reason"],
                "version_created_at": version["created_at"],
                "cost_usd": run.cost["usd"],
                "cost_provenance": run.cost["provenance"],
                "cost_source": run.cost["source"],
                "cost_note": run.cost["note"],
                # The measured total is Claude Code's accounting of the whole
                # process, which has no notion of a version. Saying so stops a
                # reader adding two traces together and doubling the bill.
                "cost_scope": "the whole run, not this version alone",
                "timestamps": "the observation times are the export's; the run's "
                              "own clock is in each span's `ts`",
                "export_gaps": run.gaps,
            },
        })

    # (version, chapter, attempt) -> the span that wrote that draft, so the
    # gate's verdict can be scored against the draft rather than against the run.
    writers: dict[tuple, str] = {}

    for unit in run.units:
        version = _version_for(unit["first_ts"], run.versions)
        ops.append({
            "op": "observation", "key": f"unit:{unit['unit']}",
            "parent": trace_keys[version["n"]], "as_type": "span",
            "name": f"unit:{unit['unit']}",
            "metadata": {k: unit[k] for k in
                         ("unit", "first_seq", "last_seq", "first_ts", "last_ts", "events")},
        })

    for index, call in enumerate(run.calls):
        version = _version_for(call.get("ts"), run.versions)
        key = f"call:{index}"
        name = f"{call['stage']}:{call['agent']}"
        if call.get("chapter"):
            name += f":ch{int(call['chapter']):02d}"

        usage = {k: v for k, v in
                 (("input", call.get("input_tokens")), ("output", call.get("output_tokens")),
                  ("cache_creation_input_tokens", call.get("cache_creation_input_tokens")),
                  ("cache_read_input_tokens", call.get("cache_read_input_tokens")),
                  ("total", call.get("total_tokens"))) if v}
        op = {
            "op": "observation", "key": key, "parent": trace_keys[version["n"]],
            "as_type": "generation", "name": name, "model": call.get("model"),
            "metadata": {**{k: scrub(v) for k, v in call.items()},
                         "version": version["n"]},
        }
        if usage:
            op["usage_details"] = usage
        # Never cost_details on a call (SPEC-EXAM-008 §4): the change's two
        # generations carry the measured cost, and anything here would be
        # added to it. An absent figure writes nothing at all.
        if call.get("cost_usd") is not None:
            if call.get("cost_provenance") == "measured":
                # A Python-loop process's own `result`: already in its change's
                # `agents` generation.
                op["metadata"]["measured_cost_usd"] = float(call["cost_usd"])
                op["metadata"]["cost_counted_in"] = "its change's agents generation"
            else:
                estimate = {"total": float(call["cost_usd"])}
                # The four parts, so input and output cost can be read apart
                # (estimated, at config/pricing.json's rates, like the total).
                if call.get("output_tokens") is not None and call.get("model"):
                    from backend.commons.config import loader
                    from backend.commons.log import agent_usage
                    parts = agent_usage.estimate_parts({
                        "model": call["model"],
                        **{k: int(call.get(k) or 0) for k in agent_usage.FIELDS}},
                        loader.load_pricing())
                    if parts:
                        estimate = parts
                op["metadata"]["estimated_cost_usd"] = estimate
        ops.append(op)

        if call["agent"] == "chapter-writer" and call.get("chapter"):
            writers.setdefault((version["n"], call["chapter"], call.get("attempt")), key)

    for attempt in run.attempts:
        version = _version_for(attempt["ts"], run.versions)
        observation = writers.get((version["n"], attempt["chapter"], attempt["attempt"]))
        for characteristic, entry in sorted(attempt["scores"].items()):
            if entry["score"] is None:
                # The critic was asked and returned nothing usable. No row: a 0
                # invents a rejection and a 10 invents an approval, and the
                # dashboard cannot tell either from a verdict somebody made.
                continue
            ops.append({
                "op": "score", "name": f"gate.{characteristic}",
                "value": float(entry["score"]), "data_type": "NUMERIC",
                "trace_id": trace_id(f"{run.run_id}|v{version['n']}"),
                "observation": observation,
                "score_id": f"{run.run_id}:ch{attempt['chapter']:02d}:"
                            f"a{attempt['attempt']}:{characteristic}",
                "comment": scrub(entry["note"] or
                                 f"ch{attempt['chapter']:02d} attempt {attempt['attempt']}: "
                                 f"{attempt['verdict']} (aggregate {attempt['aggregate']})"),
                "metadata": {"chapter": attempt["chapter"], "attempt": attempt["attempt"],
                             "verdict": attempt["verdict"]},
            })

    for row in run.validations:
        value, data_type = _score_value(row["value"])
        name = row["validator"]
        if row["criterion"]:
            name += f".{row['criterion']}"
        known = {v["n"] for v in run.versions}
        n = row["version"] if row["version"] in known else run.versions[-1]["n"]
        ops.append({
            "op": "score", "name": name, "value": value, "data_type": data_type,
            "trace_id": trace_id(f"{run.run_id}|v{n}"), "observation": None,
            "score_id": f"{run.run_id}:v{row['version']}:{row['validator']}:"
                        f"{row['criterion'] or '-'}",
            "comment": scrub(row["justification"] or ""),
            "metadata": {"kind": row["kind"], "version": row["version"],
                         "raw_value": row["value"]},
        })

    # Last, so each change's generations follow its trace and nothing else is
    # created inside a change's tag scope (see `send`).
    for change in getattr(run, "changes", []) or []:
        ops.extend(_change_ops(run, change))

    return ops


def _change_ops(run: Run, change: dict) -> list[dict]:
    """One change: a trace in the novel's session and its two generations.

    `cost_details` carries the MEASURED figure only, and only when it exists:
    an absent figure is no `cost_details` at all, never 0.00.
    """
    n = change["n"]
    key = f"change:{n}"
    chapters = change.get("chapters") or []
    tags = [change["kind"]]
    if change.get("version") is not None:
        tags.append(f"v{change['version']}")
    tags += [f"ch{int(c):02d}" for c in chapters]
    what = change["kind"].replace("_", " ")
    name = f"{run.slug} · {what} #{n}" + (f" · v{change['version']}"
                                        if change.get("version") is not None else "")
    common = {"change_n": n, "kind": change["kind"], "version": change.get("version"),
              "provenance": change.get("provenance") or "absent"}
    ops = [{
        "op": "observation", "key": key, "parent": None, "as_type": "chain",
        "trace_context": {"trace_id": change_trace_id(run.run_id, n)},
        "name": name, "tags": tags,
        "metadata": {
            **common, "run_id": run.run_id, "slug": run.slug,
            "chapters": chapters, "label": change.get("label"),
            "started_at": change.get("started_at"), "finished_at": change.get("finished_at"),
            "total_usd": change.get("total_usd"), "minutes": change.get("minutes"),
            "minutes_source": "Σ result.duration_ms (measured)",
            "results": change.get("results"), "unresulted": change.get("unresulted"),
            # Which `result` events the figures came from (§4).
            "sources": change.get("sources") or [],
            "note": change.get("note"),
        },
    }]
    for role in ("orchestrator", "agents"):
        usd = change.get(f"{role}_usd")
        op = {"op": "observation", "key": f"{key}:{role}", "parent": key,
              "as_type": "generation", "name": role,
              "model": change.get(f"{role}_model"),
              "metadata": {**common, "role": role,
                           "provenance": "measured" if usd is not None else "absent"}}
        if role == "orchestrator" and change.get("orchestrator_model") is None \
                and "no orchestrator" in (change.get("note") or ""):
            op["metadata"]["note"] = "no orchestrator (python loop)"
        if usd is not None:
            op["cost_details"] = {"total": float(usd)}
        ops.append(op)
    return ops


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------

def describe(ops: list[dict]) -> None:
    """What would be sent, grouped the way the dashboard will group it."""
    session = next(o for o in ops if o["op"] == "session")
    prompts = [o for o in ops if o["op"] == "prompt"]
    changes = [o for o in ops if o["op"] == "observation" and o["key"].startswith("change:")]
    traces = [o for o in ops if o["op"] == "observation" and o["parent"] is None
              and not o["key"].startswith("change:")]
    spans = [o for o in ops if o["op"] == "observation" and o["parent"] is not None
             and not o["key"].startswith("change:")]
    scores = [o for o in ops if o["op"] == "score"]

    print(f"{'session':<12}{session['session_id']}")
    print(f"{'prompts':<12}{len(prompts)} versions from .claude/agents/")
    for prompt in prompts:
        print(f"  {prompt['name']:<24}{prompt['config']['sha256']}")
    print()

    cost = traces[0]["metadata"]
    if cost["cost_usd"] is None:
        print(f"{'cost':<12}absent — {cost['cost_note']}")
    else:
        print(f"{'cost':<12}${cost['cost_usd']:.2f} {cost['cost_provenance']} "
              f"({cost['cost_source']})")
        print(f"{'':<12}{cost['cost_scope']}")
    print()

    for trace in traces:
        mine = [s for s in spans if s["parent"] == trace["key"]]
        calls = [s for s in mine if s["as_type"] == "generation"]
        units = [s for s in mine if s["as_type"] == "span"]
        here = [s for s in scores
                if s["trace_id"] == trace["trace_context"]["trace_id"]]
        print(f"trace       {trace['name']}  {trace['trace_context']['trace_id']}")
        if trace["metadata"]["version_reason"]:
            print(f"  reason    {trace['metadata']['version_reason']}")
        print(f"  units     {len(units)}"
              + (": " + ", ".join(u["metadata"]["unit"] for u in units) if units else ""))
        print(f"  calls     {len(calls)}")
        by_agent: dict[str, int] = {}
        for call in calls:
            by_agent[call["metadata"]["agent"]] = by_agent.get(call["metadata"]["agent"], 0) + 1
        for agent, count in sorted(by_agent.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {agent:<22}{count}")
        print(f"  scores    {len(here)}")
        for score in here:
            value = score["value"]
            shown = f"{value:g}" if isinstance(value, float) else value
            # What it was scored ABOUT, not only what it scored. Thirty-five
            # `gate.*` rows in a column are unreadable without it, and the first
            # question anybody asks of a 4 is which chapter it was.
            meta = score["metadata"]
            where = (f"ch{meta['chapter']:02d} attempt {meta['attempt']}"
                     if meta.get("chapter") else "")
            print(f"    {score['name']:<28}{str(shown):<10}{where}")
        print()

    roots = [c for c in changes if c["parent"] is None]
    if roots:
        print("changes     measured cost, one trace each")
        for root in roots:
            meta = root["metadata"]
            gens = {c["name"]: c for c in changes if c["parent"] == root["key"]}
            money = lambda g: (f"${g['cost_details']['total']:.2f}" if "cost_details" in g
                               else "absent")
            print(f"  #{meta['change_n']:<3}{meta['kind']:<15}"
                  f"{'' if meta['total_usd'] is None else format(meta['total_usd'], '.2f'):>8}"
                  f"  orchestrator {money(gens['orchestrator'])}"
                  f"  agents {money(gens['agents'])}  {meta['provenance']}")
        print()

    gaps = traces[0]["metadata"]["export_gaps"]
    if gaps:
        print("what the record could not give:")
        for gap in gaps:
            print(f"  - {gap}")
        print()
    print(f"nothing was sent. {_plural(traces + roots, 'trace')}, {_plural(spans, 'span')}, "
          f"{_plural(scores, 'score')} and {_plural(prompts, 'prompt version')} would be.")


def _plural(items: list, word: str) -> str:
    return f"{len(items)} {word}" + ("" if len(items) == 1 else "s")


# ---------------------------------------------------------------------------
# The real thing
# ---------------------------------------------------------------------------

def send(ops: list[dict], client, *, session_scope=None) -> dict:
    """Perform the plan against a client.

    `session_scope` is the one seam. In SDK v4 the session id is attached by
    `propagate_attributes`, a module-level context manager rather than a method,
    so it is the only part of the surface that cannot be substituted by handing
    this function a different object — which is what the tests need to do.
    """
    scope = session_scope or _propagate_attributes
    session = next(o for o in ops if o["op"] == "session")
    made: dict[str, object] = {}
    created: list = []
    counts = {"traces": 0, "spans": 0, "scores": 0, "prompts": 0}

    with scope(session_id=session["session_id"]), ExitStack() as outer:
        tagged = ExitStack()
        outer.callback(lambda: tagged.close())
        for op in ops:
            if op["op"] == "observation" and op["parent"] is None:
                # A change trace's tags are trace attributes, set by the same
                # scope as the session and held while its generations are made.
                tagged.close()
                tagged = ExitStack()
                if op.get("tags"):
                    tagged.enter_context(scope(session_id=session["session_id"],
                                               tags=op["tags"]))
            if op["op"] == "prompt":
                client.create_prompt(name=op["name"], prompt=op["prompt"], type="text",
                                     labels=op["labels"], config=op["config"])
                counts["prompts"] += 1
            elif op["op"] == "observation":
                kwargs = {k: v for k, v in op.items()
                          if k not in ("op", "key", "parent", "tags")}
                parent = made.get(op["parent"]) if op["parent"] else None
                observation = (parent.start_observation(**kwargs) if parent
                               else client.start_observation(**kwargs))
                made[op["key"]] = observation
                created.append(observation)
                counts["traces" if parent is None else "spans"] += 1
            elif op["op"] == "score":
                observation = made.get(op["observation"]) if op["observation"] else None
                client.create_score(
                    name=op["name"], value=op["value"], data_type=op["data_type"],
                    trace_id=op["trace_id"],
                    observation_id=observation.id if observation else None,
                    score_id=op["score_id"], comment=op["comment"],
                    metadata=op["metadata"])
                counts["scores"] += 1

        # Children before parents: a span ended before the spans hung under it
        # is a span whose duration excludes its own work.
        for observation in reversed(created):
            observation.end()

    # A short-lived process that exits without this loses its last batch.
    client.flush()
    return counts


def purge(client, trace_ids: list[str], *, sleep=None, timeout: float = 120) -> None:
    """Delete these traces and wait until Langfuse no longer returns them.

    SDK v4 mints observation ids itself, so a re-export adds rather than
    replaces. Deleting the run's traces first makes it a replacement; waiting
    matters because deletion is queued, and a deletion still pending when the
    new observations arrive would take them too. Reads use the v2 endpoint —
    the legacy GETs answer 410 in this organisation."""
    import time

    sleep = sleep or time.sleep
    client.api.trace.delete_multiple(trace_ids=list(trace_ids))
    waited = 0.0
    while any(client.api.observations.get_many(trace_id=t, limit=1).data
              for t in trace_ids):
        if waited >= timeout:
            sys.exit(f"Langfuse still returns observations for {trace_ids} after "
                     f"{timeout:.0f}s; nothing was sent")
        sleep(5)
        waited += 5


@contextmanager
def _propagate_attributes(*, session_id: str, tags: list[str] | None = None):
    """The SDK's own session scope, imported late so `--dry-run` never needs it."""
    from langfuse import propagate_attributes

    with propagate_attributes(session_id=session_id, **({"tags": tags} if tags else {})):
        yield


def credentials() -> None:
    """Present or not, by name. The values are never read into a message."""
    missing = [name for name in REQUIRED if not (os.environ.get(name) or "").strip()]
    if not missing:
        return
    sys.exit(
        "not configured: " + ", ".join(missing) + "\n"
        "These are read from the environment only — never from a flag, which "
        "would land in shell history and in the process table.\n"
        "  PowerShell:  $env:LANGFUSE_PUBLIC_KEY = 'pk-lf-...'\n"
        "  bash:        export LANGFUSE_PUBLIC_KEY=pk-lf-...\n"
        "LANGFUSE_BASE_URL is required rather than defaulted: the SDK points at "
        "the EU host on its own, and a US project's keys against it fail with a "
        "401 that never mentions regions. It is the host in the address bar of "
        "your dashboard — https://cloud.langfuse.com or https://us.cloud.langfuse.com."
    )


def _database() -> sqlite3.Connection | None:
    """The archive, when there is one. A directory that was never archived is
    exported from its own files rather than refused."""
    from backend.commons.config.settings import load_settings

    path = load_settings().db_path
    if not Path(path).is_file():
        return None
    from backend.commons.db.connection import connect

    return connect(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ship a finished storyMaker run to Langfuse.")
    parser.add_argument("workspace", type=Path, help="a run directory, e.g. output/<slug>")
    parser.add_argument("--replace", action="store_true",
                        help="delete this run's traces in Langfuse first and wait "
                             "until they are gone, so a re-export does not duplicate")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be sent; no credentials, no SDK, "
                             "no network")
    args = parser.parse_args(argv)

    if not args.workspace.is_dir():
        sys.exit(f"{args.workspace} is not a directory")

    run = collect(args.workspace, _database())
    ops = plan(run)

    if args.dry_run:
        describe(ops)
        return 0

    # Before the SDK is imported and before anything is constructed: the failure
    # this catches costs nothing to catch here and a 401 to catch later.
    credentials()

    from langfuse import get_client

    client = get_client()
    try:
        reachable = bool(client.auth_check())
        detail = ""
    except Exception as exc:                       # noqa: BLE001 — any of these means "cannot reach"
        reachable, detail = False, str(exc)
    if not reachable:
        sys.exit(f"Langfuse rejected these credentials or this host "
                 f"({os.environ['LANGFUSE_BASE_URL']}). "
                 f"A key pair is valid on exactly one region.\n{detail}")

    if args.replace:
        purge(client, [o["trace_context"]["trace_id"] for o in ops
                       if o["op"] == "observation" and o["parent"] is None])
    counts = send(ops, client)
    print(f"sent {counts['traces']} traces, {counts['spans']} spans, "
          f"{counts['scores']} scores and {counts['prompts']} prompt versions "
          f"to session {run.slug}")
    for gap in run.gaps:
        print(f"  gap: {gap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
