"""The chapter hook: length, canonical names, and the shape of the critiques.

    python .claude/hooks/validate-chapter.py output/<slug>/chapters/ch01.md

Wired in `.claude/settings.json` as a `PostToolUse` matcher on `Write` under
`output/*/chapters/`, where the event arrives as JSON on stdin; the argument
form is the one the tests use and the one a human can run.

Three of the validators in `docs/spec.md` §2 meet here, and each of them already
exists somewhere else:

- `chapter_length` — the band from the run's own `config.snapshot.json`, scored
  by `chapters.domain.score_length`. Not a second copy of the widening formula:
  the gate's arithmetic is the arithmetic, or the hook and the gate disagree
  about the same chapter.
- `canonical_names` — `chapters.names.check`, unchanged. This script **calls**
  it rather than reimplementing it; a name check that drifts from the one the
  gate runs is worse than none, because two answers about one draft is a
  question nobody can settle.
- `schema_role_output` — the critique files for this chapter, held against the
  models below.

**Prints JSON and exits 1 when it finds something**, like `check_prose`. Exit 2
is reserved for "I could not look" — a missing file, an unusable argument —
because a hook that answers 0 when it read nothing is the absent-read-as-clean
mistake, and a hook that answers 1 for it cries wolf.

**What it did not check, it says it did not check.** A run with no
`bible/characters.md` yet gets `not_checked`, never `clean`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ConfigDict, Field, ValidationError  # noqa: E402

from backend.chapters.domain import score_length                   # noqa: E402
from backend.chapters.names import check as check_names            # noqa: E402

#: `ch01.md`, `ch01.attempt2.md`, `ch01.final.md` — all chapter 1.
CHAPTER_N = re.compile(r"ch0*(\d+)")


# ----------------------------------------------------- the critique's schema
#
# Written from what the runs in `output/` actually wrote, not from what the
# agents' prompts ask for: across 218 critique files there are three top-level
# shapes and the findings carry between four and seven keys. A schema written
# from the prompt would reject eight real runs, which is how a validator gets
# switched off.
#
# So: extras are allowed everywhere, and only the load-bearing fields are
# required. The one that is load-bearing is `quote` — all 89 findings in the
# archive have one, the sheet's rule 3 requires it literally, and a finding
# without it cannot be sent to the writer at all. It would be dropped in silence
# at the exact moment it was needed, which is the failure this validator is for.
#
# They live in this file because nothing can import from `.claude/hooks/` — the
# folder is not a package and the name has a hyphen. If a second consumer
# appears, they move to `backend/chapters/` and this imports them.


class Finding(BaseModel):
    model_config = ConfigDict(extra="allow")
    quote: str = Field(min_length=1)


class Iteration(BaseModel):
    model_config = ConfigDict(extra="allow")
    #: `None` is legitimate: a critic that returned no usable verdict is
    #: recorded as unscored, and `domain.aggregate` excludes it rather than
    #: counting it as a pass. A schema that demanded a number here would push
    #: runs into inventing one.
    score: int | None = Field(default=None, ge=0, le=10)
    findings: list[Finding] = []


class Critique(BaseModel):
    """The usual shape: `{critic, chapter, ..., iterations: [...]}`."""
    model_config = ConfigDict(extra="allow")
    iterations: list[Iteration] = Field(min_length=1)


class Audit(BaseModel):
    """`critiques/outline.audit.json`: the FLOW-3 audit of the commission.

    Written against the ten audit files in `output/`, not against an idea of
    them. Nine say `verdict` and `violations`; the tenth, the oldest, says
    `score` and `findings`. Both are admitted and everything else is extra,
    because this file has never had a schema and refusing the shapes that
    exist would report every run in the repository as malformed.
    """
    model_config = ConfigDict(extra="allow")
    verdict: str | None = None
    violations: list = []
    score: int | None = Field(default=None, ge=0, le=10)
    findings: list[Finding] = []


def validate_critique(raw: object) -> str | None:
    """`None` when it conforms, else what is wrong with it, in one line."""
    try:
        if isinstance(raw, list):
            # A bare array of iterations. Three runs wrote this shape and the
            # archive reads it; refusing it here would report eight historical
            # runs as malformed.
            for item in raw:
                Iteration.model_validate(item)
            return None
        if isinstance(raw, dict):
            if "iterations" in raw:
                Critique.model_validate(raw)
            elif "verdict" in raw or "violations" in raw or "score" in raw:
                Audit.model_validate(raw)
            else:
                return ("no `iterations`, no `verdict`, no `score` — "
                        "no shape this reader knows")
            return None
        return f"a critique must be an object or an array, not {type(raw).__name__}"
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "(root)"
        return f"{where}: {first['msg']}"


# ----------------------------------------------------------------- the hook


def chapter_from_stdin() -> Path | None:
    """The `PostToolUse` event on stdin. See `policy.py` — deliberately the same
    shape, and deliberately duplicated: two standalone scripts in a folder that
    is not a package cannot share a helper without becoming one."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
        path = event.get("tool_input", {}).get("file_path")
    except (ValueError, AttributeError):
        return None
    return Path(path) if path else None


