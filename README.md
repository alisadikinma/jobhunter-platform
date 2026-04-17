# JobHunter

Automated AI-era job hunting pipeline: scrape → AI score → CV tailor →
cold email. Built around **Claude CLI** as the core differentiator
(Opus for tailoring, Sonnet for scoring + email drafting).

**Stack:** FastAPI 0.115 · Next.js 15 · PostgreSQL 16 · Claude CLI ·
Pandoc · APScheduler · Firecrawl (self-hosted, optional).

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
| Trigger a scrape | `make scrape-run CONFIG=1` |
| Generate one CV | `POST /api/cv/generate {"application_id": N}` |

## Production deploy (srv941303, Traefik)

Set these in `.env` (alongside `docker-compose.yml`):

- `POSTGRES_PASSWORD` · `JWT_SECRET` (≥32 bytes) · `ADMIN_EMAIL`,
  `ADMIN_PASSWORD` · `CALLBACK_SECRET` (≥32 bytes) ·
  `APIFY_FERNET_KEY` (`Fernet.generate_key()`).
- Optional: `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`, `PROXY_URL` +
  credentials for JobSpy residential proxy.

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
- **Claude plugin**: [claude-plugin/](claude-plugin/) — skills
  (`/job-score`, `/cv-tailor`, `/cold-email`) + refs + a plugin-level
  CLAUDE.md describing the subprocess + callback contract.
