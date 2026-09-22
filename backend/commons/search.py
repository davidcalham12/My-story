"""`python -m backend.commons.search <slug> "<text>"` — retrieval, for the orchestrator.

D17, under Annex C. The critics keep `tools: Glob` and gain no way to read: the
**orchestrator** runs this through `Bash(python *)` and pastes the fragments into
the continuity critic's prompt itself.

That is the whole point of routing it this way. Giving a critic a reader to fetch
its own context would hand it the same capability the chapter writer is denied,
and the denial is the strongest guarantee this project has.

**Only the Bible and the summaries are indexed. Never chapter prose.** A
retrieval that could return a previous chapter's sentences would be the leak the
architecture exists to prevent, arriving through the back door.
"""

from __future__ import annotations

import sys
from pathlib import Path

from backend.commons.config.settings import load_settings
from backend.commons.db.connection import connect
from backend.commons.db.migrate import migrate
from backend.commons.db import vectors

# What may be indexed. A chapter file is not on this list and must never be.
INDEXABLE = ("bible/world.md", "bible/characters.md", "bible/timeline.md",
             "bible/mysteries.md", "outline.md")
SUMMARY_GLOB = "chapters/*.summary.md"


def index_run(conn, slug: str, workspace: Path, embedder) -> int:
    index = vectors.Index(conn=conn, embedder=embedder)
    index.create()
    written = 0
    for rel in INDEXABLE:
        path = workspace / rel
        if path.exists():
            written += index.add(slug, rel, vectors.chunk(path.read_text(encoding="utf-8")))
    for path in sorted(workspace.glob(SUMMARY_GLOB)):
        written += index.add(
            slug, f"chapters/{path.name}",
            vectors.chunk(path.read_text(encoding="utf-8")),
        )
    return written


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print('usage: python -m backend.commons.search <slug> "<text>" [k]', file=sys.stderr)
        return 2
    slug, query = argv[1], argv[2]
    k = int(argv[3]) if len(argv) > 3 else 6

    settings = load_settings()
    conn = connect(settings.db_path)
    migrate(conn)
    if not vectors.available(conn):
        # Said plainly rather than returning nothing, which would read as "the
        # Bible contains nothing relevant".
        print("retrieval unavailable: sqlite-vec is not installed", file=sys.stderr)
        return 1

    try:
        embedder = vectors.LocalEmbedder()
    except Exception as exc:
        print(f"retrieval unavailable: {exc}", file=sys.stderr)
        return 1

    index = vectors.Index(conn=conn, embedder=embedder)
    hits = index.nearest(slug, query, k=k)
    if not hits:
        print("(no fragments indexed for this run yet)")
        return 0
    for hit in hits:
        # The source path travels with the text: a fragment that cannot say
        # where it came from is not usable as evidence.
        print(f"--- {hit['source_path']} (distance {hit['distance']:.4f})")
        print(hit["text"])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
