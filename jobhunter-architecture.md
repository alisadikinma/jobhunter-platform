# JobHunter — Architecture Plan v1.0

> Automated job hunting pipeline: scrape → AI score → CV tailor → cold email draft
> Stack: FastAPI (Python) + Next.js 15 (React) + PostgreSQL + Claude Code Agents

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 15)                     │
│  App Router + Server Actions + shadcn/ui + TanStack Query   │
│  Port: 3000 (Dev) | Static export or Node (Prod)            │
├──────────────────────────┬──────────────────────────────────┤
│                          │ REST API + WebSocket              │
├──────────────────────────▼──────────────────────────────────┤
│                    BACKEND (FastAPI)                         │
│  SQLAlchemy + Pydantic + Celery Workers + WebSocket          │
│  Port: 8000                                                  │
├──────────┬───────────┬──────────┬───────────────────────────┤
│ JobSpy   │ Resume-   │ Claude   │ Pandoc                    │
│ (import) │ Matcher   │ CLI      │ (subprocess)              │
│          │ (import)  │ (subproc)│                           │
├──────────┴───────────┴──────────┴───────────────────────────┤
│                    DATA LAYER                                │
│  PostgreSQL 16 + Redis 7 (Celery broker + cache)            │
├─────────────────────────────────────────────────────────────┤
│                    INFRASTRUCTURE                            │
│  Docker Compose + Traefik (jobs.alisadikinma.com)            │
│  VPS: srv941303 (shared with Portfolio_v2)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Project Structure

