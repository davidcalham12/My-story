"""The rule, guarded structurally rather than remembered.

**What cannot be measured is reported as unmeasurable, never as zero.** It is in
the brief, in `verification.md` G12, in four code comments and in a migration.
And it was broken twice in one morning, in the same payload:

- `total_usd` served the sum over `calls` while a measured total sat in
  `cost.json`;
- `input_tokens` and `output_tokens` served **0** for a run whose every call
  stored `NULL`, so the panel printed "0 / 0 tokens" beside $18.82.

The second was found an hour after the first, in the field next to it. **This
class of bug is never fixed once**, which is the argument for a guard instead of
a note: a rule everybody agrees with is exactly the kind that erodes one
COALESCE at a time.

Both checks are **A**. They read source as text and hold while it is that shape.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sources(folder: Path, suffix: str) -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8"))
            for p in sorted(folder.rglob(f"*{suffix}"))
            if ".test." not in p.name and not p.name.startswith("test_")
            and "__pycache__" not in p.parts]


def test_there_is_something_to_check():
    assert len(sources(ROOT / "backend", ".py")) >= 10
    assert len(sources(ROOT / "frontend/src", ".ts")) >= 3


def test_no_read_query_coalesces_a_measurement_to_zero():
    """`COALESCE(SUM(x), 0)` turns "nobody reported this" into "this was zero".

    SUM over all-NULL rows is NULL, and NULL is the honest answer. A caller that
    genuinely wants a zero can write one where the decision is visible.
    """
    offenders = []
    for path, text in sources(ROOT / "backend", ".py"):
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"COALESCE\s*\(\s*SUM\(", line, re.I):
                offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, offenders


def test_number_formatting_goes_through_the_provenance_helpers():
    """`toFixed` and `toLocaleString` on a nullable figure is how a zero gets on
    screen without anyone deciding to put it there.

    `money()` and `tokens()` each start with the null check. Keeping the
    formatters in one file is what makes that check unavoidable rather than
    remembered.
    """
    allowed = ROOT / "frontend/src/shared/lib/provenance.ts"
    offenders = []
    for path, text in sources(ROOT / "frontend/src", ".ts") + \
                      sources(ROOT / "frontend/src", ".tsx"):
        if path == allowed:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "toFixed" in line or "toLocaleString" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, offenders


def test_the_payload_reports_an_unsummed_cost_as_absent_not_zero(db):
    from backend.commons.db import repository
    from backend.runs import repository as read_repo

    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    payload = read_repo.cost(db, "r")
    assert payload["summed_from_calls_usd"] is None
    assert payload["total_usd"] is None
    assert payload["input_tokens"] is None
    assert payload["total_provenance"] == "absent"
    assert payload["tokens_provenance"] == "absent"
