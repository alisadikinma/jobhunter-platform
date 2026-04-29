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

## Companion plugin repo

Claude skills (`/jobhunter:job-score`, `/jobhunter:cv-tailor`, `/jobhunter:cold-email`)
live in their own repo: **https://github.com/alisadikinma/jobhunter-plugin**.

- **Local dev:** `make plugin-init` clones it to `../claude-plugin/jobhunter-plugin`
  (sibling of this repo). Point `CLAUDE_PLUGIN_PATH` in `.env` at the absolute
  path of the clone.
- **Production:** `backend/Dockerfile` clones the plugin during build via the
  `JOBHUNTER_PLUGIN_REF` build arg (default `main`; pin to a tag for
  deterministic deploys).
- **VPS Claude CLI invocations:** `claude --plugin-dir <path> -p "/jobhunter:..."`
  works once `--plugin-dir` points at the clone.
- **Adding skills:** any complex AI / orchestration task should go into the
  plugin (not the FastAPI backend). The backend stays minimal — scraping,
  storage, kanban, Jaccard ATS. Anything Claude-driven lives in the plugin
  so it can be processed by VPS Claude CLI without a backend redeploy.

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

## Deployment

GitHub Actions auto-deploys to the VPS on every push to `master`:

- **`.github/workflows/deploy.yml`** SSHes into the VPS and runs `scripts/deploy.sh`.
- **`scripts/deploy.sh`** does `git pull` → `docker compose build --pull` → `docker compose up -d` → `docker image prune -f`. Alembic migrations and admin seed run inside the api container's CMD, so no separate migrate step.
- Post-deploy probe: `https://jobs.alisadikinma.com/api/health` (retries 60s while api boots).
- Required GitHub secrets: `VPS_SSH_HOST`, `VPS_SSH_USER`, `VPS_SSH_KEY`, `VPS_PROJECT_PATH` (+ optional `VPS_SSH_PORT`). Full setup in [.github/workflows/README.md](.github/workflows/README.md).
- Manual dispatch flags: `force_rebuild` (after a plugin-only update — busts the Dockerfile `git clone` layer cache) and `skip_frontend`.

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
GET    /api/applications/activity-timeline?days=N    # for dashboard chart

# WebSocket — live progress for any agent_job (CV tailor, cold email, job score)
WS     /ws/progress/{agent_job_id}?token=<JWT>

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

# Health
GET    /api/health                   # liveness probe — used by deploy.yml post-deploy check
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

## Architecture Decisions

- **Sync SQLAlchemy (not async)** — plan mentioned async but the codebase uses sync `create_engine` + `Session` with `psycopg2-binary`. FastAPI runs sync DB dependencies in a threadpool, which is fine for a single-admin workload and avoids the `asyncpg` + `AsyncSession` learning curve. Revisit if request volume ever exceeds ~100 concurrent users.
- **JWT via PyJWT (not python-jose)** — `python-jose` is unmaintained (last release 2022) and has open CVEs; `PyJWT>=2.8` is the industry replacement with near-identical API. All timestamps compared to JWT claims must be timezone-aware (`datetime.now(timezone.utc)`).
- **TIMESTAMPTZ everywhere** — all `DateTime` columns are `DateTime(timezone=True)` mapped to PostgreSQL `TIMESTAMP WITH TIME ZONE`. Existing naive timestamps converted via `AT TIME ZONE 'UTC'` in migration `003_fk_tz_jsonb`.

## Debugging Checklist

Non-obvious gotchas discovered during the 23-phase build. Hit any of these first
before you go deeper.

### Backend / infra

- **APScheduler is in-process — `--workers 1` only.** Two uvicorn workers means
  two schedulers means duplicate cron-fired scrapes. The Dockerfile pins
  `--workers 1` (`backend/Dockerfile:50`); don't override that in
  `docker-compose.yml` to "scale up".
