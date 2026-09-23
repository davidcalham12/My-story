"""`mandatory_facts` — docs/spec.md §2, kind **a**, at the publish gate.

Every fact the buyer put in the brief and marked mandatory must appear in the
book. The Story Bible records where each fact was used — `fact_usage`, one row
per fact per version per chapter — so the check is a set difference and not a
judgement: **the mandatory facts of this run, minus the ones this version used.**

It reports the leftovers **by id**, and that is the whole design. docs/spec.md
§7 accepts, as a written gap, that `fact_usage` is string matching of canonical
names and fact text against the prose: a fact the writer paraphrased is missed.
The gap is accepted only because the error runs one way — "a fact paraphrased is
missed and reported as uncovered, never invented as covered" — and a person can
settle an uncovered id in ten seconds by opening the chapter. A percentage
cannot be settled at all: 75% tells a reader a quarter is wrong and nothing
about which quarter, so the number would be read as a grade and the missing
fact would ship.

`facts` and `fact_usage` arrive with migration 010 (PLAN-001 E3), which is being
built in parallel; this module queries their documented shape —
`facts(id, run_id, kind, text, source, mandatory)` and
`fact_usage(fact_id, version_id, chapter)` — and creates nothing.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from backend.publish import validations

VALIDATOR = "mandatory_facts"
KIND = "a"


@dataclass(frozen=True)
class Coverage:
    covered: list[str]
    uncovered: list[str]

    @property
    def total(self) -> int:
        return len(self.covered) + len(self.uncovered)

    @property
    def fraction(self) -> float | None:
        """Covered over mandatory, or `None` when there are none.

        `0/0` is not 1.0 and it is not 0.0 — there is no denominator, so there
        is no figure. docs/domain-knowledge.md §7.10 lists four bugs in one day
        that were all this substitution, and a brief with no mandatory facts is
        the commonest run this validator will ever see: reporting it as a
        perfect score would put a 100% beside every one of them and make the
        column meaningless where it matters.
        """
        return len(self.covered) / self.total if self.total else None

    def justify(self) -> str:
        """What the fraction means, in ids, so the figure never travels without
        the thing a person would act on."""
        if not self.total:
            return ("no fact in this brief is marked mandatory, so there is no "
                    "denominator and no fraction")
        if not self.uncovered:
            return f"all {self.total} mandatory facts have a fact_usage row"
        return (f"{len(self.covered)} of {self.total} mandatory facts covered; "
                f"uncovered: {', '.join(str(i) for i in self.uncovered)}")


def check(conn: sqlite3.Connection, *, run_id: str, version_id: int) -> Coverage:
    """The set difference, in one query.

    `source = 'brief'` and `mandatory = 1` together, never either alone: a fact
    the Bible invented is not something the buyer asked for, and an optional
    brief fact is not a failure to be counted against the book. Both filters
    shrink the denominator, which is the direction that makes the figure
    truthful rather than flattering.

    `version_id` is the version's row id, not its number — `fact_usage` is
    per-version because a reader change rewrites some chapters and not others,
    and a fact covered in v1 is not thereby covered in v2.
    """
    rows = conn.execute(
        "SELECT f.id AS id, "
        "       EXISTS (SELECT 1 FROM fact_usage u "
        "               WHERE u.fact_id = f.id AND u.version_id = ?) AS used "
        "FROM facts f "
        "WHERE f.run_id = ? AND f.source = 'brief' AND f.mandatory = 1 "
        "ORDER BY f.id",
        (version_id, run_id),
    ).fetchall()
    return Coverage(covered=[r["id"] for r in rows if r["used"]],
                    uncovered=[r["id"] for r in rows if not r["used"]])


def record(conn: sqlite3.Connection, *, run_id: str, version: int,
           coverage: Coverage) -> None:
    """One row into `validations`.

    The value is `covered/total` rather than a decimal because that is the form
    that keeps the denominator attached: `0.67` over three facts and `0.67` over
    ninety are the same number and not the same book. The ids go in the
    justification, where the pivot in `evals/results.md` can show them under the
    cell a reader clicks.
    """
    value = None if coverage.total == 0 else f"{len(coverage.covered)}/{coverage.total}"
    validations.record(conn, run_id=run_id, version=version, validator=VALIDATOR,
                       kind=KIND, rows=[(None, value, coverage.justify())])
