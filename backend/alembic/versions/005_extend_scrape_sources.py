"""extend default scrape source list with weworkremotely + aijobs + linkedin_apify

Revision ID: 005_extend_sources
Revises: 004_seed_configs
Create Date: 2026-04-29 20:55:00.000000

Adds three more sources to every existing scrape_config:

- `weworkremotely` (RSS, free)
- `aijobs` (aijobs.net + aicareers.io, HTML)
- `linkedin_apify` (opt-in via APIFY_LINKEDIN_ENABLED env, otherwise skipped
  by scraper_service)

Idempotent — uses array-append-distinct so a re-run is a no-op.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_extend_sources"
down_revision: Union[str, None] = "004_seed_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_SOURCES = ("weworkremotely", "aijobs", "linkedin_apify")


def upgrade() -> None:
    conn = op.get_bind()
    for src in _NEW_SOURCES:
        conn.execute(
            sa.text("""
                UPDATE scrape_configs
                SET sources = sources || ARRAY[:src]::text[]
                WHERE NOT (:src = ANY(sources))
            """),
            {"src": src},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for src in _NEW_SOURCES:
        conn.execute(
            sa.text("""
                UPDATE scrape_configs
                SET sources = array_remove(sources, :src)
                WHERE :src = ANY(sources)
            """),
            {"src": src},
        )
