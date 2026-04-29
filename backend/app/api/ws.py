"""WebSocket progress streaming for agent_jobs.

The frontend opens `ws://host/ws/progress/{agent_job_id}?token=<JWT>` and
gets a JSON message every poll interval until the job hits a terminal
state (`completed` / `failed`). No pub/sub — the WS coroutine just
SELECTs the row, sends, sleeps. Cheap and good enough for a single-admin
deployment.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.security import decode_token
from app.database import SessionLocal
from app.models.agent_job import AgentJob

log = logging.getLogger(__name__)

router = APIRouter()

_TERMINAL_STATUSES = {"completed", "failed"}
_POLL_SECONDS = 2.0
_MAX_DURATION_SECONDS = 600  # safety cap; CV tailor never takes 10 minutes


def _job_to_payload(job: AgentJob) -> dict:
    log_entries = job.progress_log or []
    last = log_entries[-1] if log_entries else None
    return {
        "agent_job_id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress_pct": job.progress_pct or 0,
        "current_step": job.current_step,
        "latest_log": last,
        "error_message": job.error_message,
        "result": job.result if job.status in _TERMINAL_STATUSES else None,
    }


def _verify_ws_token(token: str | None) -> bool:
    if not token:
        return False
    payload = decode_token(token)
    return bool(payload and payload.get("sub") is not None)


@router.websocket("/ws/progress/{agent_job_id}")
async def progress_socket(
    websocket: WebSocket,
    agent_job_id: int,
    token: str | None = Query(default=None),
):
    if not _verify_ws_token(token):
        # Code 4401 = app-level "unauthorized" (1000-range is reserved for protocol).
        await websocket.close(code=4401)
        return

    await websocket.accept()

    elapsed = 0.0
    last_serialized: str | None = None
    try:
        while elapsed < _MAX_DURATION_SECONDS:
            with SessionLocal() as db:
                job = db.get(AgentJob, agent_job_id)
                if job is None:
                    await websocket.send_json({"error": "agent job not found"})
                    return
                payload = _job_to_payload(job)
                serialized = repr(payload)  # cheap diff key
                if serialized != last_serialized:
                    await websocket.send_json(payload)
                    last_serialized = serialized
                if job.status in _TERMINAL_STATUSES:
                    return

            await asyncio.sleep(_POLL_SECONDS)
            elapsed += _POLL_SECONDS

        # Max duration exceeded — tell the client to fall back to polling.
        await websocket.send_json({
            "agent_job_id": agent_job_id,
            "status": "timeout",
            "progress_pct": 0,
            "error_message": (
                f"WebSocket exceeded {_MAX_DURATION_SECONDS}s without terminal status; "
                "fall back to GET /api/cv/{id}"
            ),
        })
    except WebSocketDisconnect:
        return
    except Exception as e:  # network blip, DB error, etc.
        log.exception("progress_socket %d errored: %s", agent_job_id, e)
        try:
            await websocket.send_json({"error": str(e), "status": "failed"})
        except Exception:
            pass
