"""Retrieval over the Story Bible, with `sqlite-vec`.

What this is for, precisely: the continuity critic receives the Bible fragments
nearest its draft rather than the whole Bible. The critics are roughly half the
spend, so this is the one lever that reduces context and cost at the same time.

**What it is deliberately NOT for.** `science` receives `## Rules` entire and
`outline` receives its entry entire, and neither is ever retrieved. Retrieval
returns what is *similar*, never what is *complete*, and **a rule that was not
retrieved is a violation nobody looked for.** Where a check must see everything,
it is passed everything.

Both the extension and the embedder are optional: the whole test suite runs
without either, and `available()` says which route this process has.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

# Fixed at table creation and unchangeable afterwards. Recorded beside every
# vector: two models of the same dimension are accepted by the store and return
# confident nonsense, and this column is the only thing that catches it.
MODEL = "all-MiniLM-L6-v2"
DIMENSION = 384


class Embedder(Protocol):
    name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    """`sentence-transformers`, on this machine. No per-call cost, no network."""

    def __init__(self, model_name: str = MODEL):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()


class HashEmbedder:
    """A deterministic stand-in for tests. It does not retrieve sensibly.

    That is the point: it proves the plumbing — that vectors of the right length
    reach the store and come back joined to their rows — without downloading
    four hundred megabytes. Anything about retrieval QUALITY needs the real
    model and is a different, slower test.
    """

    name = "hash-stand-in"
    dimension = DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        out = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            raw = [digest[i % len(digest)] / 255.0 for i in range(self.dimension)]
            norm = sum(v * v for v in raw) ** 0.5 or 1.0
            out.append([v / norm for v in raw])
        return out


def available(conn: sqlite3.Connection) -> bool:
    """Whether this process can load the extension.

    Extension loading is off by default and must be re-enabled per CONNECTION,
    not once per database — a pooled connection that skipped it fails at the
    first query rather than at connect.
    """
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)  # close the door again immediately
        conn.execute("SELECT vec_version()").fetchone()
        return True
    except Exception:
        return False


@dataclass
class Index:
    conn: sqlite3.Connection
    embedder: Embedder

    def create(self) -> None:
        if self.embedder.dimension != DIMENSION:
            raise ValueError(
                f"{self.embedder.name} produces {self.embedder.dimension} dimensions; "
                f"the table is fixed at {DIMENSION} and changing it means a re-index"
            )
        self.conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0("
            f"  chunk_id INTEGER PRIMARY KEY, embedding float[{DIMENSION}])"
        )

    def add(self, run_id: str, source_path: str, pieces: list[str]) -> int:
        """Store chunks and their vectors.

        The chunk rows are the durable half; the vector table is an index and is
        rebuildable from them. If you could not rebuild it, the design would be
        the wrong way round.
        """
        from sqlite_vec import serialize_float32

        vectors = self.embedder.embed(pieces)
        written = 0
        for ordinal, (text, vector) in enumerate(zip(pieces, vectors)):
            cur = self.conn.execute(
                "INSERT INTO chunks (run_id, source_path, ordinal, text, embed_model) "
                "VALUES (?,?,?,?,?)",
                (run_id, source_path, ordinal, text, self.embedder.name),
            )
            self.conn.execute(
                "INSERT INTO chunk_vectors (chunk_id, embedding) VALUES (?, ?)",
                (int(cur.lastrowid), serialize_float32(vector)),
            )
            written += 1
        return written

    def nearest(self, run_id: str, query: str, k: int = 6) -> list[dict]:
        """The k nearest chunks, joined back to where they came from.

        `match` engages the index, `order by distance` makes it the nearest k
        rather than any k, and `limit` is required — a KNN query without one is
        an error rather than a scan.

        Distance is a distance: smaller is nearer. It is not a similarity score
        and not bounded to 0-1, so it is returned raw rather than thresholded
        against a number copied from somewhere else.
        """
        from sqlite_vec import serialize_float32

        vector = self.embedder.embed([query])[0]
        # The KNN runs ALONE, in a subquery, with a literal limit. `vec0` rejects
        # a parameterised LIMIT and rejects arbitrary joined constraints mixed
        # into the match, which is the extension telling you this is an index
        # lookup and not a WHERE clause.
        #
        # So the run filter happens OUTSIDE, and that has a consequence worth
        # stating rather than discovering: the search ranges over every run's
        # chunks and the other runs' hits are then discarded, so a query can come
        # back with fewer than k. Over-fetching by a factor makes that unlikely;
        # it does not make it impossible, and the caller gets what there was.
        over = max(k * 8, 40)
        rows = self.conn.execute(
            f"SELECT c.text, c.source_path, v.distance FROM ("
            f"  SELECT chunk_id, distance FROM chunk_vectors "
            f"  WHERE embedding MATCH ? ORDER BY distance LIMIT {over}"
            f") v JOIN chunks c ON c.id = v.chunk_id "
            f"WHERE c.run_id = ? ORDER BY v.distance LIMIT {int(k)}",
            (serialize_float32(vector), run_id),
        ).fetchall()
        return [dict(r) for r in rows]


def chunk(text: str, *, min_words: int = 25) -> list[str]:
    """Split on meaning, not on characters.

    A paragraph, a bible entry, one bullet. A fixed-width window that cuts a
    sentence stores half of two ideas and retrieves neither. Very short
    fragments are folded forward so chunks stay comparable in size — similarity
    is skewed by length, and one tiny chunk among large ones wins or loses
    queries for reasons unrelated to its content.
    """
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    out: list[str] = []
    for block in blocks:
        if out and len(block.split()) < min_words:
            out[-1] = out[-1] + "\n\n" + block
        else:
            out.append(block)
    return out
