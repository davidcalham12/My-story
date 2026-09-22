"""The app, assembled from its routers."""

from __future__ import annotations

from fastapi import Depends, FastAPI

from backend.commons.config.settings import load_settings
from backend.commons.db.connection import connect
from backend.commons.db.migrate import migrate
from backend.runs import router as runs_router
from backend.runs.service import RunService

app = FastAPI(title="NovaForge", version="2.0.0")


def build_service() -> RunService:
    settings = load_settings()
    conn = connect(settings.db_path)
    migrate(conn)  # the same function the tests run, so the schemas cannot drift
    service = RunService(conn, settings)
    # A run left `running` by a server that died has no process behind it now
    # (FR-RUN-7). Marked before the first request, or the panel shows it live.
    service.sweep_orphans()
    return service


_service: RunService | None = None


def get_service() -> RunService:
    global _service
    if _service is None:
        _service = build_service()
    return _service


app.dependency_overrides[runs_router.get_service] = get_service
app.include_router(runs_router.router, prefix="/api/runs", tags=["runs"])


@app.get("/api/health")
def health(svc: RunService = Depends(runs_router.get_service)) -> dict:
    """FR-HLT-1: what this machine can do, without doing any of it.

    Nothing here calls a model or loads one. The embeddings model is reported
    from its cache directory on disk — `present`, `absent`, or `unchecked` when
    the cache location cannot be determined — because importing the library to
    ask would take seconds and memory for a health check.
    """
    from backend.commons.db import vectors
    from backend.commons.runner.process import available

    settings = svc.settings
    try:
        migrations = svc.conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
        db_ok = True
    except Exception:  # noqa: BLE001 - the whole point is to report, not raise
        migrations, db_ok = 0, False
    return {
        "ok": db_ok,
        # Said plainly, because a panel showing costs from a replayed stream
        # would be lying about money.
        "orchestrator": "recorded-stream" if settings.use_recorded_stream else "claude-code",
        # Whether this machine could orchestrate at all. There is no API
        # fallback: Claude Code is the only route to a model.
        "claude_on_path": available(),
        "db": db_ok,
        "migrations": migrations,
        "sqlite_vec": vectors.available(svc.conn) if db_ok else False,
        "embeddings_model": vectors.model_cached(),
    }