- **Postgres is on port 5433, not 5432.** Avoids a clash with the Portfolio_v2
  MySQL stack on the same host. Set `DATABASE_URL=...:5433/...` everywhere —
  the dev compose, the prod compose, and any local scripts. `pytest-postgresql`
  in `tests/conftest.py` also expects `:5433`.
- **Auth uses `bcrypt` directly, not `passlib[bcrypt]`.** `passlib` broke on
  bcrypt 5.x (introspection bug); we hash via `bcrypt.hashpw` /
  `bcrypt.checkpw` in `backend/app/core/security.py`. If you reintroduce
  passlib you'll get a "trapped error reading bcrypt version" cryptic warning
  before every login.
- **JWT was swapped from `python-jose` to `PyJWT`.** `python-jose` is
  unmaintained (last release 2022, open CVEs). Decoding code lives in
  `backend/app/core/security.py::decode_token`; all JWT timestamps must be
  timezone-aware (`datetime.now(timezone.utc)`) or you get the classic
  "expiration claim in the past" false-negative when the host TZ is non-UTC.
- **All `DateTime` columns are TIMESTAMPTZ.** Phases 1–2 used naive
  timestamps; migration `003_fk_tz_jsonb` rewrites them to
  `DateTime(timezone=True)` and casts existing rows via `AT TIME ZONE 'UTC'`.
  New columns must follow suit, otherwise `email_sent_at - replied_at` math
  breaks across DST.
- **`resume-matcher` is intentionally NOT installed.** It's ~400MB of
  torch+spacy for a keyword-overlap metric. We ship a Jaccard-style scorer at
  `backend/app/services/scorer_service.py` instead — the rationale is in the
  module docstring. If you `pip install resume-matcher` "to be safe" you'll
  blow up the Docker image and the Claude CLI install timeout.
- **Pandoc + LibreOffice are both required at runtime for PDF.** Pandoc does
  Markdown → DOCX; LibreOffice headless does DOCX → PDF. Pandoc's PDF engines
  (xelatex, wkhtmltopdf) all break in slim containers — see the docstring at
  `backend/app/services/docx_service.py::docx_to_pdf`. The `cv-template.docx`
  Pandoc reference is generated at Docker build time
  (`backend/Dockerfile`, the `--print-default-data-file` step) so no binary
  lives in git; for dev hosts run
  `python backend/scripts/generate_cv_template.py`.
- **Apify tokens are Fernet-encrypted.** `APIFY_FERNET_KEY` is required even in
  dev — without it `apify_pool.encrypt`/`decrypt` raise on the first DB read.
  Generate via
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Same key encrypts the singleton `mailbox_config.password_encrypted` row.
- **Mailbox creds live in the DB**, not `.env` (managed via
  `/settings/credentials` UI). `.env` `MAIL_*` keys are only a bootstrap
  fallback before the user opens the form. Source of truth:
  `mailbox_config` singleton row id=1.
- **Hostinger / Dovecot Drafts folder is `INBOX.Drafts`, not `Drafts`.**
  Bare `Drafts` returns `NO [TRYCREATE] nonexistent namespace`. Different
  providers use different prefixes — Gmail = `[Gmail]/Drafts`, iCloud =
  `Drafts`, Migadu = `Drafts`. The mailbox config form has a hint;
  default value in `.env.example` is `INBOX.Drafts` to bias toward
  Hostinger / cPanel users.
- **APPENDUID parser must strip `]` glued to the digit.** Hostinger emits
  `APPENDUID 12345 1]` not `[APPENDUID 12345 1]` after split — first
  attempt returned uid `1]`. Fixed in `mailer_service._parse_appenduid`.
- **Firecrawl is opt-in via `--profile firecrawl`.** The two services
  (`firecrawl-api`, `firecrawl-worker`) are profile-gated in
  `docker-compose.yml` because the upstream image is large and not everyone
  needs JD enrichment. Without the profile, `services/firecrawl_service.py`
  short-circuits to a no-op.

### Claude CLI / skills

