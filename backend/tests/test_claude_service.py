"""Unit tests for claude_service.spawn_claude — subprocess injected."""
from unittest.mock import MagicMock

import pytest

from app.services.claude_service import spawn_claude

pytestmark = pytest.mark.integration


def test_spawn_claude_creates_agent_job_row_and_launches_subprocess(pg_session, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "AGENT_JOB_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "CLAUDE_PATH", "claude")
    monkeypatch.setattr(settings, "CLAUDE_PLUGIN_PATH", "/app/claude-plugin")
    monkeypatch.setattr(settings, "CALLBACK_API_URL", "http://api.local")
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s3cr3t")

    fake_proc = MagicMock()
    fake_proc.pid = 12345
    runner = MagicMock(return_value=fake_proc)

    agent_job = spawn_claude(
        pg_session,
        skill_name="/job-score",
        reference_id=None,
        reference_type="batch",
        job_type="job_score",
        subprocess_runner=runner,
    )

    assert agent_job.id is not None
    assert agent_job.status == "running"
    assert agent_job.process_pid == 12345

    called_cmd = runner.call_args[0][0]
    # Binary may resolve via shutil.which to a Windows .cmd shim — only assert
    # the basename is right.
    assert "claude" in called_cmd[0].lower()
    assert "--plugin-dir" in called_cmd
    assert "/app/claude-plugin" in called_cmd
    assert "--print" in called_cmd
    assert "--dangerously-skip-permissions" in called_cmd

    # The skill + its callback args are bundled into the final prompt arg.
    skill_prompt = called_cmd[-1]
    assert "/jobhunter:job-score" in skill_prompt
    assert "--api-url http://api.local" in skill_prompt
    assert "--api-token s3cr3t" in skill_prompt
    assert f"--job-id {agent_job.id}" in skill_prompt


def test_spawn_claude_marks_failed_when_binary_missing(pg_session, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "AGENT_JOB_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "x")

    def _raise(*_a, **_k):
        raise FileNotFoundError("claude not on PATH")

    with pytest.raises(FileNotFoundError):
        spawn_claude(
            pg_session,
            skill_name="/job-score",
            reference_id=None,
            reference_type="batch",
            job_type="job_score",
            subprocess_runner=_raise,
        )

    from app.models.agent_job import AgentJob

    row = pg_session.query(AgentJob).order_by(AgentJob.id.desc()).first()
    assert row.status == "failed"
    assert "spawn failed" in (row.error_message or "")
