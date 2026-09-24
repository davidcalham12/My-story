"""HTTP in. Translates requests to arguments and results to responses."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.runs.models import ResumeRun, RunCreated, StartRun
from backend.runs.service import (AlreadyRunning, BriefNotReady, CeilingRequired,
                                  NotFound, NotLive, Refused, RunService)

router = APIRouter()


def get_service() -> RunService:  # overridden in tests and at startup
    raise NotImplementedError


@router.post("", response_model=RunCreated, status_code=status.HTTP_201_CREATED)
def start_run(body: StartRun, svc: RunService = Depends(get_service)) -> RunCreated:
    """Start a run from a premise, or from a brief that already passed FLOW-0.

    404 for a brief that is not there and 422 for one that no longer passes:
    a brief the buyer has not finished is not a server error, and the run it
    would start costs money.
    """
    try:
        created = (svc.start_from_brief(body.brief_id, body.profile, body.chapters) if body.brief_id
                   else svc.start(body.premise, body.profile, body.tone))
    except AlreadyRunning as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except BriefNotReady as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return RunCreated(**created)


@router.get("")
def list_runs(trashed: bool = False, svc: RunService = Depends(get_service)) -> list[dict]:
    """The library; with `?trashed=true`, the bin (SPEC-EXAM-007 §3)."""
    return svc.list(trashed=trashed)


@router.get("/{run_id}")
def get_run(run_id: str, svc: RunService = Depends(get_service)) -> dict:
    try:
        return svc.detail(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/{run_id}/halt", status_code=status.HTTP_200_OK)
def halt(run_id: str, svc: RunService = Depends(get_service)) -> dict:
    try:
        svc.halt(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except NotLive as exc:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"run {run_id} is not in flight; nothing to halt") from exc
    return {"id": run_id, "halted": "user"}


@router.post("/{run_id}/resume", status_code=status.HTTP_200_OK)
def resume(run_id: str, body: ResumeRun | None = None,
           svc: RunService = Depends(get_service)) -> dict:
    """Continue a run that stopped, in the directory it stopped in.

    Every refusal carries its reason in `detail`, and the panel shows it as it
    is: 409 for a run that cannot be continued now, 422 for one that needs a
    ceiling typed for it (SPEC-EXAM-007 §2).
    """
    try:
        return svc.resume(run_id, ceiling_usd=body.ceiling_usd if body else None)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except (NotLive, AlreadyRunning, Refused) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except CeilingRequired as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/{run_id}/trash", status_code=status.HTTP_200_OK)
def trash(run_id: str, svc: RunService = Depends(get_service)) -> dict:
    """Move a stopped novel to `output/_papelera/`. Nothing is deleted."""
    try:
        return svc.trash(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except Refused as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{run_id}/restore", status_code=status.HTTP_200_OK)
def restore(run_id: str, svc: RunService = Depends(get_service)) -> dict:
    """Move a binned novel back, byte for byte, and clear `trashed_at`."""
    try:
        return svc.restore(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except Refused as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/{run_id}/events")
def events(run_id: str, request: Request,
           svc: RunService = Depends(get_service)) -> StreamingResponse:
    # `Last-Event-ID` is what EventSource sends on reconnect: the `id:` of the
    # last frame it saw, which here is a row number in `events`.
    header = request.headers.get("last-event-id")
    after_seq = int(header) if header and header.isdigit() else None

    def stream():
        for item in svc.follow(run_id, after_seq):
            head = f"id: {item['id']}\n" if item.get("id") is not None else ""
            # Two newlines end an event. One, and the browser waits forever.
            yield f"{head}event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
