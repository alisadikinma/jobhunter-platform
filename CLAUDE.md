# JobHunter

Automated job hunting pipeline targeting remote AI-era agency roles (vibe coding, AI automation, AI video) in US/EU/AU markets. Core differentiator: Claude CLI orchestration (Opus for CV tailoring, Sonnet for scoring/email drafting).

## 🧠 Vault Context Link

Pre-read MANDATORY via `obsidian` MCP `read-note`:
- `20-Projects/jobhunter/README.md` — pipeline state, scoring rubric versions
- `10-Identity/positioning.md` — USP, target audience (re-read kalau modify CV/email tone)
- `10-Identity/ali.md` — voice (auto-loaded global)

Persist decisions: append ke vault README "Decision Log" via `obsidian` MCP `edit-note`. CV tailoring + cold email harus konsisten dengan positioning vault.

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
│   │   ├── services/            # Business logic — claude, apify_pool, cv_generator,
│   │   │                        # master_cv_renderer, portfolio_cv_api, docx_service, ...
│   │   ├── scrapers/            # Per-source scraper implementations
│   │   ├── utils/               # Deduplicator, keyword matcher, etc.
│   │   └── core/                # Security, deps
│   ├── alembic/                 # DB migrations
│   ├── tests/
│   ├── scripts/                 # seed_admin.py, seed_master_cv.py,
│   │                            # generate_cv_template.py (python-docx ATS template)
│   ├── storage/                 # Generated CVs (DOCX/PDF), gitignored
│   ├── templates/               # cv-ats-template.docx (committed; ATS-friendly
│   │                            # Pandoc reference, regenerated at build time)
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

# CV — master (active record + ATS-friendly download)
GET    /api/cv/master                                # active master_cv content
PUT    /api/cv/master                                # manual JSON edit
POST   /api/cv/master/upload                         # PDF/DOCX/MD/TXT -> LLM parse
POST   /api/cv/master/import-url                     # URL -> JSON-fast-path / md+LLM / Firecrawl
                                                     # body: {url, urls?, include_portfolio?}
                                                     # returns: portfolio_imported / _skipped when JSON path also created drafts
GET    /api/cv/master/preview                        # rendered ATS markdown (no LLM)
GET    /api/cv/master/preview.html                   # standalone styled HTML for iframe srcDoc
GET    /api/cv/master/download/{docx|pdf}            # cached per master_cv.version

# CV — tailored per application (cv-tailor skill via Claude CLI)
POST   /api/cv/generate                              # body: {application_id} -> spawns /cv-tailor
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
POST   /api/portfolio/import-url                     # JSON-fast-path or Firecrawl,
                                                     # URL-dedup on the API path

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
  `backend/app/services/docx_service.py::docx_to_pdf`. Both binaries are
  installed in `backend/Dockerfile`; dev hosts on Windows can render
  preview/download against a running container instead of installing locally.
- **DOCX style template is built programmatically.** `cv-ats-template.docx`
  is committed to `backend/templates/` and regenerated at Docker build time
  via `backend/scripts/generate_cv_template.py` (python-docx, NOT pandoc
  `--print-default-data-file`). The script defines ATS-safe styles —
  Calibri 11pt body, navy H1 24pt, uppercase tracking H2 13pt with bottom
  border, H3 12pt, 0.6"×0.7" margins. Edit the script + commit + redeploy
  to refresh styles deterministically. `CV_REFERENCE_DOCX` env var points
  at this file. The legacy `cv-template.docx` (Pandoc default) was
  retired May 2026; do not reintroduce.
- **HTML preview wraps the same markdown the DOCX uses.** The
  `/api/cv/master/preview.html` endpoint runs `pandoc -t html5` and wraps
  the output in inline `<style>` mirroring the DOCX template
  (24pt H1, 13pt uppercase H2, 12pt H3, Calibri). Frontend
  `AtsCvTab.tsx` feeds the response into `<iframe srcDoc sandbox="">`
  for safe render — sandbox="" blocks JS / forms inside the doc, so any
  CSS/HTML changes that need to interact with the parent must move into
  the React component instead.
