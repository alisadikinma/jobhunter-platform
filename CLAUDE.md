# JobHunter

Automated job hunting pipeline targeting remote AI-era agency roles (vibe coding, AI automation, AI video) in US/EU/AU markets. Core differentiator: Claude CLI orchestration (Opus for CV tailoring, Sonnet for scoring/email drafting).

## Tech Stack

### Backend
- **Framework:** FastAPI 0.115.x (Python 3.12)
- **ORM:** SQLAlchemy 2.0.x + Alembic 1.14.x
- **Database:** PostgreSQL 16 (port 5433 dev, avoids Portfolio_v2 MySQL conflict)
- **Scheduler:** APScheduler 3.10.x (in-process, no Celery)
- **Auth:** JWT via python-jose + passlib[bcrypt]
- **HTTP Client:** httpx 0.28.x (async)
- **Job Scraping:** python-jobspy 1.1.x (primary for LinkedIn/Indeed/Glassdoor), Apify client (Wellfound)
- **Enrichment:** Firecrawl self-hosted (JD + company research → clean Markdown)
- **ATS Scoring:** resume-matcher
- **Document Gen:** Pandoc subprocess (Markdown → DOCX → PDF)
- **Claude CLI:** subprocess.Popen with plugin mount at /app/claude-plugin

### Frontend
- **Framework:** Next.js 15 (App Router) + React 19
- **State:** TanStack React Query 5.60 (server) + Zustand 5 (client)
- **UI:** shadcn/ui + Tailwind CSS 4 + Lucide React icons
- **Drag-drop:** @dnd-kit/core + @dnd-kit/sortable
- **Charts:** recharts 2.13
- **HTTP:** axios 1.7
- **Testing:** vitest + @testing-library/react

### Infrastructure
- **Containers:** Docker Compose (api + frontend + db + redis + firecrawl-api + firecrawl-worker)
- **Reverse proxy:** Traefik (jobs.alisadikinma.com)
- **VPS:** srv941303 (shared with Portfolio_v2)

## Directory Structure

```
D:\Projects\jobhunter\
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── main.py              # FastAPI entry + CORS + lifespan
│   │   ├── config.py            # pydantic-settings
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── scheduler.py         # APScheduler setup
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── api/                 # Route handlers
│   │   ├── services/            # Business logic (claude, apify_pool, cv_generator, etc.)
│   │   ├── scrapers/            # Per-source scraper implementations
│   │   ├── utils/               # Deduplicator, keyword matcher, etc.
│   │   └── core/                # Security, deps
│   ├── alembic/                 # DB migrations
│   ├── tests/
│   ├── scripts/                 # seed_admin.py, seed_master_cv.py
│   ├── storage/                 # Generated CVs (DOCX/PDF), gitignored
│   ├── templates/               # Pandoc DOCX reference template
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Next.js 15
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   ├── components/          # UI components
│   │   ├── hooks/               # TanStack Query + custom hooks
│   │   └── lib/                 # api.ts, auth.ts, utils.ts
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── claude-plugin/               # Claude Code skills for job hunting
│   ├── CLAUDE.md
│   ├── skills/                  # job-score, cv-tailor, cold-email, company-research
│   ├── refs/                    # refs-cv, refs-email, refs-scoring
│   └── agents/                  # job-hunter batch agent
├── docs/
│   ├── plans/                   # Implementation plans
│   └── seed/                    # master-cv.template.json
├── docker-compose.yml           # Production
├── docker-compose.dev.yml       # Development (db + redis + firecrawl)
├── .env.example
├── Makefile
├── CLAUDE.md                    # This file
└── README.md
```

## Key Commands

```bash
# Development
make dev-backend          # uvicorn app.main:app --reload --port 8000
make dev-frontend         # cd frontend && npm run dev
make db-up                # docker-compose -f docker-compose.dev.yml up -d db
make db-migrate           # cd backend && alembic upgrade head
make db-revision MSG=...  # cd backend && alembic revision --autogenerate -m "$MSG"
make test-backend         # cd backend && pytest -v
make test-frontend        # cd frontend && npm test

# Scraping
make scrape-run CONFIG=1  # curl -X POST localhost:8000/api/scraper/run -d '{"config_id":1}'

# Docker (prod)
make build                # docker-compose build
make up                   # docker-compose up -d
make logs                 # docker-compose logs -f api
```

