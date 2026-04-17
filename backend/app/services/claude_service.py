"""Claude CLI subprocess spawner + agent_jobs tracking.

The FastAPI side fire-and-forgets a subprocess. The skill itself is
responsible for calling back to us (PUT /api/callbacks/progress and
PUT /api/callbacks/complete) using the shared CALLBACK_SECRET.

We don't await the subprocess — it may take minutes. The caller gets
an agent_job_id back and polls/websocket-subscribes to progress.
"""
import logging
import os
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_job import AgentJob

log = logging.getLogger(__name__)


def spawn_claude(
    db: Session,
    *,
    skill_name: str,
    reference_id: int | None,
    reference_type: str | None,
    job_type: str,
    extra_args: list[str] | None = None,
    model_used: str | None = None,
    subprocess_runner=subprocess.Popen,  # injected in tests
) -> AgentJob:
    """Start a Claude CLI skill in the background, return the AgentJob row.

    The subprocess receives `--api-url`, `--api-token`, and `--job-id` as
    arguments — the skill uses them to call back via HTTP.
    """
    agent_job = AgentJob(
        job_type=job_type,
        reference_id=reference_id,
        reference_type=reference_type,
        status="running",
        model_used=model_used,
        progress_pct=0,
        progress_log=[],
    )
    db.add(agent_job)
    db.commit()
    db.refresh(agent_job)

    log_dir = Path(settings.AGENT_JOB_LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{agent_job.id}.log"

    cmd: list[str] = [
        settings.CLAUDE_PATH,
        "--plugin-path", settings.CLAUDE_PLUGIN_PATH,
        skill_name,
        "--api-url", settings.CALLBACK_API_URL.rstrip("/"),
        "--api-token", settings.CALLBACK_SECRET,
        "--job-id", str(agent_job.id),
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        with log_path.open("ab", buffering=0) as fh:
            proc = subprocess_runner(
                cmd,
                stdout=fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                env={**os.environ},
            )
    except (FileNotFoundError, OSError) as e:
        agent_job.status = "failed"
        agent_job.error_message = f"spawn failed: {e}"
        db.commit()
        raise

    agent_job.process_pid = proc.pid
    db.commit()
    log.info("spawned %s (agent_job=%d, pid=%s)", skill_name, agent_job.id, proc.pid)
    return agent_job
