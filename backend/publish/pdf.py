"""The book a reader is given: one HTML document, printed to one PDF.

The module is split in two on purpose, and the seam is the whole design.

`build_html` is a **pure function** — a `Novel` in, a string out. No clock, no
filesystem, no browser. That is what makes the cover, the index anchors and the
character sheet's links testable on a machine with no Chromium, which is every
machine in CI and was this one while the browser was still downloading.

`print_pdf` is the browser half. It imports Playwright *inside the function*, so
a missing browser fails at the one call that needs it, with a message that names
the install command, instead of at import time in every module that touches
publishing. The first half is class T; the second is class D, and saying which
is which is the point (docs/spec.md §4, AC-6).

Markdown is converted here in about twenty lines rather than with a library.
Everything is escaped first and the conversion then only ever *adds* tags, so a
chapter containing `<script>` renders as text — a novel is user text and the
brief's free text is explicitly untrusted (AC-2).
"""

from __future__ import annotations

import html as html_mod
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from backend import versions as versions_repo


@dataclass(frozen=True)
class Chapter:
    n: int
    title: str
    body: str                       # Markdown, with its own heading removed


@dataclass(frozen=True)
class Entry:
    """One line of the character/place sheet.

    `first_chapter` is `None` when nobody worked it out. It is never 0 and never
    quietly 1: the sheet says "not recorded" and renders no link, because a link
    to the wrong chapter is worse than no link, and indistinguishable from a
    right one on a printed page.
    """

    name: str
    detail: str | None = None
    first_chapter: int | None = None


@dataclass(frozen=True)
class Sheet:
    """`None` means the table does not exist or was never filled; `[]` means it
    was filled and found nobody. Rendering both as an empty list is how a broken
    ingest ships looking like a novel with no characters in it."""

    characters: list[Entry] | None = None
    places: list[Entry] | None = None


@dataclass(frozen=True)
class Change:
    """What a reader asked for, and what it moved."""

    fact_id: str
    to: str
    chapters: tuple[int, ...]
    parent: int


@dataclass(frozen=True)
class Novel:
    title: str
    version: int
    chapters: list[Chapter]
    sheet: Sheet = field(default_factory=Sheet)
    dedication: str | None = None
    synopsis: str | None = None
    change: Change | None = None


# --------------------------------------------------------------- Markdown


_STRONG = re.compile(r"\*\*(.+?)\*\*", re.S)
_EM = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)


