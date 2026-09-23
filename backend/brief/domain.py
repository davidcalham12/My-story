"""The two decisions FLOW-0 makes, in code rather than in the agent.

AGENTS.md §5: *before proposing an agent for a task, say why a script will not
do*. Here one does. "Which fields are still missing" is a set difference and
"is this tone wrong for this age" is a comparison against a list — both are
arithmetic, both are the same answer every time they are asked, and both are
the difference between class **T** and class **D** in `verification.md`.

So the `interviewer` agent reads what the buyer wrote, fills the fields it can
and asks the questions this module hands it. It never concludes that a brief is
complete, and it never decides that an eight-year-old can have a noir: it cannot
even see those rules.

The third thing that happens here is `facts()`. Free text is the only field the
buyer writes freely, so it is the only field an attacker controls; brief 04 puts
"IGNORE ALL PREVIOUS INSTRUCTIONS" in it. It leaves this module as a row with
`source = "freetext"` and as nothing else (SPEC-EXAM-001 AC-2).
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.brief.models import Brief, Fact

#: Where the five committed briefs live. They are the contract for this phase:
#: 01, 02 and 04 must pass, 03 is the missing-data case, 05 the temporal one.
EXAMPLES = Path(__file__).resolve().parents[2] / "evals" / "briefs"

#: Keys the eval files carry that are *about* a brief rather than part of one.
#: They are the fixture's envelope — an id to name the row in `evals/results.md`
#: and a sentence saying what the brief is for — and a `Brief` that accepted
#: them would be a `Brief` with two fields no buyer ever fills.
ENVELOPE = ("id", "purpose")

#: What FLOW-0 will not start without, and the question to ask when it is
#: missing. A question and not an error code: the buyer who left the tone blank
#: is mid-conversation, and the interviewer reads these out loud.
REQUIRED: dict[str, str] = {
    "occasion": "What is the occasion — a birthday, an anniversary, a retirement?",
    "recipient.alias": "What should the novel call the person it is for?",
    "recipient.age": "How old is the recipient? Their age decides what the book may contain.",
    "recipient.relationship_to_buyer": "What is this person to you — a son, a wife, a father?",
    "genre": "What kind of story should this be?",
    "tone": "What tone should it have — warm, funny, tender, sharp?",
    "memories": "Tell us at least one real memory: a place, a moment, a pet, a joke.",
    "length_chapters": "How many chapters should the novel have?",
}

#: A brief is for a child below this age. Thirteen, and it is the number the
#: exam's contradiction case is written around (brief 03, a niece of eight).
CHILD_UNDER = 13

#: Normalised markers of a book an adult reads and a child does not. The three
#: the spec names — `novela negra adulta`, `erótico`, `thriller violento` — plus
#: the English each arrives in: brief 03 says "adult noir thriller" and a rule
#: that only reads Spanish would let it through. Matched as substrings so the
#: word survives whatever the buyer wrapped it in.
ADULT_MARKERS = (
    "adult",            # also "adulta", "adulto", "novela negra adulta"
    "erotic",           # also "erótico" once the accent is stripped
    "noir",
    "novela negra",
    "thriller violento",
    "violent thriller",
    "gore",
)

#: Where an adult marker is looked for. Genre and tone both carry it in the
#: wild: the exam's AC-1 says "an adult tone", brief 03 puts it in the genre,
#: and a rule that read only the field the spec sentence names would pass the
#: one brief written to fail.
ADULT_FIELDS = ("tone", "genre")

Status = Literal["ok", "incomplete", "contradiction", "invalid"]


class CheckResult(BaseModel):
    """What FLOW-0 tells the buyer before anything is spent.

    `status` is the one word the frontend enables or disables *Write it* on.
    The three lists are always present and usually empty — a brief can be both
    incomplete and contradictory (brief 03 is) and losing one of those to the
    other would send the buyer round twice.
    """

    model_config = ConfigDict(extra="forbid")

    status: Status
    questions: list[str] = []
    contradictions: list[str] = []
    #: Only for `invalid`: the schema's own complaints, one per offending key.
    errors: list[str] = []


def normalise(text: str) -> str:
    """casefold, then strip the accents NFKD separates.

    `Erótico` and `erotico` are the same word to everyone except a string
    comparison, and the buyer types whichever their keyboard offers.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def parse(payload: dict) -> Brief:
    """A `Brief` from a raw body, with the fixture envelope dropped.

    Raises `ValidationError` for anything else unknown — that is the point of
    `extra="forbid"`, and `check()` is the caller that turns it into a sentence.
    """
    return Brief(**{k: v for k, v in payload.items() if k not in ENVELOPE})