```
D:\Projects\JobHunter\
│
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry + CORS + lifespan
│   │   ├── config.py                 # Settings via pydantic-settings
│   │   ├── database.py               # SQLAlchemy engine + session
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── job.py                # ScrapedJob
│   │   │   ├── company.py            # Company cache
│   │   │   ├── application.py        # JobApplication (tracker)
│   │   │   ├── cv.py                 # MasterCV + GeneratedCV
│   │   │   ├── email_draft.py        # ColdEmailDraft
│   │   │   ├── scrape_config.py      # ScrapeConfig (keywords, sites, schedule)
│   │   │   └── user.py               # User (admin auth)
│   │   │
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── job.py
│   │   │   ├── application.py
│   │   │   ├── cv.py
│   │   │   └── email.py
│   │   │
│   │   ├── api/                      # Route handlers
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # Main router aggregator
│   │   │   ├── jobs.py               # /api/jobs/* — scraped listings
│   │   │   ├── applications.py       # /api/applications/* — tracker
│   │   │   ├── cv.py                 # /api/cv/* — master CV + generated
│   │   │   ├── emails.py             # /api/emails/* — cold email drafts
│   │   │   ├── scraper.py            # /api/scraper/* — trigger/config
│   │   │   ├── auth.py               # /api/auth/* — JWT login
│   │   │   └── callbacks.py          # /api/callbacks/* — Claude CLI webhooks
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── scraper_service.py    # JobSpy + API aggregation
│   │   │   ├── scorer_service.py     # Resume-Matcher ATS scoring
│   │   │   ├── claude_service.py     # Claude CLI subprocess manager
│   │   │   ├── cv_generator.py       # CV generation orchestrator
│   │   │   ├── email_generator.py    # Cold email orchestrator
│   │   │   └── docx_service.py       # Markdown → Pandoc → DOCX → PDF
│   │   │
│   │   ├── scrapers/                 # Individual scraper implementations
│   │   │   ├── __init__.py
│   │   │   ├── jobspy_scraper.py     # JobSpy wrapper (LinkedIn, Indeed, etc)
│   │   │   ├── remoteok.py           # RemoteOK free API
│   │   │   ├── adzuna.py             # Adzuna API
│   │   │   ├── arbeitnow.py          # Arbeitnow API
│   │   │   ├── wellfound.py          # Wellfound/AngelList
│   │   │   └── aggregator.py         # Combine + dedup all sources
│   │   │
│   │   ├── workers/                  # Celery async tasks
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py         # Celery configuration
│   │   │   ├── scrape_tasks.py       # Daily scraping task
│   │   │   ├── cv_tasks.py           # CV generation task
│   │   │   └── email_tasks.py        # Email draft generation task
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── deduplicator.py       # Job dedup (title + company hash)
│   │       └── keyword_matcher.py    # Relevance scoring keywords
│   │
│   ├── alembic/                      # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── tests/
│   │   ├── test_scraper.py
│   │   ├── test_cv_generator.py
│   │   └── test_scorer.py
│   │
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                         # Next.js 15 application
│   ├── src/
│   │   ├── app/                      # App Router
│   │   │   ├── layout.tsx            # Root layout + providers
│   │   │   ├── page.tsx              # Redirect → /dashboard
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx          # Stats overview
│   │   │   ├── jobs/
│   │   │   │   ├── page.tsx          # Scraped job listings (table)
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # Job detail + actions
│   │   │   ├── applications/
│   │   │   │   ├── page.tsx          # Kanban tracker
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # Application detail
│   │   │   ├── cv/
│   │   │   │   ├── page.tsx          # Master CV editor
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx      # Generated CV preview/edit
│   │   │   ├── emails/
│   │   │   │   └── page.tsx          # Email drafts list
│   │   │   └── settings/
│   │   │       └── page.tsx          # Scrape config, keywords, schedule
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui components
│   │   │   ├── jobs/
│   │   │   │   ├── JobTable.tsx       # DataTable with filters
│   │   │   │   ├── JobCard.tsx        # Job listing card
│   │   │   │   └── JobScoreBar.tsx    # Relevance + ATS score
│   │   │   ├── applications/
│   │   │   │   ├── KanbanBoard.tsx    # Drag-drop status board
│   │   │   │   ├── ApplicationCard.tsx
│   │   │   │   └── TimelineView.tsx   # Activity timeline
│   │   │   ├── cv/
│   │   │   │   ├── CVEditor.tsx       # Rich text master CV editor
│   │   │   │   ├── CVPreview.tsx      # DOCX rendered preview
│   │   │   │   ├── CVDiff.tsx         # Before/after comparison
│   │   │   │   └── ATSScoreCard.tsx   # Resume-Matcher score display
│   │   │   ├── emails/
│   │   │   │   ├── EmailPreview.tsx   # Email draft with copy button
│   │   │   │   └── EmailEditor.tsx    # Edit before send
│   │   │   ├── dashboard/
│   │   │   │   ├── StatsCards.tsx     # Jobs found, applied, response rate
│   │   │   │   └── WeeklyChart.tsx    # Application activity chart
│   │   │   └── shared/
│   │   │       ├── ProgressModal.tsx  # Claude CLI progress tracking
│   │   │       └── Sidebar.tsx        # Navigation sidebar
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                # Axios/fetch client
│   │   │   ├── auth.ts               # JWT auth helpers
│   │   │   └── utils.ts              # Shared utilities
│   │   │
│   │   └── hooks/
│   │       ├── useJobs.ts            # TanStack Query hooks
│   │       ├── useApplications.ts
│   │       ├── useCV.ts
│   │       └── useProgress.ts        # WebSocket progress hook
│   │
│   ├── public/
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
│
├── claude-plugin/                    # Claude Code skills for job hunting
│   ├── CLAUDE.md                     # Plugin config
│   ├── skills/
│   │   ├── job-score.md              # Score job relevance
│   │   ├── cv-tailor.md              # Rewrite CV per JD (Opus)
│   │   ├── cover-letter.md           # Generate cover letter (Sonnet)
│   │   ├── cold-email.md             # Draft cold email (Sonnet)
│   │   └── company-research.md       # Research company context
│   ├── refs/
│   │   ├── refs-cv.md                # ATS rules + formatting + master CV
│   │   ├── refs-email.md             # Cold email strategy + templates
│   │   └── refs-scoring.md           # Job relevance scoring criteria
│   └── agents/
│       └── job-hunter.md             # Batch agent (score → tailor → email)
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── Makefile                          # dev, build, deploy shortcuts
├── CLAUDE.md                         # Project-level Claude Code context
└── README.md
```

---

## 3. Database Schema (PostgreSQL)

