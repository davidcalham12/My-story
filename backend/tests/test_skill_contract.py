"""The validator `verification.md` §5 promised and did not have.

`SKILL.md` is the procedure; `flow.yaml`, `config/` and the schema are the
contract. Nothing held them together, and they diverged: `SKILL.md` told the
orchestrator to write the verdict `accept_with_warnings`, which the `attempts`
table's CHECK does not admit and which `patch_then_halt` exists to abolish. An
orchestrator obeying that paragraph would either crash on the insert or keep a
failed chapter — and the divergence was invisible because no test read both.

These are class **T** and they read files, not runs. They cannot say the
procedure is *right*; they can say the two documents still describe the same
system.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL = (ROOT / ".claude/skills/novaforge/SKILL.md").read_text(encoding="utf-8")
FLOW = yaml.safe_load((ROOT / "specs/flow.yaml").read_text(encoding="utf-8"))
CONFIG = json.loads((ROOT / "config/novel.config.json").read_text(encoding="utf-8"))
SCHEMA = (ROOT / "backend/commons/db/migrations/002_chapters.sql").read_text(
    encoding="utf-8"
)


def schema_verdicts() -> set[str]:
    """The verdicts the database will actually accept, read off the CHECK."""
    m = re.search(r"verdict\s+TEXT\s+CHECK\s*\(verdict IN \(([^)]*)\)\)", SCHEMA)
    assert m, "the attempts table no longer constrains verdict; that is the bug"
    return set(re.findall(r"'([a-z_]+)'", m.group(1)))


def test_the_verdict_vocabulary_skill_teaches_is_the_one_the_schema_accepts():
    lines = [ln for ln in SKILL.splitlines() if ln.startswith("`verdict` is ")]
    assert len(lines) == 1, f"expected one enumeration of the verdicts, got {lines}"
    taught = set(re.findall(r"`([a-z_]+)`", lines[0])) - {"verdict"}
    assert taught == schema_verdicts(), (
        f"SKILL.md teaches {sorted(taught)}; the schema accepts "
        f"{sorted(schema_verdicts())}"
    )


@pytest.mark.parametrize("name", ["SKILL.md", "specs/flow.yaml"])
def test_accept_with_warnings_survives_only_as_a_repudiation(name):
    """It may be named — the history is worth keeping — but never instructed.

    `patch_then_halt` replaced it precisely because it put a chapter that had
    failed three times into the book with a note in the margin. A line that
    mentions it without saying it is gone reads as an instruction to a model.
    """
    path = ROOT / (".claude/skills/novaforge/SKILL.md" if name == "SKILL.md" else name)
    text = path.read_text(encoding="utf-8")
    # Both spellings: the identifier a verdict row would carry, and the prose a
    # report would use. The second is how it survived at the end of SKILL.md
    # after the first had been corrected at the top.
    spellings = ("accept_with_warnings", "accepted with warnings")
    repudiations = ("not ", "replaces", "replaced", "no longer", "old ", "used to",
                    "put a chapter")
    # By paragraph, because a repudiation wraps onto the next line and a
    # line-by-line reading calls that a violation.
    for para in re.split(r"\n\s*\n", text):
        if not any(s in para for s in spellings):
            continue
        assert any(w in para for w in repudiations), (
            f"{name} names accept_with_warnings as live vocabulary:\n{para.strip()}"
        )


def gate_stage() -> dict:
    for stage in FLOW["stages"]:
        if stage.get("gate"):
            return stage
    raise AssertionError("no stage in flow.yaml carries a gate")


def test_the_threshold_is_one_number_everywhere():
    gate = gate_stage()["gate"]
    assert gate["threshold"] == CONFIG["quality_gate"]["threshold"] == 8


def test_three_attempts_and_two_revisions_are_the_same_statement():
    """`flow.yaml` counts attempts; the config counts revisions.

    Three attempts is one draft plus two revisions. Written as two different
    numbers in two files, they can drift into meaning four attempts or two, and
    nobody would see it — the arithmetic is the only thing tying them together.
    """
    gate = gate_stage()["gate"]
    assert gate["max_iterations"] == 3, "AGENTS.md §6: not moved without a SPEC"
    assert CONFIG["quality_gate"]["max_revisions"] == gate["max_iterations"] - 1


def test_the_five_characteristics_agree_across_contract_and_code():
    from backend.chapters.domain import CHARACTERISTICS

    gate = gate_stage()["gate"]
    assert set(gate["critics"]) == set(CHARACTERISTICS)
    assert set(CONFIG["quality_gate"]["critics"]) == set(CHARACTERISTICS)
    assert len(CHARACTERISTICS) == 5


def test_skill_defers_the_decision_to_the_script_instead_of_deciding():
    """SPEC-004 A9. The procedure must call the rule, not restate it.

    A restated rule is a second copy, and two copies of a rule drift. This one
    drifting means a chapter the gate rejected going into a book.
    """
    assert "python -m backend.chapters.decide" in SKILL, (
        "SKILL.md no longer tells the orchestrator to ask the decision script"
    )
    # The four answers it has to know how to obey.
    for action in ("accept", "retry", "patch", "halt"):
        assert f"`{action}`" in SKILL, f"SKILL.md does not say what to do on {action}"


def test_the_decision_script_is_runnable_with_the_tools_the_run_is_given():
    """A rule the orchestrator is not permitted to invoke is a rule it must
    remember, which is what SPEC-004 exists to stop."""
    from backend.commons.runner.process import ALLOWED_TOOLS

    assert any(t.startswith("Bash(python") for t in ALLOWED_TOOLS), ALLOWED_TOOLS


def test_on_fail_is_patch_then_halt_in_all_three():
    assert gate_stage()["on_fail"] == "patch_then_halt"
    assert CONFIG["quality_gate"]["on_fail"] == "patch_then_halt"
    assert "patch_then_halt" in SKILL


def test_the_aggregate_is_min_not_an_average():
    assert gate_stage()["gate"]["aggregate"] == "min"
    assert CONFIG["quality_gate"]["aggregate"] == "min"
