"""Did the run obey its own gate? SPEC-004 A10, checked after the fact.

`decide()` made the rule arithmetic. It could not make the orchestrator's
*obedience* testable, because obedience is a procedure and §3.10 says procedures
need a real run. So `verification.md` §3.1 stayed critical with one line standing
out: **the only signal was reading a book with a bad chapter in it.**

This is the earlier signal. It reads a run's archived attempts, recomputes what
`decide()` would have answered at each one, and reports where the record and the
rule disagree. It cannot prevent a disobeyed halt. It can make one **visible the
moment the run ends**, which is the difference between an accepted risk and an
undetectable one.

It runs over the archive, so it costs $0 and works on any run ever archived —
including, the first time it was run, every run imported from v1.

**What it cannot see.** A run that never wrote its attempts (§3.11), and a
chapter whose promotion happened outside the archive. It reads the record; a
record that was never written says nothing, and this reports that as unchecked
rather than as conformant.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from backend.chapters.domain import (MAX_ATTEMPTS_DEFAULT, THRESHOLD_DEFAULT,
                                     decide)


@dataclass(frozen=True)
class Breach:
    chapter: int
    attempt: int | None
    rule: str
    detail: str

    def __str__(self) -> str:
        where = f"ch{self.chapter:02d}" + (
            f" attempt {self.attempt}" if self.attempt else "")
        return f"{where}: {self.rule} — {self.detail}"


def audit(conn: sqlite3.Connection, run_id: str, *, threshold: int = THRESHOLD_DEFAULT,
          max_attempts: int = MAX_ATTEMPTS_DEFAULT) -> list[Breach]:
    """Every way the record can contradict the rule. Empty means it obeyed.

    **Two things this deliberately refuses to call a breach**, both learned by
    running it over the eight v1 runs the first time it existed:

    - **An attempt with no aggregate cannot be judged.** Six of those runs
      recorded no usable scores at all, and the first version reported them as
      chapters promoted below the threshold. That is *absent read as failure* —
      the mirror of reading absent as zero, and just as wrong. They are
      unjudgeable, and `summary()` counts them apart.
    - **A run judged by a rule that did not exist is not disobedient.** Runs
      marked `pre-loop003` were scored on two or three characteristics with
      `accept_with_warnings` available. Applying today's rule to them produces
      confident nonsense, which is the same category error the `source` column
      was added to prevent.
    """
    run = conn.execute(
        "SELECT halted, source FROM runs WHERE id = ?", (run_id,)).fetchone()
    if run and run["source"] != "v2":
        return []
    halted = run["halted"] if run else None

    rows = [dict(r) for r in conn.execute(
        "SELECT chapter, attempt, aggregate, verdict, promoted FROM attempts "
        "WHERE run_id = ? ORDER BY chapter, attempt", (run_id,))]

    by_chapter: dict[int, list[dict]] = {}
    for row in rows:
        by_chapter.setdefault(row["chapter"], []).append(row)

    breaches: list[Breach] = []
    for chapter, attempts in sorted(by_chapter.items()):
        last = attempts[-1]

        for row in attempts:
            aggregate = row["aggregate"]

            # An attempt with no aggregate is unjudgeable, not delinquent. The
            # record cannot answer, and a check that answers anyway is inventing
            # the thing it claims to be watching for.
            if aggregate is None:
                continue

            # 1. The one that matters. A promoted draft below the threshold is
            #    the outcome the whole system exists to prevent.
            #
            #    `patched` is NOT a blanket exemption, and it used to be. The
            #    verdict means *the patch brought this to the threshold*, so a
            #    `patched` row still under it is incoherent — `decide` cannot
            #    produce one. Exempting it unconditionally left the widest
            #    possible door open under the one label nobody would question.
            if row["promoted"] and aggregate < threshold:
                breaches.append(Breach(
                    chapter, row["attempt"], "promoted below the threshold",
                    f"aggregate {aggregate} was put in the book with verdict "
                    f"{row['verdict']!r}",
                ))

            # 2. The recorded verdict against the rule, at that state.
            expected = decide(
                aggregate=aggregate, attempt=row["attempt"],
                max_attempts=max_attempts,
                # The archive records a rescue as `patched`; nothing else can
                # have been through the patch.
                patched=row["verdict"] == "patched",
                threshold=threshold,
            )
            if row["verdict"] not in {expected.verdict, expected.action}:
                breaches.append(Breach(
                    chapter, row["attempt"], "verdict the rule would not give",
                    f"recorded {row['verdict']!r}, the rule says "
                    f"{expected.action!r} ({expected.why})",
                ))

        # 3. More attempts than the loop allows.
        if len(attempts) > max_attempts:
            breaches.append(Breach(
                chapter, None, "more attempts than allowed",
                f"{len(attempts)} drafts against max_attempts {max_attempts}",
            ))

        # 4. A chapter that never reached the threshold and was not promoted must
        #    have stopped the run. Carrying on means the book has a hole in it
        #    that nobody decided to make.
        reached = any(a["aggregate"] is not None and a["aggregate"] >= threshold
                      for a in attempts)
        promoted = any(a["promoted"] for a in attempts)
        if not reached and not promoted and not halted:
            breaches.append(Breach(
                chapter, last["attempt"], "failed without halting",
                "no attempt reached the threshold, nothing was promoted, and the "
                "run did not halt",
            ))

        # 5. Two promotions is two accepted drafts for one chapter.
        if sum(1 for a in attempts if a["promoted"]) > 1:
            breaches.append(Breach(
                chapter, None, "more than one draft promoted",
                "a chapter ships once",
            ))

    return breaches


def summary(conn: sqlite3.Connection, run_id: str) -> dict:
    """For the API and the panel. `checked: 0` is not `conformant: true`.

    **Four states, not two**, and each of the extra two is a claim the obvious
    version would have got wrong:

    - `not_applicable` — a `pre-loop003` run, judged by a rule that did not
      exist. Six of the eight scored `breached` against today's rule, which
      measured nothing.
    - `unchecked` — no attempt with an aggregate to judge. Not conformant. Not
      breached. **Unknown**, which is the answer.
    """
    row = conn.execute(
        "SELECT source FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row and row["source"] != "v2":
        return {"attempts_checked": 0, "unjudgeable": 0, "breaches": [],
                "verdict": "not_applicable",
                "why": f"judged as {row['source']}, by a rule that did not exist"}

    counts = conn.execute(
        "SELECT COUNT(*) AS n, SUM(aggregate IS NULL) AS blind FROM attempts "
        "WHERE run_id = ?", (run_id,)
    ).fetchone()
    blind = int(counts["blind"] or 0)
    judged = int(counts["n"] or 0) - blind
    breaches = audit(conn, run_id)

    return {
        "attempts_checked": judged,
        "unjudgeable": blind,
        "breaches": [str(b) for b in breaches],
        "verdict": ("unchecked" if not judged
                    else "conformant" if not breaches else "breached"),
    }
