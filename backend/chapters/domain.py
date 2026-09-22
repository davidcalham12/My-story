"""The gate. Pure functions over values; the standard library and nothing else.

That constraint is the point. In v1 these rules were entangled with network
calls, so the only way to exercise them was to write a novel — which is why
three of them were wrong for months without anyone noticing. Here they are
arithmetic over data and a test costs a millisecond.

Every rule below was arrived at by a run that went wrong. The docstrings say
which, because a rule whose reason is lost is a rule somebody eventually
"simplifies".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: SPEC-006 added `prose`. Six, not five — and `AGENTS.md` §6 means this tuple
#: does not change again without another spec that names it.
CHARACTERISTICS = ("continuity", "science", "outline", "length", "chatter", "prose")
THRESHOLD_DEFAULT = 8

#: Three attempts, and the third is the last. `AGENTS.md` §6 lists it among the
#: things no change may touch without a spec that names it — which is an argument
#: for it having exactly one home. It was a bare `3` in three function
#: signatures, the same shape as the threshold that turned out to be written in
#: four places.
MAX_ATTEMPTS_DEFAULT = 3

# The sheet's field labels. In one place because the builder writes them and the
# validator looks for them, and two copies of a format drift.
FIELDS = ("Quote:", "What is wrong:", "Against what:", "How it should read:")
REPLACEMENT = "Replacement:"
LABELS = {
    "continuity": "Continuity",
    "science": "Science",
    "outline": "Outline",
    "length": "Length",
    "chatter": "Heading",
    "prose": "Prose",
}


# --------------------------------------------------------------- aggregation


@dataclass(frozen=True)
class Verdict:
    aggregate: int | None
    passed: bool
    worst: list[str]
    unscored: list[str]
    note: str


def aggregate(scores: dict[str, int | None], threshold: int = THRESHOLD_DEFAULT) -> Verdict:
    """`min` over the characteristics that produced a usable verdict.

    Two rules meet here, and both were learned the hard way.

    **A chapter is worth what its worst characteristic is worth.** An average
    would let four tens carry a four, and a four is a defect a reader meets.

    **A characteristic with no usable verdict is EXCLUDED, never counted as a
    pass.** This once returned 10, which meant a malformed critic reply silently
    passed a draft — the one failure a quality gate must not have. There is no
    honest substitute: 10 invents an approval and 0 invents a rejection. So it
    leaves the minimum, is recorded as unscored, and the chapter does not pass on
    a partial gate: four critics is a weaker gate, not a passing one.
    """
    unscored = sorted(k for k, v in scores.items() if v is None)
    scored = {k: v for k, v in scores.items() if v is not None}

    if not scored:
        return Verdict(None, False, [], unscored,
                       "no characteristic produced a usable verdict")

    lowest = min(scored.values())
    worst = sorted(k for k, v in scored.items() if v == lowest)
    complete = len(scored) == len(CHARACTERISTICS)
    passed = complete and lowest >= threshold

    if unscored:
        note = (f"{' and '.join(unscored)} returned no usable verdict and was "
                f"excluded from the minimum; a gate running on "
                f"{len(scored)} characteristics is weaker than one running on "
                f"{len(CHARACTERISTICS)}")
    else:
        note = f"min {lowest} against threshold {threshold}"

    return Verdict(lowest, passed, worst, unscored, note)


# ------------------------------------------------- the two arithmetic critics


def score_length(words: int, band: tuple[int, int], tolerance_pct: int) -> int:
    """In the band, widened by the tolerance, or not. Nothing in between.

    Arithmetic, so it reproduces: the same draft scores the same every run, which
    is what separates these two characteristics from the three that are models.
    """
    low, high = band
    widened_low = round(low * (1 - tolerance_pct / 100))
    widened_high = round(high * (1 + tolerance_pct / 100))
    return 10 if widened_low <= words <= widened_high else 0


def score_chatter(draft: str) -> int:
    """Zero unless the first line opens the chapter.

    Not a craft rubric's idea of a defect, which is why no ontology names it: it
    exists because a generated draft that begins "Here is the chapter you asked
    for" is a failure mode no rubric anticipates.
    """
    first = draft.lstrip().split("\n", 1)[0] if draft.strip() else ""
    return 10 if re.match(r"^#\s+Chapter\b", first) else 0


def score_prose(*, mechanical: int, major: int, minor: int) -> int:
    """SPEC-006. `10 − 3·mechanical − 2·major − 1·minor`, floored at 0.

    The shape of `score_outline`, and for the same reason: **a score a model
    picks freely is a number nobody can check.** The critic finds defects and
    quotes them; the arithmetic is here, so the orchestrator can recompute the
    sum against the findings the way it already does for `outline`.

    `mechanical` costs the most because it is the only term that is certain. A
    repeated sentence is equality — there is no argument to have about it —
    while a *major* defect is one model's reading of a paragraph. Weighting the
    judged terms above the counted one would be backwards.

    It comes from `backend/chapters/prose.py`, never from the critic. A critic
    asked to count what a script already counted will disagree with it, and then
    the score depends on which of the two was asked.
    """
    return max(0, 10 - 3 * mechanical - 2 * major - 1 * minor)


def score_outline(missing: int, out_of_order: int) -> int:
    """`10 − 3·missing − 1·out_of_order`, floor 0.

    A missing beat costs more than a misplaced one because it is a harder repair:
    a misplaced beat is a move, a missing one is a paragraph. That asymmetry is
    also why `outline` is the weakest link in the third-attempt guarantee.
    """
    return max(0, 10 - 3 * missing - 1 * out_of_order)


# ------------------------------------------------------------------ patching


@dataclass(frozen=True)
class PatchResult:
    text: str
    applied: int
    skipped: list[str]

    @property
    def nothing_applied(self) -> bool:
        """The caller's cue to fall back to a full rewrite rather than burn the
        attempt on nothing."""
        return self.applied == 0


def apply_patches(draft: str, patches: list[dict]) -> PatchResult:
    """Substitutions, matched literally, applied by the orchestrator.

    Asking for the whole chapter back "with these fixed and nothing else" relies
    on the writer's restraint, and a model handed a whole chapter tends to
    improve it. Asking instead for the exact sentences makes over-rewriting
    impossible: **anything no finding names cannot change, because nothing
    touches it.**

    A `find` that does not match is skipped and counted, **never applied
    approximately**. An approximation does something nobody asked for, which is
    worse than doing nothing.
    """
    text = draft
    applied = 0
    skipped: list[str] = []
    for patch in patches:
        find = patch.get("find")
        replace = patch.get("replace")
        if not find or replace is None:
            continue
        if find in text:
            text = text.replace(find, replace, 1)
            applied += 1
        else:
            skipped.append(find)
    return PatchResult(text, applied, skipped)


# -------------------------------------------------------------- the attempts


@dataclass(frozen=True)
class AttemptResult:
    attempt: int
    aggregate: int | None
    passed: bool


def best_of(attempts: list[AttemptResult]) -> AttemptResult:
    """The highest aggregate, not the last.

    A chapter whose first attempt scored 7 and whose third scored 4 must ship the
    7. A rewrite is not guaranteed to be an improvement and the gate must not
    assume it was. Ties go to the earlier attempt: it is the one that cost less.
    """
    return min(attempts, key=lambda a: (-(a.aggregate or -1), a.attempt))


def accepted_of(attempts: list[AttemptResult]) -> AttemptResult | None:
    """The attempt that passed. Not always the best one, and not the same
    question."""
    for a in attempts:
        if a.passed:
            return a
    return None


# ------------------------------------------------------- what happens next


@dataclass(frozen=True)
class Decision:
    #: accept | retry | patch | halt
    action: str
    #: what the `attempts` row should record, when the action is `accept`
    verdict: str
    why: str


def decide(*, aggregate: int | None, attempt: int,
           max_attempts: int = MAX_ATTEMPTS_DEFAULT,
           patched: bool = False, threshold: int = THRESHOLD_DEFAULT) -> Decision:
    """What follows an attempt. SPEC-004.

    **This was a paragraph in `SKILL.md`** and is now arithmetic, for the reason
    every other check moved: a rule a model reads is a rule a model can reason
    around, and this one is read at the worst possible moment — when a run has
    spent an hour and is about to be thrown away. `accept_with_warnings`, the
    exit `patch_then_halt` replaced, is what reasoning around it looks like when
    it wins.

    The order is the whole rule, and `patch_then_halt` is two words in that
    order:

    1. **At or above the threshold: accept.** Whatever the attempt number, and
       recorded as `patched` when the patch is what got it there — it passed, and
       it did not pass on its own, and a reader is entitled to both facts.
    2. **Below, with attempts left: retry**, with the escalated sheet.
    3. **Below, on the last attempt: patch.** Never accept. The critics' own
       literal replacements, arbitrated, then a rescore.
    4. **Below, after the patch: halt.** By construction the only way to arrive
       here is a replacement that was itself wrong and that arbitration did not
       catch, and that is worth a person before another chapter is written.

    `aggregate is None` means no characteristic produced a usable verdict. It is
    **not a low score**, it is the absence of one, and it can never accept: this
    returned 10 once and a malformed reply silently passed a draft.
    """
    if aggregate is not None and aggregate >= threshold:
        return Decision(
            "accept",
            "patched" if patched else "accept",
            f"aggregate {aggregate} at or above threshold {threshold}"
            + (", reached with the patch applied" if patched else ""),
        )

    shown = "no usable verdict" if aggregate is None else f"aggregate {aggregate}"

    if patched:
        return Decision(
            "halt", "halt",
            f"{shown} after the patch was applied: a critic's replacement was "
            f"itself wrong and arbitration did not catch it, so the run stops "
            f"rather than putting the chapter in the book",
        )

    if attempt >= max_attempts:
        return Decision(
            "patch", "retry",
            f"{shown} on attempt {attempt} of {max_attempts}: apply the critics' "
            f"literal replacements, arbitrate each first, then rescore",
        )

    return Decision(
        "retry", "retry",
        f"{shown} below threshold {threshold} on attempt {attempt} of "
        f"{max_attempts}: redraft against a level-"
        f"{2 if attempt + 1 >= max_attempts else 1} sheet",
    )


def mark_late(findings: list[dict], first_draft: str, seen_quotes: set[str]) -> list[dict]:
    """Flag findings that were available on the first draft and went unmentioned.

    A critic that raises on attempt 3 something equally present in attempt 1 is
    moving the goalposts. **Without this rule the third-attempt guarantee does
    not exist**, because something new can always appear.

    Marked, recorded, patched where possible — and never blocking.
    """
    out = []
    for finding in findings:
        quote = (finding.get("quote") or "").strip()
        late = bool(
            quote
            and len(quote) > 12
            and quote not in seen_quotes
            and quote in first_draft
        )
        out.append({**finding, "late": late})
    return out


def blocking(findings: list[dict]) -> list[dict]:
    """The findings that hold a chapter back. Late ones do not."""
    return [f for f in findings if not f.get("late")]


# ----------------------------------------------------------------- the sheet


@dataclass(frozen=True)
class SheetReport:
    ok: bool
    problems: list[str] = field(default_factory=list)


def build_sheet(
    *,
    chapter: int,
    attempt: int,
    level: int,
    scores: dict[str, int | None],
    findings: list[dict],
    resolved: list[str],
    threshold: int = THRESHOLD_DEFAULT,
) -> str:
    """The sheet the writer receives after a failed attempt.

    Five rules, each of which is also in the validator, because a format checked
    only where it is written is a format that drifts where it is read.

    Findings are ordered worst first and **none is trimmed**: one held back to
    keep the sheet short is one that fails again next attempt.
    """
    line = " · ".join(
        f"{LABELS[k]} {scores.get(k) if scores.get(k) is not None else '—'}"
        for k in CHARACTERISTICS
    )
    values = [v for v in scores.values() if v is not None]
    lowest = min(values) if values else "—"
    passing = [LABELS[k] for k in CHARACTERISTICS
               if (scores.get(k) or 0) >= threshold]

    rank = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(findings, key=lambda f: rank.get(f.get("severity", "medium"), 1))

    out = [
        f"CHAPTER {chapter} — ATTEMPT {attempt} OF 3",
        "",
        "SCORES FROM THE PREVIOUS ATTEMPT",
        f"  {line}",
        f"  The lowest is {lowest}. All five must reach {threshold}.",
        "",
        "DO NOT TOUCH — these passed, and changing them can only cost you:",
        "  " + (" · ".join(passing) if passing else "(nothing passed)"),
        "",
        f"OPEN ({len(ordered)} findings, worst first)",
    ]
    for i, f in enumerate(ordered, 1):
        # A missing field is OMITTED, never emitted empty.
        #
        # The first version wrote `Quote: ""` when a finding had no quote, which
        # meant the label was present and the validator waved it through - the
        # builder papering over the very gap the validator exists to catch. An
        # incomplete finding has to produce an incomplete sheet, or the gate on
        # the instrument is decorative.
        out.append(f"  {i}. [{f.get('severity', 'medium')}] {f.get('characteristic', '?')}")
        if f.get("quote"):
            out.append(f"     Quote:        \"{f['quote']}\"")
        if f.get("claim"):
            out.append(f"     What is wrong: {f['claim']}")
        if f.get("reference"):
            out.append(f"     Against what:  {f['reference']}")
        if f.get("fix"):
            out.append(f"     How it should read: {f['fix']}")
        if f.get("replacement"):
            out.append(f"     {REPLACEMENT}   \"{f['replacement']}\"")
    out += [
        "",
        "RESOLVED since the last attempt:",
        "  " + ("; ".join(resolved) if resolved
               else "(none — this is the first correction)"),
        "",
        "RULE: change only the lines quoted above. The orchestrator counts the "
        "lines you touched against the lines it cited.",
    ]
    return "\n".join(out)


def validate_sheet(sheet: str, level: int) -> SheetReport:
    """A gate on the instrument. **An incomplete sheet is not sent.**

    The loop's claim is that each failed attempt makes the next one *easier*, and
    that rests entirely on the sheet being complete. A sheet missing its quote
    does not degrade the redraft a little — it returns the writer to guessing,
    which is the state attempt 1 was already in.
    """
    problems: list[str] = []

    if not re.search(r"CHAPTER\s+\d+\s+—\s+ATTEMPT\s+[123]\s+OF\s+3", sheet):
        problems.append('no "CHAPTER n — ATTEMPT k OF 3" header')

    for block in ("SCORES FROM THE PREVIOUS ATTEMPT", "DO NOT TOUCH", "OPEN",
                  "RESOLVED", "RULE:"):
        if block not in sheet:
            problems.append(f"missing block: {block}")

    # Rule 1 — all five scores, including the passing ones. The writer has to
    # know what is right in order to leave it alone.
    for label in LABELS.values():
        if not re.search(rf"{label}\s+(\d+|—)", sheet):
            problems.append(f"score not shown for: {label}")

    items = re.split(r"\n\s{2}\d+\.\s", sheet)[1:]
    if not items:
        problems.append("no findings — a sheet is only sent when something failed")

    for i, item in enumerate(items, 1):
        for label in FIELDS:
            if label not in item:
                problems.append(f'finding {i}: missing "{label}"')
        quote = re.search(r'Quote:\s*"([^"]*)"', item)
        if quote is not None and len(quote.group(1).strip()) < 8:
            problems.append(f'finding {i}: "Quote:" is too short to be literal')
        # Rule 3 — "Against what" points at the Bible or the outline, NEVER at a
        # previous chapter. The writer has never seen one and this sheet is not
        # the hole through which it finally does.
        against = re.search(r"Against what:\s*(.+)", item)
        if against and re.search(r"\bch(apter)?\s*\d|ch\d{2}\.md", against.group(1), re.I):
            problems.append(
                f"finding {i}: cites a previous chapter, not the Bible or the outline"
            )
        has_replacement = REPLACEMENT in item
        if level == 2 and not has_replacement:
            problems.append(f"finding {i}: attempt 3 needs a literal replacement")
        if level == 1 and has_replacement:
            problems.append(
                f"finding {i}: a literal replacement is attempt 3's escalation, not this one"
            )

    if re.search(r"\{[a-z][^}\n]*\}", sheet, re.I):
        problems.append("template slot left unfilled")

    return SheetReport(ok=not problems, problems=problems)
