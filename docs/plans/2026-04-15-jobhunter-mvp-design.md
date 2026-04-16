# JobHunter MVP Implementation Plan

> **For Claude:** REQUIRED SKILL: Use gaspol-execute to implement this plan.
> **CRITICAL:** This plan specifies real integrations. During execution,
> NEVER substitute placeholders for real data sources without explicit
> user approval. If a data source doesn't exist yet, STOP and ask.

## Goal

Build a single-user admin app that automates the full job hunting pipeline — scrape → AI score → tailor CV → draft cold email — specifically targeting **remote AI-era agency roles** (vibe coding, AI automation, AI video) in US/EU/AU markets. The core differentiator is **Claude CLI orchestration** (Opus for CV tailoring, Sonnet for scoring and email drafting). Phase 1 ships a standalone working MVP in ~17 days; Phase 2 integrates with Portfolio_v2 as source-of-truth for master CV data.

## Architecture Context

**No existing codebase** — this is a greenfield greenfield project. Source-of-truth decisions from `jobhunter-architecture.md` v1.0 (modified by brainstorm 2026-04-15) and `jobhunter-research-material.md`.

**Reference documents in repo root:**
- [jobhunter-architecture.md](../../jobhunter-architecture.md) — v1.0 architecture baseline
- [jobhunter-research-material.md](../../jobhunter-research-material.md) — open-source tool survey

**Key brainstorm decisions (locked 2026-04-15):**

