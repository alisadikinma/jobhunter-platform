"""Score + download endpoints — docx/pdf conversion mocked."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.cv import GeneratedCV
from app.models.job import ScrapedJob
from app.models.user import User

pytestmark = pytest.mark.integration


@pytest.fixture
def api(pg_engine, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CV_STORAGE_DIR", str(tmp_path))

    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="a@t.local", password_hash=hash_password("x"), name="A"))
        s.commit()
        user = s.query(User).filter_by(email="a@t.local").one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    def _db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, SessionLocal, tmp_path
    finally:
        app.dependency_overrides.clear()


def _seed_cv(SL, *, markdown="# Ali\n\nSummary with Python FastAPI Claude Code."):
    with SL() as s:
        job = ScrapedJob(
            source="x", title="AI Eng", company_name="Acme",
            content_hash="hj",
            description="Python FastAPI Claude Code role with Kubernetes and PostgreSQL.",
        )
        s.add(job)
        s.commit()
        cv = GeneratedCV(
            job_id=job.id, status="ready",
            tailored_markdown=markdown,
            variant_used="vibe_coding",
        )
        s.add(cv)
        s.commit()
        return cv.id


def test_rescore_populates_ats_fields(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)

    r = client.post(f"/api/cv/{cv_id}/score")
    body = r.json()
    assert r.status_code == 200
    assert 0 <= body["ats_score"] <= 100
    assert "python" in body["keyword_matches"]
    assert body["suggestions"]["ats"]  # non-empty suggestions list


def test_rescore_409_when_no_markdown(api):
    client, SL, _ = api
    with SL() as s:
        cv = GeneratedCV(status="pending")  # no markdown
        s.add(cv)
        s.commit()
        cv_id = cv.id

    r = client.post(f"/api/cv/{cv_id}/score")
    assert r.status_code == 409


def test_download_renders_docx_via_pandoc(api):
    client, SL, _tmp = api
    cv_id = _seed_cv(SL)

    def fake_md_to_docx(markdown, output_path, **_kw):
        output_path.write_bytes(b"fake-docx")
        return output_path

    def fake_docx_to_pdf(src, out, **_kw):
        out.write_bytes(b"fake-pdf")
        return out

    with patch("app.api.cv.markdown_to_docx", side_effect=fake_md_to_docx), \
         patch("app.api.cv.docx_to_pdf", side_effect=fake_docx_to_pdf):
        r = client.get(f"/api/cv/{cv_id}/download/docx")

    assert r.status_code == 200
    assert r.content == b"fake-docx"
    assert "filename" in r.headers["content-disposition"]


def test_download_pdf_caches_path_after_first_render(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)

    def fake_md_to_docx(_m, output_path, **_kw):
        output_path.write_bytes(b"docx")
        return output_path

    render_count = {"n": 0}

    def fake_docx_to_pdf(_src, out, **_kw):
        render_count["n"] += 1
        out.write_bytes(b"pdf")
        return out

    with patch("app.api.cv.markdown_to_docx", side_effect=fake_md_to_docx), \
         patch("app.api.cv.docx_to_pdf", side_effect=fake_docx_to_pdf):
        client.get(f"/api/cv/{cv_id}/download/pdf")
        client.get(f"/api/cv/{cv_id}/download/pdf")

    # Second hit uses cached path (file still on disk).
    assert render_count["n"] == 1


def test_download_422_for_invalid_format(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)
    assert client.get(f"/api/cv/{cv_id}/download/rtf").status_code == 422


def test_download_502_when_conversion_fails(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)

    from app.services.docx_service import ConversionError

    with patch("app.api.cv.markdown_to_docx", side_effect=ConversionError("pandoc missing")):
        r = client.get(f"/api/cv/{cv_id}/download/docx")
    assert r.status_code == 502


def test_edit_invalidates_cached_artifacts(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)
    with SL() as s:
        cv = s.get(GeneratedCV, cv_id)
        cv.docx_path = "some/old.docx"
        cv.pdf_path = "some/old.pdf"
        s.commit()

    client.put(f"/api/cv/{cv_id}", json={"tailored_markdown": "# New\n\nNew body."})
    with SL() as s:
        cv = s.get(GeneratedCV, cv_id)
        assert cv.docx_path is None
        assert cv.pdf_path is None


def test_preview_returns_markdown_and_score(api):
    client, SL, _ = api
    cv_id = _seed_cv(SL)

    # Run score first to populate fields.
    client.post(f"/api/cv/{cv_id}/score")
    r = client.get(f"/api/cv/{cv_id}/preview")
    body = r.json()
    assert body["markdown"].startswith("# Ali")
    assert body["variant_used"] == "vibe_coding"
    assert body["ats_score"] is not None
