"""The backend's payload against the panel's types.

Two descriptions of the same JSON, in two languages, with a network between
them. Nothing compared them: `tsc` type-checks the frontend against what the
frontend *believes*, and pytest checks the backend against what the backend
believes, and both pass while the panel reads `undefined`.

It is the same shape as every other defect found today — two copies of a fact,
no one reading both — and it is the one that breaks a screen rather than a
document.

**A**, not T: it parses TypeScript with a regular expression, which holds while
the interfaces are written the way they are written. It would not survive a
clever type, and the interfaces here are deliberately plain.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.commons.db import repository
from backend.runs import repository as read_repo

ROOT = Path(__file__).resolve().parents[2]
TYPES = (ROOT / "frontend/src/shared/api/types.ts").read_text(encoding="utf-8")

#: A field line inside an interface: `  total_usd: number | null` — ignoring
#: comments, and keeping whether it is optional.
FIELD = re.compile(r"^\s{2}(\w+)(\??):", re.M)


def interface(name: str) -> tuple[set[str], set[str]]:
    """(required fields, optional fields) of a TypeScript interface."""
    start = TYPES.index(f"export interface {name} {{")
    end = TYPES.index("\n}", start)
    fields = FIELD.findall(TYPES[start:end])
    return ({n for n, opt in fields if not opt}, {n for n, opt in fields if opt})


def test_the_types_file_is_parsed_at_all():
    required, _ = interface("Cost")
    assert {"calls", "total_usd", "provenance"} <= required, required


def test_the_cost_payload_has_exactly_the_fields_the_panel_declares(db):
    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    required, optional = interface("Cost")
    served = set(read_repo.cost(db, "r"))
    assert required <= served, f"the panel expects and does not get: {required - served}"
    assert served <= required | optional, (
        f"the backend serves fields the panel does not declare: {served - required - optional}"
    )


def test_the_conformance_payload_matches_its_interface(db):
    from backend.runs import conformance

    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    required, optional = interface("Conformance")
    served = set(conformance.summary(db, "r"))
    assert required <= served, f"missing: {required - served}"
    assert served <= required | optional, f"undeclared: {served - required - optional}"


def test_a_not_applicable_run_still_matches_the_interface(db):
    """The branch that returns early, and therefore the one that drifts.

    It has its own `return` with its own dict literal, which is exactly how a
    payload ends up shaped differently depending on which run you open.
    """
    from backend.runs import conformance

    repository.create_run(db, run_id="r", slug="s", premise="p", profile="tiny",
                          tone=None, snapshot="{}")
    db.execute("UPDATE runs SET source = 'pre-loop003' WHERE id = 'r'")
    required, optional = interface("Conformance")
    served = set(conformance.summary(db, "r"))
    assert required <= served, f"missing: {required - served}"
    assert served <= required | optional, f"undeclared: {served - required - optional}"


@pytest.mark.parametrize("verdict", ["conformant", "breached", "unchecked",
                                     "not_applicable"])
def test_every_conformance_verdict_the_backend_can_produce_is_declared(verdict):
    """The union type is a promise about what the backend will send.

    A fifth verdict added in Python renders as nothing on a page that switches
    on four.
    """
    declared = re.search(r"export type ConformanceVerdict = ([^\n]+)", TYPES).group(1)
    assert f"'{verdict}'" in declared, declared


def test_the_run_detail_keys_are_the_ones_the_service_serves():
    """`RunDetail` is what `detail()` returns, and the two are written apart."""
    from backend.runs.service import RunService

    source = Path(RunService.detail.__code__.co_filename).read_text(encoding="utf-8")
    body = source[source.index("def detail(self"):]
    body = body[:body.index("\n    # ")]
    served = set(re.findall(r'^\s+"(\w+)":', body, re.M))

    required, optional = interface("RunDetail")
    assert required <= served, f"the panel expects and does not get: {required - served}"
    assert served <= required | optional, f"undeclared: {served - required - optional}"
