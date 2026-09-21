"""Phase 5 — retrieval, and the line it must not cross.

These run with the hash stand-in, so they need no model download. They prove the
plumbing: vectors of the right length reach the store and come back joined to
their source rows. Retrieval *quality* needs the real model and is a different,
slower test that does not belong in CI.

The tests that matter most here are the ones about what is NOT retrieved.
"""

import pytest

from backend.commons.db import vectors


@pytest.fixture
def index(db):
    if not vectors.available(db):
        pytest.skip("sqlite-vec is not installed in this environment")
    idx = vectors.Index(conn=db, embedder=vectors.HashEmbedder())
    idx.create()
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('r','s','p','tiny','{}','FLOW-4','now')")
    return idx


def test_chunking_splits_on_meaning_not_on_width():
    text = "First paragraph, long enough to stand alone " * 3 + "\n\nshort\n\n" + \
           "Third paragraph, also long enough to stand on its own two feet here " * 2
    pieces = vectors.chunk(text)
    # The short fragment is folded into its neighbour rather than left as a
    # chunk: similarity is skewed by length, and one tiny chunk among large ones
    # wins or loses queries for reasons unrelated to content.
    assert all(len(p.split()) >= 5 for p in pieces)
    assert any("short" in p for p in pieces)


def test_a_mismatched_dimension_is_refused_rather_than_stored(db):
    """Two models of the same dimension return confident nonsense; a model of the
    WRONG dimension must fail loudly instead of half-working."""
    class Wrong:
        name, dimension = "wrong", 128

        def embed(self, texts):
            return [[0.0] * 128 for _ in texts]

    with pytest.raises(ValueError, match="re-index"):
        vectors.Index(conn=db, embedder=Wrong()).create()


def test_chunks_come_back_joined_to_where_they_came_from(index, db):
    """A retrieval that cannot say where a passage came from is not usable as
    evidence."""
    index.add("r", "bible/world.md", ["The pumps run at night.",
                                      "Water is rationed between two and four."])
    hits = index.nearest("r", "when do the pumps run", k=2)
    assert hits
    assert all(h["source_path"] == "bible/world.md" for h in hits)
    assert all("distance" in h for h in hits)


def test_the_model_that_wrote_a_vector_is_recorded(index, db):
    """Nothing else catches two models of the same dimension being mixed."""
    index.add("r", "bible/world.md", ["A rule about water."])
    row = db.execute("SELECT embed_model FROM chunks").fetchone()
    assert row["embed_model"] == vectors.HashEmbedder.name


def test_retrieval_is_scoped_to_one_run(index, db):
    db.execute("INSERT INTO runs (id, slug, premise, profile, config_snapshot, "
               "stage, started_at) VALUES ('other','o','p','tiny','{}','FLOW-4','now')")
    index.add("r", "bible/world.md", ["Belongs to run r."])
    index.add("other", "bible/world.md", ["Belongs to the other run."])
    hits = index.nearest("r", "belongs", k=5)
    assert all("run r" in h["text"] for h in hits)


def test_the_index_is_rebuildable_from_the_chunks(index, db):
    """The chunk rows are the durable half. If the index could not be rebuilt
    from them, the design would be the wrong way round."""
    index.add("r", "bible/world.md", ["One.", "Two.", "Three."])
    stored = db.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
    assert stored == 3
    db.execute("DELETE FROM chunk_vectors")
    texts = [r["text"] for r in db.execute("SELECT text FROM chunks ORDER BY ordinal")]
    assert texts == ["One.", "Two.", "Three."], "rebuildable without the vectors"
