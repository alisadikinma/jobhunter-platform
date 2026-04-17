"""harden schema: FK constraints, TIMESTAMPTZ, JSONB default, FK indexes

Revision ID: 003_fk_tz_jsonb
Revises: f087c407b308
Create Date: 2026-04-17 12:00:00.000000

Addresses code review findings:
- Missing FK constraints on applications.{cv_id, email_draft_id, cover_letter_id}
- Timezone-naive DateTime columns (inconsistent with JWT's TZ-aware now(UTC))
- Invalid server_default='[]' on JSONB (agent_jobs.progress_log)
- Missing indexes on FK columns (applications, generated_cvs, email_drafts, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_fk_tz_jsonb"
down_revision: Union[str, None] = "f087c407b308"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) pairs where we convert TIMESTAMP WITHOUT TZ → TIMESTAMPTZ.
_TZ_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("companies", "created_at"),
    ("companies", "updated_at"),
    ("scraped_jobs", "enriched_at"),
    ("scraped_jobs", "scraped_at"),
    ("scraped_jobs", "posted_at"),
    ("scraped_jobs", "expires_at"),
    ("scraped_jobs", "created_at"),
    ("scraped_jobs", "updated_at"),
    ("applications", "targeted_at"),
    ("applications", "applied_at"),
    ("applications", "email_sent_at"),
    ("applications", "replied_at"),
    ("applications", "interview_at"),
    ("applications", "offered_at"),
    ("applications", "closed_at"),
    ("applications", "created_at"),
    ("applications", "updated_at"),
    ("application_activities", "created_at"),
    ("master_cv", "synced_at"),
    ("master_cv", "created_at"),
    ("master_cv", "updated_at"),
    ("generated_cvs", "created_at"),
    ("generated_cvs", "updated_at"),
    ("cover_letters", "created_at"),
    ("cover_letters", "updated_at"),
    ("email_drafts", "sent_at"),
    ("email_drafts", "created_at"),
    ("email_drafts", "updated_at"),
    ("scrape_configs", "last_run_at"),
    ("scrape_configs", "created_at"),
    ("scrape_configs", "updated_at"),
    ("agent_jobs", "started_at"),
    ("agent_jobs", "completed_at"),
    ("agent_jobs", "created_at"),
    ("agent_jobs", "updated_at"),
    ("apify_accounts", "quota_reset_at"),
    ("apify_accounts", "exhausted_at"),
    ("apify_accounts", "last_used_at"),
    ("apify_accounts", "cooldown_until"),
    ("apify_accounts", "last_success_at"),
    ("apify_accounts", "created_at"),
    ("apify_accounts", "updated_at"),
    ("apify_usage_log", "started_at"),
    ("apify_usage_log", "completed_at"),
    ("apify_usage_log", "created_at"),
    ("portfolio_assets", "reviewed_at"),
    ("portfolio_assets", "created_at"),
]


# FK indexes that migration 002 omitted. (table, column, index_name).
_FK_INDEXES = [
    ("applications", "job_id", "idx_app_job"),
    ("applications", "company_id", "idx_app_company"),
    ("applications", "cv_id", "idx_app_cv"),
    ("applications", "email_draft_id", "idx_app_email_draft"),
    ("applications", "cover_letter_id", "idx_app_cover_letter"),
    ("application_activities", "application_id", "idx_app_activity_app"),
    ("generated_cvs", "application_id", "idx_gen_cv_app"),
    ("generated_cvs", "job_id", "idx_gen_cv_job"),
    ("generated_cvs", "master_cv_id", "idx_gen_cv_master"),
    ("cover_letters", "application_id", "idx_cover_letter_app"),
    ("cover_letters", "job_id", "idx_cover_letter_job"),
    ("email_drafts", "application_id", "idx_email_draft_app"),
    ("email_drafts", "job_id", "idx_email_draft_job"),
    ("portfolio_assets", "reviewed_by", "idx_portfolio_reviewed_by"),
]


def upgrade() -> None:
    # 1. Fix invalid JSONB default on agent_jobs.progress_log.
    op.execute("ALTER TABLE agent_jobs ALTER COLUMN progress_log SET DEFAULT '[]'::jsonb")

    # 2. Add missing FK constraints on applications.
    op.create_foreign_key(
        "fk_applications_cv",
        "applications", "generated_cvs",
        ["cv_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_applications_email_draft",
        "applications", "email_drafts",
        ["email_draft_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_applications_cover_letter",
        "applications", "cover_letters",
        ["cover_letter_id"], ["id"],
        ondelete="SET NULL",
    )

    # 3. Convert all DateTime columns to TIMESTAMPTZ (assume UTC for existing data).
    for table, column in _TZ_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITH TIME ZONE USING {column} AT TIME ZONE 'UTC'"
        )

    # 4. Add indexes on FK columns that were omitted in migration 002.
    for table, column, name in _FK_INDEXES:
        op.create_index(name, table, [column])


def downgrade() -> None:
    for _, _, name in _FK_INDEXES:
        op.drop_index(name)

    for table, column in _TZ_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING {column} AT TIME ZONE 'UTC'"
        )

    op.drop_constraint("fk_applications_cover_letter", "applications", type_="foreignkey")
    op.drop_constraint("fk_applications_email_draft", "applications", type_="foreignkey")
    op.drop_constraint("fk_applications_cv", "applications", type_="foreignkey")

    op.execute("ALTER TABLE agent_jobs ALTER COLUMN progress_log SET DEFAULT '[]'")