| # | Decision | Value |
|---|----------|-------|
| 1 | Core value thesis | Claude CLI integration is the differentiator; other tools generic |
| 2 | Execution pattern | FastAPI BackgroundTasks + APScheduler (drop Celery entirely) |
| 3 | Scraping strategy | **3-tier hybrid:** Tier 1 = free APIs (RemoteOK, HN Algolia, HiringCafe, Adzuna, Arbeitnow). Tier 2 = **JobSpy library** (primary LinkedIn/Indeed/Glassdoor with location splitting + TLS fingerprinting, optional residential proxy $5-10/mo). Tier 3 = **Apify free pool (5 accounts)** for Wellfound + emergency LinkedIn fallback. **Plus Firecrawl self-hosted** for JD enrichment + company research. |
| 4 | Target roles | vibe_coding (#1 priority) > ai_automation (#2) > ai_video (#3) |
| 5 | Apify pool algorithm | LRU + `FOR UPDATE SKIP LOCKED`. **Small free pool (5 accounts)** for Wellfound + emergency LinkedIn fallback only. $5/month recurring credit (resets monthly, not lifetime). Not primary scraper — JobSpy handles LinkedIn/Indeed directly. |
| 6 | Master CV model | JSON Resume + modular composition with `summary_variants`, tagged `highlights`, `relevance_hint` arrays |
| 7 | Portfolio assets | Hybrid audit (Claude auto-draft → Ali review via admin UI) |
| 8 | Hourly scraping | 3 variant-targeted configs @ cron `0 */3 * * *` (8x/day each) |
| 9 | Portfolio_v2 integration | **Phase 2 scope** — hybrid webhook + nightly. MVP uses manual CV seed. |

**Stack note:** This project uses FastAPI + Next.js 15 (different from Portfolio_v2's Laravel + Vue). Zero code reuse with Portfolio_v2. Trade-off accepted because Claude CLI orchestration + Python AI ecosystem justify the stack divergence.

## Tech Stack

### Backend (Python)
- **FastAPI** 0.115.x — async API framework
- **SQLAlchemy** 2.0.x (ORM) + **Alembic** 1.14.x (migrations)
- **PostgreSQL** 16 — primary datastore
- **APScheduler** 3.10.x — in-process scheduler (no Redis dependency for scheduling)
- **python-jose** + **passlib[bcrypt]** — JWT auth
- **httpx** 0.28.x — async HTTP client for scrapers
- **python-jobspy** 1.1.x — job scraping library (optional, secondary source)
- **apify-client** — Apify SDK for Wellfound + emergency LinkedIn fallback (small pool)
- **firecrawl-py** — Firecrawl self-hosted client for JD enrichment + company research
- **resume-matcher** — ATS scoring
- **cryptography.fernet** — encrypt Apify tokens at rest
- **pytest** + **pytest-asyncio** — testing
- **subprocess** (stdlib) — Claude CLI invocation

### Frontend (Node.js)
- **Next.js 15** (App Router) + **React 19**
- **TanStack React Query** 5.60 — server state
- **Zustand** 5 — client state
- **shadcn/ui** + **Tailwind CSS 4** — design system
- **@dnd-kit/core** + **@dnd-kit/sortable** — Kanban drag-drop
- **recharts** 2.13 — dashboard charts
- **axios** 1.7 — HTTP client
- **vitest** + **@testing-library/react** — testing

### Infrastructure
- **Docker Compose** — local + prod
- **Traefik** — reverse proxy on VPS srv941303 (shared with Portfolio_v2)
- **Pandoc** — Markdown → DOCX/PDF conversion
- **Claude CLI** — installed in API container, mounted plugin directory

### Claude CLI Plugin Structure
```
claude-plugin/
├── CLAUDE.md                     # Plugin-level context
├── skills/
│   ├── job-score.md              # Sonnet — batch score 20 jobs
│   ├── cv-tailor.md              # Opus — 3-variant CV tailoring
│   ├── cold-email.md             # Sonnet — initial + 2 follow-ups
│   └── company-research.md       # Sonnet — company context (optional P1)
├── refs/
│   ├── refs-cv.md                # 3 variant presets + ATS rules
│   ├── refs-email.md             # Cold email templates per variant
│   └── refs-scoring.md           # Score rubric per variant
└── agents/
    └── job-hunter.md             # Batch agent: score→tailor→email
```

## Data Integration Map

This table is the **CONTRACT** between planner and executor. No placeholders allowed — every "No" row must become a real implementation.

| Feature | Data Source | Hook/API | Exists? | Action |
|---------|-------------|----------|---------|--------|
| User auth | `users` table + JWT | `/api/auth/login` → `useAuth()` | No | Create new |
| Scraped job list | `scraped_jobs` table | `GET /api/jobs` → `useJobs()` | No | Create new |
| Job scoring | Claude CLI `/job-score` via subprocess | `claude_service.py` | No | Create new |
| Apify account pool | `apify_accounts` table | `apify_pool.py` service | No | Create new |
| RemoteOK scraper | `https://remoteok.com/api` | `scrapers/remoteok.py` | No | Create new (official API, free) |
| HN Who is Hiring | Algolia API `hn.algolia.com/api/v1/search` | `scrapers/hn_algolia.py` | No | Create new (official API, free) |
| HiringCafe | Direct crawl `hiring.cafe` | `scrapers/hiring_cafe.py` | No | Create new |
| Adzuna | `api.adzuna.com` | `scrapers/adzuna.py` | No | Create new (register for API key) |
| Arbeitnow | `arbeitnow.com/api` | `scrapers/arbeitnow.py` | No | Create new (free public API) |
| LinkedIn (primary) | `python-jobspy` library | `scrapers/jobspy_linkedin.py` | No | Create new. Location splitting helper bypasses 1000-cap. Optional residential proxy. |
| Indeed | `python-jobspy` library | `scrapers/jobspy_indeed.py` | No | Create new (bundled in same JobSpy wrapper) |
| Glassdoor | `python-jobspy` library | `scrapers/jobspy_glassdoor.py` | No | Create new (bundled in same JobSpy wrapper) |
| Wellfound | Apify actor | `scrapers/wellfound_apify.py` | No | Create new (via Apify pool — primary use of Apify) |
| LinkedIn emergency fallback | Apify actor `bebity/linkedin-jobs-scraper` | `scrapers/linkedin_apify.py` | No | Create new. **Disabled by default**, only enabled if JobSpy detected/blocked. |
| Residential proxy rotation | IPRoyal / BrightData | env-driven config in JobSpy | No | Create new (optional, env vars: `PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD`) |
| JD enrichment | **Firecrawl self-hosted** | `firecrawl_service.py` | No | Create new. Auto-fetch full JD markdown when description too short. |
| Company research | **Firecrawl self-hosted** | `firecrawl_service.py` (same) | No | Create new. Used by `/cold-email` for personalization. |
| Master CV | `master_cv` table (JSONB) | `GET /api/cv/master` → `useMasterCV()` | No | Create new. Phase 1 manual seed; Phase 2 Portfolio_v2 sync |
| Portfolio assets | `portfolio_assets` table | `GET /api/portfolio` → `usePortfolioAssets()` | No | Create new |
| Portfolio audit script | `portfolio_auditor.py` service | Admin button → `POST /api/portfolio/audit` | No | Create new (scans `~/.claude/plugins/cache/` + `D:/Projects/`) |
| CV tailoring | Claude CLI `/cv-tailor` subprocess | `cv_generator.py` | No | Create new |
| Generated CV storage | `generated_cvs` table + filesystem `storage/cvs/` | `GET /api/cv/{id}/download/{format}` | No | Create new |
| ATS scoring | `resume-matcher` library | `scorer_service.py` | No | Create new (import Python lib) |
| Pandoc conversion | Pandoc subprocess | `docx_service.py` | No | Create new (subprocess.run) |
| Applications | `applications` table | `GET /api/applications/kanban` → `useApplications()` | No | Create new |
| Kanban board | `applications` grouped by status | `/applications` page | No | Create new (dnd-kit) |
| Cold email drafts | `email_drafts` table | Claude CLI `/cold-email` | No | Create new |
| Scrape configs | `scrape_configs` table | `GET /api/scraper/configs` | No | Create new. Seed 3 variant configs |
| Scheduler | APScheduler in-process | `scheduler.py` in FastAPI lifespan | No | Create new (replaces Celery Beat) |
| Background job tracking | `agent_jobs` table + progress callback | `PUT /api/callbacks/progress/{job_id}` | No | Create new |
| WebSocket progress | Native FastAPI WebSocket | `/ws/progress/{job_id}` → `useProgress()` | No | Create new |
| Dashboard stats | `GET /api/jobs/stats` + `/api/applications/stats` | `useStats()` | No | Create new |
| Design system | shadcn/ui + Tailwind 4 | Components in `src/components/ui/` | No | Install shadcn, scaffold base |

**Phase 2 scope (NOT built in MVP):**
| Feature | Data Source | Notes |
|---------|-------------|-------|
| Portfolio_v2 CV sync (webhook) | `POST /api/callbacks/cv-sync` | Phase 2. Columns pre-added to `master_cv` in Phase 1 migration. |
| Portfolio_v2 CV sync (nightly) | APScheduler daily 3 AM | Phase 2. Fetches from `portfolio.alisadikinma.com/api/public/cv`. |
| `cv_sync_events` table | New table | Phase 2. Not created in Phase 1. |

---

## Phase Breakdown

### Phase 0: Repo Bootstrap + CLAUDE.md

**Estimated time:** 60 minutes

**Files:**
- Create: `CLAUDE.md` (project-level Claude context)
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md` (minimal)
- Create: `backend/` + `frontend/` + `claude-plugin/` + `docs/` skeleton folders
- Create: `Makefile` (dev/build/deploy shortcuts)
- Create: `docker-compose.dev.yml` (db + redis stubs)

**Steps:**
1. Initialize git repo: `git init && git commit --allow-empty -m "chore: init repo"`
2. Write `CLAUDE.md` with: project overview, tech stack, directory map, key commands, debugging checklist (seeded empty)
3. Create backend/frontend/claude-plugin skeleton directories with empty `.gitkeep`
4. Write `.gitignore` covering Python (venv, __pycache__, .pytest_cache), Node (node_modules, .next), envs, storage files
5. Write `.env.example` with: `DATABASE_URL`, `JWT_SECRET`, `CLAUDE_PATH`, `APIFY_FERNET_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
6. Write minimal `Makefile`: `dev-backend`, `dev-frontend`, `db-up`, `test-backend`, `test-frontend`
7. Write `docker-compose.dev.yml` with postgres:16-alpine on port 5433 (avoid conflict with Portfolio_v2 MySQL)
8. Commit: `chore: bootstrap repo structure with CLAUDE.md`

**Verification:**
- [ ] `CLAUDE.md` exists with all sections (overview, stack, directories, commands, debug checklist)
- [ ] `docker-compose -f docker-compose.dev.yml up -d db` starts postgres on port 5433
- [ ] `psql postgresql://jobhunter:jobhunter@localhost:5433/jobhunter -c "SELECT 1"` returns 1
- [ ] No placeholder/TODO comments in CLAUDE.md

---

### Phase 1: Backend Skeleton + DB Schema (Part 1 — Core Tables)

**Estimated time:** 90 minutes

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/001_init_core.py`
- Create: `backend/app/models/user.py`, `backend/app/models/company.py`, `backend/app/models/job.py`
- Create: `backend/tests/conftest.py`, `backend/tests/test_health.py`

**Steps:**
1. Write `requirements.txt` with pinned versions (fastapi 0.115.*, sqlalchemy 2.0.*, alembic 1.14.*, psycopg2-binary 2.9.*, pydantic-settings 2.7.*, python-jose 3.3.*, passlib 1.7.*, pytest 8.*, pytest-asyncio 0.24.*)
2. Set up venv: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Write `config.py` using `pydantic-settings` with `DATABASE_URL`, `JWT_SECRET`, `CLAUDE_PATH`
4. Write `database.py` with async engine + `get_db()` dependency
5. Write failing test `tests/test_health.py::test_health_endpoint_returns_200`
6. Run `pytest`, confirm fail (endpoint doesn't exist)
7. Write `main.py` with FastAPI app + `/health` endpoint returning `{"status": "ok"}`
8. Run `pytest`, confirm pass
9. Initialize Alembic: `alembic init alembic`
10. Write ORM models: `User`, `Company`, `ScrapedJob` (per architecture.md section 3, tables `users`, `companies`, `scraped_jobs`)
11. Generate migration: `alembic revision --autogenerate -m "init core tables"`
12. Review + adjust migration file (ensure indexes `idx_jobs_status`, `idx_jobs_source`, `idx_jobs_score`, `idx_jobs_scraped_at` are present)
13. Apply: `alembic upgrade head`
14. Verify schema: `psql ... -c "\dt"` shows users, companies, scraped_jobs
15. Commit: `feat(backend): bootstrap FastAPI skeleton + core DB schema`

**Verification:**
- [ ] `pytest backend/tests/` passes
- [ ] `alembic upgrade head` applies cleanly
- [ ] Tables `users`, `companies`, `scraped_jobs` exist in database
- [ ] Indexes `idx_jobs_status`, `idx_jobs_score`, `idx_jobs_scraped_at` exist
- [ ] `GET /health` returns 200 `{"status": "ok"}`
- [ ] No placeholder/TODO comments in new code

---

### Phase 2: DB Schema (Part 2 — Applications, CV, Email, Config, Agent, Apify, Portfolio)

**Estimated time:** 90 minutes

**Files:**
- Create: `backend/app/models/application.py`, `backend/app/models/cv.py`, `backend/app/models/email_draft.py`
- Create: `backend/app/models/scrape_config.py`, `backend/app/models/agent_job.py`
- Create: `backend/app/models/apify_account.py` (with `ApifyUsageLog`)
- Create: `backend/app/models/portfolio_asset.py`
- Create: `backend/alembic/versions/002_applications_cv_email.py`
- Create: `backend/alembic/versions/003_apify_pool.py`
- Create: `backend/alembic/versions/004_portfolio_assets.py`

**Steps:**
1. Write `application.py` models: `Application`, `ApplicationActivity` (per arch section 3)
2. Write `cv.py` models: `MasterCV`, `GeneratedCV`, `CoverLetter`. **IMPORTANT:** pre-add Phase 2 columns to `MasterCV`: `source_type VARCHAR(20) DEFAULT 'manual'`, `source_hash VARCHAR(64)`, `synced_at TIMESTAMP`, `source_version VARCHAR(50)`
3. Add to `MasterCV.content` JSONB: must support `summary_variants: {vibe_coding, ai_automation, ai_video}` (document schema in model docstring)
4. Write `email_draft.py` model: `EmailDraft`
5. Write `scrape_config.py` model: `ScrapeConfig` with **additional column `variant_target VARCHAR(50)`** (values: `vibe_coding`, `ai_automation`, `ai_video`)
6. Write `agent_job.py` model: `AgentJob`
7. Generate + apply migration 002 for all above tables
8. Write `apify_account.py` models: `ApifyAccount`, `ApifyUsageLog`. **Credit model:** free tier only, $5 LIFETIME per account, permanent exhaustion (no reset). Schema fields: `status` (active/exhausted/suspended), `priority`, `lifetime_credit_usd NUMERIC(10,2) DEFAULT 5.00`, `credit_used_usd NUMERIC(10,2) DEFAULT 0.00`, `exhausted_at TIMESTAMP`, `cooldown_until`, `consecutive_failures`, `last_used_at`, `last_success_at`, `last_error`, `notes`. Usage log: `compute_units`, `cost_usd`, `jobs_scraped`. No `is_disposable`, no `quota_reset_at`, no paid variants — simplified for disposable pool.
9. Generate + apply migration 003 for Apify pool
10. Write `portfolio_asset.py` model: `PortfolioAsset` per brainstorm — with `status` (draft/reviewed/published/skipped), `auto_generated BOOLEAN`, `source_path TEXT`, `relevance_hint TEXT[]`, `display_priority INTEGER`
11. Add column `suggested_variant VARCHAR(50)` to `scraped_jobs` in migration 004 (populated by scorer)
12. Generate + apply migration 004
13. Write test `tests/test_models.py::test_all_models_importable` that imports all models and asserts no SQLAlchemy relationship errors
14. Run `pytest`, confirm pass
15. Commit: `feat(backend): add application, cv, email, scrape_config, apify, portfolio schemas`

**Verification:**
- [ ] All 4 migrations apply cleanly in order
- [ ] `psql ... -c "\dt"` shows 13 tables total (users, companies, scraped_jobs, applications, application_activities, master_cv, generated_cvs, cover_letters, email_drafts, scrape_configs, agent_jobs, apify_accounts, apify_usage_log, portfolio_assets)
- [ ] `master_cv` has `source_type`, `source_hash`, `synced_at`, `source_version` columns (Phase 2 prep)
- [ ] `scrape_configs` has `variant_target` column
- [ ] `scraped_jobs` has `suggested_variant` column
- [ ] `portfolio_assets` has `status`, `auto_generated`, `source_path`, `relevance_hint` columns
- [ ] `pytest` passes
- [ ] No placeholder/TODO comments in new code

---

### Phase 3: Auth + User Seed

**Estimated time:** 60 minutes

**Files:**
- Create: `backend/app/api/auth.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/deps.py` (dependency injection)
- Create: `backend/tests/test_auth.py`
- Create: `backend/scripts/seed_admin.py`

**Steps:**
1. Write failing test `test_auth.py::test_login_returns_jwt_for_valid_credentials`
2. Run `pytest`, confirm fail
3. Write `security.py` with `hash_password`, `verify_password`, `create_access_token`, `decode_token`
4. Write `schemas/auth.py` with `LoginRequest`, `TokenResponse`
5. Write `api/auth.py` with `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me`
6. Write `deps.py` with `get_current_user()` FastAPI dependency
7. Include auth router in `main.py`
8. Write `scripts/seed_admin.py` that creates default admin user from env vars (`ADMIN_EMAIL`, `ADMIN_PASSWORD`)
9. Run seed script: `python scripts/seed_admin.py`
10. Run `pytest`, confirm pass
11. Commit: `feat(backend): JWT auth with admin seed`

**Verification:**
- [ ] `POST /api/auth/login` with valid creds returns JWT access token
- [ ] `POST /api/auth/login` with invalid creds returns 401
- [ ] `GET /api/auth/me` with valid JWT returns current user
- [ ] `GET /api/auth/me` without JWT returns 401
- [ ] Admin user exists in DB after seed script
- [ ] `pytest` passes
- [ ] No placeholder/TODO comments in new code

---

### Phase 4: Scraper Infrastructure — API Sources (RemoteOK, HN Algolia, Arbeitnow, Adzuna, HiringCafe)

**Estimated time:** 180 minutes

**Files:**
- Create: `backend/app/scrapers/__init__.py`, `backend/app/scrapers/base.py`
- Create: `backend/app/scrapers/remoteok.py`
- Create: `backend/app/scrapers/hn_algolia.py`
- Create: `backend/app/scrapers/arbeitnow.py`
- Create: `backend/app/scrapers/adzuna.py`
- Create: `backend/app/scrapers/hiring_cafe.py`
- Create: `backend/app/scrapers/aggregator.py`
- Create: `backend/app/utils/deduplicator.py`
- Create: `backend/tests/test_scrapers.py`

**Steps:**
1. Write `base.py` with `BaseScraper` abstract class — methods: `scrape(keywords, locations, limit)` returning `list[NormalizedJob]` pydantic schema
2. Write normalized `NormalizedJob` pydantic schema: title, company_name, location, description, source, source_url, external_id, salary_min, salary_max, remote_type, job_type, posted_at, tech_stack
3. Write `deduplicator.py`: SHA256 hash over `normalize(title + company + description[:200])`
4. Write failing test `test_scrapers.py::test_remoteok_scraper_returns_normalized_jobs`
5. Run `pytest`, confirm fail
6. Implement `remoteok.py` — fetch `https://remoteok.com/api`, filter by keywords, normalize
7. Run test, confirm pass
8. Write failing test for HN Algolia scraper
9. Implement `hn_algolia.py` — query `http://hn.algolia.com/api/v1/search_by_date?query=<kw>&tags=comment,story_<latest_whoshiring_id>` for monthly Who is Hiring thread
10. Run test, confirm pass
11. Write failing test for Arbeitnow
12. Implement `arbeitnow.py` — fetch `https://arbeitnow.com/api/job-board-api` with filters
13. Run test, confirm pass
14. Write failing test for Adzuna (mock response — requires API key registration)
15. Implement `adzuna.py` — fetch `https://api.adzuna.com/v1/api/jobs/{country}/search/{page}` with `app_id` + `app_key` from env
16. Run test, confirm pass
17. Write failing test for HiringCafe scraper
18. Implement `hiring_cafe.py` — direct crawl with BeautifulSoup (check `hiring.cafe` structure; if JS-heavy, defer to P1 or use simpler RSS if available)
19. Run test, confirm pass
20. Write `aggregator.py` — `aggregate(keywords, configs) -> list[NormalizedJob]` with dedup via `deduplicator.py`
21. Write integration test: aggregator calls all scrapers, dedups, returns unique list
22. Run all tests, confirm pass
23. Commit: `feat(scrapers): implement 5 API-first scrapers with aggregator + dedup`

**Verification:**
- [ ] RemoteOK scraper returns ≥1 job when queried with keyword "engineer"
- [ ] HN Algolia scraper returns ≥1 comment from most recent Who is Hiring thread
- [ ] Arbeitnow scraper returns ≥1 job
- [ ] Adzuna scraper returns ≥1 job (requires `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` in .env)
- [ ] HiringCafe scraper returns ≥1 job OR is explicitly marked deferred with documented reason in `hiring_cafe.py`
- [ ] Aggregator dedups duplicate jobs (same hash)
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 5: JobSpy Scraper (Primary LinkedIn/Indeed/Glassdoor) + Small Apify Pool (Wellfound + Emergency)

**Estimated time:** 180 minutes (120 for JobSpy + 60 for simplified Apify pool)

**Files:**
- Create: `backend/app/scrapers/jobspy_scraper.py` (unified wrapper — LinkedIn, Indeed, Glassdoor via python-jobspy)
- Create: `backend/app/utils/location_splitter.py` (generate per-city search URLs to bypass LinkedIn 1000-cap)
- Create: `backend/app/services/encryption.py`
- Create: `backend/app/services/apify_pool.py` (simplified — 5-account pool)
- Create: `backend/app/scrapers/wellfound_apify.py` (primary Apify use case)
- Create: `backend/app/scrapers/linkedin_apify.py` (emergency fallback, disabled by default)
- Create: `backend/app/api/apify.py` (admin CRUD)
- Create: `backend/app/schemas/apify.py`
- Create: `backend/tests/test_jobspy_scraper.py`, `backend/tests/test_apify_pool.py`, `backend/tests/test_location_splitter.py`

**Steps:**

### Part A: JobSpy Primary Scraper (120 min)
1. Add `python-jobspy==1.1.*` to requirements.txt, install
2. Write failing test `test_location_splitter.py::test_generates_per_city_urls_for_remote_us_target`
3. Implement `location_splitter.py::generate_location_variants(base_keywords, target_regions)` — returns list of `{location, search_term}` tuples. For "USA Remote": splits to `San Francisco`, `New York`, `Austin`, `Seattle`, `Remote`. For "Europe": `London`, `Berlin`, `Amsterdam`, `Remote`. For "Australia": `Sydney`, `Melbourne`, `Remote`. ~9-10 variants per config.
4. Run test, confirm pass
5. Write failing test `test_jobspy_scraper.py::test_scrape_with_location_splitting_returns_deduped_jobs`
6. Implement `jobspy_scraper.py::JobSpyScraper.scrape(keywords, locations, limit, site_names)` — wraps `jobspy.scrape_jobs()` with:
   - Location splitting via `location_splitter`
   - 2-5s delay between per-city requests
   - Optional proxy config from env: `PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD` (if set, pass as `proxies` param to jobspy)
   - Handle per-site quirks: LinkedIn (max 1000/search, use `linkedin_fetch_description=True` for full JD), Indeed (less aggressive rate limit), Glassdoor (Cloudflare — may fail gracefully)
   - Normalize output to `NormalizedJob` pydantic schema
   - Dedup within single scrape via `content_hash`
7. Run test, confirm pass
8. Add env vars to `.env.example`: `PROXY_URL`, `PROXY_USERNAME`, `PROXY_PASSWORD` (all optional, empty = direct connection)

### Part B: Simplified Apify Pool (60 min)
9. Write `encryption.py` with `encrypt_token(plain)` and `decrypt_token(encrypted)` using `cryptography.fernet.Fernet` with key from `APIFY_FERNET_KEY` env
10. Write failing test `test_apify_pool.py::test_acquire_returns_active_account_with_budget`
11. Run `pytest`, confirm fail
12. Implement `apify_pool.py::ApifyPool.acquire_account(estimated_cost_usd)` — SQL query with `FOR UPDATE SKIP LOCKED`, filter `status='active' AND credit_used + cost*1.2 <= monthly_credit_usd AND (cooldown_until IS NULL OR cooldown_until <= now)`, order by `priority ASC, last_used_at ASC NULLS FIRST`. Simple LRU across 5 accounts.
13. Run test, confirm pass
14. Write failing test `test_acquire_raises_when_pool_exhausted`
15. Implement `ApifyPoolExhausted` exception + empty-pool handling
16. Write failing test `test_record_usage_updates_credit_and_status`
17. Implement `ApifyPool.record_usage(account_id, cost_usd, jobs_count, status)` — updates `credit_used_usd`. Status transitions: (a) `credit_used + $0.50 safety margin >= monthly_credit_usd` OR `status='quota_exceeded'` → set `status='exhausted'` + `exhausted_at=now()`. Exhausted accounts auto-reactivate on monthly `quota_reset_at`. (b) `rate_limited` → `cooldown_until = now + 1h`. (c) 3 consecutive failures → `status='suspended'`. When pool drops below `ACTIVE_THRESHOLD_WARNING=2` active accounts (of 5 total), trigger admin alert banner.
18. Implement `ApifyPool.reset_monthly_quotas()` — filter `WHERE status='exhausted' AND quota_reset_at <= now()`, set `credit_used_usd=0`, `status='active'`, advance `quota_reset_at` by 30 days. This runs via APScheduler (Phase 14).
15. Run test, confirm pass
19. Write `scrapers/wellfound_apify.py` — wraps Apify Wellfound actor (check Apify store for actor ID). **Primary use case for Apify** — JobSpy doesn't cover Wellfound.
20. Write `scrapers/linkedin_apify.py` — wraps Apify client call to `bebity/linkedin-jobs-scraper` actor. **Disabled by default via env flag `APIFY_LINKEDIN_ENABLED=false`**. Only activate manually via admin if JobSpy direct blocked.
21. Write `schemas/apify.py` — request/response schemas for admin CRUD
22. Write `api/apify.py` — endpoints: `GET /api/apify/accounts`, `POST /api/apify/accounts`, `PATCH /api/apify/accounts/{id}`, `DELETE /api/apify/accounts/{id}`, `POST /api/apify/accounts/{id}/test` (verify token works)
23. API tokens stored encrypted; response schemas never expose decrypted token (only last 4 chars)
24. Include router in `main.py` with auth required
25. Run all tests, confirm pass
26. Commit: `feat(scrapers): JobSpy primary for LinkedIn/Indeed/Glassdoor + small Apify pool for Wellfound`

**Verification:**
- [ ] JobSpy scraper returns ≥1 LinkedIn job for query "AI Engineer Remote" (integration test can use mocked jobspy response if network unavailable)
- [ ] Location splitter generates distinct search URLs per target region (verify: USA Remote → 5+ city variants)
- [ ] JobSpy scraper respects proxy config from env (verify via test with mock proxy)
- [ ] JobSpy scraper enforces 2-5s delay between per-city requests
- [ ] `ApifyPool.acquire_account()` respects `FOR UPDATE SKIP LOCKED` (concurrent calls don't return same account — test with threading)
- [ ] Account status transitions correctly on quota/rate/failure events
- [ ] `ApifyPool.reset_monthly_quotas()` reactivates exhausted accounts past `quota_reset_at`
- [ ] API tokens encrypted at rest (`SELECT api_token FROM apify_accounts` returns gibberish, not plaintext)
- [ ] `GET /api/apify/accounts` lists accounts with masked token (last 4 chars only)
- [ ] `POST /api/apify/accounts/{id}/test` returns success/failure by calling a cheap Apify endpoint
- [ ] Wellfound scraper calls pool, returns jobs
- [ ] LinkedIn Apify scraper respects `APIFY_LINKEDIN_ENABLED` flag (disabled = raises ServiceDisabled error)
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 5.5: Firecrawl Self-Hosted + Enrichment Service

**Estimated time:** 120 minutes

**Why this phase:** Free API aggregators often return truncated job descriptions. Company career pages + About pages are rich context for AI scoring and cold email personalization. Firecrawl self-hosted gives us `url → clean Markdown` for FREE (runs in VPS Docker, no subscription).

**Files:**
- Update: `docker-compose.yml` (add firecrawl-api + firecrawl-worker services)
- Update: `docker-compose.dev.yml` (same)
- Re-add: `redis` service to docker-compose (dropped earlier when Celery removed — Firecrawl needs Redis queue)
- Create: `backend/app/services/firecrawl_service.py`
- Create: `backend/app/schemas/firecrawl.py`
- Create: `backend/app/api/enrichment.py`
- Create: `backend/tests/test_firecrawl_service.py`

**Steps:**

### Part A: Firecrawl Deployment (45 min)
1. Add `firecrawl-api` service to `docker-compose.yml`:
   ```yaml
   firecrawl-api:
     image: firecrawl/firecrawl:latest
     environment:
       - REDIS_URL=redis://redis:6379/1
       - WORKER_MODE=api
       - PORT=3002
     depends_on: [redis]
     restart: unless-stopped
   ```
2. Add `firecrawl-worker` service:
   ```yaml
   firecrawl-worker:
     image: firecrawl/firecrawl:latest
     environment:
       - REDIS_URL=redis://redis:6379/1
       - WORKER_MODE=worker
       - MAX_CONCURRENT_SCRAPERS=5
     depends_on: [redis]
     restart: unless-stopped
   ```
3. Re-add `redis:7-alpine` service (dropped earlier) on port 6380 to avoid conflict with Portfolio_v2
4. Verify locally: `docker-compose up -d firecrawl-api firecrawl-worker redis`
5. Test scrape: `curl -X POST http://localhost:3002/v0/scrape -H "Content-Type: application/json" -d '{"url": "https://example.com"}'` returns markdown

### Part B: Service Wrapper (45 min)
6. Add `firecrawl-py==*` to requirements.txt, install
7. Write failing test `test_firecrawl_service.py::test_scrape_returns_markdown_for_valid_url`
8. Implement `firecrawl_service.py::FirecrawlService.scrape(url, opts={}) -> dict`:
   - Calls local Firecrawl API at `http://firecrawl-api:3002/v0/scrape`
   - Returns `{markdown, title, description, html, metadata}`
   - Handles timeout (60s default), retries (max 2), errors (returns `{error: str, markdown: ""}`)
   - Optional opts: `only_main_content=True`, `wait_for=2000`, `timeout=60000`
9. Implement `FirecrawlService.scrape_with_extraction(url, schema) -> dict`:
   - Uses Firecrawl's schema-based extraction for structured data
   - Useful for company About pages → `{name, industry, size, mission, recent_news}`
10. Run test, confirm pass
11. Write integration test: scrape a real job posting URL, verify markdown contains key fields (title, company, description)

### Part C: API Integration Points (30 min)
12. Write `schemas/firecrawl.py`: `EnrichmentRequest`, `EnrichmentResponse`, `CompanyResearchResponse`
13. Write `api/enrichment.py`:
    - `POST /api/enrichment/job/{job_id}` — fetch full JD markdown from `source_url`, update `scraped_jobs.description` with enriched content, set `scraped_jobs.enriched_at`
    - `POST /api/enrichment/company/{company_id}` — scrape company domain + store in `companies.metadata.enriched_context` (JSONB)
14. Schema additions: `ALTER TABLE scraped_jobs ADD COLUMN enriched_at TIMESTAMP`, `ALTER TABLE scraped_jobs ADD COLUMN description_source VARCHAR(20) DEFAULT 'aggregator'` (values: aggregator, firecrawl_enriched)
15. Extend `api/callbacks.py` `GET /api/callbacks/context/{application_id}` to include enriched JD markdown (when available) for `/cv-tailor` and `/cold-email`
16. Commit: `feat(firecrawl): self-hosted enrichment service for JD + company research`

**Verification:**
- [ ] `docker-compose up -d` starts firecrawl-api + firecrawl-worker + redis — all healthy
- [ ] `FirecrawlService.scrape("https://example.com")` returns markdown string (non-empty)
- [ ] `POST /api/enrichment/job/{id}` updates `scraped_jobs.description` with longer content (verify length grows)
- [ ] `scraped_jobs.description_source='firecrawl_enriched'` after enrichment
- [ ] Callback context endpoint includes enriched description when available
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 6: Scraped Jobs API + Scrape Configs API

**Estimated time:** 120 minutes

**Files:**
- Create: `backend/app/api/jobs.py`
- Create: `backend/app/api/scraper.py`
- Create: `backend/app/schemas/job.py`
- Create: `backend/app/schemas/scrape_config.py`
- Create: `backend/app/services/scraper_service.py`
- Create: `backend/tests/test_jobs_api.py`, `backend/tests/test_scraper_api.py`
- Create: `backend/alembic/versions/005_seed_scrape_configs.py` (seed 3 variant configs)

**Steps:**
1. Write `schemas/job.py`: `JobResponse`, `JobListResponse`, `JobUpdateRequest`, `JobStatsResponse`, `JobFilter`
2. Write `schemas/scrape_config.py`: `ScrapeConfigResponse`, `ScrapeConfigCreate`, `ScrapeConfigUpdate`
3. Write failing test `test_jobs_api.py::test_list_jobs_returns_paginated_results`
4. Run `pytest`, confirm fail
5. Implement `api/jobs.py`: `GET /api/jobs` (filters: status, source, min_score, variant; sort: relevance_score DESC, scraped_at DESC; paginate)
6. Implement `GET /api/jobs/{id}`, `PATCH /api/jobs/{id}` (update status), `DELETE /api/jobs/{id}`, `POST /api/jobs/{id}/favorite`, `GET /api/jobs/stats`
7. Run tests, confirm pass
8. Write `services/scraper_service.py::run_scrape_config(config_id)` — orchestrates: load config → resolve sources → run aggregator → dedup vs existing `content_hash` → insert new jobs → return stats `{total, new, duplicates}`
9. Write failing test `test_scraper_api.py::test_manual_scrape_run_inserts_jobs`
10. Implement `api/scraper.py`: `POST /api/scraper/run` (body: `config_id` or inline keywords), `GET /api/scraper/status`, `GET /api/scraper/configs`, `POST /api/scraper/configs`, `PUT /api/scraper/configs/{id}`
11. Run tests, confirm pass
12. Write migration 005 with seed SQL for 3 scrape configs (per brainstorm spec): `Vibe Coding Remote (US/EU/AU)`, `AI Automation Engineer Remote`, `AI Video Generation Specialist`. Each with variant_target, keywords array, cron `0 */3 * * *`, sources array, max_results_per_source=30
13. Apply migration
14. Run full scrape via `POST /api/scraper/run` with seeded vibe_coding config; verify jobs inserted with `suggested_variant='vibe_coding'`
15. Commit: `feat(backend): jobs + scraper API with 3 seeded variant configs`

**Verification:**
- [ ] `GET /api/jobs?status=new&min_score=70&sort=score` returns filtered + sorted list
- [ ] `GET /api/jobs/stats` returns counts by source, status, suggested_variant
- [ ] `POST /api/scraper/run` inserts new jobs with `suggested_variant` populated from config
- [ ] 3 scrape configs seeded in DB after migration 005 applies
- [ ] Dedup works: running same scrape twice does not insert duplicates (validate via `content_hash` uniqueness)
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 7: Claude CLI Service + `/job-score` Skill

**Estimated time:** 180 minutes

**Files:**
- Create: `backend/app/services/claude_service.py`
- Create: `backend/app/api/callbacks.py`
- Create: `backend/app/schemas/callbacks.py`
- Create: `claude-plugin/CLAUDE.md`
- Create: `claude-plugin/skills/job-score.md`
- Create: `claude-plugin/refs/refs-scoring.md`
- Create: `backend/tests/test_claude_service.py`

**Steps:**
1. Write `claude-plugin/CLAUDE.md` with plugin overview, auth flow (receives `--api-url` + `--api-token`), callback URL pattern, max tokens guidance
2. Write `claude-plugin/refs/refs-scoring.md` with 3-variant scoring rubric (per architecture section 5): skill match 40%, role fit 25%, remote/location 15%, salary 10%, company 10%. Plus variant-specific signal detection (`vibe_coding` keywords, `ai_automation` keywords, `ai_video` keywords)
3. Write `claude-plugin/skills/job-score.md` with: input params (`--batch-ids`, `--api-url`, `--api-token`), process flow, variant classification logic, expected callback format
4. Write failing test `test_claude_service.py::test_spawn_claude_subprocess_tracks_agent_job`
5. Implement `claude_service.py::spawn_claude(skill_name, args, reference_id, reference_type)`:
   - Inserts `agent_jobs` row with `status='pending'`
   - Uses `subprocess.Popen([CLAUDE_PATH, '--plugin-path', '/app/claude-plugin', skill_name, ...args])`
   - Captures stdout/stderr to agent_jobs.progress_log
   - Returns `agent_job_id`
6. Run test, confirm pass (with mocked subprocess)
7. Write `schemas/callbacks.py`: `ProgressUpdate`, `CompletionResult`, `JobScoreResult`
8. Write `api/callbacks.py`:
   - `PUT /api/callbacks/progress/{job_id}` — auth via shared token, updates `agent_jobs.progress_pct`, `current_step`, appends to `progress_log`
   - `PUT /api/callbacks/complete/{job_id}` — validates result schema, updates `agent_jobs.status='completed'`, `result` JSONB. For `job_score` type: also updates `scraped_jobs.relevance_score`, `score_reasons`, `match_keywords`, `suggested_variant`
   - `GET /api/callbacks/context/{job_id}` — returns context needed by skill (master_cv, job details, etc) — authenticated via shared token
9. **Firecrawl enrichment integration:** In `/job-score` skill pre-processing step, if any job in batch has `len(description) < 500 chars`, auto-trigger `POST /api/enrichment/job/{id}` BEFORE scoring. Enriched descriptions give Claude richer context → more accurate scores.
10. Run integration test: spawn real `/job-score` against 3 seeded jobs; verify `agent_jobs` completes; verify `scraped_jobs.relevance_score` populated; verify short-description jobs got enriched (description_source='firecrawl_enriched')
11. Commit: `feat(claude): /job-score skill with 3-variant rubric + Firecrawl enrichment + callback pipeline`

**Verification:**
- [ ] `claude-plugin/CLAUDE.md` and `skills/job-score.md` exist with all documented sections
- [ ] `refs-scoring.md` includes all 3 variant signal sets
- [ ] `spawn_claude()` creates `agent_jobs` row and Popen subprocess
- [ ] `PUT /api/callbacks/progress/{id}` updates progress_pct and current_step
- [ ] `PUT /api/callbacks/complete/{id}` for job_score updates `scraped_jobs.relevance_score` AND `suggested_variant`
- [ ] Real end-to-end: scoring 3 jobs results in 3 jobs with `relevance_score > 0` and `suggested_variant` in {vibe_coding, ai_automation, ai_video, null}
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 8: Master CV Editor + Schema

**Estimated time:** 120 minutes

**Files:**
- Create: `backend/app/api/cv.py` (master CV endpoints only — generated CV in Phase 10)
- Create: `backend/app/schemas/cv.py`
- Create: `backend/scripts/seed_master_cv.py`
- Create: `backend/tests/test_cv_api.py`

**Steps:**
1. Write `schemas/cv.py`: `MasterCVContent` pydantic schema enforcing JSON Resume structure + `summary_variants: {vibe_coding: str, ai_automation: str, ai_video: str}` + `work[*].highlights[*]: {text, tags, metrics?, relevance_hint}`
2. Validate `relevance_hint` values MUST be one of `["vibe_coding", "ai_automation", "ai_video"]`
3. Write failing test `test_cv_api.py::test_get_master_cv_returns_active_version`
4. Implement `api/cv.py`:
   - `GET /api/cv/master` — returns active master_cv (highest version where `is_active=true`)
   - `PUT /api/cv/master` — validates content against `MasterCVContent` schema, increments version, marks old version `is_active=false`
5. Run tests, confirm pass
6. Write `scripts/seed_master_cv.py` — reads a file `docs/seed/master-cv.json` (Ali creates this manually outside of this plan; script reads it and inserts) OR creates a minimal template if file absent
7. Create `docs/seed/master-cv.template.json` with placeholder JSON Resume structure + all 3 `summary_variants` slots + example `relevance_hint` tagging
8. Commit: `feat(backend): master CV CRUD with JSON Resume + 3-variant schema`

**Verification:**
- [ ] `PUT /api/cv/master` with invalid `relevance_hint` (e.g., `["ai_image"]`) returns 422 validation error
- [ ] `PUT /api/cv/master` with valid content creates new version and deactivates old
- [ ] `GET /api/cv/master` returns only active version
- [ ] Template file `docs/seed/master-cv.template.json` exists with all required sections documented
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 9: Portfolio Assets CRUD + Hybrid Audit Script

**Estimated time:** 150 minutes

**Files:**
- Create: `backend/app/api/portfolio.py`
- Create: `backend/app/schemas/portfolio.py`
- Create: `backend/app/services/portfolio_auditor.py`
- Create: `backend/tests/test_portfolio_api.py`, `backend/tests/test_portfolio_auditor.py`

**Steps:**
1. Write `schemas/portfolio.py`: `PortfolioAssetResponse`, `PortfolioAssetCreate`, `PortfolioAssetUpdate`, `PortfolioAuditResult`
2. Write failing test `test_portfolio_api.py::test_list_assets_filtered_by_status`
3. Implement `api/portfolio.py`:
   - `GET /api/portfolio` — list with `?status=draft|published|skipped` filter
   - `POST /api/portfolio` — manual add (for external assets like alisadikinma.com)
   - `PATCH /api/portfolio/{id}` — edit metadata
   - `POST /api/portfolio/{id}/publish` — transition `draft` → `published` (set `reviewed_at`, `reviewed_by`)
   - `POST /api/portfolio/{id}/skip` — transition to `skipped`
   - `DELETE /api/portfolio/{id}`
   - `POST /api/portfolio/audit` — trigger auto-scan, returns count of new drafts created
4. Run tests, confirm pass
5. Write `services/portfolio_auditor.py::PortfolioAuditor.scan() -> list[dict]` with:
   - `_scan_plugins()` — iterate `~/.claude/plugins/cache/*/`, read `CLAUDE.md` + `plugin.json` if present
   - `_scan_projects()` — iterate `D:/Projects/*/CLAUDE.md`, read project-level metadata
   - `_parse_plugin(path, claude_md)` — extract title (H1 or frontmatter), description (first paragraph, truncate to 300), tech_stack (regex-infer from code + CLAUDE.md stack sections), tags (keyword inference), relevance_hint (`_classify_variants()`)
   - `_classify_variants(content)` — regex-based classification mapping content to `ai_video`, `ai_automation`, `vibe_coding` hints (default: `["vibe_coding"]`)
   - Idempotent upsert: detect existing by `source_path`, only INSERT new or UPDATE if `content_hash` changed
6. Write failing test `test_portfolio_auditor.py::test_scan_generates_drafts_for_known_plugins`
7. Implement scan, run test with test fixtures (mock `~/.claude/plugins/cache/` with 2 sample plugins)
8. Run test, confirm pass
9. Execute real audit: `POST /api/portfolio/audit` → verify drafts created for gaspol-dev, ai-image-carousel-prompt-gen, ai-video-promo-engine, article-content-writer, Portfolio_v2, JobHunter (6 expected)
10. Commit: `feat(portfolio): CRUD + hybrid audit script for 6 known assets`

**Verification:**
- [ ] `POST /api/portfolio/audit` creates ≥6 draft portfolio_assets (gaspol-dev, carousel-gen, video-promo-engine, article-writer, Portfolio_v2, JobHunter)
- [ ] Auto-generated drafts have `auto_generated=true`, `status='draft'`, correct `source_path`
- [ ] `relevance_hint` correctly assigned per plugin (video-promo has `ai_video`, article-writer has `ai_automation`, JobHunter has `vibe_coding`+`ai_automation`)
- [ ] Re-running audit is idempotent (no duplicates)
- [ ] `POST /api/portfolio/{id}/publish` transitions status and sets `reviewed_at`
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 10: `/cv-tailor` Skill (3 Variants) + Generated CV Storage

**Estimated time:** 240 minutes

**Files:**
- Create: `claude-plugin/skills/cv-tailor.md`
- Create: `claude-plugin/refs/refs-cv.md`
- Create: `backend/app/services/cv_generator.py`
- Create: `backend/app/api/cv_generate.py` (generation endpoints only)
- Extend: `backend/app/api/cv.py` for generated CV endpoints
- Create: `backend/tests/test_cv_generator.py`

**Steps:**
1. Write `claude-plugin/refs/refs-cv.md` with:
   - **ATS rules** (single column, standard headers, 70-80% JD keyword match, BOTH acronym + full term, no tables/graphics)
   - **Variant 1: vibe_coding preset** (priority 1) — header tagline template, summary rewrite instructions, tag priority `[claude-code, rapid-build, full-stack, saas]`, skill section order `[ai_tooling, full_stack, automation, generative_media]`, portfolio filter rules
   - **Variant 2: ai_automation preset** (priority 2) — tag priority `[automation, claude-cli, pipeline, mcp, n8n]`, skill section order `[automation, ai_tooling, infrastructure, full_stack]`
   - **Variant 3: ai_video preset** (priority 3) — tag priority `[video, image-generation, runway, veo, pipeline]`, skill section order `[generative_media, automation, ai_tooling, full_stack]`
   - **Bullet ranking algorithm** (score function) documented for Claude to follow
   - **Confidence thresholds** (vibe_coding 0.40, ai_automation 0.55, ai_video 0.60) for classification
2. Write `claude-plugin/skills/cv-tailor.md` with:
   - Input: `--application-id`, `--api-url`, `--api-token`
   - Process flow:
     1. GET `/api/callbacks/context/{application_id}` → receives `{master_cv, job, portfolio_assets, company}`
     2. JD classification → pick variant A/B/C OR return `no_match` error
     3. Load variant preset from refs-cv.md
     4. Select `summary_variants[variant_key]` OR generate fresh (variant preset rules)
     5. Filter + rank `work.highlights` by bullet ranking algorithm
     6. Pick top 3-5 bullets per work entry
     7. Select top 3-4 `portfolio_assets` by relevance_hint match + display_priority (filter `status='published'`)
     8. Reorder skills per variant preset
     9. Apply ATS rules
     10. Output markdown + structured JSON
     11. PUT `/api/callbacks/complete/{job_id}` with `{tailored_markdown, tailored_json, keyword_matches, missing_keywords, variant_used, confidence}`
3. Extend `api/callbacks.py` `GET /api/callbacks/context/{application_id}` to return full context payload
4. Write failing test `test_cv_generator.py::test_generate_cv_spawns_claude_and_creates_generated_cv_row`
5. Implement `services/cv_generator.py::generate_cv(application_id)` — creates `generated_cvs` row with `status='pending'`, spawns `/cv-tailor`, returns `agent_job_id` for tracking
6. Run test, confirm pass (mocked subprocess)
7. Write `api/cv_generate.py`:
   - `POST /api/cv/generate` — body `{application_id}`, returns `{generated_cv_id, agent_job_id}`
   - `GET /api/cv/{id}` — get generated CV detail
   - `PUT /api/cv/{id}` — edit markdown manually
8. Extend callback handler: on `/cv-tailor` completion, update `generated_cvs` row with `tailored_markdown`, `tailored_json`, `status='ready'`
9. Run end-to-end integration test: create application for a seeded job, trigger `POST /api/cv/generate`, wait for completion, verify `generated_cvs.tailored_markdown` populated AND `variant_used` matches expected
10. Commit: `feat(claude): /cv-tailor skill with 3 variants + bullet ranking + ATS rules`

**Verification:**
- [ ] `refs-cv.md` contains all 3 variant presets with priority-ordered tag lists
- [ ] Bullet ranking algorithm documented with scoring weights
- [ ] `POST /api/cv/generate` creates `generated_cvs` row and spawns subprocess
- [ ] End-to-end: real `/cv-tailor` call produces markdown CV with correct variant in `variant_used` field
- [ ] If JD doesn't match any variant with required confidence, result has `variant_used='no_match'` and `status='failed'` (or similar graceful handling)
- [ ] Only `status='published'` portfolio_assets appear in generated CVs
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 11: Pandoc DOCX/PDF Pipeline + ATS Scoring

**Estimated time:** 120 minutes

**Files:**
- Create: `backend/app/services/docx_service.py`
- Create: `backend/app/services/scorer_service.py`
- Extend: `backend/app/api/cv_generate.py`
- Create: `backend/tests/test_docx_service.py`, `backend/tests/test_scorer_service.py`
- Create: `backend/storage/cvs/` directory (gitignored)

**Steps:**
1. Install Pandoc in dev + Docker image (add to `backend/Dockerfile` — apt-get install pandoc)
2. Write failing test `test_docx_service.py::test_markdown_to_docx_creates_valid_file`
3. Implement `docx_service.py::markdown_to_docx(markdown: str, output_path: str) -> Path` using `subprocess.run(['pandoc', '-o', output_path, '--reference-doc=templates/cv-template.docx'])`
4. Create reference DOCX template at `backend/templates/cv-template.docx` with single-column layout, standard fonts (Calibri 11pt), clean section styles
5. Run test, confirm pass (validates output DOCX file exists and is non-empty)
6. Write `docx_service.py::docx_to_pdf(docx_path, pdf_path)` — uses LibreOffice headless OR pandoc with pdf engine (choose one, document reason)
7. Write test for PDF conversion
8. Install `resume-matcher` from PyPI (or git if not on PyPI); document install in requirements.txt
9. Write failing test `test_scorer_service.py::test_ats_score_returns_0_to_100_with_keywords`
10. Implement `scorer_service.py::score_cv(cv_markdown, job_description) -> dict` returning `{score, keyword_matches, missing_keywords, suggestions}`
11. Run test, confirm pass
12. Extend `api/cv_generate.py`:
    - `POST /api/cv/{id}/score` — re-run ATS scoring
    - `GET /api/cv/{id}/download/{format}` — format in `[docx, pdf]`, generates on-demand if missing, caches path in `generated_cvs.docx_path`/`pdf_path`
    - `GET /api/cv/{id}/preview` — returns markdown rendered to HTML (use `markdown2` lib)
13. On `/cv-tailor` completion callback, auto-trigger ATS scoring and DOCX generation; update `generated_cvs.ats_score`, `docx_path`
14. Test end-to-end: generate CV → verify DOCX file created → download DOCX → verify ATS score populated
15. Commit: `feat(cv): Pandoc DOCX/PDF + ATS scoring pipeline`

**Verification:**
- [ ] `markdown_to_docx()` creates valid DOCX file (open-able in Word/LibreOffice)
- [ ] DOCX respects single-column ATS rules (no tables, standard fonts)
- [ ] `docx_to_pdf()` creates valid PDF
- [ ] `scorer_service.score_cv()` returns score 0-100 + keyword lists
- [ ] `GET /api/cv/{id}/download/docx` streams file download
- [ ] After CV generation completes, `generated_cvs.docx_path` and `ats_score` are both populated
- [ ] All tests pass
- [ ] Pandoc + LibreOffice installed in Dockerfile (verified via test container)
- [ ] No placeholder/TODO comments in new code

---

### Phase 12: Application Tracker API + Kanban Backend

**Estimated time:** 120 minutes

**Files:**
- Create: `backend/app/api/applications.py`
- Create: `backend/app/schemas/application.py`
- Create: `backend/app/services/application_service.py`
- Create: `backend/tests/test_applications_api.py`

**Steps:**
1. Write `schemas/application.py`: `ApplicationResponse`, `ApplicationCreate`, `ApplicationUpdate`, `KanbanBoardResponse`, `ApplicationStatsResponse`, `ApplicationActivityResponse`
2. Write failing test `test_applications_api.py::test_create_application_from_job_id`
3. Implement `api/applications.py`:
   - `GET /api/applications` — list with status filter, pagination
   - `POST /api/applications` — body `{job_id}`, creates application with `status='targeting'`
   - `GET /api/applications/{id}` — detail + activities timeline
   - `PATCH /api/applications/{id}` — update status/notes/dates (logs status_change activity automatically)
   - `DELETE /api/applications/{id}`
   - `GET /api/applications/kanban` — returns `{targeting: [...], cv_generating: [...], cv_ready: [...], applied: [...], email_sent: [...], replied: [...], interview_scheduled: [...], interviewed: [...], offered: [...], accepted: [...], rejected: [...], ghosted: [...]}`
   - `GET /api/applications/stats` — response rates, avg time between statuses, counts
4. Implement `application_service.py::log_activity(app_id, activity_type, **kwargs)` — auto-called on status changes
5. Run tests, confirm pass
6. Commit: `feat(backend): applications tracker + Kanban API`

**Verification:**
- [ ] `POST /api/applications` creates application and logs `created` activity
- [ ] `PATCH /api/applications/{id}` with status change auto-creates `status_change` activity in `application_activities`
- [ ] `GET /api/applications/kanban` returns dict grouped by status with all statuses present (empty arrays if none)
- [ ] `GET /api/applications/stats` computes response_rate = replied / email_sent (correct when denominator is 0: return 0, not crash)
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 13: `/cold-email` Skill + Email Drafts API

**Estimated time:** 150 minutes

**Files:**
- Create: `claude-plugin/skills/cold-email.md`
- Create: `claude-plugin/refs/refs-email.md`
- Create: `backend/app/api/emails.py`
- Create: `backend/app/schemas/email.py`
- Create: `backend/app/services/email_generator.py`
- Create: `backend/tests/test_email_api.py`

**Steps:**
1. Write `claude-plugin/refs/refs-email.md` with:
   - Cold email 5-part structure (subject <10 words, personalized opening, value prop with quantified results, social proof, CTA asking conversation not job)
   - Per-variant tone adjustments (vibe_coding = ship velocity narrative, ai_automation = operational impact, ai_video = pipeline infrastructure angle)
   - Word count 75-150
   - Follow-up sequence rules (day 5, day 10, each adds new value)
2. Write `claude-plugin/skills/cold-email.md` — input params, process flow, output schema `{initial: {subject, body}, follow_up_1: {subject, body}, follow_up_2: {subject, body}, strategy, personalization_notes}`. **Firecrawl integration:** skill flow auto-triggers `POST /api/enrichment/company/{company_id}` if `companies.metadata.enriched_context` is null. Claude then reads company About/news markdown for authentic personalized openers (not generic "I noticed your company...").
3. Write `schemas/email.py`
4. Write failing test `test_email_api.py::test_generate_email_creates_3_drafts`
5. Implement `services/email_generator.py::generate_emails(application_id)` — spawns `/cold-email`, creates 3 `email_drafts` rows (email_type: `initial`, `follow_up_1`, `follow_up_2`)
6. Implement `api/emails.py`:
   - `POST /api/emails/generate` — body `{application_id, strategy?}`, triggers generation
   - `GET /api/emails/{id}`, `PUT /api/emails/{id}` (edit), `POST /api/emails/{id}/approve` (status → approved)
   - `POST /api/emails/generate-followup` — regenerate specific follow-up
7. Callback handler update: on `/cold-email` completion, create/update 3 email_drafts rows
8. Run tests, confirm pass; run end-to-end integration test
9. Commit: `feat(claude): /cold-email skill with 3-variant tone + follow-up sequence`

**Verification:**
- [ ] `POST /api/emails/generate` creates exactly 3 `email_drafts` rows (initial, follow_up_1, follow_up_2)
- [ ] Each email body is 75-150 words (validate in test)
- [ ] Subject lines under 10 words
- [ ] Email tone matches application's associated variant (vibe_coding emails mention velocity/MVP shipping)
- [ ] `PUT /api/emails/{id}` allows manual editing
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 14: APScheduler + 3-Hourly Scrape Configs

**Estimated time:** 90 minutes

**Files:**
- Create: `backend/app/scheduler.py`
- Extend: `backend/app/main.py` (lifespan integration)
- Create: `backend/tests/test_scheduler.py`

**Steps:**
1. Add `apscheduler==3.10.*` to requirements.txt, `pip install`
2. Write `scheduler.py::setup_scrape_schedules(app)`:
   - On startup: load active `scrape_configs`, for each create `CronTrigger.from_crontab(config.cron_expression)` scheduled job calling `run_scrape_config(config.id)`
   - Job ID: `scrape-config-{config_id}` (replace_existing=True)
   - Misfire grace time: 300 seconds
3. SKIP — no Apify quota reset job needed (pool is pure free/disposable)
4. Integrate in `main.py` FastAPI `lifespan` context manager
5. Write failing test `test_scheduler.py::test_scheduler_registers_all_active_configs_on_startup`
6. Run tests (use `AsyncIOScheduler` with memory jobstore for tests), confirm pass
7. Add API endpoint `GET /api/scheduler/status` returning list of scheduled jobs + next fire time
8. Verify in dev: start app, check logs show 3 scrape jobs registered + 1 Apify quota reset job
9. Commit: `feat(backend): APScheduler in-process for 3-hourly scraping`

**Verification:**
- [ ] On app startup, 3 scrape jobs registered in scheduler (one per active config)
- [ ] `GET /api/scheduler/status` returns 3 jobs: 3 scrape configs only (no Apify quota reset — pool is disposable)
- [ ] Each scrape job has next_fire_time ≤ 3 hours from now
- [ ] Misfire tolerance is 300 seconds
- [ ] Scheduler gracefully shuts down on app teardown (no orphan threads)
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 15: Frontend — Next.js Bootstrap + Auth + Base Layout

**Estimated time:** 180 minutes

**Files:**
- Create: `frontend/package.json`, `frontend/next.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`
- Create: `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx` (redirect to /dashboard), `frontend/src/app/login/page.tsx`
- Create: `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/components/shared/Sidebar.tsx`
- Create: `frontend/src/app/(authed)/layout.tsx` (authenticated layout wrapper)
- Create: `frontend/src/app/(authed)/dashboard/page.tsx` (stub, populated in Phase 21)
- Create: `frontend/__tests__/useAuth.test.tsx`

**Steps:**
1. `npx create-next-app@15 frontend --ts --tailwind --app` (or manual setup)
2. Install deps: `next@15`, `react@19`, `@tanstack/react-query@5.60`, `axios`, `zustand`, `@dnd-kit/core`, `@dnd-kit/sortable`, `lucide-react`, `recharts`, `date-fns`, `clsx`, `tailwind-merge`
3. Install shadcn/ui: `npx shadcn@latest init` → scaffold button, input, dialog, card, table, toast, sheet components
4. Write `lib/api.ts` — axios instance with base URL from `NEXT_PUBLIC_API_URL`, interceptor that attaches JWT from localStorage, handles 401 by redirecting to /login
5. Write `lib/auth.ts` — helpers: `login(email, pw)`, `logout()`, `getToken()`, `isAuthenticated()`
6. Write failing test `__tests__/useAuth.test.tsx::test_login_stores_token_and_user`
7. Implement `hooks/useAuth.ts` using TanStack Query + Zustand for auth state
8. Run test, confirm pass
9. Write `app/layout.tsx` with `<QueryClientProvider>` + `<Toaster>`
10. Write `app/login/page.tsx` — login form with email/password, uses `useAuth().login()`
11. Write `app/(authed)/layout.tsx` — checks auth; redirects to /login if not authenticated; renders `<Sidebar>` + main content
12. Write `components/shared/Sidebar.tsx` — nav items: Dashboard, Jobs, Applications, CV, Emails, Portfolio, Apify Pool, Settings
13. Write `app/(authed)/dashboard/page.tsx` stub with title + placeholder ("Stats coming in Phase 21" — this is OK because Phase 21 populates it, not a permanent placeholder)
14. Run `npm run dev`, verify: unauthed → /login, after login → /dashboard with sidebar visible
15. Commit: `feat(frontend): Next.js bootstrap + auth + base layout with sidebar`

**Verification:**
- [ ] `npm run build` succeeds (no type errors)
- [ ] Visiting `/` without auth redirects to `/login`
- [ ] Login with valid admin credentials (seeded in Phase 3) redirects to `/dashboard`
- [ ] Invalid login shows error toast
- [ ] Authed layout renders sidebar with 8 nav items
- [ ] Logout clears token and redirects to /login
- [ ] `npm test` passes for `useAuth` tests
- [ ] No placeholder/TODO comments in new code (except Phase-pointer comment in dashboard stub which is acceptable per explicit scoping)

---

### Phase 16: Frontend — Jobs Table + Filters

**Estimated time:** 150 minutes

**Files:**
- Create: `frontend/src/app/(authed)/jobs/page.tsx`
- Create: `frontend/src/app/(authed)/jobs/[id]/page.tsx`
- Create: `frontend/src/components/jobs/JobTable.tsx`
- Create: `frontend/src/components/jobs/JobCard.tsx`
- Create: `frontend/src/components/jobs/JobScoreBar.tsx`
- Create: `frontend/src/components/jobs/JobFilters.tsx`
- Create: `frontend/src/hooks/useJobs.ts`
- Create: `frontend/__tests__/useJobs.test.tsx`, `frontend/__tests__/JobTable.test.tsx`

**Steps:**
1. Write failing test `__tests__/useJobs.test.tsx::test_useJobs_fetches_with_filters`
2. Implement `hooks/useJobs.ts` — TanStack Query hook for `GET /api/jobs` with filter params
3. Run test, confirm pass
4. Write failing test `__tests__/JobTable.test.tsx::test_renders_jobs_with_score_bar`
5. Implement `JobTable.tsx` using shadcn Table — columns: title, company, source, score, variant, scraped_at, status, actions
6. Implement `JobScoreBar.tsx` — visual bar for 0-100 relevance + ATS dual display
7. Implement `JobFilters.tsx` — status dropdown, source multi-select, min_score slider, variant filter, search box
8. Run tests, confirm pass
9. Write `app/(authed)/jobs/page.tsx` — uses `useJobs()` + `JobFilters` + `JobTable` with pagination
10. Write `app/(authed)/jobs/[id]/page.tsx` — job detail with full description, score reasons, "Create Application" button (calls `POST /api/applications`)
11. Verify in browser: `/jobs` loads, filters work, clicking row navigates to detail, detail shows score_reasons
12. Commit: `feat(frontend): jobs table with filters + detail page`

**Verification:**
- [ ] `/jobs` page loads and fetches from `/api/jobs` with real data
- [ ] Filters (status, source, min_score, variant) correctly pass query params
- [ ] JobScoreBar renders score 0-100 visually
- [ ] "Create Application" button on detail page creates application and redirects to `/applications/{id}`
- [ ] Pagination works (next/prev buttons)
- [ ] All frontend tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 17: Frontend — Master CV Editor + Portfolio UI

**Estimated time:** 210 minutes

**Files:**
- Create: `frontend/src/app/(authed)/cv/page.tsx` (master CV editor)
- Create: `frontend/src/components/cv/CVEditor.tsx`
- Create: `frontend/src/components/cv/VariantSummaryEditor.tsx`
- Create: `frontend/src/components/cv/HighlightsEditor.tsx`
- Create: `frontend/src/app/(authed)/portfolio/page.tsx`
- Create: `frontend/src/components/portfolio/PortfolioAssetCard.tsx`
- Create: `frontend/src/components/portfolio/PortfolioDraftTab.tsx`
- Create: `frontend/src/hooks/useMasterCV.ts`, `frontend/src/hooks/usePortfolioAssets.ts`

**Steps:**
1. Implement `hooks/useMasterCV.ts` — `useQuery` for GET, `useMutation` for PUT with optimistic update
2. Implement `hooks/usePortfolioAssets.ts` with filter by status
3. Write `CVEditor.tsx` — form-based editor with sections: basics, summary_variants (3 tabs), work, education, skills, projects
4. Write `VariantSummaryEditor.tsx` — 3 tabs (vibe_coding, ai_automation, ai_video), each with textarea + character count + "suggested opener" hints
5. Write `HighlightsEditor.tsx` — per-work entry list of bullets with: text (textarea), tags (multi-select with autocomplete), metrics (JSON editor), relevance_hint (multi-select: vibe_coding/ai_automation/ai_video ONLY)
6. Frontend validation: `relevance_hint` cannot contain values other than 3 allowed variants (match backend schema)
7. Write `app/(authed)/cv/page.tsx` — full editor with "Save" button → PUT master CV
8. Write `app/(authed)/portfolio/page.tsx` — 3 tabs: Draft, Published, Add External
9. Write `PortfolioAssetCard.tsx` — shows pre-filled fields (from audit), editable fields for Ali to fill (url, thumbnail, metrics, display_priority), Publish/Skip buttons
10. Write `PortfolioDraftTab.tsx` — list of draft assets with "Re-scan" button calling `POST /api/portfolio/audit`
11. Run `POST /api/portfolio/audit` from UI, see 6 draft cards appear, publish 3 manually to test flow
12. Commit: `feat(frontend): master CV editor + portfolio assets hybrid UI`

**Verification:**
- [ ] `/cv` page loads master CV from API and displays in editor
- [ ] Saving CV with invalid `relevance_hint` (e.g., `["ai_image"]`) shows validation error (frontend + backend)
- [ ] Saving valid CV increments version
- [ ] `/portfolio` Draft tab shows 6 auto-generated assets after clicking "Re-scan"
- [ ] Publishing a draft moves it to Published tab
- [ ] External asset can be manually added via "Add External" tab
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 18: Frontend — CV Generation Preview + Download

**Estimated time:** 120 minutes

**Files:**
- Create: `frontend/src/app/(authed)/cv/generated/[id]/page.tsx`
- Create: `frontend/src/components/cv/CVPreview.tsx`
- Create: `frontend/src/components/cv/ATSScoreCard.tsx`
- Create: `frontend/src/components/cv/CVDiff.tsx`
- Create: `frontend/src/components/shared/ProgressModal.tsx`
- Create: `frontend/src/hooks/useProgress.ts` (WebSocket)

**Steps:**
1. Write `hooks/useProgress.ts` — WebSocket connection to `/ws/progress/{agent_job_id}`, streams progress updates
2. Write `ProgressModal.tsx` — modal showing current_step + progress_pct + latest log line, auto-closes on completion
3. Write `CVPreview.tsx` — renders tailored markdown as HTML (use `react-markdown`) side-by-side with original master CV for comparison
4. Write `CVDiff.tsx` — uses `diff` lib to highlight added/removed content
5. Write `ATSScoreCard.tsx` — shows score, keyword_matches (green chips), missing_keywords (red chips), suggestions
6. Write `/cv/generated/[id]/page.tsx` — full preview + download buttons (DOCX/PDF) + "Edit Markdown" action
7. From application detail page (Phase 19), "Generate CV" button triggers `POST /api/cv/generate` and opens `ProgressModal`
8. On completion, navigates to `/cv/generated/{id}`
9. Verify end-to-end: create application → generate CV → progress modal shows live updates → lands on preview → download DOCX works
10. Commit: `feat(frontend): CV preview + ATS scorecard + live progress via WebSocket`

**Verification:**
- [ ] `/cv/generated/{id}` renders tailored markdown as HTML
- [ ] ATSScoreCard shows score, matched keywords (green), missing keywords (red)
- [ ] Download DOCX/PDF buttons trigger file download
- [ ] Progress modal shows live updates during generation (not just final result)
- [ ] CVDiff highlights differences between master CV and tailored version
- [ ] No placeholder/TODO comments in new code

---

### Phase 19: Frontend — Applications Kanban + Detail Page

**Estimated time:** 180 minutes

**Files:**
- Create: `frontend/src/app/(authed)/applications/page.tsx`
- Create: `frontend/src/app/(authed)/applications/[id]/page.tsx`
- Create: `frontend/src/components/applications/KanbanBoard.tsx`
- Create: `frontend/src/components/applications/ApplicationCard.tsx`
- Create: `frontend/src/components/applications/TimelineView.tsx`
- Create: `frontend/src/hooks/useApplications.ts`

**Steps:**
1. Implement `useApplications.ts` — hooks for list, detail, create, update, kanban
2. Write `KanbanBoard.tsx` using `@dnd-kit/core` + `@dnd-kit/sortable`:
   - 12 columns for all statuses (targeting → ghosted/rejected/accepted)
   - Drag-drop between columns triggers `PATCH /api/applications/{id}` with new status
   - Optimistic UI update
3. Write `ApplicationCard.tsx` — compact card showing title, company, variant, CV status, last activity
4. Write `TimelineView.tsx` — vertical timeline of activities from `application_activities` table
5. Write `app/(authed)/applications/page.tsx` — KanbanBoard view (default)
6. Write `app/(authed)/applications/[id]/page.tsx` — detail with: job info, timeline, generated CV link, email drafts, notes editor, action buttons (Generate CV, Generate Email, Update Status)
7. Verify in browser: create application → drag card across statuses → timeline updates
8. Commit: `feat(frontend): applications Kanban + detail page with timeline`

**Verification:**
- [ ] Kanban shows all 12 status columns
- [ ] Drag-drop between columns updates status in DB (verify via API call)
- [ ] Timeline shows status_change activities in reverse chronological order
- [ ] "Generate CV" button from detail page triggers generation and shows progress modal
- [ ] "Generate Email" button creates 3 email drafts
- [ ] Notes save and persist
- [ ] All tests pass
- [ ] No placeholder/TODO comments in new code

---

### Phase 20: Frontend — Email Drafts UI + Apify Pool Admin

**Estimated time:** 120 minutes

**Files:**
- Create: `frontend/src/app/(authed)/emails/page.tsx`
- Create: `frontend/src/components/emails/EmailPreview.tsx`
- Create: `frontend/src/components/emails/EmailEditor.tsx`
- Create: `frontend/src/app/(authed)/apify-pool/page.tsx`
- Create: `frontend/src/components/apify/AccountTable.tsx`
- Create: `frontend/src/components/apify/AddAccountDialog.tsx`

**Steps:**
1. Write `app/(authed)/emails/page.tsx` — list of all email drafts grouped by application
2. Write `EmailPreview.tsx` — renders subject + body with "Copy to clipboard" button + variant badge
3. Write `EmailEditor.tsx` — edit mode with subject + body textarea + regenerate follow-up button
4. Write `app/(authed)/apify-pool/page.tsx` — admin view of account pool
5. Write `AccountTable.tsx` — columns: label, email (masked), status badge, credit used/total bar, last_used_at, next_reset, actions (test/suspend/reactivate/delete)
6. Write `AddAccountDialog.tsx` — form: label, email, api_token (password field), notes. `lifetime_credit_usd` defaults to $5 (editable in case Apify changes policy). No plan type selector — all accounts are free/disposable.
7. Write **Bulk Add Dialog** — textarea accepting lines of format `label,email,token` for fast bulk import of 10-15 accounts at once
8. Write pool health widget on top of page:
   - Status counts (active/exhausted/suspended) with colored badges
   - Total credit remaining / total credit budget (e.g., "$42.50 / $75.00")
   - Daily burn rate (7-day rolling avg)
   - Projected runway in days based on burn rate
   - Sprint progress indicator: "Day N of ~14 target"
   - Alert banner when `active_count < 3` (warning) or `< 1` (critical — auto-disable LinkedIn source)
7. "Test Connection" button calls `POST /api/apify/accounts/{id}/test` to verify token
8. Verify in browser: add 2 test Apify accounts, see them in table, test connections
9. Commit: `feat(frontend): email drafts UI + Apify pool admin`

**Verification:**
- [ ] Email preview shows correct variant-specific tone
- [ ] Copy button copies body to clipboard
- [ ] Edit + save updates draft via PUT API
- [ ] Apify pool table shows all accounts with status badges
- [ ] Adding new account encrypts token (verify by querying DB directly)
- [ ] "Test Connection" returns success for valid token, failure for invalid
- [ ] Credit-used bar visually accurate (color shifts at 80%, 95% thresholds)
- [ ] No placeholder/TODO comments in new code

---

### Phase 21: Frontend — Dashboard Stats + Settings

**Estimated time:** 90 minutes

**Files:**
- Create: `frontend/src/components/dashboard/StatsCards.tsx`
- Create: `frontend/src/components/dashboard/WeeklyChart.tsx`
- Update: `frontend/src/app/(authed)/dashboard/page.tsx`
- Create: `frontend/src/app/(authed)/settings/page.tsx`
- Create: `frontend/src/hooks/useStats.ts`

**Steps:**
1. Implement `hooks/useStats.ts` — fetches `/api/jobs/stats` and `/api/applications/stats`
2. Write `StatsCards.tsx` — 4 cards: total scraped jobs, active applications, response rate, avg score
3. Write `WeeklyChart.tsx` using `recharts` — bar chart of application activity per day (last 14 days)
4. Update `dashboard/page.tsx` — replace stub with StatsCards + WeeklyChart + "Recent High-Score Jobs" table
5. Write `settings/page.tsx` — scrape config CRUD UI (edit keywords per variant, toggle active, see next_run)
6. Commit: `feat(frontend): dashboard + settings pages`

**Verification:**
- [ ] Dashboard loads with real stats from API
- [ ] WeeklyChart renders with actual data (or empty state if no data yet)
- [ ] Settings page allows editing scrape_configs.keywords with validation
- [ ] Changing cron_expression shows warning and confirmation modal
- [ ] No placeholder/TODO comments in new code

---

### Phase 22: Docker + Traefik + Production Deploy

**Estimated time:** 150 minutes

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml` (prod)
- Update: `docker-compose.dev.yml`
- Create: `.github/workflows/deploy.yml` (optional — if using GitHub Actions for CI)
- Update: `Makefile` (deploy target)

**Steps:**
1. Write `backend/Dockerfile` — python:3.12-slim base, install pandoc + libreoffice-core (for PDF), install Claude CLI binary, copy app, run uvicorn
2. Write `frontend/Dockerfile` — node:20-alpine, next build, serve via `node server.js` on port 3000
3. Write `docker-compose.yml` (prod) — per architecture.md section 6 BUT:
   - **Remove** `worker` + `beat` services (no Celery anymore)
   - **Keep** `api`, `frontend`, `db` (Postgres 16)
   - **Add** `redis:7-alpine` on port 6380 (required by Firecrawl)
   - **Add** `firecrawl-api` service (port 3002 internal only, not exposed)
   - **Add** `firecrawl-worker` service with MAX_CONCURRENT_SCRAPERS=5
   - Add Traefik labels per architecture (Host rule `jobs.alisadikinma.com`, PathPrefix `/api`)
4. Ensure `claude-plugin/` volume mounted into `api` container at `/app/claude-plugin`
5. Ensure `storage/` volume mounted for generated CV files
6. Update `.env.example` with all required prod env vars
7. Test `docker-compose up -d` locally — verify all services healthy
8. Test end-to-end: login → trigger scrape → generate CV → download DOCX — all from containerized setup
9. Document deploy steps in `README.md` under "Deploy"
10. Commit: `feat(infra): Docker Compose + Traefik for production deploy`

**Verification:**
- [ ] `docker-compose up -d` starts api, frontend, db, redis, firecrawl-api, firecrawl-worker — all healthy after 30s
- [ ] Claude CLI available inside `api` container (`docker exec api claude --version` returns version)
- [ ] Pandoc available inside `api` container (`docker exec api pandoc --version`)
- [ ] Firecrawl responds: `docker exec api curl http://firecrawl-api:3002/v0/scrape -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com"}'` returns markdown
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] `curl http://localhost:3000` returns Next.js frontend
- [ ] End-to-end flow works in containerized setup (including Firecrawl enrichment during /job-score)
- [ ] Traefik labels correctly route `jobs.alisadikinma.com` and `jobs.alisadikinma.com/api`
- [ ] No placeholder/TODO comments in new code

---

### Phase 23: Smoke Test + Documentation Polish

**Estimated time:** 60 minutes

**Files:**
- Update: `CLAUDE.md` (fill in learnings, gotchas, debug checklist)
- Update: `README.md` (quickstart, architecture diagram, deploy)
- Create: `docs/user-guide.md` (Ali's day-one workflow)

**Steps:**
1. Run full smoke test: fresh DB → seed admin → seed master CV → manually trigger scrape on vibe_coding config → wait for scoring → create application from top job → generate CV → download DOCX → generate email → verify all 4 artifacts present and coherent
2. Document any gotchas discovered in `CLAUDE.md` > Debugging Checklist section
3. Update `README.md` with: prerequisites (Claude CLI installed, Pandoc, Docker), quickstart commands, deploy steps
4. Write `docs/user-guide.md` — Ali's Day-1 workflow: add Apify accounts → seed/edit master CV → publish portfolio assets → trigger first scrape → review top jobs → generate first CV → send first cold email
5. Final commit: `docs: smoke test + user guide + CLAUDE.md polish`

**Verification:**
- [ ] Smoke test passes end-to-end from fresh state
- [ ] CLAUDE.md contains at least 3 non-obvious gotchas discovered during implementation
- [ ] README deploy steps actually work on a fresh VPS simulation
- [ ] User guide covers 7 steps of first-run workflow
- [ ] No placeholder/TODO comments in any doc

---

## Phase 2 (Post-MVP, NOT built in this plan)

Portfolio_v2 integration — deferred per brainstorm Decision 9:

- **JobHunter changes:** Add `/api/callbacks/cv-sync` endpoint with HMAC verification, add APScheduler daily 3 AM sync job, create `cv_sync_events` table, add data mapper (Portfolio_v2 schema → JSON Resume), admin UI `/settings/sync`
- **Portfolio_v2 changes (external):** Add `GET /api/public/cv` + `GET /api/public/projects` endpoints, `SyncJobHunterJob` Laravel queue job, event listeners on CV/Project updates, shared secret env
- **Estimated:** ~3 days (JobHunter side) + ~2 days (Portfolio_v2 side, external to this repo)

---

## Scraping Stack Playbook (Option D — Hybrid)

**Context:** 3-tier hybrid scraping strategy. JobSpy does heavy lifting (LinkedIn/Indeed/Glassdoor direct via TLS fingerprinting), free APIs cover niche remote sources, small Apify pool (5 accounts) handles Wellfound + emergency fallback, Firecrawl self-hosted enriches truncated descriptions and researches companies.

**Apify free tier:** $5/month **recurring** credit per account (resets monthly, NOT lifetime). Pool of 5 gives ~$25/month rolling budget. Monthly reset via APScheduler Phase 14.

### Pool Health Thresholds

```python
ACTIVE_THRESHOLD_WARNING = 2   # <2 active (of 5) → warning banner
ACTIVE_THRESHOLD_CRITICAL = 0  # 0 active → disable Wellfound scraping, rely on Tier 1/2
```

### Tiered Source Strategy

**Tier 1 — Free APIs (zero-risk primary):**
- RemoteOK JSON API — official, free
- HN Who is Hiring via Algolia API — official, free
- Arbeitnow — free public API
- Adzuna — free with registration (API key)
- HiringCafe — direct crawler

**Tier 2 — JobSpy (free self-hosted, primary for LinkedIn/Indeed/Glassdoor):**
- `python-jobspy` library with TLS fingerprinting
- Location splitting helper bypasses LinkedIn's 1000-cap
- Rate limiting: 2-5s delay between per-city requests
- Optional residential proxy ($5-10/mo IPRoyal) if direct scraping blocked
- Target: ~500-1000 LinkedIn jobs/day sustainable

**Tier 3 — Apify Pool (small, niche sources):**
- 5 free accounts × $5/mo = $25/mo rolling credit (resets monthly)
- **Primary use:** Wellfound (JobSpy doesn't cover)
- **Emergency fallback:** LinkedIn via Apify actor — disabled by default, admin toggle
- Pool rotation via LRU + cooldown

**Enrichment Layer — Firecrawl Self-Hosted:**
- 2 Docker containers on VPS (api + worker)
- Zero subscription cost (VPS already paid for Portfolio_v2)
- Auto-enriches jobs with `len(description) < 500` before scoring
- Scrapes company About/news pages for cold-email personalization

### Pre-Launch: Create 5 Apify Accounts (~1-1.5 hours over 2 days)

Much smaller pool than originally planned — just 5 accounts for Wellfound + emergency.

1. Generate 5 fresh emails: `alisadikin+apify01@gmail.com` to `+apify05@`
2. **Day 1:** Signup 3 accounts (rotate VPN)
3. **Day 2:** Signup 2 more accounts
4. Per account: verify email → generate API token
5. Input all 5 to JobHunter admin UI via Bulk Add Dialog
6. "Test Connection" per account

### Pre-Launch: Configure JobSpy (~30 min)

Optional (only if LinkedIn direct scraping blocked):
1. Sign up IPRoyal residential proxy ($5-10/mo) OR BrightData
2. Configure `.env`:
   ```
   PROXY_URL=proxy.iproyal.com:7777
   PROXY_USERNAME=your-username
   PROXY_PASSWORD=your-password
   ```
3. JobSpy auto-detects proxy env vars and routes through

### Alert Behavior

**Warning (active Apify < 2):** Banner on admin dashboard, Wellfound scraping degrades to every 6h.
**Critical (active Apify = 0):** Wellfound disabled. Tier 1 (free APIs) + Tier 2 (JobSpy) continue normally — main pipeline unaffected.

### Detection Mitigation

- Small pool (5 only) = low detection pattern signal
- Space signups over 2 days, rotate VPN IPs
- Email diversity via distinct `+tag` aliases
- LRU spreads load across pool

### Exit Strategy (Post-Offer)

When job offer accepted (sprint success):
1. Disable all `scrape_configs` (set `is_active=false`)
2. Archive application data for future reference
3. Cancel IPRoyal proxy subscription if used ($5-10/mo saved)
4. Apify accounts → leave as-is; monthly $5 credits will just pile up harmlessly
5. JobHunter project becomes dormant — codebase preserved

**Monthly cost after sprint: $0** (unless you keep proxy). Firecrawl runs on existing VPS, zero added infra.

### If Sprint Extends Beyond 14 Days

No action needed — this stack is sustainable indefinitely:
- **Tier 1 APIs:** free forever
- **JobSpy:** free (+ $5-10/mo proxy if needed)
- **Apify pool:** monthly $25 credit resets automatically
- **Firecrawl:** zero recurring cost

Just continue pipeline. This is actually **more sustainable** than the original Apify-only plan.

---

## Phase 3 (Future Enhancements — Claude Managed Agent / Routines)

**Scheduling decision:** APScheduler remains the scheduler for MVP (Phase 14). Claude Managed Agent / Routines deferred to Phase 3 for reasoning-based workflows only. Ali uses Claude Max Plan so invocations are covered by subscription.

**Why deferred (not in MVP):** Keeps Phase 1 simple — deterministic cron jobs don't need LLM reasoning. APScheduler in-process is zero-dependency and fast. Managed Agent adds value only for workflows that require decision-making or summarization.

**Target Managed Agent routines (to be built post-MVP):**

1. **Daily application review (morning routine)**
   - Schedule: daily 7 AM local time
   - Reads current kanban state, summarizes what needs action today (follow-ups due, interviews scheduled, CVs pending approval)
   - Output: dashboard alert or Telegram notification

2. **Hourly high-score alert**
   - Schedule: hourly
   - Queries `scraped_jobs WHERE status='new' AND relevance_score > 85` since last run
   - Pushes notification if new matches found
   - Optional: auto-create application entry in `targeting` status

3. **Weekly CV gap analysis**
   - Schedule: weekly Sunday 9 AM
   - Reads last 30 days' rejected/ghosted applications with their tailored CVs
   - Cross-references to identify pattern failures per variant
   - Writes suggestions to new `master_cv_suggestions` table
   - Ali reviews via admin UI → accept/reject

4. **Bi-weekly scrape strategy review**
   - Schedule: bi-weekly
   - Analyzes yield per source over last 14 days (which source produced highest-score jobs)
   - Suggests rebalancing `scrape_configs.priority` or Apify budget allocation
   - Writes to `scrape_strategy_reviews` table

5. **Monthly portfolio refresh check**
   - Schedule: monthly
   - Compares `portfolio_assets.tech_stack` vs trending keywords from recent high-score JDs
   - Flags outdated descriptions (e.g., "FastAPI + Next.js 14" vs trending "Next.js 15 Server Actions")
   - Suggests updates to each flagged asset

**Integration pattern for Phase 3:**
- JobHunter exposes dedicated endpoints: `POST /api/agent/context/{routine_name}` (returns context payload), `POST /api/agent/result/{routine_name}` (accepts reasoning output)
- Authentication: shared token per routine, rotated via admin UI
- All agent outputs persisted to dedicated `*_suggestions` or `*_reviews` tables — never auto-applied without Ali review
- New admin UI section `/settings/routines` to view execution history + enable/disable

**Estimated:** ~5 days total for all 5 routines + admin UI.

**Why Max Plan changes the calculus:**
Claude Max subscription covers Managed Agent invocations at flat rate. No per-token cost. This makes LLM-reasoned scheduled workflows economically viable for single-user tools like JobHunter, whereas pay-per-token would make them cost-prohibitive at hourly cadence.

---

## Total Estimated Time

| Phase range | Focus | Days |
|-------------|-------|------|
| Phase 0-2 | Bootstrap + DB | 1 |
| Phase 3-5 | Auth + scrapers (API, JobSpy, small Apify pool) | 4.5 |
| Phase 5.5 | Firecrawl self-host + enrichment service | 0.5 |
| Phase 6-7 | Jobs API + Claude CLI scoring | 2 |
| Phase 8-14 | CV + portfolio + emails + scheduler | 6 |
| Phase 15-21 | Frontend (Next.js) | 6 |
| Phase 22-23 | Deploy + smoke test | 1.5 |
| **Total** | | **~21.5 days** |

Note: Net +1 day vs previous revision because:
- -0.5 day: smaller Apify pool (5 not 15) = simpler admin UI + faster setup
- +1.5 day: new Phase 5.5 (Firecrawl integration) + Phase 4 JobSpy improvements

Trade-off is justified: Firecrawl enrichment significantly improves CV tailoring + cold email quality by giving Claude full JD + company context instead of truncated aggregator snippets. This is a **quality multiplier** on the core Claude CLI differentiator.

---

## Execution Handoff

**Option 1: Execute in this session**
> "Ready to start Phase 0? I'll use gaspol-execute to implement with per-phase checkpoints."

**Option 2: Parallel execution**
> "Phases 15-21 (frontend) can run in parallel with Phase 22 (Docker) via gaspol-parallel after backend is complete."

**Option 3: Separate session**
> "Save plan for a new session. The plan file at `docs/plans/2026-04-15-jobhunter-mvp-design.md` has everything needed to resume."
