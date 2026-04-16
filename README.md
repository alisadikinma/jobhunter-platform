# JobHunter

Automated job hunting pipeline: scrape → AI score → CV tailor → cold email draft.

**Stack:** FastAPI + Next.js 15 + PostgreSQL + Claude CLI

## Quick Start

```bash
cp .env.example .env          # configure secrets
make db-up                    # start PostgreSQL on port 5433
make db-migrate               # run migrations
make dev-backend              # start API on port 8000
make dev-frontend             # start frontend on port 3000
```

## Architecture

See [docs/plans/2026-04-15-jobhunter-mvp-design.md](docs/plans/2026-04-15-jobhunter-mvp-design.md) for full implementation plan.
