import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app

_PG_CONN_KW = dict(
    host=os.getenv("TEST_PG_HOST", "localhost"),
    port=int(os.getenv("TEST_PG_PORT", "5433")),
    user=os.getenv("TEST_PG_USER", "jobhunter"),
    password=os.getenv("TEST_PG_PASSWORD", "jobhunter"),
    dbname="jobhunter",
)


@pytest.fixture(scope="session", autouse=True)
def _drop_orphaned_test_templates():
    """pytest-postgresql can leave jobhunter_test_tmpl behind after a crashed
    session. On the next run, CREATE DATABASE collides. Wipe before starting."""
    try:
        conn = psycopg.connect(**_PG_CONN_KW, autocommit=True)
    except psycopg.Error:
        yield
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pg_database SET datistemplate=false "
                "WHERE datname='jobhunter_test_tmpl'"
            )
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname IN ('jobhunter_test','jobhunter_test_tmpl')"
            )
            cur.execute("DROP DATABASE IF EXISTS jobhunter_test")
            cur.execute("DROP DATABASE IF EXISTS jobhunter_test_tmpl")
    finally:
        conn.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# Real-Postgres fixture via pytest-postgresql noproc mode. Points at the
# running dev/CI Postgres (default: docker-compose.dev.yml on localhost:5433)
# and creates a fresh template-derived DB per test.
postgresql_noproc = factories.postgresql_noproc(
    host=os.getenv("TEST_PG_HOST", "localhost"),
    port=int(os.getenv("TEST_PG_PORT", "5433")),
    user=os.getenv("TEST_PG_USER", "jobhunter"),
    password=os.getenv("TEST_PG_PASSWORD", "jobhunter"),
    dbname="jobhunter_test",
)
postgresql = factories.postgresql("postgresql_noproc", dbname="jobhunter_test")


@pytest.fixture
def pg_engine(postgresql):
    """SQLAlchemy engine bound to a throwaway test DB with all tables created."""
    info = postgresql.info
    url = (
        f"postgresql+psycopg2://{info.user}:{info.password}"
        f"@{info.host}:{info.port}/{info.dbname}"
    )
    engine = create_engine(url)

    # Trigger model registration on Base.metadata.
    import app.models.agent_job
    import app.models.apify_account
    import app.models.application
    import app.models.company
    import app.models.cv
    import app.models.email_draft
    import app.models.job
    import app.models.portfolio_asset
    import app.models.scrape_config
    import app.models.user  # noqa: F401
    from app.database import Base

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
