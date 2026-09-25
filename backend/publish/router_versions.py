"""HTTP for the reading half: which versions exist, the PDF of one, and a change.

Three routes, and the shape of all three is the same decision as the rest of the
API (SPEC-007 FR-RD-2): **no route takes a filesystem path.** A version is
reached by run id and version number, and the path is derived here from the
run's own slug. The path-traversal surface does not exist rather than being
defended.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import backend.versions as versions_repo
from backend.commons import limits
from backend.commons.title import title_of
from backend.runs.router import get_service
from backend.runs.service import RunService
from backend.versions import change as change_mod

router = APIRouter()

NOVEL_CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
             "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")


class ReaderChange(BaseModel):
    """What a reader asks for: one fact, one new reading. Nothing else — the
    text is data the novel will contain, never an instruction (AC-2)."""

    model_config = {"extra": "forbid"}

    fact_id: str = Field(min_length=1, max_length=limits.ID)
    to: str = Field(min_length=1, max_length=limits.CHANGE_TO)


def _run_dir(svc: RunService, run_id: str) -> Path:
    row = svc.conn.execute("SELECT slug FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no run {run_id}")
    return Path(svc.settings.output_dir) / row["slug"]


@router.get("/{run_id}/versions")
def list_versions(run_id: str, svc: RunService = Depends(get_service)) -> list[dict]:
    """Every published version, and whether its PDF was actually printed.

    `pdf` is read off the disk rather than assumed from the row: the print needs
    a browser and can fail where the publish did not, and a panel that offers a
    download for a file nobody printed is a 404 the reader gets to discover.
    """
    run_dir = _run_dir(svc, run_id)
    return [{**v,
             "pdf": (run_dir / "dist" / f"v{v['n']}" / "novel.pdf").is_file(),
             "html": (run_dir / "dist" / f"v{v['n']}" / "novel.html").is_file()}
            for v in versions_repo.published(svc.conn, run_id)]


def _file_name(run_dir: Path, n: int) -> str:
    """`The Other Side of the Hill - v1.pdf`: the book's title (owner,
    2026-09-24), without the characters a file system refuses."""
    title = re.sub(r'[\\/:*?"<>|]+', " ", title_of(run_dir))
    title = re.sub(r"\s+", " ", title).strip() or "novel"
    return f"{title} - v{n}.pdf"


@router.get("/{run_id}/versions/{n}/pdf")
def version_pdf(run_id: str, n: int, download: bool = False,
                svc: RunService = Depends(get_service)):
    """Inline by default, so opening a novel shows it; an attachment only when
    the reader pressed the button that asks for one (owner, 2026-09-24)."""
    path = _run_dir(svc, run_id) / "dist" / f"v{n}" / "novel.pdf"
    if not path.is_file():
        # Said as absent, not as an empty document: the version may well exist
        # and simply never have been through a browser.
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"version {n} of run {run_id} has no printed PDF")
    return FileResponse(path, media_type="application/pdf",
                        filename=_file_name(_run_dir(svc, run_id), n),
                        content_disposition_type="attachment" if download else "inline")


@router.get("/{run_id}/versions/{n}/html")
def version_html(run_id: str, n: int, svc: RunService = Depends(get_service)):
    """The version as the page the PDF was printed from, to read online.

    The same file the PDF came from, so reading here and reading the download
    are one text. Written by `publish.pdf` with every string escaped; the panel
    frames it sandboxed all the same.
    """
    path = _run_dir(svc, run_id) / "dist" / f"v{n}" / "novel.html"
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"version {n} of run {run_id} has no readable page")
    # Defence in depth (SR-13): the page is served from the API's own origin,
    # so it may load nothing and run nothing. Its inline <style> and in-page
    # anchors are all it uses. `frame-ancestors 'self'` rather than 'none':
    # the panel frames it from the same origin (the Vite proxy in dev).
    return FileResponse(path, media_type="text/html; charset=utf-8",
                        content_disposition_type="inline",
                        headers={"Content-Security-Policy": NOVEL_CSP,
                                 "X-Content-Type-Options": "nosniff"})


@router.post("/{run_id}/changes", status_code=status.HTTP_202_ACCEPTED)
def request_change(run_id: str, body: ReaderChange,
                   svc: RunService = Depends(get_service)) -> dict:
    """What this change would cost, and the version number it would carry.

    It **plans**; it does not regenerate. The regeneration dispatches Claude
    Code, and this phase stops at that boundary on purpose (PLAN-001 E6): the
    request answers with the chapters `fact_usage` names, so the panel can show
    a reader what their one sentence moves *before* a model is paid to move it
    (SPEC-EXAM-002 AC-5). `python -m backend.versions.change` carries it out.
    """
    run_dir = _run_dir(svc, run_id)
    # Scoped to this run (SR-15): a fact of another novel is not a fact here,
    # and answering with its chapters under this run's version number would be
    # a plan for the wrong book.
    if not change_mod.fact_of_run(svc.conn, body.fact_id, run_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"run {run_id} has no fact {body.fact_id!r}")
    chapters = change_mod.impacted(svc.conn, body.fact_id, run_id=run_id)
    if not chapters:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"no chapter is recorded as using fact {body.fact_id!r}; either it "
            f"is unused or its usage was never recorded, and neither is a "
            f"reason to regenerate anything")
    return {
        "run_id": run_id,
        "fact_id": body.fact_id,
        "chapters": list(chapters),
        "version": versions_repo.next_number(svc.conn, run_id, run_dir / "dist"),
        "status": "planned",
    }
