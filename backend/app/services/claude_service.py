"""Claude CLI subprocess spawner + agent_jobs tracking.

The FastAPI side fire-and-forgets a subprocess. The skill itself is
responsible for calling back to us (PUT /api/callbacks/progress and
PUT /api/callbacks/complete) using the shared CALLBACK_SECRET.

We don't await the subprocess — it may take minutes. The caller gets
an agent_job_id back and polls/websocket-subscribes to progress.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_job import AgentJob

log = logging.getLogger(__name__)


def _resolve_claude_binary() -> str:
    """Resolve `settings.CLAUDE_PATH` to an actual executable.

    On Windows, npm-installed CLIs ship as `claude`, `claude.cmd`,
    `claude.ps1` — `subprocess.Popen` needs the `.cmd` shim, not the
    bash-style script. `shutil.which` picks the right one (it honours
    PATHEXT).
    """
    raw = settings.CLAUDE_PATH
    # If the user gave an absolute path, trust it.
    if os.path.isabs(raw) and os.path.exists(raw):
        return raw
    resolved = shutil.which(raw)
    if resolved:
        return resolved
    # Fall back to the raw value — Popen will raise FileNotFoundError
    # with a message the caller can surface.
    return raw


def spawn_claude(
    db: Session,
    *,
    skill_name: str,
    reference_id: int | None,
    reference_type: str | None,
    job_type: str,
    extra_args: list[str] | None = None,
    model_used: str | None = None,
    subprocess_runner=None,  # lazily resolved so monkeypatch(subprocess.Popen) works
) -> AgentJob:
    if subprocess_runner is None:
        subprocess_runner = subprocess.Popen
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

    # Claude CLI v2 contract:
    #   - `--plugin-dir <path>` (not `--plugin-path`) loads the local plugin.
    #   - Skills resolve via `/<plugin-name>:<skill>` (we prefix `jobhunter:`
    #     here so callers can pass the bare skill slug).
    #   - `-p` runs in print mode so the subprocess actually exits.
    #   - Skills hit FastAPI via Bash/curl — `--dangerously-skip-permissions`
    #     is required because there's no human to approve tool calls.
    bare = skill_name.lstrip("/")
    if ":" not in bare:
        bare = f"jobhunter:{bare}"
    skill_prompt_parts = [
        f"/{bare}",
        "--api-url", settings.CALLBACK_API_URL.rstrip("/"),
        "--api-token", settings.CALLBACK_SECRET,
        "--job-id", str(agent_job.id),
    ]
    if extra_args:
        skill_prompt_parts.extend(extra_args)
    skill_prompt = " ".join(skill_prompt_parts)

    cmd: list[str] = [
        _resolve_claude_binary(),
        "--plugin-dir", settings.CLAUDE_PLUGIN_PATH,
        "--print",
        "--output-format", "text",
        # Real bypass flag; --allow-dangerously-skip-permissions only EXPOSES
        # the option, --dangerously-skip-permissions actually applies it.
        "--dangerously-skip-permissions",
    ]
    if model_used:
        cmd.extend(["--model", model_used])
    cmd.append(skill_prompt)

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
