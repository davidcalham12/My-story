"""HTTP in. Translates requests to arguments and results to responses."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from backend.runs.models import RunCreated, StartRun
from backend.runs.service import AlreadyRunning, NotFound, RunService

router = APIRouter()


def get_service() -> RunService:  # overridden in tests and at startup
    raise NotImplementedError


@router.post("", response_model=RunCreated, status_code=status.HTTP_201_CREATED)
def start_run(body: StartRun, svc: RunService = Depends(get_service)) -> RunCreated:
    try:
        created = svc.start(body.premise, body.profile, body.tone)
    except AlreadyRunning as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return RunCreated(**created)


@router.get("")
def list_runs(svc: RunService = Depends(get_service)) -> list[dict]:
    return svc.list()


@router.get("/{run_id}")
def get_run(run_id: str, svc: RunService = Depends(get_service)) -> dict:
    try:
        return svc.detail(run_id)
    except NotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{run_id}/events")
def events(run_id: str, svc: RunService = Depends(get_service)) -> StreamingResponse:
    def stream():
        for item in svc.follow(run_id):
            # Two newlines end an event. One, and the browser waits forever.
            yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
