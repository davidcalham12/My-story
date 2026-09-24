"""HTTP for the reading half: which versions exist, the PDF of one, and a change.

Three routes, and the shape of all three is the same decision as the rest of the
API (SPEC-007 FR-RD-2): **no route takes a filesystem path.** A version is
reached by run id and version number, and the path is derived here from the
run's own slug. The path-traversal surface does not exist rather than being
defended.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import backend.versions as versions_repo
from backend.runs.router import get_service
from backend.runs.service import RunService
from backend.versions import change as change_mod

router = APIRouter()


class ReaderChange(BaseModel):
    """What a reader asks for: one fact, one new reading. Nothing else — the
    text is data the novel will contain, never an instruction (AC-2)."""

    model_config = {"extra": "forbid"}

    fact_id: str = Field(min_length=1)
    to: str = Field(min_length=1)


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
                        filename=f"novel-v{n}.pdf",
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
    return FileResponse(path, media_type="text/html; charset=utf-8",
                        content_disposition_type="inline")


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
    chapters = change_mod.impacted(svc.conn, body.fact_id)
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