```sql
-- ============================================
-- CORE TABLES
-- ============================================

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    name            VARCHAR(100),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE companies (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255),              -- company.com
    linkedin_url    VARCHAR(500),
    industry        VARCHAR(100),
    size_range      VARCHAR(50),               -- 1-10, 11-50, 51-200, 201-500, 501+
    location        VARCHAR(255),
    description     TEXT,
    hiring_contact  JSONB,                     -- {name, title, email, linkedin}
    metadata        JSONB,                     -- extra info from research
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, domain)
);

CREATE TABLE scraped_jobs (
    id              SERIAL PRIMARY KEY,
    external_id     VARCHAR(255),              -- job board's ID
    source          VARCHAR(50) NOT NULL,      -- linkedin, indeed, remoteok, adzuna, etc
    source_url      VARCHAR(1000),
    company_id      INTEGER REFERENCES companies(id),
    title           VARCHAR(500) NOT NULL,
    company_name    VARCHAR(255) NOT NULL,     -- denormalized for speed
    location        VARCHAR(255),
    job_type        VARCHAR(50),               -- full-time, contract, freelance
    remote_type     VARCHAR(50),               -- remote, hybrid, onsite
    salary_min      INTEGER,
    salary_max      INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'USD',
    description     TEXT,
    requirements    TEXT,                       -- extracted from description
    tech_stack      TEXT[],                    -- parsed technologies
    experience_level VARCHAR(50),              -- entry, mid, senior, lead

    -- AI Scoring (by Claude agent)
    relevance_score INTEGER,                   -- 0-100, how well it matches profile
    score_reasons   JSONB,                     -- {pros: [...], cons: [...]}
    match_keywords  TEXT[],                    -- matching skills/keywords

    -- Dedup
    content_hash    VARCHAR(64) UNIQUE,        -- SHA256(title + company + description[:200])

    -- Status
    status          VARCHAR(20) DEFAULT 'new', -- new, reviewed, targeting, skipped, expired
    is_favorite     BOOLEAN DEFAULT FALSE,

    scraped_at      TIMESTAMP DEFAULT NOW(),
    posted_at       TIMESTAMP,                 -- job post date
    expires_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_status ON scraped_jobs(status);
CREATE INDEX idx_jobs_source ON scraped_jobs(source);
CREATE INDEX idx_jobs_score ON scraped_jobs(relevance_score DESC);
CREATE INDEX idx_jobs_scraped_at ON scraped_jobs(scraped_at DESC);

-- ============================================
-- APPLICATION TRACKER
-- ============================================

CREATE TABLE applications (
    id              SERIAL PRIMARY KEY,
    job_id          INTEGER REFERENCES scraped_jobs(id),
    company_id      INTEGER REFERENCES companies(id),

    -- Status tracking
    status          VARCHAR(30) DEFAULT 'targeting',
    -- targeting → cv_generating → cv_ready → applied →
    -- email_sent → replied → interview_scheduled →
    -- interviewed → offered → accepted / rejected / ghosted

    -- Key dates
    targeted_at     TIMESTAMP DEFAULT NOW(),
    applied_at      TIMESTAMP,
    email_sent_at   TIMESTAMP,
    replied_at      TIMESTAMP,
    interview_at    TIMESTAMP,
    offered_at      TIMESTAMP,
    closed_at       TIMESTAMP,

    -- Application details
    applied_via     VARCHAR(50),               -- linkedin, email, website, referral
    applied_url     VARCHAR(1000),             -- where applied
    contact_name    VARCHAR(255),              -- hiring manager / recruiter
    contact_email   VARCHAR(255),
    contact_title   VARCHAR(255),
    salary_asked    INTEGER,
    salary_offered  INTEGER,

    -- Notes
    notes           TEXT,
    tags            TEXT[],                    -- custom tags

    -- Links to generated content
    cv_id           INTEGER,                   -- → generated_cvs.id
    email_draft_id  INTEGER,                   -- → email_drafts.id
    cover_letter_id INTEGER,                   -- → cover_letters.id

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_app_status ON applications(status);
CREATE INDEX idx_app_dates ON applications(applied_at DESC);

-- Activity log for each application
CREATE TABLE application_activities (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    activity_type   VARCHAR(50) NOT NULL,      -- status_change, note, email, interview, etc
    description     TEXT,
    old_value       VARCHAR(100),
    new_value       VARCHAR(100),
    metadata        JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- CV SYSTEM
-- ============================================

CREATE TABLE master_cv (
    id              SERIAL PRIMARY KEY,
    version         INTEGER DEFAULT 1,
    content         JSONB NOT NULL,            -- structured CV data (JSON Resume format)
    raw_markdown    TEXT,                       -- markdown version
    skills          TEXT[],                    -- all skills for matching
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE generated_cvs (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER REFERENCES applications(id),
    job_id          INTEGER REFERENCES scraped_jobs(id),
    master_cv_id    INTEGER REFERENCES master_cv(id),

    -- Generated content
    tailored_markdown TEXT,                    -- Claude-generated markdown
    tailored_json   JSONB,                     -- structured data
    docx_path       VARCHAR(500),              -- stored DOCX file path
    pdf_path        VARCHAR(500),              -- stored PDF file path

    -- ATS scoring (Resume-Matcher)
    ats_score       INTEGER,                   -- 0-100
    keyword_matches TEXT[],
    missing_keywords TEXT[],
    suggestions     JSONB,

    -- Generation metadata
    model_used      VARCHAR(50),               -- opus, sonnet
    generation_log  JSONB,                     -- progress log
    status          VARCHAR(20) DEFAULT 'pending',
    -- pending → generating → ready → approved → sent

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cover_letters (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER REFERENCES applications(id),
    job_id          INTEGER REFERENCES scraped_jobs(id),
    content         TEXT NOT NULL,
    tone            VARCHAR(30) DEFAULT 'professional', -- professional, casual, enthusiastic
    model_used      VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'draft',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- COLD EMAIL
-- ============================================

CREATE TABLE email_drafts (
    id              SERIAL PRIMARY KEY,
    application_id  INTEGER REFERENCES applications(id),
    job_id          INTEGER REFERENCES scraped_jobs(id),

    -- Email content
    subject         VARCHAR(255),
    body            TEXT NOT NULL,
    email_type      VARCHAR(30) DEFAULT 'initial',  -- initial, follow_up_1, follow_up_2
    recipient_email VARCHAR(255),
    recipient_name  VARCHAR(255),

    -- Strategy
    strategy        VARCHAR(50),               -- value_prop, mutual_connection, portfolio_showcase
    personalization JSONB,                     -- {company_news, recipient_work, etc}

    -- Status
    status          VARCHAR(20) DEFAULT 'draft', -- draft, approved, sent, replied
    sent_at         TIMESTAMP,

    model_used      VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- CONFIGURATION
-- ============================================

CREATE TABLE scrape_configs (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,     -- "AI Remote Jobs USA"
    is_active       BOOLEAN DEFAULT TRUE,

    -- Search parameters
    keywords        TEXT[] NOT NULL,            -- ["AI Agent", "AI Engineer", "Prompt Engineer"]
    excluded_keywords TEXT[],                   -- ["intern", "unpaid"]
    locations       TEXT[],                    -- ["USA", "Remote"]
    job_types       TEXT[],                    -- ["full-time", "contract"]
    remote_only     BOOLEAN DEFAULT TRUE,
    min_salary      INTEGER,

    -- Sources to scrape
    sources         TEXT[] DEFAULT ARRAY['linkedin', 'indeed', 'remoteok', 'adzuna'],
    max_results_per_source INTEGER DEFAULT 50,

    -- Schedule
    cron_expression VARCHAR(50) DEFAULT '0 6 * * *',  -- daily 6 AM UTC
    last_run_at     TIMESTAMP,
    last_run_results JSONB,                    -- {total: 120, new: 35, duplicates: 85}

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Claude CLI job tracking (same pattern as Portfolio_v2 content_ideas)
CREATE TABLE agent_jobs (
    id              SERIAL PRIMARY KEY,
    job_type        VARCHAR(50) NOT NULL,      -- cv_tailor, cover_letter, cold_email, job_score, company_research
    reference_id    INTEGER,                   -- application_id or job_id
    reference_type  VARCHAR(50),               -- application, scraped_job

    -- Progress (Claude CLI callback pattern)
    status          VARCHAR(20) DEFAULT 'pending',
    -- pending → running → completed → failed
    progress_pct    INTEGER DEFAULT 0,
    current_step    VARCHAR(100),
    progress_log    JSONB DEFAULT '[]',

    -- Execution
    model_used      VARCHAR(50),
    process_pid     INTEGER,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    error_message   TEXT,

    -- Result
    result          JSONB,

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 4. API Endpoints

### Jobs
```
GET    /api/jobs                         # List scraped jobs (filter, sort, paginate)
GET    /api/jobs/{id}                    # Job detail
PATCH  /api/jobs/{id}                    # Update status (reviewed, skipped, targeting)
POST   /api/jobs/{id}/favorite           # Toggle favorite
DELETE /api/jobs/{id}                    # Remove job
GET    /api/jobs/stats                   # Dashboard stats (counts by source, status)
```

### Scraper
```
POST   /api/scraper/run                  # Trigger manual scrape
GET    /api/scraper/status               # Current scrape status
GET    /api/scraper/configs              # List scrape configs
POST   /api/scraper/configs              # Create config
PUT    /api/scraper/configs/{id}         # Update config
```

### Applications
```
GET    /api/applications                 # List all (filter by status)
POST   /api/applications                 # Create from job_id
GET    /api/applications/{id}            # Detail + timeline
PATCH  /api/applications/{id}            # Update status, notes, dates
DELETE /api/applications/{id}            # Remove
GET    /api/applications/kanban          # Grouped by status for Kanban
GET    /api/applications/stats           # Response rates, avg time, etc
```

### CV
```
GET    /api/cv/master                    # Get active master CV
PUT    /api/cv/master                    # Update master CV
POST   /api/cv/generate                  # Trigger CV tailoring (Claude CLI)
GET    /api/cv/{id}                      # Get generated CV
PUT    /api/cv/{id}                      # Edit generated CV markdown
POST   /api/cv/{id}/score                # Re-score with Resume-Matcher
GET    /api/cv/{id}/download/{format}    # Download DOCX or PDF
GET    /api/cv/{id}/preview              # Render preview
```

### Cover Letter
```
POST   /api/cover-letters/generate       # Generate for application
GET    /api/cover-letters/{id}           # Get content
PUT    /api/cover-letters/{id}           # Edit
```

### Email
```
POST   /api/emails/generate              # Generate cold email draft
GET    /api/emails/{id}                  # Get draft
PUT    /api/emails/{id}                  # Edit draft
POST   /api/emails/{id}/approve          # Mark as approved/sent
POST   /api/emails/generate-followup     # Generate follow-up email
```

### Callbacks (Claude CLI → FastAPI)
```
PUT    /api/callbacks/progress/{job_id}  # Progress update
PUT    /api/callbacks/complete/{job_id}  # Job completed + result
```

### Auth
```
POST   /api/auth/login                   # JWT login
POST   /api/auth/refresh                 # Refresh token
GET    /api/auth/me                      # Current user
```

---

## 5. Claude Code Plugin Design

### Skill: `/cv-tailor` (Opus)

```markdown
Input:
  --application-id {id}
  --api-url {url}
  --api-token {token}

