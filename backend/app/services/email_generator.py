"""Cold email generation orchestrator — spawns /cold-email Claude skill."""
from sqlalchemy.orm import Session

from app.models.application import Application
from app.services.claude_service import spawn_claude


class EmailGenerationError(RuntimeError):
    pass


def generate_emails(
    db: Session,
    application_id: int,
) -> int:
    """Kick off the /cold-email skill. Returns the agent_job_id.

    The actual email_drafts rows are created by the callback handler when
    /cold-email posts its result — because we don't know how many drafts
    the skill will produce (normally 3: initial + 2 follow-ups) until it
    returns. Empty drafts upfront would create edge cases around partial
    failures.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise EmailGenerationError(f"Application id={application_id} not found")

    agent_job = spawn_claude(
        db,
        skill_name="/cold-email",
        reference_id=application_id,
        reference_type="application",
        job_type="cold_email",
        model_used="claude-sonnet-4-6",
    )
    return int(agent_job.id)
