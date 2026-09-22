"""`architecture.md` is the map of the codebase, and maps go stale silently.

Its `commons/` tree named `llm/`, `context/` and `budget/` — the D2 design, none
of which survived Annex C and none of which exists. A map that no longer matches
the code is worse than no map: it sends a reader looking for a module, and when
they do not find it they stop trusting the rest of the document too.

**A**, not T. It reads the document as text and compares it against the
filesystem. It cannot tell whether the prose is right; it can tell whether the
directories it names are there.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")

#: A line inside a fenced tree: `├── runner/    launches ...`
TREE_ENTRY = re.compile(r"^[│├└─\s]*([a-z_]+)/\s{2,}", re.M)


def commons_tree() -> set[str]:
    start = DOC.index("```\ncommons/")
    end = DOC.index("```", start + 4)
    return set(TREE_ENTRY.findall(DOC[start:end]))


def test_the_tree_is_readable_at_all():
    assert len(commons_tree()) >= 4, commons_tree()


def test_every_directory_the_tree_names_exists():
    for name in sorted(commons_tree()):
        assert (ROOT / "backend/commons" / name).is_dir(), (
            f"architecture.md names commons/{name}/ and it is not there"
        )


def test_every_directory_that_exists_is_in_the_tree():
    """The other direction, which is how `runner/` went undocumented.

    A module nobody wrote down is a module nobody knows to look in — and
    `runner/` is the one that launches Claude Code.
    """
    real = {p.name for p in (ROOT / "backend/commons").iterdir()
            if p.is_dir() and not p.name.startswith(("_", "."))}
    assert real == commons_tree(), (
        f"undocumented: {sorted(real - commons_tree())}; "
        f"documented and absent: {sorted(commons_tree() - real)}"
    )


def test_the_removed_modules_are_not_described_as_present():
    """`llm/`, `context/` and `budget/` may be named in the paragraph explaining
    that they are gone. They may not be back in the tree."""
    assert not ({"llm", "context", "budget"} & commons_tree())


# ------------------------------------------- §4, the nine agents

AGENTS_DIR = ROOT / ".claude/agents"

#: `### 4.1 worldbuilder — FLOW-1, opus`
AGENT_HEADING = re.compile(r"^### 4\.\d+ ([a-z-]+) — (FLOW-\d)[^,]*, (\w+)\s*$", re.M)


def documented_agents() -> dict[str, tuple[str, str]]:
    return {name: (stage, model) for name, stage, model in AGENT_HEADING.findall(DOC)}


def front_matter(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").split("---")[1].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def test_the_document_lists_exactly_the_agents_that_exist():
    """§4 is the catalogue `AGENTS.md` sends readers to, so a missing agent
    there is an agent nobody knows can be dispatched."""
    on_disk = {p.stem for p in AGENTS_DIR.glob("*.md")}
    assert documented_agents().keys() == on_disk, (
        f"documented only: {documented_agents().keys() - on_disk}; "
        f"on disk only: {on_disk - documented_agents().keys()}"
    )


def test_each_agents_model_matches_its_front_matter():
    """The model decides what the run costs and which judgements are whose.

    Two copies of it — a heading in prose and a line of YAML — drift, and the
    prose copy is the one people plan with.
    """
    for name, (_stage, model) in sorted(documented_agents().items()):
        declared = front_matter(AGENTS_DIR / f"{name}.md").get("model")
        assert declared == model, f"{name}: doc says {model}, front matter says {declared}"


def test_each_agents_stage_matches_its_description():
    for name, (stage, _model) in sorted(documented_agents().items()):
        description = front_matter(AGENTS_DIR / f"{name}.md").get("description", "")
        assert stage in description, f"{name}: doc says {stage}, its description does not"


# ------------------------------------------- paths the docs point at

BACKTICKED_PATH = re.compile(r"`((?:backend|frontend|config|specs|docs)/[\w./<>-]+)`")


def cited_paths(doc: Path) -> set[str]:
    """Paths a document names, minus the ones with a `<placeholder>` in them."""
    text = doc.read_text(encoding="utf-8")
    # `<feature>` and `SPEC-NNN` are templates, not paths.
    return {p for p in BACKTICKED_PATH.findall(text)
            if "<" not in p and "NNN" not in p}


def test_the_documents_cite_paths_at_all():
    assert len(cited_paths(ROOT / "claude.md")) >= 4


def test_every_concrete_path_the_docs_name_exists():
    """`claude.md` is the first file a coding agent is told to read.

    It pointed at `backend/<feature>/prompts/` and `backend/commons/context/` —
    the D2 design, where Python built a typed packet and called an API. Annex C
    removed the API and the packet with it. A path that does not resolve teaches
    a reader that the document is decoration.
    """
    missing = []
    for doc in ("claude.md", "README.md", "AGENTS.md"):
        for cited in sorted(cited_paths(ROOT / doc)):
            target = ROOT / cited
            if not (target.exists() or list(ROOT.glob(cited))):
                missing.append(f"{doc} -> {cited}")
    assert not missing, missing


# ------------------------------------------- the front door

README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_readme_does_not_state_the_unverified_claim_as_fact():
    """"chapter thirty-four's prompt is the same size as chapter one's, and the
    cost curve is flat" was the opening sentence, as a statement of fact.

    The prompt size is structural and holds. **Whether the book holds over
    thirty-four chapters is U** — the longest run is eight, and the two runs that
    exist disagree about whether later chapters get harder. The front door is the
    one place a reader will believe without checking.
    """
    opening = README[:README.index("## Running it")]
    assert "not established" in opening or "is not established" in opening
    assert "verification.md" in opening


def test_the_readme_counts_the_characteristics_the_gate_has():
    from backend.chapters.domain import CHARACTERISTICS

    words = {5: "five", 6: "six", 7: "seven"}
    assert f"of its {words[len(CHARACTERISTICS)]} characteristics" in README, (
        "the README states how many characteristics are model judgements; "
        "SPEC-006 changed the denominator"
    )


def test_the_readme_says_detection_is_not_prevention():
    """Two chapters entered a book that should not have. A front page that
    implies the gate cannot be disobeyed would be the most expensive sentence in
    the repository."""
    assert "detection" in README and "not prevention" in README
