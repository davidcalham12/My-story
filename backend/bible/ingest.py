"""The Markdown Bible, read into the tables — PLAN-001-exam E3.

    python -m backend.bible.ingest output/<slug>

**Nothing new is written by a model here.** `worldbuilder` and
`character-architect` already write `bible/world.md`, `characters.md`,
`timeline.md` and `mysteries.md`, and those files are what the chapter writer
and the four critics are given. This reads exactly those files. Asking an agent
to emit the same content a second time as JSON would be a second source of truth
for the canon, and the two would disagree by chapter three — which is the
failure the Bible exists to prevent.

So this is a parser, and a parser is class **T** (AGENTS.md §5). What it costs
is precision: the Bible is prose written by a model, and prose has no schema.
Each extraction below says what it will miss.

Run at FLOW-2, after the Bible is written and before the first chapter is
drafted, and again after any correction to it — ingesting twice is safe and
changes nothing but the rows it re-reads.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.bible.domain import rules_bullets
from backend.commons.db.connection import tx

#: `- **Ada Rowe** — keeper of the Corbie Light, eleven years on the post`
#:
#: The same shape `chapters/names.py` reads canonical names from, and the same
#: shape `bible.domain.canonical_names` reads. A character written without the
#: bold is invisible to all three, which is why FLOW-2 checks the count.
CHARACTER = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*[—–-]\s*(.*)$", re.M)

#: `- **Whose hand wrote the *Marigold* on page 91?**`, with its sub-bullets.
MYSTERY = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*$", re.M)

#: The sub-bullet that holds the answer. `Planted:` and `Lands:` are staging —
#: where the mystery is shown — and are not facts about the world.
TRUE_LINE = re.compile(r"^\s+[-*]\s*\*{0,2}True\*{0,2}\s*:\s*(.+)$", re.M | re.I)

#: A Markdown table row. Every timeline in `output/` is a table; the number of
#: columns is not fixed (`| When | What |`, `| Day | What happens | Who knows |`)
#: so only the first two are given a meaning.
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$", re.M)
SEPARATOR = re.compile(r"^[\s|:-]+$")

#: `(Chapter 2)` beside a present-day timeline row.
PINNED_TO_CHAPTER = re.compile(r"\(\s*chapter\s+(\d+)\s*\)", re.I)

#: `born 3 March 1961`, `Born: 1961-03-03`. Absent in every Bible written so
#: far; the personalised novels of `docs/spec.md` carry one, and the Lean age
#: invariant can only be exported for the characters that have it.
BORN = re.compile(r"\bborn\s*:?\s*(?:on\s+)?([^;,.\n]+)", re.I)

#: A run of capitalised words, joined across the small words a place name keeps
#: — `Register of Passage`, `Nether Scarrow`.
PROPER_NOUN = re.compile(
    r"\b[A-Z][a-z]+(?:\s+(?:of|the|on|at|in)\s+[A-Z][a-z]+|\s+[A-Z][a-z]+)*")

#: Everything before this match was a sentence ending, so the capital that
#: follows says nothing about whether the word is a name.
SENTENCE_START = re.compile(r"(?:^|[.!?:]\s+|\n)\s*$")


class UnknownRun(Exception):
    """The run has no row. Ingesting anyway would leave orphan facts that no
    endpoint can reach and no reader change can find."""


@dataclass(frozen=True)
class IngestReport:
    """What the Bible **now holds**, not what this pass happened to insert.

    Ingest is re-run after a correction to `characters.md`, and a report that
    counted inserts would print zeros on the second run and read as a failure.
    """
    run_id: str
    facts: int
    characters: int
    places: int
    chronology: int
    participants: int


def _read(run_dir: Path, name: str) -> str:
    path = run_dir / "bible" / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def name_needles(name: str) -> list[str]:
    """The strings a text may call this person by, longest first.

    `Nell Harker` is *Nell* in one paragraph and *Harker* in the next, and the
    timeline's `Who knows` column uses whichever is shorter. Parts under three
    letters are dropped: a two-letter particle matches half the language.

    `chapters/fact_usage.py` matches on the same list, so "who is in this event"
    and "who is in this chapter" cannot drift apart.
    """
    parts = [p for p in re.split(r"[\s'’-]+", name) if len(p) >= 3]
    return [name] + [p for p in parts if p != name]


def _blocks(text: str, heading: re.Pattern[str]) -> list[tuple[str, str]]:
    """Each bold bullet and everything under it, up to the next one."""
    marks = list(heading.finditer(text))
    return [(m.group(1), text[m.end():(marks[i + 1].start()
                                       if i + 1 < len(marks) else len(text))])
            for i, m in enumerate(marks)]


def characters_in(characters_md: str) -> list[tuple[str, str, str | None]]:
    """(canonical name, role, birth date or None), in the order written."""
    out = []
    for match in CHARACTER.finditer(characters_md):
        name, role = match.group(1).strip(), match.group(2).strip()
        born = BORN.search(match.group(0))
        out.append((name, role, born.group(1).strip() if born else None))
    return out


def mysteries_in(mysteries_md: str) -> list[str]:
    """The `True:` line of each mystery — what the book has committed to.

    A mystery with no `True:` line contributes its question instead: a question
    the book has raised is still a promise to the reader, and dropping it would
    make the fact list look complete when it is not.
    """
    facts = []
    for heading, body in _blocks(mysteries_md, MYSTERY):
        answer = TRUE_LINE.search(body)
        facts.append(answer.group(1).strip() if answer else heading.strip())
    return facts


def setting_prose(world_md: str) -> str:
    """The paragraphs before the first `##` — where a world says where it is.

    The bullets below the headings are factions and instruments, which are not
    places however capitalised they look, so reading the whole file would fill
    the reader's sheet with organisations.
    """
    body = re.split(r"^##\s", world_md, maxsplit=1, flags=re.M)[0]
    return re.sub(r"^#\s.*$", "", body, flags=re.M).strip()


def places_in(world_md: str, known_people: set[str]) -> list[tuple[str, str]]:
    """(place, the sentence it was named in), by proper nouns in the prose.

    **What this misses, on purpose.** A capital at the start of a sentence says
    nothing — `Passing vessels are written…` is not a place called Passing — so
    a run of capitals that begins a sentence loses its first word. The cost is
    real and one-directional: a place named only at the start of a sentence
    (`Scarrowdale is the hundred's last unapportioned parish`) is missed. The
    alternative admits every sentence's first word, and a sheet of forty
    non-places is a sheet nobody reads.

    It also over-admits: a capitalised thing that is not a place (`Tithe
    Commutation`) is kept, which is why `places.note` stores the sentence it
    came from. The sheet is a reading aid, not a claim.
    """
    parts = {p for person in known_people for p in person.split()}
    found: dict[str, str] = {}
    for sentence in re.split(r"(?<=[.!?])\s+", setting_prose(world_md)):
        for match in PROPER_NOUN.finditer(sentence):
            name = match.group(0)
            if SENTENCE_START.search(sentence[:match.start()]):
                # Drop the word the sentence started with; keep any name after it.
                name = name.split(" ", 1)[1] if " " in name else ""
            name = name.strip()
            if not name or set(name.split()) & parts:
                continue
            found.setdefault(name, " ".join(sentence.split()))
    return list(found.items())


def timeline_in(timeline_md: str) -> list[tuple[str, str, int | None, str]]:
    """(moment, event, the chapter it is pinned to or None, the whole row).

    The Bible's own words for *when* are kept verbatim. Normalising "3 March,
    eleven years ago, 3 a.m." and "Day 12 — Mon 22 May" to a date would invent a
    calendar neither story has; `seq` is the only ordering both share.
    """
    rows = []
    for match in TABLE_ROW.finditer(timeline_md):
        line = match.group(1)
        if SEPARATOR.fullmatch(line):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 2 or not cells[0] or not cells[1]:
            continue
        pinned = PINNED_TO_CHAPTER.search(match.group(0))
        rows.append((cells[0], cells[1],
                     int(pinned.group(1)) if pinned else None,
                     " ".join(cells)))
    # The header row names its columns; it is not an event.
    return rows[1:] if rows and rows[0][1].lower().startswith("what") else rows


def ingest(conn: sqlite3.Connection, run_dir: Path) -> IngestReport:
    # The directory is named after the run's SLUG. For the v1 runs, imported
    # under their slug, that is also the id; for a v2 run it is not, and the
    # first conductor novel ingested nothing because of it.
    run_id = run_dir.name
    if not conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
        by_slug = conn.execute("SELECT id FROM runs WHERE slug = ?", (run_dir.name,)).fetchone()
        if by_slug:
            run_id = by_slug[0]
    if not conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
        raise UnknownRun(
            f"no run {run_id!r} in this database; import or start the run "
            f"first, or the Bible would be rows nothing can reach")

    world = _read(run_dir, "world.md")
    people = characters_in(_read(run_dir, "characters.md"))
    names = {name for name, _, _ in people}
    places = places_in(world, names)
    events = timeline_in(_read(run_dir, "timeline.md"))

    facts: list[tuple[str, str, str]] = []
    facts += [("rule", bullet.lstrip("-* ").strip(), "world")
              for bullet in rules_bullets(world)]
    facts += [("character", f"{name} — {role}", "characters")
              for name, role, _ in people]
    facts += [("place", f"{name} — {note}", "world") for name, note in places]
    facts += [("chronology", f"{moment} — {event}", "timeline")
              for moment, event, _, _ in events]
    facts += [("mystery", text, "mysteries")
              for text in mysteries_in(_read(run_dir, "mysteries.md"))]

    with tx(conn):
        for kind, text, source in facts:
            # OR IGNORE, never DELETE: `fact_usage` points at these ids, and a
            # re-ingest that renumbered them would silently move every recorded
            # usage onto a different fact.
            conn.execute(
                "INSERT OR IGNORE INTO facts (run_id, kind, text, source) "
                "VALUES (?,?,?,?)", (run_id, kind, text, source))

        for name, role, born in people:
            # `first_chapter` is left alone: it is `fact_usage`'s to write, and
            # re-reading the Bible says nothing about which chapter a person
            # first appeared in.
            conn.execute(
                "INSERT INTO characters (run_id, canonical_name, role, birth_date) "
                "VALUES (?,?,?,?) ON CONFLICT (run_id, canonical_name) DO UPDATE "
                "SET role = excluded.role, birth_date = excluded.birth_date",
                (run_id, name, role, born))

        for name, note in places:
            conn.execute(
                "INSERT INTO places (run_id, canonical_name, note) VALUES (?,?,?) "
                "ON CONFLICT (run_id, canonical_name) DO UPDATE "
                "SET note = excluded.note", (run_id, name, note))

        # The timeline is rewritten whole. Nothing outside
        # `chronology_participants` points at these rows, and a corrected
        # timeline that kept its old rows beside the new ones would be two
        # timelines, which is how a chronology validator ends up proving both.
        conn.execute(
            "DELETE FROM chronology_participants WHERE chronology_id IN "
            "(SELECT id FROM chronology WHERE run_id = ?)", (run_id,))
        conn.execute("DELETE FROM chronology WHERE run_id = ?", (run_id,))
        participants = 0
        for seq, (moment, event, pinned, whole_row) in enumerate(events, 1):
            place = next((p for p, _ in places if p in whole_row), None)
            cursor = conn.execute(
                "INSERT INTO chronology (run_id, seq, event, moment, place, "
                "excludes_after) VALUES (?,?,?,?,?,?)",
                (run_id, seq, event, moment, place, pinned))
            for name in sorted(names):
                # The whole row, so the `Who knows` column some timelines carry
                # counts as being in the event.
                if any(n in whole_row for n in name_needles(name)):
                    conn.execute(
                        "INSERT INTO chronology_participants "
                        "(chronology_id, canonical_name) VALUES (?,?)",
                        (cursor.lastrowid, name))
                    participants += 1

    report = IngestReport(
        run_id=run_id,
        facts=conn.execute("SELECT COUNT(*) FROM facts WHERE run_id = ?",
                           (run_id,)).fetchone()[0],
        characters=len(people), places=len(places), chronology=len(events),
        participants=participants,
    )

    # A receipt, on disk, because that is where the conductor looks.
    #
    # The `cast` unit writes three Markdown files and then ingests them. The
    # first resumed run found the three files, decided the unit was done, and
    # skipped an ingest that had never happened — leaving the story bible
    # empty and fact_usage, mandatory_facts and the Lean export with nothing
    # to stand on. The unit's contract now includes this file, so "done" means
    # the whole unit rather than its visible half.
    receipt = run_dir / "bible" / ".ingest.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps({
            "run_id": report.run_id,
            "facts": report.facts,
            "characters": report.characters,
            "places": report.places,
            "chronology": report.chronology,
            "participants": report.participants,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, indent=2) + "\n",
        encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <run_dir>", file=sys.stderr)
        return 2

    from backend.commons.config.settings import load_settings
    from backend.commons.db.connection import connect
    from backend.commons.db.migrate import migrate

    conn = connect(load_settings().db_path)
    migrate(conn)
    try:
        report = ingest(conn, Path(argv[1]))
    except UnknownRun as exc:
        print(f"ingest: {exc}", file=sys.stderr)
        return 1

    print(f"{report.run_id}: {report.facts} facts, {report.characters} characters, "
          f"{report.places} places, {report.chronology} chronology rows, "
          f"{report.participants} participants")
    # Said out loud and non-zero, because a Bible that parsed to nothing looks
    # exactly like a Bible that was never written until somebody reads the
    # numbers — and FLOW-3 would then plan a book with no cast.
    if not report.characters or not report.chronology:
        print("ingest: the Bible parsed to an empty cast or an empty timeline; "
              "check that characters.md uses `- **Name** — role` and that "
              "timeline.md is a table", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