- **Claude CLI subprocess uses the callback secret, NOT the user JWT.** Spawn
  passes `--api-token <CALLBACK_SECRET>` and the skill calls back via
  `X-Callback-Secret`. If you point a skill at a user-JWT-protected route it
  401s. Add new callback endpoints under `app/api/callbacks.py` only.
- **`CALLBACK_SECRET` ≥32 bytes outside `ENV=dev`.** Same threshold as
  `JWT_SECRET` per RFC 7518 §3.2. The validator in `app/config.py` rejects
  shorter values at startup so you discover this in CI, not at the first cold
  email.
- **Claude CLI flag is `--plugin-dir` (not `--plugin-path`).** The plan was
  written against a hypothetical CLI shape. Real Claude CLI v2 takes
  `--plugin-dir <path>`, repeatable. `app/services/claude_service.py` builds
  the right command — don't re-introduce the old flag from the plan text.
- **`--dangerously-skip-permissions` is the real bypass; `--allow-dangerously-skip-permissions`
  only EXPOSES the option as available.** The spawner uses the former because
  there's no human to approve curl/Bash tool calls inside the subprocess.
- **Subprocess.Popen on Windows needs `.cmd` shim.** npm-installed CLIs ship as
  `claude`, `claude.cmd`, `claude.ps1`. Bare `subprocess.Popen(['claude'])`
  fails with `WinError 2`. Resolved via `shutil.which()` in
  `claude_service._resolve_claude_binary()` — don't bypass it.
- **Slash commands in Claude CLI `-p` print mode do NOT resolve as commands.**
  Discovered during smoke test: `claude -p "/jobhunter:job-score ..."` echoes
  back `Unknown command`. Slash commands are an interactive-mode feature.
  Production-grade skill invocation needs either:
  (a) the Claude Agent SDK in-process inside FastAPI, OR
  (b) `--append-system-prompt-file <skill.md>` + the args as the prompt body, OR
  (c) feed the SKILL.md content as the system prompt and the args as the user
      message verbatim.
  Until one of these lands, `/job-score`, `/cv-tailor`, and `/cold-email`
  cannot be triggered end-to-end. Tracking as Phase 24 follow-up.
- **Plugin dir layout MUST follow Claude conventions:**
  `<dir>/.claude-plugin/plugin.json` manifest + `<dir>/skills/<name>/SKILL.md`
  with YAML frontmatter (`name:`, `description:`). Flat `skills/<name>.md`
  files are silently ignored by `--plugin-dir`.

### .env / settings

- **`Settings()` ignores extra env keys (`extra="ignore"`).** Same `.env` is
  shared with the frontend (`NEXT_PUBLIC_API_URL`) and docker-compose
  (`POSTGRES_PASSWORD`). Without `extra="ignore"` in `app/config.py`, those
  keys crash backend startup with `Extra inputs are not permitted`.
- **Pydantic-settings reads `.env` from CWD, not project root.** Run scripts
  from `backend/` or copy `.env` into `backend/.env` (gitignored, safe).

### Frontend

- **WebSocket auth is via `?token=` query param, not headers.** Browser
  WebSocket constructors can't set headers. `useProgress.ts` reads
  `localStorage` and appends the JWT to the URL; the backend at
  `app/api/ws.py` decodes it via `decode_token()` and closes with code 4401
  on failure. Don't try to add a `Sec-WebSocket-Protocol` workaround.
- **Variant CSS classes (`bg-variant-vibe` / `automation` / `video`) live in
  `tailwind.config.ts`.** If you add a fourth variant, add the matching
  `bg-variant-X` token there or the dashboard chips render transparent.

## Conventions

- Python: snake_case everywhere, type hints required
- TypeScript: camelCase variables, PascalCase components
- Database: snake_case columns, plural table names
- API: REST with consistent response envelope `{success, data, message}`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branches: `feat/<name>`, `fix/<name>`
- No comments unless explaining WHY (not WHAT)