def is_a_chapter(path: Path) -> bool:
    """`<anything>/output/<slug>/chapters/<file>`, and nothing else.

    `.claude/settings.json` matches the **tool**, `Write`, because that is all a
    `PostToolUse` matcher can match. "Under `output/*/chapters/`" is a condition
    this script applies, not one the harness applies for it — otherwise every
    `Write` in the session is measured against a chapter's word band.
    """
    parts = path.resolve().parts
    return len(parts) >= 4 and parts[-2] == "chapters" and parts[-4] == "output"


def check_length(report: dict, run_dir: Path, draft: str) -> None:
    snapshot = run_dir / "config.snapshot.json"
    if not snapshot.is_file():
        report["not_checked"].append(
            f"length — no {snapshot.name} in the run, so the band is unknown")
        return
    config = json.loads(snapshot.read_text(encoding="utf-8"))["novel"]
    band = (config["words_per_chapter"]["min"], config["words_per_chapter"]["max"])
    tolerance = config["tolerance_pct"]

    words = len(draft.split())                       # what `wc -w` counts
    report["checked"].append("length")
    if score_length(words, band, tolerance) == 0:
        report["defects"].append({
            "kind": "length-out-of-band",
            "quote": f"{words} words",
            "claim": (f"{words} words against {band[0]}–{band[1]} widened by "
                      f"{tolerance}% — the `length` characteristic scores this 0"),
        })


def check_canonical_names(report: dict, run_dir: Path, draft: str) -> None:
    characters = run_dir / "bible" / "characters.md"
    if not characters.is_file():
        report["not_checked"].append(
            f"canonical names — no {characters.relative_to(run_dir).as_posix()} "
            f"to compare against")
        return
    report["checked"].append("canonical-names")
    for suspect in check_names(draft, characters.read_text(encoding="utf-8")):
        report["defects"].append({
            "kind": "name-one-letter-out",
            "quote": suspect.written,
            "claim": str(suspect),
        })


def check_critiques(report: dict, run_dir: Path, chapter: Path) -> None:
    match = CHAPTER_N.search(chapter.name)
    if match is None:
        report["not_checked"].append(
            f"critique schema — no chapter number in {chapter.name}")
        return

    n = int(match.group(1))
    files = sorted(run_dir.glob(f"critiques/ch{n:02d}.*.json"))
    audit = run_dir / "critiques" / "outline.audit.json"
    if audit.is_file():
        files.append(audit)
    if not files:
        # Expected on the write of a draft: the critics have not run yet.
        # Still `not_checked` and never `clean` — the difference is the whole
        # of why this key exists.
        report["not_checked"].append(
            f"critique schema — no critique files for chapter {n} yet")
        return

    report["checked"].append("critique-schema")
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            report["defects"].append({
                "kind": "critique-schema",
                "claim": f"{path.name} is not JSON: {error}",
            })
            continue
        problem = validate_critique(raw)
        if problem:
            report["defects"].append({
                "kind": "critique-schema",
                "claim": f"{path.name} does not conform: {problem}",
            })


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    if len(argv) == 2:
        chapter = Path(argv[1])
    elif len(argv) == 1:
        chapter = chapter_from_stdin()
    else:
        print(f"usage: {argv[0]} <chapter.md>", file=sys.stderr)
        return 2

    if chapter is None:
        print("validate-chapter: no file_path in the hook event and none on "
              "the command line", file=sys.stderr)
        return 2
    if not chapter.is_file():
        print(f"validate-chapter: no such file: {chapter}", file=sys.stderr)
        return 2

    if not is_a_chapter(chapter):
        print(json.dumps({"hook": "validate-chapter", "file": str(chapter),
                          "verdict": "skipped",
                          "why": "not under output/<slug>/chapters/"}, indent=2))
        return 0

    run_dir = chapter.resolve().parent.parent
    draft = chapter.read_text(encoding="utf-8")
    report = {
        "hook": "validate-chapter",
        "run": run_dir.name,
        "file": str(chapter),
        "checked": [],
        "not_checked": [],
        "defects": [],
        "verdict": "clean",
    }

    check_length(report, run_dir, draft)
    check_canonical_names(report, run_dir, draft)
    check_critiques(report, run_dir, chapter)

    if report["defects"]:
        report["verdict"] = "defects"
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report["defects"]:
        print(f"validate-chapter: {len(report['defects'])} defect(s) in "
              f"{chapter.name}. Each is quoted; put them in the sheet.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
