.PHONY: dev-backend dev-frontend db-up db-down db-migrate db-revision test-backend test-frontend scrape-run build up down logs

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