- **`master_cv.source_type` was widened from `varchar(20)` to `varchar(64)`
  in migration `014_widen_master_cv_source_type`.** The label
  `portfolio-api-json:alisadikinma.com` (35ch) blew the old ceiling; even
  `url:<longer-fqdn>` was already at the limit. New
  `<provider>-<variant>:<host>` source labels need to fit in 64 — anything
  longer needs a new migration.
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
- **Portfolio CV API JSON fast-path needs `PORTFOLIO_CV_TOKEN` listed in
  `docker-compose.yml`'s `api.environment:` block.** Adding it to `.env`
  alone does NOT pass it through to the container — compose only relays
  variables that are explicitly listed (or `env_file:`-loaded). Same for
  `PORTFOLIO_CV_API_URL`. When the token is missing in-container,
  `host_supports_api()` returns False for alisadikinma.com URLs and the
  import silently falls back to the Firecrawl + LLM path (~20-40s,
  hallucinated skills like "Citus" / "Replit Agent" / "HIKROBOT" instead
  of the deterministic API output).
- **Portfolio_v2 CV data lives in `settings.about.experience`, NOT
  `settings.cv.work_experience`.** The CV API is a content-bearing
  surface that points at the same admin form rows the public /about page
  already renders. Field name mapping (Portfolio_v2 → jobhunter):
    `about.experience.title`       → `work[].position`
    `about.experience.description` → `work[].summary` (HTML stripped)
    `about.experience.end_date ""` → `work[].end_date null`
    `site.contact_email`           → `basics.email`
    `site.contact_phone`           → `basics.phone`
    `about.languages`              → `basics.languages`
    `about.certifications`         → top-level `certifications[]`
  The legacy `cv.work_experience` / `about.email` / `about.phone` settings
  are still consulted as fallbacks but should be considered deprecated.
  Education is the one section without an `about.*` source — it stays at
  `cv.education` until Portfolio_v2 grows a proper Education model.
- **CV import endpoint imports portfolio drafts in the same call by
  default.** When `body.include_portfolio` is true (default) AND the JSON
  fast-path lands AND the host is alisadikinma.com, `/api/cv/master/import-url`
  also creates `portfolio_assets` draft rows from the same `/api/cv/export`
  payload (single fetch, not double-roundtrip). Response carries
  `portfolio_imported` + `portfolio_skipped` counts. URL dedup is
  applied so re-import doesn't balloon the drafts queue. Portfolio
  side-import is best-effort: any error there is logged + swallowed
  (returned as null counts) rather than rolling back the CV save.

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
- **CV import-from-URL scrapes 4 portfolio pages in parallel.** A
  single-page scrape of typical SPAs (alisadikinma.com/en) misses 75%
  of the content because tabs are JS-rendered query-param toggles.
  `app/services/multi_scraper.py` provides `derive_portfolio_urls`
  (heuristic: base, /about, /work?tab=awards, /work?tab=projects) and
  `scrape_multiple_pages` (parallel via ThreadPoolExecutor with the
  Firecrawl pool). The endpoint accepts an optional `urls: list[str]`
  field for advanced mode (custom URL list). Extraction switched from
  haiku-4-5 to sonnet-4-6 with an ATS-aware system prompt that filters
  skills (rejects model names, vendor brands, abstract concepts).
