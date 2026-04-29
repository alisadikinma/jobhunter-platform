"""WebSocket progress streaming tests.

Uses the FastAPI TestClient WebSocket helper. The endpoint creates its
own SessionLocal, so we patch app.api.ws.SessionLocal at the module
level to use the test engine's sessionmaker for the duration of the
test. We also shrink the poll interval so terminal-state detection
returns within a fraction of a second.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api import ws as ws_module
from app.core.security import create_access_token
from app.main import app
from app.models.agent_job import AgentJob

pytestmark = pytest.mark.integration


@pytest.fixture
def ws_client(pg_engine, monkeypatch):
    test_session = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(ws_module, "SessionLocal", test_session)
    monkeypatch.setattr(ws_module, "_POLL_SECONDS", 0.05)
    monkeypatch.setattr(ws_module, "_MAX_DURATION_SECONDS", 5)
    return TestClient(app), test_session


def _good_token() -> str:
    return create_access_token({"sub": "1"})


def test_ws_rejects_missing_token(ws_client):
    client, _ = ws_client
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/progress/1"):
            pass


def test_ws_rejects_bad_token(ws_client):
    client, _ = ws_client
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/progress/1?token=garbage"):
            pass


def test_ws_streams_until_completed(ws_client):
    client, SL = ws_client

    with SL() as s:
        job = AgentJob(
            job_type="cv_tailor",
            reference_id=1,
            reference_type="application",
            status="running",
            progress_pct=42,
            current_step="tailoring",
            progress_log=[{"t": "now", "msg": "started"}],
        )
        s.add(job)
        s.commit()
        job_id = job.id

    token = _good_token()
    with client.websocket_connect(f"/ws/progress/{job_id}?token={token}") as sock:
        first = sock.receive_json()
        assert first["agent_job_id"] == job_id
        assert first["status"] == "running"
        assert first["progress_pct"] == 42
        assert first["current_step"] == "tailoring"
        assert first["latest_log"]["msg"] == "started"

        # Mutate the row → next poll picks up new state and finalizes.
        with SL() as s:
            row = s.get(AgentJob, job_id)
            row.status = "completed"
            row.progress_pct = 100
            row.result = {"variant_used": "vibe_coding"}
            s.commit()

        terminal = sock.receive_json()
        assert terminal["status"] == "completed"
        assert terminal["progress_pct"] == 100
        assert terminal["result"] == {"variant_used": "vibe_coding"}


def test_ws_returns_error_for_missing_job(ws_client):
    client, _ = ws_client
    token = _good_token()
    with client.websocket_connect(f"/ws/progress/99999?token={token}") as sock:
        msg = sock.receive_json()
        assert msg == {"error": "agent job not found"}