## API Routes

```
# Auth
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/auth/me

# Jobs
GET    /api/jobs                     # list (filter, sort, paginate)
GET    /api/jobs/{id}
PATCH  /api/jobs/{id}
DELETE /api/jobs/{id}
POST   /api/jobs/{id}/favorite
GET    /api/jobs/stats

# Scraper
POST   /api/scraper/run
GET    /api/scraper/status
GET    /api/scraper/configs
POST   /api/scraper/configs
PUT    /api/scraper/configs/{id}

# Applications
GET    /api/applications
POST   /api/applications
GET    /api/applications/{id}
PATCH  /api/applications/{id}
DELETE /api/applications/{id}
GET    /api/applications/kanban
GET    /api/applications/stats

# CV
GET    /api/cv/master
PUT    /api/cv/master
POST   /api/cv/generate
GET    /api/cv/{id}
PUT    /api/cv/{id}
POST   /api/cv/{id}/score
GET    /api/cv/{id}/download/{format}
GET    /api/cv/{id}/preview

# Emails
POST   /api/emails/generate
GET    /api/emails/{id}
PUT    /api/emails/{id}
POST   /api/emails/{id}/approve
POST   /api/emails/generate-followup

# Enrichment (Firecrawl)
POST   /api/enrichment/job/{job_id}
POST   /api/enrichment/company/{company_id}

# Portfolio
GET    /api/portfolio
POST   /api/portfolio
PATCH  /api/portfolio/{id}
POST   /api/portfolio/{id}/publish
POST   /api/portfolio/{id}/skip
DELETE /api/portfolio/{id}
POST   /api/portfolio/audit

# Apify Pool
GET    /api/apify/accounts
POST   /api/apify/accounts
PATCH  /api/apify/accounts/{id}
DELETE /api/apify/accounts/{id}
POST   /api/apify/accounts/{id}/test

# Callbacks (Claude CLI → FastAPI)
PUT    /api/callbacks/progress/{job_id}
PUT    /api/callbacks/complete/{job_id}
GET    /api/callbacks/context/{application_id}

# Scheduler
GET    /api/scheduler/status
```

## Database Tables

```
users                  # Admin auth (single user)
companies              # Company cache + enriched metadata
scraped_jobs           # All scraped listings + AI scores + suggested_variant
applications           # Job application tracker (status pipeline)
application_activities # Activity log per application
master_cv              # JSON Resume + summary_variants + tagged highlights
generated_cvs          # Tailored CVs per application (markdown + DOCX/PDF paths)
cover_letters          # Generated cover letters
email_drafts           # Cold email + follow-ups
scrape_configs         # 3 variant-targeted configs (keywords, sources, cron)
agent_jobs             # Claude CLI execution tracking (status, progress, result)
apify_accounts         # 5-account free pool for Wellfound scraping
apify_usage_log        # Per-run Apify cost/status audit
portfolio_assets       # Portfolio items for CV tailoring (auto-scanned + manual)
```

## Design System

- **Style:** Data-Dense Dashboard (Linear/GitHub-inspired)
- **Theme:** Dark mode default, light available
- **Fonts:** Fira Sans (UI) + Fira Code (data/mono)
- **Colors:** Blue primary (#3B82F6), Orange CTA (#F97316)
- **Variant colors:** Purple (#A855F7) vibe_coding, Emerald (#10B981) ai_automation, Pink (#EC4899) ai_video
- **Icons:** Lucide React only (1.75px stroke, no emojis)
- **Spacing:** 8px base, 4px for dense data layouts
- **Radius:** 6px buttons/inputs, 8px cards
- **Row height:** 36-40px data tables

## Debugging Checklist

(Populated as issues are discovered during development)

## Conventions

- Python: snake_case everywhere, type hints required
- TypeScript: camelCase variables, PascalCase components
- Database: snake_case columns, plural table names
- API: REST with consistent response envelope `{success, data, message}`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branches: `feat/<name>`, `fix/<name>`
- No comments unless explaining WHY (not WHAT)
