"""The money in the documents, against the money in the files.

`domain-knowledge.md` opens by saying every figure in it is measured, and that
**a lesson without a number is an opinion**. The numbers are therefore the whole
argument, and they are typed by hand into three documents from files sitting in
`output/`.

A figure that drifts is worse than one that was never given. It reads as
evidence, it is quoted onward, and the file it came from still says something
else.

**A**, not T: it reads text and compares it against JSON. It cannot check a
figure no file carries — the $0.07–$0.13 of an outline audit, or a duration — and
those are left alone rather than approximated.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ["docs/verification.md", "docs/domain-knowledge.md",
        "docs/architecture.md", "README.md"]

MONEY = re.compile(r"\$(\d+\.\d{2})\b")


def measured_costs() -> dict[str, float]:
    out = {}
    for path in sorted(ROOT.glob("output/*/cost.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        total = raw.get("total_cost_usd")
        if isinstance(total, (int, float)):
            out[path.parent.name] = round(float(total), 2)
    return out


def quoted() -> dict[str, list[str]]:
    out = {}
    for doc in DOCS:
        text = (ROOT / doc).read_text(encoding="utf-8")
        found = [m for m in MONEY.findall(text) if float(m) >= 1.0]
        if found:
            out[doc] = found
    return out


def test_there_are_figures_and_files_to_compare():
    assert measured_costs(), "no cost.json anywhere — nothing to check against"
    assert quoted(), "no figures quoted — check the regex"


@pytest.mark.parametrize("slug", sorted(measured_costs()))
def test_each_measured_run_cost_is_a_real_number(slug):
    assert measured_costs()[slug] > 0


def test_every_run_cost_quoted_in_the_docs_matches_a_file():
    """A dollar figure of a whole run must be one a `cost.json` actually holds.

    The exception list is short and each entry says why it is not in a file:
    v1's own estimate, which is the point of the row it appears in, and the
    budget ceiling, which is a setting rather than a measurement.
    """
    real = set(measured_costs().values())

    #: figure -> why it is not a measured run total
    ALLOWED = {
        6.21: "v1's priced-tokens ESTIMATE, quoted beside the $49.33 it missed",
        1.09: "the same estimate for the 3-chapter run, beside its $8.24",
        49.00: "the budget ceiling, a setting and not a measurement",
        8.24: "a v1 run whose cost.json was never written; reconstructed, and "
              "labelled as such where it appears",
        # Derived per thousand words from two totals that ARE in files. The
        # check is about run totals; a derived rate is a different kind of
        # figure and saying so beats widening the rule until it catches nothing.
        4.60: "$49.33 / 10,723 words, per thousand",
        4.93: "$54.87 / 11,133 words, per thousand",
    }

    offenders = []
    for doc, figures in quoted().items():
        for figure in figures:
            value = float(figure)
            if value in real or value in ALLOWED:
                continue
            offenders.append(f"{doc}: ${figure} matches no cost.json and has no reason")
    assert not offenders, offenders


def test_the_two_figures_the_whole_cost_argument_rests_on():
    """$49.33 against $6.21 is the founding measurement of the v2 design, and
    $18.82 against $7.45 is what v2's first real run cost against v1's."""
    costs = measured_costs()
    assert costs.get("ice-station-water-recycler-surplus") == 49.33
    assert costs.get("the-beginning-after-the-end") == 7.45
    assert costs.get("lighthouse-keeper-ledger") == 18.82

    text = (ROOT / "docs/domain-knowledge.md").read_text(encoding="utf-8")
    for figure in ("$49.33", "$6.21", "$18.82", "$7.45"):
        assert figure in text, f"{figure} has left domain-knowledge.md"
