"""`verification.md` is load-bearing, and nothing checked it.

It is the document every other one defers to: `AGENTS.md` sends specs to it,
`README.md` points at §3 by name, and half the code comments cite a G-number. A
document in that position rots the same way code does — a guarantee gets a row in
the summary table and no section, a §3 reference survives a renumbering, a test
file named as evidence gets renamed.

These are the cheapest possible checks and they are **A**, not T: they read the
document as text. They cannot tell whether a claim is true. They can tell whether
the document still refers to things that exist, which is the failure that makes
a reader stop trusting it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/verification.md"
TEXT = DOC.read_text(encoding="utf-8")

#: `| G6 | a failed chapter... | **critical** | ... |`
SUMMARY_ROW = re.compile(r"^\|\s*(G\d+)\s*\|([^|]+)\|\s*([^|]+?)\s*\|", re.M)
#: `### G6 — A failed chapter does not enter the book`
SECTION = re.compile(r"^### (G\d+) — (.+)$", re.M)

LEVELS = ("critical", "important", "incidental")


def summary_rows() -> dict[str, str]:
    """{G-number: level}, from the table in §2."""
    out = {}
    for number, _promise, level in SUMMARY_ROW.findall(TEXT):
        out[number] = level.replace("*", "").strip()
    return out


def test_the_document_is_readable_at_all():
    """A test that scans a file and asserts over nothing passes forever."""
    assert len(summary_rows()) >= 17
    assert len(SECTION.findall(TEXT)) >= 17


def test_every_guarantee_in_the_table_has_a_section():
    tabled = set(summary_rows())
    sectioned = {number for number, _ in SECTION.findall(TEXT)}
    assert tabled == sectioned, f"table only: {tabled - sectioned}; " \
                                f"section only: {sectioned - tabled}"


@pytest.mark.parametrize("number,level", sorted(summary_rows().items()))
def test_every_guarantee_carries_one_of_the_three_levels(number, level):
    """Annex D's whole point: the level is where the decision is written down.

    A row with no level is a row that never had that decision made.
    """
    assert level in LEVELS, f"{number} has level {level!r}"


@pytest.mark.parametrize("number,level", sorted(summary_rows().items()))
def test_a_level_in_the_table_matches_the_one_in_the_section(number, level):
    """Two copies of a fact drift, and this pair is the one that decides whether
    a guarantee needs a gap row."""
    start = TEXT.index(f"### {number} — ")
    end = TEXT.find("\n### ", start + 1)
    body = TEXT[start:end if end != -1 else len(TEXT)]
    assert level.lower() in body.lower()[:400], (
        f"{number}'s section does not restate its level {level!r}"
    )


def test_every_gap_reference_points_at_a_gap_that_exists():
    """A §3.N that survived a renumbering sends the reader nowhere.

    §3 is the section the document is for, so a dangling reference into it is
    worse here than anywhere else.
    """
    defined = set(re.findall(r"^### (3\.\d+)", TEXT, re.M))
    referenced = set(re.findall(r"§(3\.\d+)", TEXT))
    assert defined, "no gap sections found — check the heading format"
    assert referenced <= defined, f"dangling: {sorted(referenced - defined)}"


def test_the_gaps_are_numbered_without_holes():
    numbers = sorted(int(n.split(".")[1]) for n in re.findall(r"^### (3\.\d+)", TEXT, re.M))
    assert numbers == list(range(1, len(numbers) + 1)), numbers


def test_every_test_file_named_as_evidence_exists():
    """The document's evidence table is a promise that something is there.

    Scoped to the table rows on purpose. Prose may legitimately name a file to
    say it does **not** exist — G11 does exactly that — and a check that reads
    the whole document flags the sentence explaining the absence as the absence.
    It did, on its first run, which is a neat demonstration of why a check needs
    to know what it is looking at.
    """
    rows = [line for line in TEXT.splitlines()
            if line.startswith("| `test_")]
    named = {m for line in rows for m in re.findall(r"`(test_[a-z_]+\.py)`", line)}
    assert len(named) >= 8, f"only found {named} — check the table format"
    for name in sorted(named):
        assert (ROOT / "backend/tests" / name).is_file(), name


def test_every_critical_guarantee_is_strong_or_has_a_gap():
    """Annex D's rule, applied to the document by a machine.

    A critical guarantee whose letter is only I or D opens a row in §3. It was
    written as a rule for people to follow; this is what it costs to make it a
    rule that holds.
    """
    for number, level in summary_rows().items():
        if level != "critical":
            continue
        start = TEXT.index(f"### {number} — ")
        end = TEXT.find("\n### ", start + 1)
        body = TEXT[start:end if end != -1 else len(TEXT)]
        header = body[:300]
        strong = "Class A" in header or "Class T" in header
        assert strong or re.search(r"§3\.\d+", header), (
            f"{number} is critical, is not T or A, and points at no gap"
        )
