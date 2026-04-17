"""CV generation orchestrator — creates generated_cvs + spawns /cv-tailor."""
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.cv import GeneratedCV, MasterCV
from app.services.claude_service import spawn_claude


class CVGenerationError(RuntimeError):
    pass


def generate_cv(db: Session, application_id: int) -> tuple[GeneratedCV, int]:
    """Create a pending generated_cvs row and spawn the Claude skill.

    Returns (generated_cv, agent_job_id). The skill will PUT back the
    tailored markdown + metadata through the callback API.
    """
    application = db.get(Application, application_id)
    if application is None:
        raise CVGenerationError(f"Application id={application_id} not found")

    master = (
        db.query(MasterCV)
        .filter(MasterCV.is_active.is_(True))
        .order_by(MasterCV.version.desc())
        .first()
    )
    if master is None:
        raise CVGenerationError(
            "No active master CV — seed one first via scripts/seed_master_cv.py"
        )

    row = GeneratedCV(
        application_id=application_id,
        job_id=application.job_id,
        master_cv_id=master.id,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    agent_job = spawn_claude(
        db,
        skill_name="/cv-tailor",
        reference_id=application_id,
        reference_type="application",
        job_type="cv_tailor",
        model_used="claude-opus-4-7",
    )

    # Wire the agent_job back to the generated_cv for later callback dispatch.
    agent_job_id = int(agent_job.id)
    row.generation_log = {"agent_job_id": agent_job_id}
    db.commit()
    db.refresh(row)
    return row, agent_job_id