Process:
  1. GET /api/callbacks/context/{application_id}
     → receives: master_cv, job_description, company_info
  2. Analyze JD: extract required skills, experience, keywords
  3. Map master CV skills → JD requirements
  4. Rewrite CV sections:
     - Professional summary (tailored to role)
     - Experience bullets (emphasize relevant achievements)
     - Skills section (reorder by JD priority)
     - Projects (select most relevant 3-4)
  5. Apply ATS rules from refs-cv.md
  6. Output: Markdown formatted CV
  7. PUT /api/callbacks/complete/{job_id}
     → sends: {tailored_markdown, tailored_json, keyword_matches}

ATS Rules (baked into refs-cv.md):
  - Single column layout
  - Standard section headers
  - Reverse chronological
  - Keywords integrated into context (not keyword-stuffed)
  - Match 70-80% of JD keywords
  - Include both acronym and full term
  - Quantified achievements (numbers, percentages)
  - No graphics, tables, text boxes, images
```

### Skill: `/cold-email` (Sonnet)

```markdown
Input:
  --application-id {id}
  --api-url {url}
  --api-token {token}
  --strategy {value_prop|portfolio|mutual}

Process:
  1. GET context: job, company, hiring_contact, tailored_cv
  2. Research company (if company_research not cached)
  3. Generate email:
     - Subject: <10 words, specific to role
     - Opening: personalized (company news / recipient's work)
     - Value prop: 1-2 quantified achievements matching JD
     - Social proof: relevant project or result
     - CTA: ask for conversation, not job
     - Total: 75-150 words
  4. Generate 2 follow-up variants (day 5, day 10)
  5. PUT /api/callbacks/complete/{job_id}
     → sends: {initial, follow_up_1, follow_up_2}
```

### Skill: `/job-score` (Sonnet)

```markdown
Input:
  --batch-ids {id1,id2,...}   # up to 20 jobs per batch
  --api-url {url}
  --api-token {token}

Process:
  1. GET /api/jobs?ids={batch_ids} → job listings
  2. GET /api/cv/master → master CV skills
  3. For each job, score 0-100:
     - Skill match (40%): how many required skills I have
     - Role fit (25%): title + seniority alignment
     - Remote/location (15%): USA remote preference
     - Salary (10%): within expected range
     - Company (10%): industry, size, growth stage
  4. Generate score_reasons: {pros: [...], cons: [...]}
  5. PUT /api/callbacks/complete/{job_id}
     → sends: [{job_id, score, reasons, keywords}]
```

---

## 6. Docker Compose

```yaml
version: '3.8'

services:
  # --- Backend API ---
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://jobhunter:${DB_PASSWORD}@db:5432/jobhunter
      - REDIS_URL=redis://redis:6379/0
      - CLAUDE_PATH=/usr/local/bin/claude
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./storage:/app/storage          # DOCX/PDF files
      - ./claude-plugin:/app/claude-plugin
    depends_on:
      - db
      - redis
    labels:
      - "traefik.http.routers.jobhunter-api.rule=Host(`jobs.alisadikinma.com`) && PathPrefix(`/api`)"

  # --- Celery Worker (async tasks) ---
  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker -l info -c 2
    environment:
      - DATABASE_URL=postgresql://jobhunter:${DB_PASSWORD}@db:5432/jobhunter
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./storage:/app/storage
      - ./claude-plugin:/app/claude-plugin
    depends_on:
      - db
      - redis

  # --- Celery Beat (cron scheduler) ---
  beat:
    build: ./backend
    command: celery -A app.workers.celery_app beat -l info
    environment:
      - DATABASE_URL=postgresql://jobhunter:${DB_PASSWORD}@db:5432/jobhunter
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  # --- Frontend ---
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=https://jobs.alisadikinma.com/api
    labels:
      - "traefik.http.routers.jobhunter-web.rule=Host(`jobs.alisadikinma.com`)"

  # --- Database ---
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=jobhunter
      - POSTGRES_USER=jobhunter
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5433:5432"                      # 5433 to avoid conflict with Portfolio_v2 MySQL

  # --- Redis ---
  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

volumes:
  pgdata:
```

---

## 7. Key Dependencies

### Backend (Python)
```txt
# Core
fastapi==0.115.*
uvicorn[standard]==0.34.*
sqlalchemy==2.0.*
alembic==1.14.*
psycopg2-binary==2.9.*
pydantic-settings==2.7.*
celery[redis]==5.4.*

# Auth
python-jose[cryptography]==3.3.*
passlib[bcrypt]==1.7.*

# Scraping
python-jobspy==1.1.*
httpx==0.28.*
beautifulsoup4==4.12.*

# AI / CV
resume-matcher==*                       # ATS scoring
python-docx==1.1.*                     # DOCX manipulation (backup)

# Utils
pandas==2.2.*
python-multipart==0.0.*
websockets==13.*
```

### Frontend (Node.js)
```json
{
  "dependencies": {
    "next": "^15.1",
    "react": "^19",
    "@tanstack/react-query": "^5.60",
    "axios": "^1.7",
    "zustand": "^5",
    "@dnd-kit/core": "^6",
    "@dnd-kit/sortable": "^9",
    "lucide-react": "^0.460",
    "recharts": "^2.13",
    "date-fns": "^4",
    "clsx": "^2",
    "tailwind-merge": "^2"
  },
  "devDependencies": {
    "tailwindcss": "^4",
    "@shadcn/ui": "latest",
    "typescript": "^5.6"
  }
}
```

---

## 8. Data Flow: End-to-End

```
┌─────────────────────────────────────────────────────┐
│ PHASE 1: SCRAPE (Daily Cron — Celery Beat)          │
│                                                      │
│  Celery Beat (6 AM UTC)                              │
│    → scrape_tasks.run_daily_scrape()                 │
│      → JobSpy: LinkedIn, Indeed, Glassdoor (50 each) │
│      → RemoteOK API (50)                             │
│      → Adzuna API (50)                               │
│      → Arbeitnow API (50)                            │
│      → aggregator.deduplicate()                      │
│      → DB: insert scraped_jobs (status='new')        │
│      → ~100-200 unique jobs/day                      │
│                                                      │
│  Then: Claude CLI /job-score (batch 20)               │
│    → Score all new jobs                               │
│    → Update relevance_score + score_reasons           │
│    → ~5 min for 200 jobs                              │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 2: REVIEW (Admin Panel — Manual)              │
│                                                      │
│  Admin sees: sorted by relevance_score DESC          │
│    → Review job details + score reasons              │
│    → Mark as "targeting" or "skipped"                │
│    → Create application (targeting → application)    │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 3: GENERATE (Claude CLI — On Demand)          │
│                                                      │
│  Click "Generate CV" on application                  │
│    → Claude CLI /cv-tailor (Opus, ~2 min)            │
│    → Resume-Matcher ATS score                        │
│    → Pandoc: Markdown → DOCX                         │
│    → Admin: preview, edit, approve                   │
│    → Pandoc: DOCX → PDF (final)                      │
│                                                      │
│  Click "Generate Email"                              │
│    → Claude CLI /cold-email (Sonnet, ~30 sec)        │
│    → Admin: review, edit, copy                       │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ PHASE 4: APPLY & TRACK (Admin Panel — Manual)       │
│                                                      │
│  Download PDF CV → Apply on job board                │
│  Copy email → Send via personal email client         │
│  Update status: applied → email_sent → replied       │
│  Kanban board tracks all applications                │
│  Timeline shows activity history                     │
└─────────────────────────────────────────────────────┘
```

---

## 9. MVP Scope (Phase 1)

| Feature | Priority | Est. |
|---------|----------|------|
| FastAPI skeleton + auth + DB | P0 | 1 day |
| JobSpy scraper + RemoteOK + Adzuna | P0 | 1 day |
| Scraped jobs CRUD + admin table | P0 | 1.5 days |
| Claude `/job-score` skill | P0 | 1 day |
| Master CV editor (JSON + markdown) | P0 | 1 day |
| Claude `/cv-tailor` skill (Opus) | P0 | 1.5 days |
| Pandoc DOCX/PDF pipeline | P0 | 0.5 day |
| CV preview + edit + download | P0 | 1.5 days |
| Application tracker (CRUD + Kanban) | P0 | 2 days |
| Claude `/cold-email` skill | P1 | 1 day |
| Email draft editor + copy | P1 | 1 day |
| Celery cron + daily scrape | P1 | 0.5 day |
| Dashboard stats | P2 | 1 day |
| Docker Compose + Traefik | P2 | 0.5 day |
| **Total MVP** | | **~14 days** |

---

## 10. Versus Portfolio_v2 Pattern Comparison

| Aspect | Portfolio_v2 | JobHunter |
|--------|-------------|-----------|
| Backend | Laravel 12 (PHP) | FastAPI (Python) |
| Frontend | Vue 3 + Vite | Next.js 15 + App Router |
| Database | MySQL 8 | PostgreSQL 16 |
| ORM | Eloquent | SQLAlchemy |
| State mgmt | Pinia | Zustand |
| Data fetching | TanStack Vue Query | TanStack React Query |
| UI library | Tailwind + custom | Tailwind + shadcn/ui |
| Async jobs | Laravel Queue | Celery + Redis |
| Claude CLI | SSH → bash script | `subprocess.run()` direct |
| Auth | Sanctum (token) | JWT (python-jose) |
| File gen | — | Pandoc (Markdown → DOCX → PDF) |
| Migrations | Laravel migrations | Alembic |
| Cron | — | Celery Beat |
| Deployment | git pull + rebuild | Docker Compose |
