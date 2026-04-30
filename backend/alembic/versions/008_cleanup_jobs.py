"""retroactively strip HTML and purge off-topic titles in scraped_jobs

Revision ID: 008_cleanup_jobs
Revises: 007_email_imap
Create Date: 2026-04-30 06:30:00.000000

The first prod scrape ingested ~78 jobs with raw HTML descriptions and a
handful of clearly off-topic titles (Sales, Account Manager, etc.) that
should never have been kept. Running the new scraper code only fixes
NEW rows — this migration retro-applies the same cleanup to existing data.

Idempotent: re-running is a no-op once descriptions are already plain text
and off-topic rows are deleted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_cleanup_jobs"
down_revision: Union[str, None] = "007_email_imap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Import inside upgrade so alembic doesn't blow up if the app package
    # isn't on sys.path during a sql-only migration generation.
    from app.utils.html_strip import strip_html
    from app.utils.title_filter import is_offtopic_title

    bind = op.get_bind()

    # 1. Strip HTML from all existing description columns. We pull rows with
    #    `<` in the description (likely-HTML) into Python because doing this
    #    in SQL alone would need pgcrypto / a server-side regex chain and
    #    still wouldn't preserve paragraph breaks correctly.
    rows = bind.execute(sa.text("""
        SELECT id, description
        FROM scraped_jobs
        WHERE description LIKE '%<%>%'
    """)).fetchall()

    cleaned = 0
    for row_id, raw in rows:
        plain = strip_html(raw)
        if plain != raw:
            bind.execute(
                sa.text("UPDATE scraped_jobs SET description = :d WHERE id = :i"),
                {"d": plain, "i": row_id},
            )
            cleaned += 1

    # 2. Purge off-topic titles. Use the title filter from app.utils to keep
    #    one source of truth; pull all rows with status='new' (haven't been
    #    interacted with) and delete the off-topic ones. We don't touch rows
    #    the user has already triaged (status != 'new').
    candidates = bind.execute(sa.text("""
        SELECT id, title FROM scraped_jobs WHERE status = 'new'
    """)).fetchall()

    purged = 0
    for row_id, title in candidates:
        if is_offtopic_title(title):
            # Cascade-safe: scraped_jobs FKs allow NULL cleanup elsewhere.
            bind.execute(
                sa.text("DELETE FROM scraped_jobs WHERE id = :i"),
                {"i": row_id},
            )
            purged += 1

    print(f"008_cleanup_jobs: stripped HTML in {cleaned} rows, purged {purged} off-topic rows")


def downgrade() -> None:
    # Cleanup is one-way (we don't keep the original HTML or the deleted rows
    # around). Downgrade is a no-op — the migration is idempotent so leaving
    # cleaned data in place after a downgrade is safe.
    pass
