"""`judge_rubric` — docs/spec.md §2, kind **b**, AC-9.

The `judge` agent reads the assembled book and returns six criteria, each with a
score 0–10 **and a justification**. This module is the schema that reply has to
satisfy, the mean over what it actually scored, and the write into
`validations`.

**The justification is not decoration and this is the module that says so.**
The six characteristics of the chapter gate are checked against something — the
Bible, the world's rules, the outline, a word count — so a reader can go and
look. The judge is checked against nothing: it is one model's reading of a whole
book, and the only thing that makes its 6 different from a 9 it could equally
have written is the sentence next to it. A score with no reason is a number
nobody can dispute, which is the same as a number nobody can use. So a criterion
that arrives without its justification is **rejected**, and the publish gate
sees a malformed reply rather than a set of scores.

The second rule here is docs/domain-knowledge.md §7.10 at its most expensive.
The judge runs once per version, on the finished book, after every chapter has
been paid for. A criterion it failed to score is **excluded from the mean** — it
is not a 0. Five nines and an absence is a 9 on a weaker rubric; counting the
absence as 0 makes it 7.5 and publishes a claim about a criterion nobody looked
at. `chapters/domain.py:aggregate` learned this when a malformed critic reply
returned 10 and silently passed a draft; the mistake costs more here because
there is no attempt 2.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.publish import validations

#: docs/spec.md §2, in the spec's own order and with its own names. Six, and the
#: sixth is the exam's reason for existing: a novel that gets the recipient's
#: details right and reads like a form letter has failed at the only thing that
#: separates it from a novel.
CRITERIA = ("continuity", "tone", "narrative_arc", "character_coherence",
            "pacing", "natural_personalisation")

VALIDATOR = "judge_rubric"
KIND = "b"

#: A justification is stripped and must survive it. "ok", "good" and "  " are
#: the three shapes a model reaches for when it has a number and no reason, and
#: all three are the failure this schema exists to prevent — so the floor is
#: high enough that none of them clears it and low enough that a terse, real
#: sentence does.
Justification = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10)]


class Criterion(BaseModel):
    """One criterion's verdict. Both halves or neither.

    `extra="forbid"` because a reply carrying `reason` instead of
    `justification` would otherwise validate with the reason dropped on the
    floor and the score kept — the exact trade this module refuses.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    score: int = Field(ge=0, le=10)
    justification: Justification


class JudgeRubric(BaseModel):
    """The `judge` agent's whole reply.

    Every criterion is optional and defaults to `None`, which is the only
    honest representation of "the judge did not answer this one". It is not a
    default score: `None` is excluded from the mean, reported in `unscored()`
    and stored as a row with a NULL value, so a thin rubric looks thin instead
    of looking mediocre.
    """

    model_config = ConfigDict(extra="forbid")

    continuity: Criterion | None = None
    tone: Criterion | None = None
    narrative_arc: Criterion | None = None
    character_coherence: Criterion | None = None
    pacing: Criterion | None = None
    natural_personalisation: Criterion | None = None
    #: Anything the judge wants to say that is not a criterion. Never scored.
    notes: str = ""

    def scored(self) -> dict[str, int]:
        return {name: getattr(self, name).score
                for name in CRITERIA if getattr(self, name) is not None}

    def unscored(self) -> list[str]:
        return [name for name in CRITERIA if getattr(self, name) is None]

    def mean(self) -> float | None:
        """Over what was scored. `None` when nothing was — not 0.0.

        A mean, not the `min` the chapter gate takes. The gate is a pass/fail on
        a draft that can be redrafted, so it is worth what its worst
        characteristic is worth; this is a description of a finished book, and
        reducing it to its worst criterion would throw away the five figures
        AC-9 asks to be published beside the human review's five.
        """
        values = list(self.scored().values())
        return sum(values) / len(values) if values else None

    def note(self) -> str:
        """What the mean was computed over, in words, so the figure never
        travels without its denominator."""
        missing = self.unscored()
        if not missing:
            return f"mean over all {len(CRITERIA)} criteria"
        if len(missing) == len(CRITERIA):
            return "no criterion was scored; there is no mean"
        return (f"mean over {len(CRITERIA) - len(missing)} of {len(CRITERIA)} criteria; "
                f"{', '.join(missing)} returned no score and was excluded, not counted as 0")


def parse(payload: str | dict) -> JudgeRubric:
    """The agent's reply, from whatever it came back as.

    Kept separate from `JudgeRubric.model_validate` so the caller has one place
    to catch both failures — a reply that is not JSON at all and a reply that is
    JSON of the wrong shape. They arrive the same way and mean the same thing at
    the publish gate: the judge did not answer.
    """
    if isinstance(payload, str):
        payload = json.loads(payload)
    return JudgeRubric.model_validate(payload)


def record(conn: sqlite3.Connection, *, run_id: str, version: int,
           rubric: JudgeRubric) -> None:
    """Six rows and the mean, into `validations`.

    The mean is stored rather than computed on read because it is the figure
    AC-9 publishes and `evals/results.md` pivots, and a figure recomputed by
    every reader is a figure two readers can disagree about. Its justification
    carries `note()` — how many criteria it covers — so the denominator cannot
    be separated from the number.

    An unscored criterion gets a row with a NULL value and a justification
    saying so, not a missing row: "the judge was asked and did not answer" and
    "nobody ran the judge" are different facts, and only rows can tell them
    apart.
    """
    rows: list[tuple[str | None, str | None, str | None]] = []
    for name in CRITERIA:
        criterion = getattr(rubric, name)
        if criterion is None:
            rows.append((name, None, "the judge returned no score for this criterion"))
        else:
            rows.append((name, str(criterion.score), criterion.justification))

    # Stored unrounded. `evals/results.md` rounds for the page, and a figure
    # rounded on the way INTO the archive cannot be un-rounded by the reader who
    # later wants the delta against the human review's score.
    mean = rubric.mean()
    rows.append(("mean", None if mean is None else repr(mean), rubric.note()))

    validations.record(conn, run_id=run_id, version=version, validator=VALIDATOR,
                       kind=KIND, rows=rows)


def read(conn: sqlite3.Connection, run_id: str, version: int) -> dict | None:
    """What the judge said about one version, or `None` if it never ran.

    `None` and an empty rubric are different answers and the route turns the
    first into a 404. A panel showing six dashes for "no judge ran" looks
    exactly like one showing six dashes for "the judge answered nothing".
    """
    rows = validations.for_version(conn, run_id, version, validator=VALIDATOR)
    if not rows:
        return None

    criteria: dict[str, dict] = {}
    mean: float | None = None
    note = ""
    for row in rows:
        if row["criterion"] == "mean":
            mean = None if row["value"] is None else float(row["value"])
            note = row["justification"] or ""
        elif row["criterion"] in CRITERIA and row["value"] is not None:
            criteria[row["criterion"]] = {"score": int(row["value"]),
                                          "justification": row["justification"]}

    return {
        "run_id": run_id,
        "version": version,
        "criteria": criteria,
        "mean": mean,
        # Named, not inferred from a short dict: a reader has to be able to see
        # WHICH criterion is missing without diffing against a list of six.
        "unscored": [name for name in CRITERIA if name not in criteria],
        "note": note,
    }