- **Container CLI auth is via `CLAUDE_CODE_OAUTH_TOKEN` env var, NOT
  the credentials file.** The CLI prefers the env var over
  `~/.claude/.credentials.json`, and bind-mounting the credentials file
  alone returns API 401 (token is rotated/superseded by the env-var
  one). The host's claudesn shell exports the env var via
  `~/.bashrc` and `~/.profile`; `scripts/deploy.sh` explicitly sources
  those before `docker compose up`, so the value flows through to
  compose's `${CLAUDE_CODE_OAUTH_TOKEN}` interpolation. The container
  also runs as `user: "1003:1003"` so `--dangerously-skip-permissions`
  works for skill spawns (CLI hard-rejects it as root) and writes go to
  the chowned `cv_storage` volume + `/home/claudesn` (created in the
  Dockerfile so HOME is writable for the CLI's cache/state files).
  Pre-reqs: (a) `export CLAUDE_CODE_OAUTH_TOKEN=...` in the deploy
  user's shell rc; (b) `docker run --rm -v jobhunter_cv_storage:/d
  alpine chown -R 1003:1003 /d` once for the existing volume.
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
- **Internal nav uses `next/link`, not `<a href>`.** Next.js production
  build runs ESLint with `@next/next/no-html-link-for-pages` as a hard
  error, so `<a href="/applications">` aborts the deploy at the
  `npm run build` step. `tsc --noEmit` does NOT catch this; only the
  full Next build does. Either run `npm run build` locally before
  pushing frontend changes OR always use `<Link href="...">` from
  `next/link` for internal routes.

### Deploy

- **Build cache survives Dockerfile RUN changes.** `docker compose build
  --pull` (the default in `scripts/deploy.sh`) refreshes base layers but
  reuses cached `RUN`/`COPY`/`ENV` layers when their immediate inputs
  haven't visibly changed. Symptom: container runs old `ENV
  CV_REFERENCE_DOCX=...` after editing the Dockerfile, or old static
  assets after editing the Next.js build chain. Fix: `DEPLOY_FORCE_REBUILD=1
  ./scripts/deploy.sh` on the VPS, OR trigger the workflow with
  `force_rebuild=true` via `gh workflow run deploy.yml -f
  force_rebuild=true`. The frontend container is similarly cache-prone
  when only `.tsx` files change — the COPY layer hash invalidates but
  npm install can re-run from cache. Force a rebuild after large
  layout changes that don't bump dependencies.
- **`docker compose up -d` does NOT re-read `.env` for already-running
  containers.** It only recreates containers when their image hash
  changed. To pick up new env-var values added to `.env` without a code
  change, use `docker compose up -d --force-recreate <service>`.

## Conventions

- Python: snake_case everywhere, type hints required
- TypeScript: camelCase variables, PascalCase components
- Database: snake_case columns, plural table names
- API: REST with consistent response envelope `{success, data, message}`
- Commits: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- Branches: `feat/<name>`, `fix/<name>`
- No comments unless explaining WHY (not WHAT)

### Model selection by task effort

Pick the cheapest model that can do the job well. Default per effort tier:

| Effort | Model | Model ID | When to use |
|---|---|---|---|
| **High** — complex, ambiguous, multi-file | **Opus 4.7** | `claude-opus-4-7` | Architecture / design, end-to-end feature builds, deep debugging, security review, ambiguous specs, anything needing strategic reasoning across many files. Default for `gaspol-brainstorm`, `gaspol-plan`, `gaspol-design`, `gaspol-debug`, complex `gaspol-execute` phases, `cv-tailor` skill (master CV → tailored variant rewrite). |
| **Medium** — scoped feature work | **Sonnet 4.6** | `claude-sonnet-4-6` | Implement a planned phase, write tests, scaffold modules, code review, docs sync, CV parsing (URL→JSON Resume). Default for `gaspol-execute` mid-complexity phases, `article-prep`, `article-score`, `linkedin-*`, `cv-parser`. |
| **Low** — mechanical / single-file | **Haiku 4.5** | `claude-haiku-4-5-20251001` | Renames, typo fixes, format / lint passes, simple lookups, single-line patches, status checks, classification. Use for `job-score` batch scoring, simple `cold-email` follow-up drafts, log triage. |

Within a Claude Code session, switch via `/model <id>` or per-skill via the skill's frontmatter override. Subagent dispatches inherit the parent model unless the `model` field is set on the `Agent` call.

Claude API spawns from the backend (Python subprocess via `app/services/claude_service.py`) already pass `model_used` per skill — keep that aligned with this table when adding new skills.