def _present(brief: Brief, field: str) -> bool:
    """Whether a required field has been answered.

    An empty list is not an answer. `memories: []` is the shape brief 03 arrives
    in, and a brief with no memory is a novel about nobody; the emptiness has to
    reach the buyer as a question rather than pass as a filled field.
    """
    target: object = brief
    for part in field.split("."):
        target = getattr(target, part)
    if isinstance(target, (list, str)):
        return len(target) > 0
    return target is not None


def _contradictions(brief: Brief) -> list[str]:
    """The age/tone pair, named on both sides.

    "This brief is contradictory" is useless to the person who has to fix it, so
    the message carries the age and the field that fought with it. The buyer
    then knows which of the two to change, which is the whole decision.

    An unknown age contradicts nothing: absent is never zero, and a `None` age
    read as `0` would make every half-filled brief for an adult look like a
    crime against a newborn.
    """
    age = brief.recipient.age
    if age is None or age >= CHILD_UNDER:
        return []
    found = []
    for field in ADULT_FIELDS:
        value = getattr(brief, field)
        if value and any(marker in normalise(value) for marker in ADULT_MARKERS):
            found.append(
                f"recipient.age is {age} and {field} is {value!r}: "
                f"a reader under {CHILD_UNDER} and a book written for an adult. "
                f"Raise the age or change the {field}."
            )
    return found


def check(payload: dict) -> CheckResult:
    """FLOW-0's verdict on a brief, before a token is spent.

    Precedence, and it is a decision rather than an accident: a brief that does
    not fit the schema is `invalid` (nothing else can be trusted about it); one
    that fits and contradicts itself is `contradiction`, **with its questions
    still attached**, because the buyer fixing the age may as well answer the
    missing tone in the same breath; one that only lacks fields is `incomplete`.
    """
    try:
        brief = parse(payload)
    except ValidationError as exc:
        return CheckResult(
            status="invalid",
            errors=[f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                    for e in exc.errors()],
        )

    questions = [question for field, question in REQUIRED.items()
                 if not _present(brief, field)]
    contradictions = _contradictions(brief)
    status: Status = ("contradiction" if contradictions
                      else "incomplete" if questions else "ok")
    return CheckResult(status=status, questions=questions,
                       contradictions=contradictions)


def facts(brief: Brief) -> list[Fact]:
    """The brief as rows, each carrying how much it is to be trusted.

    Two sources, and they are never merged:

    - `source="brief"`: what the buyer typed into `mandatory_facts`. Promises.
      The publish gate checks every one of them appears in the novel.
    - `source="freetext"`: what the buyer typed into the free box, kept verbatim
      and kept *whole*. It is a lead for a human, never a promise, and never an
      instruction.

    Whole, because the attack and the gift arrive in the same paragraph: brief
    04 hides "he loves the smell of rain on the tomato plants" behind "IGNORE
    ALL PREVIOUS INSTRUCTIONS", and a filter clever enough to drop the second
    would have to be trusted not to drop the first. Nothing here reads the text;
    it is copied into a row whose `source` says what it is worth, and the row is
    data from that moment on.
    """
    rows = [Fact(text=text, kind="mandatory", source="brief", mandatory=True)
            for text in brief.mandatory_facts]
    if brief.free_text.strip():
        # Not split, not summarised, not paraphrased — a fact about nothing is
        # what an empty box would otherwise produce, and a paraphrase is a model
        # reading the untrusted string, which is the one thing AC-2 forbids.
        rows.append(Fact(text=brief.free_text, kind="freetext",
                         source="freetext", mandatory=False))
    return rows


def examples() -> list[dict]:
    """The five committed briefs, envelope and all.

    Served raw rather than as `Brief` objects: `GET /api/briefs/examples` exists
    so the panel can offer them for a demo, and three of the five are committed
    precisely because they do *not* pass. A reader that validated them could not
    show the ones that matter.
    """
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(EXAMPLES.glob("*.json"))]
