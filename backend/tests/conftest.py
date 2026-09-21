import pytest

from backend.commons.db.connection import memory
from backend.commons.db.migrate import migrate


@pytest.fixture
def db():
    """A fresh migrated database per test. Fast enough that sharing one, and
    cleaning up after, would be the slower and more fragile choice."""
    conn = memory()
    migrate(conn)
    yield conn
    conn.close()