def markdown(text: str) -> str:
    """Escape first, then add the two tags a novel actually uses.

    Order matters and is the security property: `html.escape` runs over the raw
    text, so every `<` in the prose is already `&lt;` before a single tag is
    inserted. Nothing below can produce a tag the author wrote.
    """
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    out = []
    for block in blocks:
        escaped = html_mod.escape(block)
        escaped = _STRONG.sub(r"<strong>\1</strong>", escaped)
        escaped = _EM.sub(r"<em>\1</em>", escaped)
        out.append("<p>" + escaped.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def _t(text: str) -> str:
    """One line of plain text, escaped. Used for titles and names."""
    return html_mod.escape(text.strip())


# --------------------------------------------------------------- the HTML


STYLE = """
  @page { size: A4; margin: 18mm 16mm; }
  body { font-family: Georgia, "Times New Roman", serif; font-size: 11.5pt;
         line-height: 1.55; color: #1a1a1a; }
  section { page-break-after: always; }
  section:last-child { page-break-after: auto; }
  #cover { text-align: center; padding-top: 28%; }
  #cover h1 { font-size: 30pt; margin: 0 0 .4em; letter-spacing: .02em; }
  #cover .dedication { font-style: italic; margin-top: 4em; }
  #cover .absent { font-style: normal; color: #777; }
  nav ol { list-style: none; padding: 0; }
  nav li { margin: .35em 0; }
  a { color: #1a1a1a; text-decoration: none; }
  .sheet-entry .absent { color: #777; font-style: italic; }
  h2 { page-break-after: avoid; }
  #what-changed { background: #f6f3ec; padding: 2em; }
"""


def _sheet_entries(entries: list[Entry] | None, kind: str) -> str:
    if entries is None:
        return (f'<p class="absent">The {kind} were not recorded for this run — '
                f"the Story Bible tables are empty, which is not the same as a "
                f"novel with no {kind}.</p>")
    if not entries:
        return f'<p class="absent">No {kind} in this novel.</p>'
    rows = []
    for e in entries:
        detail = f" — {_t(e.detail)}" if e.detail else ""
        if e.first_chapter is None:
            # Absent is never zero: no link, and the page says why.
            where = ' <span class="absent">(first chapter not recorded)</span>'
        else:
            where = (f' — first appears in <a href="#chapter-{e.first_chapter}">'
                     f"chapter {e.first_chapter}</a>")
        rows.append(f'<li class="sheet-entry"><strong>{_t(e.name)}</strong>'
                    f"{detail}{where}</li>")
    return "<ul>\n" + "\n".join(rows) + "\n</ul>"


def build_html(novel: Novel) -> str:
    """The whole book as one document. Pure: string in, string out.

    Order on the page: the "what changed" note (only on a regenerated version,
    and first so that it is literally the PDF's first page), the cover with the
    dedication, the index, the character/place sheet, then the chapters.
    """
    parts: list[str] = []

    if novel.change is not None:
        moved = "".join(
            f'<li><a href="#chapter-{n}">chapter {n}</a></li>'
            for n in novel.change.chapters)
        parts.append(
            '<section id="what-changed">\n'
            f"<h1>What changed in version {novel.version}</h1>\n"
            f"<p>You asked for one thing to be different:</p>\n"
            f"<blockquote>{_t(novel.change.to)}</blockquote>\n"
            f"<p>Fact <code>{_t(novel.change.fact_id)}</code>. "
            f"Version {novel.change.parent} is still on the shelf, unchanged. "
            f"Only these chapters were written again:</p>\n"
            f"<ul>{moved}</ul>\n</section>")

    dedication = (f'<p class="dedication">{_t(novel.dedication)}</p>'
                  if novel.dedication
                  else '<p class="dedication absent">This copy carries no '
                       "dedication.</p>")
    parts.append(
        '<section id="cover">\n'
        f"<h1>{_t(novel.title)}</h1>\n"
        f'<p class="imprint">version {novel.version}</p>\n'
        f"{dedication}\n</section>")

    index = "".join(f'<li><a href="#chapter-{c.n}">{c.n}. {_t(c.title)}</a></li>'
                    for c in novel.chapters)
    parts.append('<section id="index">\n<h1>Contents</h1>\n'
                 f"<nav><ol>{index}</ol></nav>\n</section>")

    parts.append(
        '<section id="sheet">\n<h1>The people and the places</h1>\n'
        "<h2>Characters</h2>\n" + _sheet_entries(novel.sheet.characters, "characters")
        + "\n<h2>Places</h2>\n" + _sheet_entries(novel.sheet.places, "places")
        + "\n</section>")

    if novel.synopsis:
        parts.append('<section id="synopsis">\n<h1>The story</h1>\n'
                     f"{markdown(novel.synopsis)}\n</section>")

    for c in novel.chapters:
        parts.append(f'<section id="chapter-{c.n}">\n'
                     f"<h1>Chapter {c.n} — {_t(c.title)}</h1>\n"
                     f"{markdown(c.body)}\n</section>")

    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            '<meta charset="utf-8">\n'
            f"<title>{_t(novel.title)}</title>\n<style>{STYLE}</style>\n"
            "</head>\n<body>\n" + "\n".join(parts) + "\n</body>\n</html>\n")


# --------------------------------------------------------------- reading a run


#: `ch07.md` — the promoted chapter. Not `ch07.attempt2.md`, not `ch07.final.md`,
#: not `ch07.summary.md`: the book is assembled from what `promote` copied.
CHAPTER_FILE = re.compile(r"^ch(\d+)\.md$")

#: `# Chapter 7 — The Drowned Page`
HEADING = re.compile(r"^#\s*Chapter\s+\d+\s*[—:-]\s*(.+?)\s*$", re.M)


def _chapter(path: Path, n: int) -> Chapter:
    text = path.read_text(encoding="utf-8")
    match = HEADING.search(text)
    title = match.group(1) if match else ""
    body = text[match.end():] if match else text
    return Chapter(n=n, title=title, body=body.strip())


def _title(run_dir: Path) -> str:
    """The book's title, from the manuscript the run assembled.

    Falls back to the slug rather than inventing one: a novel published under a
    title nobody wrote is the kind of figure `docs/verification.md` G12 is about.
    """
    book = run_dir / "dist" / "book.md"
    if book.is_file():
        for line in book.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    state = run_dir / "state.json"
    if state.is_file():
        slug = json.loads(state.read_text(encoding="utf-8")).get("slug")
        if slug:
            return str(slug)
    return run_dir.name


def _dedication(run_dir: Path) -> str | None:
    """`dedication.md`, or the brief's dedication in `state.json`.

    Phase E2 writes it from the `Brief`; a run made before that has none, and
    the cover then says so instead of printing a blank where a name should be.
    """
    path = run_dir / "dedication.md"
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    state = run_dir / "state.json"
    if state.is_file():
        value = json.loads(state.read_text(encoding="utf-8")).get("dedication")
        if value:
            return str(value).strip()
    return None


