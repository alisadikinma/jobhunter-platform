.PHONY: dev-backend dev-frontend db-up db-down db-migrate db-revision test-backend test-frontend lint typecheck scrape-run build up down logs plugin-init plugin-update

# --- Plugin (lives in a separate repo so it can be installed via
#     `claude /plugin marketplace add github.com/alisadikinma/jobhunter-plugin`).
#     Local dev clones it as a sibling of this repo and points
#     CLAUDE_PLUGIN_PATH at it via .env.
PLUGIN_DIR ?= ../claude-plugin/jobhunter-plugin
PLUGIN_REPO ?= https://github.com/alisadikinma/jobhunter-plugin.git

plugin-init:
	@if [ -d "$(PLUGIN_DIR)/.git" ]; then \
	  echo "plugin already cloned at $(PLUGIN_DIR)"; \
	else \
	  echo "cloning $(PLUGIN_REPO) -> $(PLUGIN_DIR)"; \
	  mkdir -p "$$(dirname $(PLUGIN_DIR))"; \
	  git clone "$(PLUGIN_REPO)" "$(PLUGIN_DIR)"; \
	fi
	@echo "set CLAUDE_PLUGIN_PATH=$$(realpath $(PLUGIN_DIR)) in your .env"

plugin-update:
	cd $(PLUGIN_DIR) && git pull --ff-only

# Development
dev-backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Database
db-up:
	docker-compose -f docker-compose.dev.yml up -d db

db-down:
	docker-compose -f docker-compose.dev.yml down

db-migrate:
	cd backend && .venv/Scripts/python -m alembic upgrade head

db-revision:
	cd backend && .venv/Scripts/python -m alembic revision --autogenerate -m "$(MSG)"

# Testing
test-backend:
	cd backend && .venv/Scripts/python -m pytest -v

test-frontend:
	cd frontend && npm test

# Lint + typecheck (same commands CI runs)
lint:
	cd backend && .venv/Scripts/ruff check app/ tests/

typecheck:
	cd backend && .venv/Scripts/mypy app/

# Scraping
scrape-run:
	curl -s -X POST http://localhost:8000/api/scraper/run -H "Content-Type: application/json" -d '{"config_id": $(CONFIG)}'

# Docker (prod)
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f api
