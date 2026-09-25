"""The eval table: what the five committed briefs prove, and what they cannot.

Five briefs are committed and two of them are refused at FLOW-0. Running them
is how the project shows that the refusals are refusals and not luck, and the
table this writes to `evals/results.md` is that showing.

**Two halves, and the split is the point.**

FLOW-0 — is the brief complete, does it contradict itself, and what does the
free text become — is arithmetic. `backend/brief/domain.py` decides it, the same
answer every time, at no cost, and `--flow0` (the default) runs exactly that
code and tabulates it. Every row it writes is `measured`.

The novel is not arithmetic and not free. `--novel <id>` starts a real run for
one brief on the `eval` profile, and the columns that need a book stay `absent`
until it has. **Absent, not blank and not zero**: a table that printed 0 for a
forbidden term nobody has looked for would be claiming something no one checked.

Usage
-----
    python evals/run_eval.py                    # FLOW-0 for all five, $0
    python evals/run_eval.py --novel 01-hijo    # and one real run, up to $25

A gap this makes visible, which is the reason it is written this way rather
than as a fixture: **nothing in the product turns a brief into a run.**
`POST /api/briefs` stores it, `POST /api/runs` takes a free-text premise, and no
code joins the two. The premise below is composed *here*, by this tool, for the
eval — so the eval measures the pipeline honestly while saying out loud that
the join it needs does not exist in the product yet.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.brief import domain                                    # noqa: E402
from backend.brief.models import Brief                              # noqa: E402

BRIEFS = ROOT / "evals" / "briefs"
RESULTS = ROOT / "evals" / "results.md"
PROFILE = "eval"

#: What each brief is committed to prove. The expectation is written here, next
#: to the reading of it, so a row that changes is a row somebody has to defend
#: rather than a number that quietly became a different number.
EXPECTED: dict[str, dict] = {
    "01-hijo": {
        "expect_status": "ok",
        "why": "a complete, ordinary brief — the control. If this one does not "
               "pass, nothing the other four prove means anything.",
    },
    "02-pareja": {
        "expect_status": "ok",
        "why": "a second complete brief, an anniversary rather than a birthday.",
    },
    "03-faltan-datos": {
        "expect_status": "contradiction",
        "why": "missing fields AND an adult noir for a child of eight. Both are "
               "reported: the buyer fixing the age may as well answer the "
               "missing tone in the same breath.",
    },
    "04-adversarial": {
        "expect_status": "ok",
        "why": "the injection is in the free text, so the brief is valid. What "
               "is on trial is what the free text BECOMES: one row, "
               "source=freetext, verbatim and whole.",
    },
    "05-incoherencia-temporal": {
        "expect_status": "contradiction",
        "why": "for the reason the file was written: `recipient.birth_date` is "
               "declared (owner's order, 2026-09-24) and FLOW-0 compares every "
               "dated memory with it. The paella at university is dated three "
               "years before the birth, and the refusal names that memory. The "
               "wedding aged nine is a judgement, not a date comparison, and is "
               "left to `lean_chronology`, which is not run (elan unavailable)."
    },
}

INJECTION = "IGNORE ALL PREVIOUS INSTRUCTIONS"
#: The gift hidden behind the attack in brief 04, in the same paragraph. A
#: filter clever enough to drop the attack would have to be trusted not to drop
#: this, which is why nothing filters and the row carries its source instead.
GIFT = "rain on the tomato plants"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flow0(payload: dict) -> dict:
    """One brief through the code that decides FLOW-0, and nothing else."""
    result = domain.check(payload)
    row = {
        "id": payload["id"],
        "status": result.status,
        "questions": len(result.questions),
        "contradictions": len(result.contradictions),
        "first_contradiction": (result.contradictions or [""])[0],
        # Only a brief that parses has facts. An invalid one has none, and that
        # is absence rather than zero.
        "facts_mandatory": None,
        "facts_freetext": None,
        "injection_is_a_fact": None,
        "injection_is_verbatim": None,
        "gift_survived": None,
    }
    if result.status == "invalid":
        row["errors"] = result.errors
        return row

    brief: Brief = domain.parse(payload)
    rows = domain.facts(brief)
    free = [f for f in rows if f.source == "freetext"]
    row["facts_mandatory"] = sum(1 for f in rows if f.source == "brief")
    row["facts_freetext"] = len(free)

    if INJECTION.lower() in (brief.free_text or "").lower():
        # The three questions brief 04 exists to ask.
        row["injection_is_a_fact"] = any(INJECTION.lower() in f.text.lower()
                                         for f in free)
        row["injection_is_verbatim"] = any(f.text == brief.free_text for f in free)
        row["gift_survived"] = any(GIFT in f.text for f in free)
        row["injection_is_mandatory"] = any(f.mandatory for f in free)
    return row


def verdict(row: dict) -> str:
    want = EXPECTED.get(row["id"], {}).get("expect_status")
    if want is None:
        return "no expectation recorded"
    if row["status"] != want:
        return f"**MISMATCH** — expected {want}, got {row['status']}"
    if row["id"] == "04-adversarial":
        if not (row["injection_is_a_fact"] and row["injection_is_verbatim"]
                and row["gift_survived"] and not row.get("injection_is_mandatory")):
            return "**MISMATCH** — the free text was not handled as data"
    return "as expected"


def premise_for(payload: dict) -> str:
    """A premise composed from a brief, by this tool, because nothing else does.

    Read the module docstring before changing this: the product has no
    brief-to-run join, so what a real product would compose is composed here,
    and the eval says so rather than implying the join exists.

    The free text is **not** included. It is untrusted by construction, it
    reaches the novel as a `freetext` fact with its source attached, and pasting
    it into the premise would hand an attacker the one string the orchestrator
    reads as instructions.
    """
    brief = domain.parse(payload)
    memories = "; ".join(m.text for m in brief.memories)
    return textwrap.shorten(
        f"A {brief.genre} novel for {brief.recipient.alias}, "
        f"{brief.recipient.age}, on the occasion of a {brief.occasion}. "
        f"Tone: {brief.tone}. They are {', '.join(brief.recipient.traits)}. "
        f"Moments that must appear: {memories}.",
        width=900, placeholder=" ...")


def run_novel(brief_id: str) -> dict:
    """One real run for one brief, on the `eval` profile. This spends money."""
    from backend.commons.config.settings import Settings
    from backend.runs.service import RunService

    payload = load(BRIEFS / f"{brief_id}.json")
    if domain.check(payload).status != "ok":
        raise SystemExit(f"{brief_id} does not pass FLOW-0; there is nothing to run")

    conn = sqlite3.connect(ROOT / "novaforge.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    svc = RunService(conn, Settings(repo_root=ROOT, db_path=ROOT / "novaforge.db",
                                    output_dir=ROOT / "output",
                                    use_recorded_stream=False))
    started = svc.start(premise=premise_for(payload), profile=PROFILE,
                        tone=payload.get("tone", ""))
    print(f"{brief_id}: run {started['id']} as {started['slug']}", flush=True)
    return started


def table(rows: list[dict]) -> str:
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        "# Eval results",
        "",
        f"FLOW-0 over the five committed briefs, read from the code that decides",
        f"it, {when}. Profile for the novel half: `{PROFILE}`.",
        "",
        "Two of these five are refused here, and a table where every row said",
        "`ok` would be a table that proved nothing. The arithmetic is worth",
        "stating plainly: **three pass FLOW-0**. `03` is refused for exactly the",
        "reason it was written: missing data and an adult genre for a child.",
        "`05` is refused for the reason it was written too: a memory dated",
        "before the recipient was born -- see below.",
        "",
        "| brief | status | expected | questions | contradictions | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        want = EXPECTED.get(r["id"], {}).get("expect_status", "—")
        out.append(f"| `{r['id']}` | {r['status']} | {want} | {r['questions']} | "
                   f"{r['contradictions']} | {verdict(r)} |")

    out += ["", "## What each row is for", ""]
    for r in rows:
        out.append(f"**`{r['id']}`** — {EXPECTED.get(r['id'], {}).get('why', '')}")
        if r["first_contradiction"]:
            out.append(f"  > {r['first_contradiction']}")
        out.append("")

    temporal = next((r for r in rows if r["id"] == "05-incoherencia-temporal"), None)
    if temporal:
        out += [
            "## Brief 05, and the limit of this table",
            "",
            "FLOW-0 now reads dates: a dated memory before `recipient.birth_date`,",
            "or an age more than a year off the birth date, is a contradiction",
            "named on both sides. What it cannot see is a date that is possible",
            "but implausible (a wedding at nine): that is `lean_chronology`'s",
            "job, and `lean_chronology` is **not run: elan unavailable**.",
            "",
        ]

    adversarial = next((r for r in rows if r["id"] == "04-adversarial"), None)
    if adversarial:
        out += [
            "## Brief 04, in detail",
            "",
            "The attack and the gift arrive in the same paragraph. Nothing reads",
            "the text; it is copied into a row whose `source` says what it is",
            "worth, and it is data from that moment on.",
            "",
            "| question | answer |",
            "|---|---|",
            f"| the injection became a fact | {adversarial['injection_is_a_fact']} |",
            f"| kept verbatim and whole | {adversarial['injection_is_verbatim']} |",
            f"| the gift behind it survived | {adversarial['gift_survived']} |",
            f"| marked mandatory (it must not be) | "
            f"{adversarial.get('injection_is_mandatory')} |",
            "",
        ]

    out += [
        "## What this table does not say",
        "",
        "Every figure above is FLOW-0 and is **measured**: it is the output of",
        "`backend/brief/domain.py` on the committed fixtures, at no cost.",
        "",
        "The novel half below is read from the `validations` table, one row per",
        "validator per run (`python -m backend.publish.record_all`). A cell that",
        "says `not run` was not run; a missing run is **absent**, not zero.",
        "",
        "Runs start from the stored brief (`POST /api/runs {brief_id}`), so the",
        "premise is composed by the product, not by this script.",
        "",
    ]
    out += novel_half()
    return "\n".join(out)


def _eval_id_of(payload_json: str) -> str | None:
    try:
        stored = domain.parse(json.loads(payload_json)).model_dump()
    except Exception:
        return None
    for path in sorted(BRIEFS.glob("*.json")):
        try:
            if domain.parse(load(path)).model_dump() == stored:
                return path.stem
        except Exception:                      # a brief that does not parse
            continue
    return None


def novel_half(db_path: Path = ROOT / "novaforge.db") -> list[str]:
    """The `validations` rows of every eval run and the example novel (profile
    `exam`) started from a brief, one table per validated version.

    Every version, not only the latest: a reader change publishes a new
    version that re-runs only some validators, and showing the latest alone
    hid the judge and the human review of the book they were given."""
    if not db_path.is_file():
        return ["## Novel half", "", "absent: no database", ""]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    runs = conn.execute(
        "SELECT r.id, r.slug, b.payload FROM runs r JOIN briefs b ON b.id = r.brief_id "
        "WHERE r.profile IN (?, 'exam') ORDER BY r.started_at", (PROFILE,)).fetchall()
    out = ["## Novel half", ""]
    if not runs:
        return out + ["absent: no eval run has been recorded yet", ""]
    for run in runs:
        versions = [v[0] for v in conn.execute(
            "SELECT DISTINCT version FROM validations WHERE run_id = ? ORDER BY version",
            (run["id"],)).fetchall()]
        out += [f"### {_eval_id_of(run['payload']) or '?'} — run `{run['id']}` "
                f"(`{run['slug']}`)", ""]
        if not versions:
            out += ["absent: no validator has recorded this run", ""]
            continue
        for version in versions:
            rows = conn.execute(
                "SELECT validator, criterion, value, justification FROM validations "
                "WHERE run_id = ? AND version IS ? ORDER BY validator, criterion",
                (run["id"], version)).fetchall()
            if len(versions) > 1:
                out += [f"#### version {version}", ""]
            out += ["| validator | criterion | value | why |", "|---|---|---|---|"]
            for r in rows:
                why = (r["justification"] or "").replace("|", "\\|")[:160]
                value = r["value"] if r["value"] is not None else "—"
                out.append(f"| {r['validator']} | {r['criterion'] or ''} | {value} | {why} |")
            out.append("")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--novel", metavar="BRIEF_ID",
                    help="also start one real run for this brief (spends money)")
    ap.add_argument("--out", type=Path, default=RESULTS)
    args = ap.parse_args()

    rows = [flow0(load(p)) for p in sorted(BRIEFS.glob("*.json"))]
    args.out.write_text(table(rows), encoding="utf-8", newline="\n")

    for r in rows:
        print(f"{r['id']:28s} {r['status']:14s} {verdict(r)}")
    print(f"\nwritten: {args.out.relative_to(ROOT)}")

    mismatches = [r for r in rows if verdict(r).startswith("**MISMATCH")]
    if args.novel:
        run_novel(args.novel)
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