def _entries(conn: sqlite3.Connection, run_id: str, table: str,
             detail_column: str) -> list[Entry] | None:
    """The sheet's rows, or `None` when the table is not there yet.

    `characters` and `places` arrive with migration 010 (phase E3), which is
    being built in parallel. E6 reads them if they exist and reports their
    absence as absence — it does not create them and owns no key into them.
    """
    try:
        rows = conn.execute(
            f"SELECT canonical_name, {detail_column} AS detail, first_chapter "
            f"FROM {table} WHERE run_id = ? ORDER BY "
            f"first_chapter IS NULL, first_chapter, canonical_name",
            (run_id,)).fetchall()
    except sqlite3.OperationalError:
        return None
    return [Entry(name=r["canonical_name"], detail=r["detail"],
                  first_chapter=r["first_chapter"]) for r in rows]


def read_novel(conn: sqlite3.Connection, run_dir: Path, run_id: str, *,
               version: int, change: Change | None = None,
               chapters_from: Path | None = None) -> Novel:
    """Everything `build_html` needs, gathered from the archive and the disk.

    `chapters_from` is a version's own workspace: a regenerated chapter is read
    from there and every other chapter from the run. It is what keeps a
    regeneration from writing over prose the gate already accepted.
    """
    chapters = []
    for path in sorted((run_dir / "chapters").glob("ch*.md")):
        match = CHAPTER_FILE.match(path.name)
        if not match:
            continue
        n = int(match.group(1))
        rewritten = (chapters_from / "chapters" / path.name) if chapters_from else None
        chapters.append(_chapter(rewritten if rewritten and rewritten.is_file()
                                 else path, n))
    chapters.sort(key=lambda c: c.n)

    synopsis_path = run_dir / "synopsis.md"
    synopsis = (synopsis_path.read_text(encoding="utf-8").strip()
                if synopsis_path.is_file() else None)

    return Novel(
        title=_title(run_dir),
        version=version,
        chapters=chapters,
        sheet=Sheet(characters=_entries(conn, run_id, "characters", "role"),
                    places=_entries(conn, run_id, "places", "note")),
        dedication=_dedication(run_dir),
        synopsis=synopsis,
        change=change,
    )


# --------------------------------------------------------------- publishing


def write_version(run_dir: Path, novel: Novel) -> Path:
    """Write `dist/v<n>/novel.html`, and refuse to overwrite one.

    This is the structural half of "v1 is never touched". It is the only
    function in the phase that writes a version's document; the only directory
    it can name is the one its own version number derives; and the file is
    opened with mode `"x"`, which is an exclusive create in the filesystem
    rather than a check this code could race or forget. A published version
    cannot be overwritten by any code path in this repository.
    """
    out = run_dir / "dist" / f"v{novel.version}"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "novel.html"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(build_html(novel))
    return path


def publish(conn: sqlite3.Connection, run_dir: Path, run_id: str, *, reason: str,
            change: Change | None = None, chapters_from: Path | None = None,
            n: int | None = None) -> int:
    """Render the next version and record it. Returns its number.

    `n` is passed in by a reader change, which allocated the number before it
    regenerated anything and made the workspace under it. Left out, the number
    is allocated here from the archive *and* from the directories on disk, so a
    regeneration the gate halted — a workspace with no row behind it — cannot
    hand its number to the next attempt.
    """
    n = n or versions_repo.next_number(conn, run_id, run_dir / "dist")
    novel = read_novel(conn, run_dir, run_id, version=n, change=change,
                       chapters_from=chapters_from)
    write_version(run_dir, novel)
    versions_repo.record(conn, run_id, n=n, parent=change.parent if change else None,
                         reason=reason)
    return n


# --------------------------------------------------------------- the browser


def _playwright():
    """The import, behind a function.

    At module scope it would make every importer of this module — the router,
    the change CLI, the tests — depend on a package that was still downloading
    when this was written. Behind a function it is also the seam the
    missing-browser test replaces, so that path is exercised on a machine where
    the browser is present.
    """
    from playwright.sync_api import sync_playwright

    return sync_playwright


def print_pdf(html_path: Path, pdf_path: Path) -> Path:
    """The demonstrated half: Chromium prints the document.

    The failure this message exists for is `ModuleNotFoundError: playwright` at
    the end of a ten-chapter run, with nothing saying what to install.
    """
    try:
        sync_playwright = _playwright()
    except ImportError as exc:
        raise RuntimeError(
            "the PDF needs a browser and playwright is not usable here: "
            "pip install playwright && python -m playwright install chromium"
        ) from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # `as_uri()`, never "file://" + str(path): on Windows the second gives
        # Chromium a host named C.
        page.goto(html_path.as_uri())
        page.pdf(path=str(pdf_path), format="A4",
                 # Off by default, and the cover's shading disappears with it.
                 print_background=True,
                 margin={"top": "18mm", "bottom": "18mm",
                         "left": "16mm", "right": "16mm"})
        browser.close()
    return pdf_path
