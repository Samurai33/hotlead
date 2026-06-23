.PHONY: up down logs ps migrate test lint

up:
	docker compose up -d

up-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest tests/ -v --cov=app

lint:
	docker compose exec api ruff check app/
	docker compose exec api mypy app/

shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec postgres psql -U hotlead -d hotlead

health:
	curl -s http://localhost:8000/health | python3 -m json.tool
