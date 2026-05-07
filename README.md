# JobHunter

Automated AI-era job hunting pipeline: scrape → AI score → CV tailor →
cold email. Built around **Claude CLI** as the core differentiator
(Opus for tailoring, Sonnet for scoring + email drafting).

**Stack:** FastAPI 0.115 · Next.js 15 · PostgreSQL 16 · Claude CLI ·
Pandoc · LibreOffice · APScheduler · Firecrawl (self-hosted, optional).

## Highlights

- **One-click master CV import** from
  [Portfolio CV API](https://alisadikinma.com/api/cv/export) (JSON
  schema 2.0.0): basics + work + education + skills + projects + awards
  + thought leadership + certifications, validated directly against
  `MasterCVContent`. Same call also creates portfolio drafts (URL
  dedup'd). ~1s, deterministic, no LLM hallucination. Falls through to
  Firecrawl + Claude extractor for any other host.
- **ATS-friendly resume render** — generic master CV → Calibri 11pt
  single-column DOCX (Pandoc, ATS-safe template) → PDF (LibreOffice
  headless). Styled HTML preview rendered in an iframe matches the
  downloaded artifact exactly.
- **Per-job tailored CV** via the `/cv-tailor` Claude skill — rewrites
  the summary against the JD, ranks bullets by `variant_hint`
  (`vibe_coding` / `ai_automation` / `ai_video`), pipes through the
  same DOCX/PDF chain. Triggered from any Application card.
- **Auto-scrape every 3h** across 3 variant-targeted configs, AI-scored
  per-job (Sonnet) with `suggested_variant` + ATS keyword overlap.
- **Cold-email drafting** straight into your IMAP `INBOX.Drafts` —
  initial outreach stays manual, follow-ups auto-fire 5d / 10d after
  `email_sent_at`.

## Dev quickstart

Prerequisites: Docker, Python 3.12, Node 20+.

```bash
cp .env.example .env
make db-up                                   # Postgres on :5433
cd backend && python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python scripts/seed_admin.py
.venv/Scripts/python scripts/seed_master_cv.py
.venv/Scripts/python scripts/generate_cv_template.py   # ATS DOCX template
cd .. && make dev-backend                    # API on :8000

cd frontend && npm install
npm run dev                                  # UI on :3000
```

Sign in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`.

## Ship-ready actions

| Action | Command |
|---|---|
| Backend tests | `make test-backend` |
| Backend lint | `make lint` |
| Backend typecheck | `make typecheck` |
| Frontend full build (catches Next.js ESLint errors `tsc` misses) | `cd frontend && npm run build` |
| Trigger a scrape | `make scrape-run CONFIG=1` |
| Import master CV (JSON fast-path) | `POST /api/cv/master/import-url {"url": "https://alisadikinma.com/en"}` |
| Download generic ATS resume | `GET /api/cv/master/download/{docx\|pdf}` |
| Generate tailored CV (per application) | `POST /api/cv/generate {"application_id": N}` |

## Production deploy (srv941303, Traefik)

Set these in `.env` (alongside `docker-compose.yml`):

- `POSTGRES_PASSWORD` · `JWT_SECRET` (≥32 bytes) · `ADMIN_EMAIL`,
  `ADMIN_PASSWORD` · `CALLBACK_SECRET` (≥32 bytes) ·
  `APIFY_FERNET_KEY` (`Fernet.generate_key()`).
- Optional: `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`, `PROXY_URL` +
  credentials for JobSpy residential proxy.
- Optional: `PORTFOLIO_CV_TOKEN` to enable the alisadikinma.com JSON
  fast-path on `/api/cv/master/import-url`. Without it, imports from
  alisadikinma.com fall back to the Firecrawl + LLM extractor (~20-40s
  vs ~1s, plus LLM hallucination risk on skill names).
  `docker-compose.yml` already lists the variable in the api service's
  `environment:` block — adding it to `.env` alone won't propagate.

```bash
docker compose build
docker compose up -d
# Optional: enable Firecrawl self-hosted (requires upstream image build)
docker compose --profile firecrawl up -d
```

Traefik labels are wired for `jobs.alisadikinma.com` + `/api` path
split. The API container runs `alembic upgrade head` + `seed_admin.py`
on boot.

## Architecture

- **23-phase build plan**: [docs/plans/2026-04-15-jobhunter-mvp-design.md](docs/plans/2026-04-15-jobhunter-mvp-design.md)
- **Project memory**: [CLAUDE.md](CLAUDE.md) — tech stack, conventions,
  architecture decisions (sync SQLAlchemy, PyJWT, TIMESTAMPTZ).
- **Claude plugin** (separate repo): https://github.com/alisadikinma/jobhunter-plugin —
  skills (`/jobhunter:job-score`, `/jobhunter:cv-tailor`, `/jobhunter:cold-email`)
  + refs + a plugin-level CLAUDE.md describing the subprocess + callback
  contract. Run `make plugin-init` to clone it as a sibling for local dev.
