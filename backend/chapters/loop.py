"""One chapter, from first draft to promotion, conducted by code. SPEC-EXAM-006.

    python -m backend.chapters.loop <run_dir> <n> [--change <fact_id>]

Measured on two real units, the orchestrator was 88–92 % of the bill, and what
it did in FLOW-4 was deterministic: assemble a packet, dispatch the writer,
count words, dispatch the critics, take `min`, ask `decide`, build the sheet,
call `promote`. Every one of those rules was already a function in
`chapters.domain`. The model was being paid to read a procedure and call them.

So this calls them. **The agents still write and judge**: each is its own
`claude -p --agent <name>` process, the packet on stdin, exactly as
`publish/run_judge.py` calls `judge`. What moves to code is the order, the
counts, the thresholds and the bookkeeping — and with them four guarantees that
were a model's obedience before:

- **The writer's isolation.** The packet is built here, from the Bible, this
  chapter's outline entry and the promoted summaries. No other chapter's prose is
  ever opened by this module, so it cannot be pasted (AC-3).
- **The 100,000-token ceiling becomes a reservation.** A packet is measured
  before dispatch and one over the ceiling is never sent (AC-4). The measure is
  SKILL.md §7's estimate, words × 1.35; there is no tokenizer in the project.
- **The budget is shared before launch.** Processes started together split what
  is left, so four critics cannot each spend the whole remainder (AC-5b).
- **No orphans.** Every sibling is stopped before this returns or raises
  (AC-5c; red-team case 9).

**What is not done here, and is a gap the spec names (§7):** arbitration. A
finding survives if its quote is in the draft, and a critic's replacement is
applied literally. The orchestrator used to overrule a false finding; nothing
here can.

Hooks: they fire on Claude Code's `Write`, and this writes with Python, so it
calls what they call — `score_length`, `names.check`, `forbidden.check`.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import re
import sqlite3
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from backend.chapters import check_summary, promote
from backend.chapters.domain import (
    CHARACTERISTICS,
    THRESHOLD_DEFAULT,
    aggregate,
    apply_patches,
    blocking,
    build_sheet,
    decide,
    mark_late,
    score_chatter,
    score_length,
    score_outline,
    score_prose,
    validate_sheet,
)
from backend.chapters.names import canonical_names
from backend.chapters.names import check as check_names
from backend.chapters.prose import find as mechanical_defects
from backend.commons.log.calls import CallRow, write_call
from backend.commons.runner.process import RunProcess
from backend.policy import forbidden

ROOT = Path(__file__).resolve().parents[2]
LOOP_DIR = ROOT / "specs" / "loops" / "LOOP-003"
BIBLE = ("world", "characters", "timeline", "mysteries")
STAGE = "FLOW-4"

#: SKILL.md §7's estimate. Named as an estimate wherever it is reported.
TOKENS_PER_WORD = 1.35

#: The four separate critics, and which characteristic each scores. SPEC-EXAM-006
#: §3 step 6. `bible-critic` replaces the first three where the config enables it.
SEPARATE = {"continuity": "continuity-critic", "science": "science-critic",
            "outline": "outline-critic", "prose": "prose-critic"}

_FINDING = {"type": "object", "properties": {
    "quote": {"type": "string"}, "claim": {"type": "string"},
    "fix": {"type": "string"}, "reference": {"type": "string"},
    "severity": {"type": "string"}, "kind": {"type": "string"},
    "replacement": {"type": "string"}}, "required": ["quote"]}
_SCORED = {"type": "object", "required": ["score", "findings"], "properties": {
    "score": {"type": ["integer", "null"]},
    "findings": {"type": "array", "items": _FINDING},
    "notes": {}}}
SCHEMAS = {
    "continuity-critic": _SCORED,
    "science-critic": _SCORED,
    "outline-critic": _SCORED,
    "prose-critic": {"type": "object", "required": ["major", "minor"], "properties": {
        "major": {"type": "array", "items": _FINDING},
        "minor": {"type": "array", "items": _FINDING},
        "notes": {}}},
    "bible-critic": {"type": "object", "required": ["continuity", "science", "outline"],
                     "properties": {k: _SCORED for k in ("continuity", "science",
                                                         "outline")}},
}

#: What "Against what" says when the critic gave nothing usable. Never a previous
#: chapter: sheet rule 3.
REFERENCE = {"continuity": "the Story Bible", "science": "bible/world.md § Rules",
             "outline": "outline.md, this chapter's own entry",
             "prose": "prose characteristic", "length": "config.snapshot.json, the word band",
             "chatter": "the chapter's first line", "forbidden_words": "the forbidden-words policy"}
PREVIOUS_CHAPTER = re.compile(r"\bch(apter)?\s*\d|ch\d{2}\.md", re.I)


# ------------------------------------------------------------------ the runner


@dataclass(frozen=True)
class Call:
    """One agent process: who, what it reads, what it may spend, what it returns."""

    agent: str
    packet: str
    budget_usd: float | None
    schema: dict | None = None
    attempt: int | None = None
    #: The packet's size, estimated (words × 1.35), for the `calls` row.
    tokens: int = 0


#: `Call` → a process with `start()`, `lines()` and `stop()` (`RunProcess`'s shape).
Runner = Callable[[Call], object]


def real_runner(cwd: Path, executable: str = "claude") -> Runner:
    """A real `claude -p --agent <name>` per call. Never used by a test."""

    def make(call: Call) -> RunProcess:
        command = [executable, "-p", "--agent", call.agent,
                   "--output-format", "stream-json", "--verbose",
                   "--permission-mode", "dontAsk"]
        if call.schema:
            command += ["--json-schema", json.dumps(call.schema)]
        if call.budget_usd is not None:
            command += ["--max-budget-usd", f"{call.budget_usd:.2f}"]
        return RunProcess(command=command, prompt=call.packet, cwd=cwd)

    return make


@dataclass
class Reply:
    call: Call
    text: str
    cost_usd: float | None
    usage: dict
    model: str
    duration_ms: int | None
    ts: str
    #: `budget` or `api` when the CLI stopped the process rather than it answering.
    cut: str | None = None
    #: The `result` event itself, for its change's row (SPEC-EXAM-008).
    result: dict | None = None


class Halt(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reply(call: Call, process) -> Reply:
    """Read one process to its `result` event: the answer and its measured bill."""
    process.start()
    result: dict | None = None
    for _, event in process.lines():
        if isinstance(event, dict) and event.get("type") == "result":
            result = event
    if result is None:
        raise Halt("process", f"{call.agent} ended without a result event")
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    by_model = result.get("modelUsage") if isinstance(result.get("modelUsage"), dict) else {}
    model = (max(by_model, key=lambda k: float((by_model[k] or {}).get("costUSD") or 0))
             if by_model else "unknown")
    structured = result.get("structured_output")
    text = json.dumps(structured) if structured is not None else str(result.get("result") or "")
    cost = result.get("total_cost_usd")
    cut = None
    lowered = text.lower()
    if result.get("subtype") == "error_max_budget_usd" or "spend limit" in lowered \
            or "usage limit" in lowered:
        cut = "budget"
    elif result.get("is_error"):
        cut = "api"
    return Reply(call=call, text=text,
                 cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
                 usage=usage, model=model, duration_ms=result.get("duration_ms"),
                 ts=_now(), cut=cut, result=result)


# ------------------------------------------------------------------ the outcome


@dataclass
class Outcome:
    chapter: int
    #: accept | halt
    action: str
    #: accept | patched | halt — the words the `attempts` table admits
    verdict: str
    attempts: list[dict] = field(default_factory=list)
    halted: tuple[str, str] | None = None
    cost_usd: float = 0.0
    notes: list[str] = field(default_factory=list)


def mode(cfg: dict) -> str:
    """`orchestration.chapter_loop`; absent is `"claude"`, the path that ran before."""
    return str(((cfg or {}).get("orchestration") or {}).get("chapter_loop") or "claude")


# ------------------------------------------------------------------ the packets


def outline_entry(outline: str, n: int) -> tuple[str, str] | None:
    """This chapter's entry, heading to the next heading, and its title."""
    m = re.search(rf"^(#{{2,4}})\s*Chapter\s+{n}\b\s*[—–:-]?\s*(.*)$", outline, re.M)
    if not m:
        return None
    rest = outline[m.end():]
    stop = re.search(r"^#{1,%d}\s" % len(m.group(1)), rest, re.M)
    body = rest[:stop.start()] if stop else rest
    return (m.group(0) + body).strip(), m.group(2).strip()


