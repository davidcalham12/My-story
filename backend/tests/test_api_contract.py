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


def test_the_panel_knows_every_characteristic_the_gate_scores():
    """A characteristic the panel does not declare renders as nothing.

    `scores` is keyed by `Characteristic`, so a sixth added in Python and not
    here means the column the chapter actually failed on is the one the reader
    cannot see.
    """
    from backend.chapters.domain import CHARACTERISTICS

    declared = set(re.findall(r"^  \| '(\w+)'$", TYPES, re.M))
    assert set(CHARACTERISTICS) <= declared, (
        f"the gate scores and the panel cannot show: "
        f"{set(CHARACTERISTICS) - declared}"
    )


def test_the_panel_and_the_config_agree_on_the_threshold():
    """A fourth copy of the number, in a language that cannot import it.

    `commons/config/loader.py` opens by saying a threshold written into Python is
    a second source of truth and the two disagree within a month. It is written
    into TypeScript too, where the argument is the same and the import is not
    available — so the check is.
    """
    import json

    config = json.loads((ROOT / "config/novel.config.json").read_text(encoding="utf-8"))
    lib = (ROOT / "frontend/src/entities/run/lib.ts").read_text(encoding="utf-8")
    match = re.search(r"export const THRESHOLD = (\d+)", lib)
    assert match, "the panel no longer states a threshold"
    assert int(match.group(1)) == config["quality_gate"]["threshold"]


def test_the_panel_names_every_characteristic_it_shows_a_column_for():
    """`Record<string, string>` returned undefined for a missing entry and the
    column header rendered empty — which is how `prose` would have shipped
    nameless. It is typed against `Characteristic` now; this says so out loud so
    the type cannot be loosened back without a red test."""
    from backend.chapters.domain import CHARACTERISTICS

    quality = (ROOT / "frontend/src/pages/quality/Quality.tsx").read_text(encoding="utf-8")
    assert "Record<Characteristic, string>" in quality, (
        "LABEL is no longer typed against Characteristic; a missing column name "
        "would render empty again"
    )
    for characteristic in CHARACTERISTICS:
        assert f"{characteristic}:" in quality, characteristic


# ------------------------------------------------------- PLAN-007 6.10


def test_no_route_takes_a_path_and_reads_a_file():
    """SPEC-007 FR-RD-2 / AC-10, as decided at Paso 4 (Q2): the backend serves
    no artefact by file path, so the path-traversal surface does not exist.
    This test is the day it appears: a new route must be added here on
    purpose, with its normalisation test beside it."""
    from backend.main import app

    served = {route.path for route in app.routes if hasattr(route, "methods")}
    framework = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    ours = served - framework
    assert ours == {
        "/api/health",
        "/api/runs",
        "/api/runs/{run_id}",
        "/api/runs/{run_id}/events",
        "/api/runs/{run_id}/halt",
    }, sorted(ours)
    for path in ours:
        assert "{path" not in path and "{name" not in path and "{section" not in path
