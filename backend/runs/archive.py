"""SPEC-003 — reading a finished run's own record back into the database.

The orchestrator writes the gate's record to disk, because that is what
`SKILL.md` §"Record it" tells it to do and because files survive a crashed
process. Nothing read them back, so v2's first real run — three chapters, eight
drafts, four sheets, $18.82 measured — finished with `attempts`, `scores`,
`findings`, `gate_decisions` and `sheets` all empty.

**This module is a reader, not a judge.** It records what the run decided. It
does not recompute a score, correct an aggregate or infer a fact from prose: a
figure invented here would be indistinguishable on screen from one the run
produced, which is the failure the provenance grades exist to prevent.

What it cannot do is in SPEC-003 A10: it sees what was written. A chapter whose
critique file was never written is indistinguishable from a chapter that was
never attempted, and that difference goes to `run_warnings` rather than being
smoothed away.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from backend.chapters.domain import CHARACTERISTICS, THRESHOLD_DEFAULT
from backend.chapters.domain import aggregate as aggregate_of
from backend.commons.db import repository

#: Imported, not written again. `commons/config/loader.py` opens by saying a
#: threshold written into Python is a second source of truth and the two
#: disagree within a month — and this file had one, four lines from the module
#: that owns it.
THRESHOLD = THRESHOLD_DEFAULT

#: `chNN.attemptK.md`
DRAFT = re.compile(r"^ch(\d+)\.attempt(\d+)$")


@dataclass
class ArchiveReport:
    attempts: int = 0
    scores: int = 0
    findings: int = 0
    sheets: int = 0
    prose_defects: int = 0
    cost_usd: float | None = None
    notes: list[str] = field(default_factory=list)


def _words(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def _iterations(raw: dict) -> list[dict]:
    its = raw.get("iterations")
    return [it for it in its if isinstance(it, dict)] if isinstance(its, list) else []


def _read_critiques(run_dir: Path, report: ArchiveReport) -> dict[int, dict]:
    """`{chapter: {characteristic: {attempt: iteration}}}`, keyed by attempt.

    **Iteration index is not attempt index**, and assuming it is invents drafts
    that never existed. Chapter 1 of the first real run had `science` run three
    iterations over two drafts: the third was a rescore of the identical draft
    against an amended rule, with no prose changed between them. An iteration
    past the draft count belongs to the last draft, and the fact that it happened
    is worth a note rather than a silent merge.
    """
    out: dict[int, dict[str, dict[int, dict]]] = {}
    for path in sorted((run_dir / "critiques").glob("ch*.json")):
        if path.name.startswith("outline.audit"):
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        critic, chapter = raw.get("critic"), raw.get("chapter")
        if critic not in CHARACTERISTICS or not isinstance(chapter, int):
            report.notes.append(f"{path.name}: not a chapter critique, skipped")
            continue
        drafts = int(raw.get("drafts") or 0)
        by_attempt = out.setdefault(chapter, {}).setdefault(critic, {})
        for it in _iterations(raw):
            i = int(it.get("iteration") or 0)
            attempt = i
            if drafts and i > drafts:
                attempt = drafts
                report.notes.append(
                    f"ch{chapter:02d} {critic}: iteration {i} is a rescore of "
                    f"draft {drafts}; there is no draft {i}"
                )
            # A later iteration on the same draft is the standing verdict.
            by_attempt[attempt] = it
    return out


def _findings_of(iteration: dict, characteristic: str) -> list[dict]:
    out = []
    for f in iteration.get("findings") or []:
        if not isinstance(f, dict):
            continue
        ruling = f.get("orchestrator_arbitration")
        out.append({
            **f,
            "characteristic": characteristic,
            # Overruled only where the ruling says so in as many words. Reading
            # intent out of free text is how a critic that was right gets filed
            # as one that was wrong.
            "upheld": not (isinstance(ruling, str)
                           and ruling.strip().upper().startswith("OVERRULED")),
            "ruling": ruling,
        })
    return out


def _verdict(scores: dict[str, int | None], *, promoted: bool,
             halted: str | None, gate: tuple[str, ...]) -> str:
    """What the gate decided, asked of the gate **this run actually ran**.

    **This used to re-derive it: `aggregate >= THRESHOLD`.** That is the pass
    rule written a second time, and the second copy was wrong — it ignored
    completeness. A chapter whose critic returned nothing usable had an aggregate
    over the ones that answered, and this recorded `accept`. The gate had not
    passed it. **A gate short a critic is a weaker gate, not a passing one**, and
    that rule returned 10 once already and let a malformed reply ship a draft. So
    the verdict comes from `domain.aggregate`.

    `gate` is the second half, and it cost a wrong answer to learn. SPEC-006
    added a sixth characteristic **while an eight-chapter run was in flight**,
    and archiving that run against today's six marked every attempt of it
    unpassed — including chapters that scored 10 on all five the run had. A
    characteristic that did not exist when a run ran is not a critic that failed
    to answer; it is **a different gate**. That is the category error the
    `source` column exists to prevent between implementations, reappearing
    between two versions of v2.

    So completeness is judged against the characteristics **this run ever
    scored**. A critic that answered elsewhere in the run and not here is still
    an incomplete gate: that protection is untouched.
    """
    relevant = {k: v for k, v in scores.items() if k in gate}
    if aggregate_of(relevant, expected=gate).passed:
        return "accept"
    if promoted:
        # It shipped without passing, which under patch_then_halt can only mean
        # the patch carried it there.
        return "patched"
    return "halt" if halted else "retry"


def _sheet_level(body: str) -> int:
    """2 when the critic wrote the literal replacement, 1 when it described it."""
    return 2 if "Replacement:" in body else 1


def _lines_cited(body: str) -> int:
    return sum(1 for line in body.splitlines() if line.strip().startswith("Quote:"))


def archive_run(
    conn: sqlite3.Connection,
    run_id: str,
    run_dir: Path,
    *,
    sheets_dir: Path | None = None,
) -> ArchiveReport:
    """Read `run_dir` into the database. Idempotent: archiving twice is a no-op.

    Idempotence matters more than it sounds. The service archives on completion
    and on halt, a halted run can be archived again by hand, and a second pass
    that doubled every row would corrupt exactly the statistics the archive
    exists to make computable.
    """
    report = ArchiveReport()
    run_dir = Path(run_dir)

    already = {
        (r["chapter"], r["attempt"])
        for r in conn.execute(
            "SELECT chapter, attempt FROM attempts WHERE run_id = ?", (run_id,))
    }
    halted = conn.execute(
        "SELECT halted FROM runs WHERE id = ?", (run_id,)
    ).fetchone()["halted"]

    critiques = _read_critiques(run_dir, report)

    # The gate this run actually ran: every characteristic that has a critique
    # FILE, whatever the score in it. Judging a five-characteristic run against
    # today's six marks chapters unpassed that passed everything that existed.
    #
    # The file, not a usable score, is the discriminator — and it has to be. A
    # critic that ran and returned nothing parseable looks exactly like a critic
    # that did not exist if you only read the scores, and those are opposite
    # facts: the first is a gate one critic short, which must not pass, and the
    # second is a different gate, which may.
    gate = tuple(c for c in CHARACTERISTICS
                 if any(c in by_critic for by_critic in critiques.values()))
    if gate:
        repository.save_gate_set(conn, run_id, gate)
    if gate and set(gate) != set(CHARACTERISTICS):
        report.notes.append(
            "this run was judged by " + ", ".join(gate)
            + f" — {len(CHARACTERISTICS) - len(gate)} of today's characteristics "
              "did not exist for it, and its attempts are judged against its own "
              "gate rather than against this one"
        )

    drafts: dict[int, list[int]] = {}
    for path in sorted((run_dir / "chapters").glob("ch*.attempt*.md")):
        m = DRAFT.match(path.stem)
        if m:
            drafts.setdefault(int(m.group(1)), []).append(int(m.group(2)))

    for chapter in sorted(drafts):
        attempts = sorted(drafts[chapter])
        accepted = (run_dir / "chapters" / f"ch{chapter:02d}.md").exists()
        last = attempts[-1]
        for attempt in attempts:
            if (chapter, attempt) in already:
                continue
            draft = run_dir / "chapters" / f"ch{chapter:02d}.attempt{attempt}.md"

            scores: dict[str, int | None] = {}
            findings: list[dict] = []
            for characteristic in CHARACTERISTICS:
                it = critiques.get(chapter, {}).get(characteristic, {}).get(attempt)
                if it is None:
                    # No usable verdict. NULL, never 0 and never 10 - one of
                    # those invents a rejection and the other an approval.
                    scores[characteristic] = None
                    report.notes.append(
                        f"ch{chapter:02d} attempt {attempt}: no {characteristic} "
                        f"verdict on file"
                    )
                    continue
                raw = it.get("score")
                scores[characteristic] = int(raw) if isinstance(raw, (int, float)) else None
                findings.extend(_findings_of(it, characteristic))

            usable = [s for s in scores.values() if s is not None]
            aggregate = min(usable) if usable else None
            promoted = accepted and attempt == last
            verdict = _verdict(scores, promoted=promoted, halted=halted,
                               gate=gate or CHARACTERISTICS)

            repository.save_attempt(
                conn,
                run_id=run_id,
                chapter=chapter,
                attempt=attempt,
                title=None,
                draft_path=str(draft.relative_to(run_dir)).replace("\\", "/"),
                words=_words(draft),
                scores=scores,
                verdict=verdict,
                aggregate=aggregate,
                findings=findings,
                promoted=promoted,
            )
            repository.save_gate(
                conn,
                run_id=run_id,
                chapter=chapter,
                attempt=attempt,
                aggregate=aggregate,
                threshold=THRESHOLD,
                verdict=verdict,
                note=f"archived from {draft.name}",
            )
            report.attempts += 1
            report.scores += len(scores)
            report.findings += len(findings)

    if sheets_dir and Path(sheets_dir).is_dir():
        for path in sorted(Path(sheets_dir).glob("ch*.attempt*.md")):
            m = DRAFT.match(path.stem)
            if not m:
                continue
            body = path.read_text(encoding="utf-8")
            repository.save_sheet(
                conn,
                run_id=run_id,
                chapter=int(m.group(1)),
                attempt=int(m.group(2)),
                level=_sheet_level(body),
                body=body,
                # It reached the writer, so it passed the validator: a sheet that
                # fails validation is never sent. Recording that as measured
                # would overstate it, and the run does not log the check.
                validated=True,
                lines_cited=_lines_cited(body),
            )
            report.sheets += 1

    for path in sorted((run_dir / "critiques").glob("ch*.prose.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report.notes.append(f"{path.name}: unreadable, skipped")
            continue
        chapter = int(path.name[2:4])
        for defect in raw.get("defects") or []:
            if not isinstance(defect, dict):
                continue
            # A warning, not a finding. The gate has five characteristics and
            # SPEC-005 did not add a sixth; a mechanical defect is an
            # observation about a chapter, not a score against it.
            repository.warn(
                conn, run_id, f"prose:{defect.get('kind', 'unknown')}",
                f"{defect.get('claim', '')} — {defect.get('quote', '')[:120]!r}",
                chapter=chapter,
            )
            report.prose_defects += 1

    cost_path = run_dir / "cost.json"
    if cost_path.exists():
        raw = json.loads(cost_path.read_text(encoding="utf-8"))
        total = raw.get("total_cost_usd")
        if isinstance(total, (int, float)):
            repository.save_cost(
                conn,
                run_id,
                cost_usd=float(total),
                provenance=raw.get("provenance") or "measured",
                turns=raw.get("turns"),
                duration_ms=raw.get("duration_ms"),
                subagent_dispatches=raw.get("subagent_dispatches"),
            )
            report.cost_usd = float(total)
    else:
        report.notes.append("no cost.json: the run reported no total, which is "
                            "absent rather than zero")

    for note in report.notes:
        repository.warn(conn, run_id, "archive", note)

    return report