def rolling_summary(run_dir: Path, n: int, cap: int) -> str:
    """The promoted summaries before `n`, newest first, whole files while they fit.

    Never a chapter's prose, and never a summary cut in half: the latest one is
    always carried, and older ones only while the total stays inside the cap.
    """
    kept: list[str] = []
    words = 0
    for k in range(n - 1, 0, -1):
        path = run_dir / "chapters" / f"ch{k:02d}.summary.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        size = len(text.split())
        if kept and words + size > cap:
            break
        kept.append(text)
        words += size
    return "\n\n".join(reversed(kept))


def measure(packet: str) -> int:
    return math.ceil(len(packet.split()) * TOKENS_PER_WORD)


def _json_in(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


@dataclass
class _Ctx:
    run_dir: Path
    n: int
    cfg: dict
    title: str
    entry: str
    bible: dict[str, str]
    summary: str
    names: list[str]
    genre: str
    change_note: str | None

    @property
    def band(self) -> tuple[int, int]:
        w = self.cfg["novel"]["words_per_chapter"]
        return int(w["min"]), int(w["max"])

    @property
    def target(self) -> int:
        return int(self.cfg["novel"]["words_per_chapter"]["target"])

    def bible_block(self) -> str:
        return "\n\n".join(f"### bible/{k}.md\n\n{v.strip()}" for k, v in self.bible.items())


def _writer_packet(ctx: _Ctx, *, attempt: int, max_attempts: int,
                   previous: str | None = None, sheet: str | None = None,
                   patches: bool = True) -> str:
    low, high = ctx.band
    parts = [
        f"genre and tone: {ctx.genre}",
        f"Write chapter {ctx.n}, titled \"{ctx.title}\". Open with the heading "
        f"`# Chapter {ctx.n} — {ctx.title}`.",
        f"Target: {ctx.target} words (the band is {low}–{high}; it is counted).",
        "Canonical names, spelled exactly: " + ", ".join(ctx.names),
        "",
        "--- THE STORY BIBLE ---", "", ctx.bible_block(), "",
        "--- THIS CHAPTER'S OUTLINE ENTRY ---", "", ctx.entry, "",
        "--- THE STORY SO FAR (the rolling summary) ---", "",
        ctx.summary or "(this is the first chapter)",
    ]
    if ctx.change_note:
        parts += ["", ctx.change_note]
    if previous is not None and sheet is not None:
        parts += ["", "--- YOUR OWN REJECTED DRAFT OF THIS CHAPTER ---", "", previous.strip(),
                  "", "--- THE SHEET ---", "", sheet, ""]
        if patches:
            parts += ["Return ONLY a JSON object of substitutions, nothing else:",
                      '{"patches": [{"find": "<text copied EXACTLY from your draft>", '
                      '"replace": "<the corrected text>", "why": "<which finding>"}]}']
        else:
            parts += ["Your substitutions matched nothing in the draft. Return the whole "
                      "chapter, corrected, and nothing else."]
    else:
        parts += ["", "Return the chapter and nothing else."]
    if attempt >= max_attempts:
        parts += ["", f"This is attempt {attempt} of {max_attempts}: your last."]
    return "\n".join(parts) + "\n"


def _critic_packet(ctx: _Ctx, agent: str, draft: str, *, replacements: bool) -> str:
    parts = [f"genre and tone: {ctx.genre}", f"chapter: {ctx.n} — {ctx.title}", ""]
    if agent in ("continuity-critic", "science-critic", "bible-critic"):
        parts += ["--- THE STORY BIBLE ---", "", ctx.bible_block(), ""]
    if agent in ("outline-critic", "bible-critic"):
        parts += ["--- THIS CHAPTER'S OUTLINE ENTRY (beats numbered) ---", "", ctx.entry, ""]
    parts += ["--- THE DRAFT ---", "", draft.strip(), ""]
    if replacements:
        parts += ["For every finding also give `replacement`: the literal text that "
                  "should stand in place of `quote`, in the book's voice, ready to be "
                  "substituted as given."]
    parts += ["Judge it as your instructions say. Return only the JSON."]
    return "\n".join(parts) + "\n"


def _summary_packet(ctx: _Ctx, chapter: str, cap: int, over: int | None = None) -> str:
    parts = [f"genre and tone: {ctx.genre}",
             f"This is your own accepted chapter {ctx.n}. Write its summary for the "
             f"writer of the next chapter, in at most {cap} words: what changed, who now "
             f"knows what, and what is still open. Return the summary and nothing else.",
             "", "--- THE STORY SO FAR ---", "", ctx.summary or "(this was the first chapter)",
             "", "--- YOUR CHAPTER ---", "", chapter.strip()]
    if over is not None:
        parts += ["", f"Your summary was {over} words against a cap of {cap}. "
                      f"Write it again, shorter. It will not be truncated."]
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------------ the loop


class ChapterLoop:
    def __init__(self, run_dir: Path, n: int, *, runner: Runner,
                 conn: sqlite3.Connection | None, run_id: str | None,
                 ceiling_usd: float | None, spent_usd: float,
                 change_note: str | None, slug: str | None, loop_dir: Path | None,
                 stop: threading.Event | None = None, change: int | None = None):
        self.run_dir, self.n, self.runner = run_dir, n, runner
        #: The `changes` row (its `n`) each process's `result` adds to.
        self.change = change
        self.stop = stop or threading.Event()
        self.conn, self.run_id = conn, run_id
        self.ceiling, self.spent = ceiling_usd, float(spent_usd or 0.0)
        self.cost = 0.0
        self.slug = slug or run_dir.name
        self.loop_dir = loop_dir or LOOP_DIR
        self.cfg = json.loads((run_dir / "config.snapshot.json").read_text(encoding="utf-8"))
        gate = self.cfg.get("quality_gate") or {}
        self.threshold = int(gate.get("threshold", THRESHOLD_DEFAULT))
        self.max_attempts = int(gate.get("max_revisions", 2)) + 1
        self.token_ceiling = int((self.cfg.get("context") or {}).get(
            "max_concurrent_tokens", 100_000))
        self.bible_critic = bool((self.cfg.get("orchestration") or {}).get("bible_critic"))
        self.envelopes: dict[str, dict] = {}
        self.pending_rows: list[Reply] = []
        self.outcome = Outcome(chapter=n, action="halt", verdict="halt")
        self.change_note = change_note

    # ---------------------------------------------------------- dispatch

    def _dispatch(self, calls: list[Call]) -> list[Reply]:
        """Launch `calls` together, each on its share of what is left.

        Every process is stopped in `finally`, whatever happened: a finished one
        ignores it, a live sibling of a failure is the orphan this prevents.
        """
        for call in calls:
            if call.tokens > self.token_ceiling:
                raise Halt("context", f"{call.agent} packet for chapter {self.n} is "
                                      f"{call.tokens} tokens (estimated, words × "
                                      f"{TOKENS_PER_WORD}) against the ceiling of "
                                      f"{self.token_ceiling}; not dispatched, not truncated")
        rounds = ([calls] if sum(c.tokens for c in calls) <= self.token_ceiling
                  else [[c] for c in calls])
        replies: list[Reply] = []
        for group in rounds:
            replies += self._launch(group)
        return replies

    def _launch(self, calls: list[Call]) -> list[Reply]:
        share: float | None = None
        if self.ceiling is not None:
            left = self.ceiling - self.spent
            share = math.floor(left / len(calls) * 100) / 100 if left > 0 else 0.0
            if share <= 0:
                raise Halt("budget", f"the ceiling of ${self.ceiling:.2f} leaves "
                                     f"${max(left, 0):.2f}, not enough to launch "
                                     f"{len(calls)} process(es)")
        calls = [Call(c.agent, c.packet, share, c.schema, c.attempt, c.tokens) for c in calls]
        processes = [self.runner(c) for c in calls]
        results: list[Reply | None] = [None] * len(calls)
        errors: list[BaseException] = []
        failed = threading.Event()

        def work(i: int) -> None:
            try:
                results[i] = _reply(calls[i], processes[i])
                if results[i].cut:
                    raise Halt(results[i].cut, f"{calls[i].agent} was stopped by the CLI "
                                               f"({results[i].cut}) on chapter {self.n}")
            except BaseException as exc:  # noqa: BLE001 - carried to the caller
                errors.append(exc)
                failed.set()

        threads = [threading.Thread(target=work, args=(i,), daemon=True)
                   for i in range(len(calls))]
        try:
            for t in threads:
                t.start()
            while any(t.is_alive() for t in threads):
                if failed.wait(0.02):
                    break
                if self.stop.is_set():
                    errors.append(Halt("interrupted", f"stopped from outside during "
                                                      f"chapter {self.n}"))
                    break
        finally:
            for p in processes:
                p.stop()
            for t in threads:
                t.join(timeout=15)
            for r in results:
                if r is not None:
                    self._account(r)
            self._missing(sum(1 for r in results if r is None))
        if errors:
            raise errors[0]
        return [r for r in results if r is not None]

    def _missing(self, count: int) -> None:
        """SPEC-EXAM-008 §2: processes that ended without a `result`."""
        if count and self.conn is not None and self.run_id and self.change is not None:
            from backend.costs import repository as costs
            costs.add_missing(self.conn, self.run_id, self.change, count)

    def _account(self, reply: Reply) -> None:
        if reply.cost_usd is not None:
            self.spent += reply.cost_usd
            self.cost += reply.cost_usd
        self.pending_rows.append(reply)
        if self.conn is None or self.run_id is None:
            return
        if self.change is not None and reply.result is not None:
            # Each agent is its own process with no orchestrator above it: every
            # model in its `modelUsage` is an agent (§8.3).
            from backend.costs import measure, repository as costs
            costs.add_result(self.conn, self.run_id, self.change,
                             measure.split(reply.result, None),
                             note=costs.NO_ORCHESTRATOR)
        u = reply.usage
        write_call(self.conn, CallRow(
            run_id=self.run_id, stage=STAGE, agent=reply.call.agent, model=reply.model,
            ts=reply.ts, chapter=self.n, attempt=reply.call.attempt,
            input_tokens=u.get("input_tokens"), output_tokens=u.get("output_tokens"),
            cache_creation_input_tokens=u.get("cache_creation_input_tokens"),
            cache_read_input_tokens=u.get("cache_read_input_tokens"),
            cost_usd=reply.cost_usd, provenance="measured",
            cost_provenance="measured" if reply.cost_usd is not None else "absent",
            tokens_reserved=reply.call.tokens, duration_ms=reply.duration_ms,
            note="chapter loop (SPEC-EXAM-006): one process, its own result event"))
        self.conn.commit()

    def _one(self, agent: str, packet: str, attempt: int, schema: dict | None = None) -> Reply:
        return self._dispatch([Call(agent, packet, None, schema, attempt, measure(packet))])[0]

    # ---------------------------------------------------------- files

    def _path(self, name: str) -> Path:
        return self.run_dir / "chapters" / name

    def _write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")

    def _log(self, row: dict) -> None:
        path = self.run_dir / "logs" / "agents.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")

    def _flush_agent_rows(self, attempt: int, verdict: str) -> None:
        for r in self.pending_rows:
            u = r.usage
            self._log({"stage": STAGE, "agent": r.call.agent, "chapter": self.n,
                       "iteration": attempt, "verdict": verdict,
                       "tokens": sum(int(u.get(k) or 0) for k in (
                           "input_tokens", "cache_creation_input_tokens",
                           "cache_read_input_tokens", "output_tokens")),
                       "model": r.model, "duration_ms": r.duration_ms,
                       "cost_usd": r.cost_usd, "note": "chapter loop"})
        self.pending_rows = []

    def _record(self, characteristic: str, agent: str, iteration: dict) -> None:
        env = self.envelopes.setdefault(characteristic, {
            "critic": characteristic, "chapter": self.n,
            "kind": "arithmetic" if characteristic in ("length", "chatter") else "model",
            "agent": agent, "drafts": 0, "iterations": []})
        env["iterations"].append(iteration)
        env["drafts"] = max(env["drafts"], int(iteration["iteration"]))
        (self.run_dir / "critiques").mkdir(exist_ok=True)
        (self.run_dir / "critiques" / f"ch{self.n:02d}.{characteristic}.json").write_text(
            json.dumps(env, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
            newline="\n")

    # ---------------------------------------------------------- scoring

    def _score(self, ctx: _Ctx, draft: str, attempt: int, *, first: str,
               seen: set[str], patched: bool) -> tuple[dict, list[dict], list[str]]:
        """Six scores, the blocking findings, and notes. Writes the critiques."""
        notes: list[str] = []
        findings: list[dict] = []
        words = len(draft.split())
        low, high = ctx.band
        tol = int(ctx.cfg["novel"]["tolerance_pct"])
        scores: dict[str, int | None] = {c: None for c in CHARACTERISTICS}
        scores["length"] = score_length(words, (low, high), tol)
        scores["chatter"] = score_chatter(draft)
        tag = {"patched": True} if patched else {}
        first_line = draft.strip().split("\n", 1)[0].strip() if draft.strip() else ""
        opening = _first_sentence(draft)

        length_findings = [] if scores["length"] else [{
            "characteristic": "length", "severity": "high", "quote": opening,
            "claim": f"{words} words against {low}–{high} widened by {tol}%",
            "reference": REFERENCE["length"],
            "fix": f"bring the chapter to about {ctx.target} words",
            "replacement": f"(no single sentence: the whole chapter at about {ctx.target} words)",
            "literal": False}]
        chatter_findings = [] if scores["chatter"] else [{
            "characteristic": "chatter", "severity": "high", "quote": first_line,
            "claim": "the draft does not open with its chapter heading",
            "reference": REFERENCE["chatter"],
            "fix": f"open with `# Chapter {ctx.n} — {ctx.title}`",
            "replacement": f"# Chapter {ctx.n} — {ctx.title}\n\n{first_line}"}]
        self._record("length", "loop (arithmetic)", {
            "iteration": attempt, "score": scores["length"], "words": words,
            "findings": length_findings, **tag})
        self._record("chatter", "loop (arithmetic)", {
            "iteration": attempt, "score": scores["chatter"], "findings": chatter_findings,
            **tag})
        findings += length_findings + chatter_findings

        hits = self._forbidden(draft, notes)
        for hit in hits:
            findings.append({"characteristic": "forbidden_words", "severity": "high",
                             "quote": _sentence_with(draft, hit.quote), "claim": str(hit),
                             "reference": REFERENCE["forbidden_words"],
                             "fix": f"the same sentence without {hit.quote!r}",
                             "replacement": f"(the same sentence without {hit.quote!r})",
                             "literal": False})

        if scores["chatter"] == 0:
            notes.append("chatter 0: not a chapter yet, so no critic was dispatched")
            return scores, findings, notes + ([f"forbidden:{len(hits)}"] if hits else [])

        replacements = attempt >= self.max_attempts - 1
        agents = (["bible-critic", "prose-critic"] if self.bible_critic
                  else list(SEPARATE.values()))
        calls = []
        for agent in agents:
            packet = _critic_packet(ctx, agent, draft, replacements=replacements)
            calls.append(Call(agent, packet, None, SCHEMAS[agent], attempt, measure(packet)))
        replies = {r.call.agent: _json_in(r.text) for r in self._dispatch(calls)}

        def quoted(items) -> list[dict]:
            kept = [f for f in (items or []) if isinstance(f, dict)
                    and isinstance(f.get("quote"), str) and f["quote"].strip()
                    and f["quote"] in draft]
            dropped = len([f for f in (items or []) if isinstance(f, dict)]) - len(kept)
            if dropped:
                notes.append(f"{dropped} finding(s) dropped: their quote is not in the draft")
            return mark_late(kept, first, seen) if attempt > 1 else [
                {**f, "late": False} for f in kept]

        parts: dict[str, dict | None] = {}
        if self.bible_critic:
            whole = replies.get("bible-critic") or {}
            for c in ("continuity", "science", "outline"):
                part = whole.get(c)
                parts[c] = part if isinstance(part, dict) else None
        else:
            for c in ("continuity", "science", "outline"):
                parts[c] = replies.get(SEPARATE[c])
        agent_of = {c: ("bible-critic" if self.bible_critic else SEPARATE[c])
                    for c in ("continuity", "science", "outline")}

        for c in ("continuity", "science"):
            reply = parts[c]
            value = reply.get("score") if isinstance(reply, dict) else None
            kept = quoted(reply.get("findings")) if isinstance(reply, dict) else []
            scores[c] = int(value) if isinstance(value, (int, float)) else None
            self._record(c, agent_of[c], {"iteration": attempt, "score": scores[c],
                                          "findings": kept,
                                          "notes": (reply or {}).get("notes"), **tag})
            findings += [{"characteristic": c, **f} for f in blocking(kept)]

        reply = parts["outline"]
        if isinstance(reply, dict) and isinstance(reply.get("findings"), list):
            kept = quoted(reply["findings"])
            live = blocking(kept)
            missing = sum(1 for f in live if f.get("kind") == "beat-missing")
            order = sum(1 for f in live if f.get("kind") == "beat-out-of-order")
            scores["outline"] = score_outline(missing, order)
            why = f"10 - 3x{missing} - 1x{order} = {scores['outline']}"
            findings += [{"characteristic": "outline", **f} for f in live
                         if f.get("kind") in ("beat-missing", "beat-out-of-order")]
        else:
            kept, why = [], "no usable verdict"
        self._record("outline", agent_of["outline"], {
            "iteration": attempt, "score": scores["outline"], "findings": kept,
            "notes": (reply or {}).get("notes") if isinstance(reply, dict) else None,
            "why": why, **tag})

        reply = replies.get("prose-critic")
        mech = [{"kind": d.kind, "quote": d.quote, "claim": d.claim}
                for d in mechanical_defects(draft)]
        mech += [{"kind": "name-one-letter-out", "quote": s.written, "claim": str(s)}
                 for s in check_names(draft, ctx.bible.get("characters", ""))]
        if isinstance(reply, dict) and isinstance(reply.get("major"), list) \
                and isinstance(reply.get("minor"), list):
            major = [{**f, "severity": "high"} for f in quoted(reply["major"])]
            minor = [{**f, "severity": "low"} for f in quoted(reply["minor"])]
            n_major, n_minor = len(blocking(major)), len(blocking(minor))
            scores["prose"] = score_prose(mechanical=len(mech), major=n_major, minor=n_minor)
            why = (f"10 - 3x{len(mech)} - 2x{n_major} - 1x{n_minor} = {scores['prose']}")
            findings += [{"characteristic": "prose", **f} for f in blocking(major + minor)]
            findings += [{"characteristic": "prose", "severity": "high", **m,
                          "fix": "remove the defect the mechanical check quoted",
                          "reference": "the mechanical prose check",
                          "replacement": "(remove the repetition the check quoted)",
                          "literal": False}
                         for m in mech if len(m["quote"]) >= 8]
            self._record("prose", "prose-critic", {
                "iteration": attempt, "score": scores["prose"],
                "findings": major + minor, "notes": reply.get("notes"), "why": why,
                "major": n_major, "minor": n_minor,
                "mechanical_check": {"script": "backend.chapters.prose", "defects": mech},
                **tag})
        else:
            self._record("prose", "prose-critic", {
                "iteration": attempt, "score": None, "findings": [],
                "notes": "no usable verdict", **tag})
        if hits:
            notes.append(f"forbidden:{len(hits)}")
        return scores, findings, notes

    def _forbidden(self, draft: str, notes: list[str]) -> list:
        if self.conn is None:
            notes.append("forbidden words not checked: no database")
            return []
        return forbidden.check(draft, forbidden.terms(self.conn))

    # ---------------------------------------------------------- the decision

    def _decide(self, scores: dict, attempt: int, patched: bool):
        verdict = aggregate(scores, self.threshold)
        # `promote`'s rule, asked of the same numbers: a gate short a critic has
        # no aggregate to accept on.
        agg = verdict.aggregate if not verdict.unscored else None
        return verdict, agg, decide(aggregate=agg, attempt=attempt,
                                    max_attempts=self.max_attempts, patched=patched,
                                    threshold=self.threshold)

    def _gate_row(self, attempt: int, scores: dict, agg, verdict: str, note: str) -> None:
        self._log({"event": "gate_decision", "stage": STAGE, "chapter": self.n,
                   "iteration": attempt, "scores": scores, "aggregate": agg,
                   "threshold": self.threshold, "verdict": verdict, "note": note})

    def _sheet(self, attempt: int, scores: dict, findings: list[dict],
               resolved: list[str]) -> str:
        level = 2 if attempt + 1 >= self.max_attempts else 1
        clean = []
        for f in findings:
            f = dict(f)
            f.setdefault("claim", f.get("kind") or f.get("characteristic"))
            ref = f.get("reference")
            if not ref or PREVIOUS_CHAPTER.search(str(ref)):
                f["reference"] = REFERENCE.get(f.get("characteristic"), "the Story Bible")
            if level == 1:
                f.pop("replacement", None)
            clean.append(f)
        sheet = build_sheet(chapter=self.n, attempt=attempt + 1, level=level, scores=scores,
                            findings=clean, resolved=resolved, threshold=self.threshold)
        target = self.loop_dir / "sheets" / self.slug / f"ch{self.n:02d}.attempt{attempt + 1}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(sheet + "\n", encoding="utf-8", newline="\n")
        report = validate_sheet(sheet, level)
        if not report.ok:
            raise Halt("sheet", f"the level-{level} sheet for attempt {attempt + 1} failed "
                                f"validation and is not sent: " + "; ".join(report.problems))
        return sheet

    def _late(self, findings: list[dict], attempt: int) -> None:
        late = [f for f in findings if f.get("late")]
        if not late:
            return
        path = self.loop_dir / "late_findings.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            for f in late:
                fh.write(json.dumps({"ts": _now(), "slug": self.slug, "chapter": self.n,
                                     "attempt": attempt, **f}, ensure_ascii=False) + "\n")

    # ---------------------------------------------------------- run

    def run(self) -> Outcome:
        try:
            self._run()
        except Halt as halt:
            self._stop(halt.kind, halt.detail)
        finally:
            self.outcome.cost_usd = self.cost
        return self.outcome

    def _stop(self, kind: str, detail: str) -> None:
        self.outcome.action, self.outcome.verdict = "halt", "halt"
        self.outcome.halted = (kind, detail)
        self._flush_agent_rows(len(self.outcome.attempts) or 0, "halt")
        self._write(self.run_dir / "logs" / f"ch{self.n:02d}.halt.md",
                    f"# Chapter {self.n} halted\n\n{kind}: {detail}\n")

    def _context(self) -> _Ctx:
        outline_path = self.run_dir / "outline.md"
        found = outline_entry(outline_path.read_text(encoding="utf-8"), self.n) \
            if outline_path.is_file() else None
        if found is None:
            raise Halt("input", f"outline.md has no entry for chapter {self.n}")
        entry, title = found
        bible = {}
        for name in BIBLE:
            path = self.run_dir / "bible" / f"{name}.md"
            if not path.is_file():
                raise Halt("input", f"bible/{name}.md is missing")
            bible[name] = path.read_text(encoding="utf-8")
        cap = int((self.cfg.get("context") or {}).get("max_summary_words", 200))
        state = self.run_dir / "state.json"
        tone = (self.cfg.get("novel") or {}).get("tone")
        if not tone and state.is_file():
            tone = json.loads(state.read_text(encoding="utf-8")).get("tone")
        return _Ctx(self.run_dir, self.n, self.cfg, title, entry, bible,
                    rolling_summary(self.run_dir, self.n, cap),
                    sorted(canonical_names(bible["characters"])),
                    tone or "as the premise reads", self.change_note)

    def _run(self) -> None:
        ctx = self._context()
        first = ""
        seen: set[str] = set()
        previous: str | None = None
        sheet: str | None = None
        last_findings: list[dict] = []

        for attempt in range(1, self.max_attempts + 1):
            note = ""
            if previous is None:
                draft = self._one("chapter-writer", _writer_packet(
                    ctx, attempt=attempt, max_attempts=self.max_attempts), attempt).text
            else:
                draft, note = self._redraft(ctx, attempt, previous, sheet)
            draft = draft.strip() + "\n"
            self._write(self._path(f"ch{self.n:02d}.attempt{attempt}.md"), draft)
            if attempt == 1:
                first = draft

            scores, findings, notes = self._score(ctx, draft, attempt, first=first,
                                                  seen=seen, patched=False)
            self._late(findings, attempt)
            findings = blocking(findings)
            verdict, agg, decision = self._decide(scores, attempt, False)
            policy = any(n.startswith("forbidden:") for n in notes)
            record = {"attempt": attempt, "scores": scores, "aggregate": verdict.aggregate,
                      "aggregate_for_decide": agg, "patched": False,
                      "action": decision.action, "why": decision.why,
                      "note": "; ".join([note, *notes]).strip("; ")}
            self.outcome.attempts.append(record)

            if decision.action == "accept" and policy:
                # A forbidden term is the policy's finding, not a seventh score:
                # it goes back through the sheet and gets the same attempts.
                if attempt >= self.max_attempts:
                    self._gate_row(attempt, scores, verdict.aggregate, "halt",
                                   "a forbidden term survived the last attempt")
                    raise Halt("policy", f"chapter {self.n}: a forbidden term survived "
                                         f"attempt {attempt}")
                decision = type(decision)("retry", "retry", "a forbidden term is present")
                record["action"], record["why"] = "retry", decision.why
                record["policy_retry"] = True

            self._gate_row(attempt, scores, verdict.aggregate, decision.verdict,
                           record["note"] or decision.why)
            self._flush_agent_rows(attempt, decision.verdict)

            if decision.action == "accept":
                return self._accept(ctx, attempt, patched=False)
            if decision.action == "patch":
                return self._patch(ctx, attempt, draft, findings, first, seen)

            if not findings and verdict.unscored:
                # Nothing for the writer to correct: a critic did not answer. A
                # redraft cannot fix a critic, and a sheet with no findings is not sent.
                raise Halt("critic", f"chapter {self.n} attempt {attempt}: "
                                     f"{', '.join(verdict.unscored)} returned no usable "
                                     f"verdict and nothing else failed")
            resolved = [f["quote"] for f in last_findings
                        if f.get("quote") and f["quote"] not in draft]
            seen |= {f.get("quote", "") for f in findings}
            sheet = self._sheet(attempt, scores, findings, resolved)
            previous, last_findings = draft, findings

        raise Halt("gate", f"chapter {self.n}: no decision after {self.max_attempts} attempts")

    def _redraft(self, ctx: _Ctx, attempt: int, previous: str, sheet: str) -> tuple[str, str]:
        """Redraft rule 2: substitutions first; a full rewrite only if none applied."""
        reply = self._one("chapter-writer", _writer_packet(
            ctx, attempt=attempt, max_attempts=self.max_attempts,
            previous=previous, sheet=sheet), attempt).text
        payload = _json_in(reply)
        if payload is None or not isinstance(payload.get("patches"), list):
            if reply.lstrip().startswith("#"):
                return reply, "the writer returned a full chapter instead of substitutions"
            payload = {"patches": []}
        result = apply_patches(previous, payload["patches"])
        if not result.nothing_applied:
            return result.text, (f"{result.applied} substitution(s) applied, "
                                 f"{len(result.skipped)} skipped")
        rewrite = self._one("chapter-writer", _writer_packet(
            ctx, attempt=attempt, max_attempts=self.max_attempts, previous=previous,
            sheet=sheet, patches=False), attempt).text
        return rewrite, "no substitution matched; fell back to a full rewrite"

    def _patch(self, ctx: _Ctx, attempt: int, draft: str, findings: list[dict],
               first: str, seen: set[str]) -> None:
        """Patch-then-halt: the critics' replacements, literally, then a rescore."""
        # Only a critic's literal sentence, or the heading. An instruction such as
        # "the whole chapter at about 420 words" is for the writer, never pasted.
        patches = [{"find": f["quote"], "replace": f["replacement"]}
                   for f in findings
                   if f.get("replacement") and f.get("quote") and f.get("literal", True)]
        result = apply_patches(draft, patches)
        self._write(self._path(f"ch{self.n:02d}.unpatched.attempt{attempt}.md"), draft)
        self._write(self._path(f"ch{self.n:02d}.attempt{attempt}.md"), result.text)
        scores, _, notes = self._score(ctx, result.text.strip() + "\n", attempt, first=first,
                                       seen=seen, patched=True)
        verdict, agg, decision = self._decide(scores, attempt, True)
        if decision.action == "accept" and any(n.startswith("forbidden:") for n in notes):
            decision = type(decision)("halt", "halt", "a forbidden term survived the patch")
        note = (f"{result.applied} replacement(s) applied literally, "
                f"{len(result.skipped)} skipped; not arbitrated (SPEC-EXAM-006 §7)")
        self.outcome.attempts.append({
            "attempt": attempt, "scores": scores, "aggregate": verdict.aggregate,
            "aggregate_for_decide": agg, "patched": True, "action": decision.action,
            "why": decision.why, "note": "; ".join([note, *notes])})
        self._gate_row(attempt, scores, verdict.aggregate, decision.verdict, note)
        self._flush_agent_rows(attempt, decision.verdict)
        if decision.action == "accept":
            return self._accept(ctx, attempt, patched=True)
        raise Halt("gate" if decision.action == "halt" else decision.action,
                   f"chapter {self.n}: {decision.why}")

    def _accept(self, ctx: _Ctx, attempt: int, *, patched: bool) -> None:
        code, out = _quiet(promote.main, ["promote", str(self.run_dir), str(self.n),
                                          str(attempt)])
        if code != 0:
            raise Halt("promote", f"promote refused chapter {self.n} attempt {attempt}: "
                                  f"{out.strip()[-300:]}")
        chapter = self._path(f"ch{self.n:02d}.md").read_text(encoding="utf-8")
        cap = int((self.cfg.get("context") or {}).get("max_summary_words", 200))
        summary_path = self._path(f"ch{self.n:02d}.summary.md")
        over: int | None = None
        for _ in range(2):
            text = self._one("chapter-writer", _summary_packet(ctx, chapter, cap, over),
                             attempt).text
            self._write(summary_path, text)
            code, _ = _quiet(check_summary.main, ["check_summary", str(self.run_dir),
                                                  str(self.n)])
            if code != 1:
                break
            over = len(text.split())
        if code == 1:
            self.outcome.notes.append(f"summary is {over} words, over the {cap}-word cap "
                                      f"after asking twice; kept whole, never truncated")
        elif code == 2:
            self.outcome.notes.append("summary cap not checked: the snapshot states none")
        self._flush_agent_rows(attempt, "patched" if patched else "accept")
        self.outcome.action = "accept"
        self.outcome.verdict = "patched" if patched else "accept"


def _quiet(main: Callable[[list[str]], int], argv: list[str]) -> tuple[int, str]:
    """Call a CLI's `main(argv)` and keep what it printed."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue() + err.getvalue()


def _first_sentence(draft: str) -> str:
    """The first line of prose after the heading, as a literal quote."""
    for line in draft.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:160]
    return draft.strip()[:160]


def _sentence_with(draft: str, quote: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", draft):
        if quote in sentence:
            return sentence.strip()
    return quote


def run_chapter(run_dir: Path, n: int, *, runner: Runner,
                conn: sqlite3.Connection | None = None, run_id: str | None = None,
                ceiling_usd: float | None = None, spent_usd: float = 0.0,
                change_note: str | None = None, slug: str | None = None,
                loop_dir: Path | None = None,
                stop: threading.Event | None = None,
                change: int | None = None) -> Outcome:
    """Run chapter `n` of `run_dir` to accept or halt. Raises only on a defect.

    `ceiling_usd` is what may be spent in all, `spent_usd` what already was: the
    loop hands each process a share of the difference, never the whole of it.
    Setting `stop` halts it and stops every live process it started.
    """
    return ChapterLoop(run_dir, n, runner=runner, conn=conn, run_id=run_id,
                       ceiling_usd=ceiling_usd, spent_usd=spent_usd,
                       change_note=change_note, slug=slug, loop_dir=loop_dir,
                       stop=stop, change=change).run()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="backend.chapters.loop")
    parser.add_argument("run_dir")
    parser.add_argument("n", type=int)
    parser.add_argument("--change", metavar="fact_id")
    args = parser.parse_args(argv)

    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate

    settings = load_settings()
    run_dir = Path(args.run_dir)
    conn = connect(settings.db_path)
    migrate(conn)
    slug = run_dir.name if run_dir.parent.name != "dist" else run_dir.parent.parent.name
    row = conn.execute("SELECT id FROM runs WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        print(f"loop: no run with slug {slug!r} in the database; calls rows are not "
              f"written", file=sys.stderr)
    cfg = json.loads((run_dir / "config.snapshot.json").read_text(encoding="utf-8"))
    ceiling = (cfg.get("budget") or {}).get("max_cost_usd")
    if settings.budget_ceiling_usd is not None:
        # NOVAFORGE_BUDGET only ever lowers the profile's figure.
        ceiling = min(float(ceiling), settings.budget_ceiling_usd) if ceiling is not None \
            else settings.budget_ceiling_usd
    note = None
    if args.change:
        note = (f"Reader change: fact {args.change} has changed, and the Bible and the "
                f"outline above already carry its new text. Write the chapter so it holds.")
    sheets_slug = slug if run_dir.parent.name != "dist" else f"{slug}/{run_dir.name}"
    outcome = run_chapter(run_dir, args.n, runner=real_runner(settings.repo_root),
                          conn=conn, run_id=row[0] if row else None,
                          ceiling_usd=float(ceiling) if ceiling is not None else None,
                          change_note=note, slug=sheets_slug)
    print(json.dumps({"chapter": outcome.chapter, "action": outcome.action,
                      "verdict": outcome.verdict, "halted": outcome.halted,
                      "cost_usd": round(outcome.cost_usd, 4), "attempts": outcome.attempts,
                      "notes": outcome.notes}, indent=2, ensure_ascii=False))
    return 0 if outcome.action == "accept" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
