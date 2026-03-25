.PHONY: up down migrate test lint shell logs api-logs worker-logs

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm api alembic upgrade head

migrate-create:
	docker compose run --rm api alembic revision --autogenerate -m "$(name)"

setup-test-db:
	docker compose exec db psql -U car_finder -c "CREATE DATABASE car_finder_test;" || true

test: setup-test-db
	docker compose run --rm -e TEST_DATABASE_URL=postgresql+asyncpg://car_finder:car_finder@db:5432/car_finder_test api pytest tests/ -v --cov=app --cov-report=term-missing

test-unit:
	docker compose run --rm api pytest tests/unit/ -v

test-integration: setup-test-db
	docker compose run --rm -e TEST_DATABASE_URL=postgresql+asyncpg://car_finder:car_finder@db:5432/car_finder_test api pytest tests/integration/ -v

lint:
	docker compose run --rm api ruff check app/ tests/
	docker compose run --rm api ruff format --check app/ tests/

format:
	docker compose run --rm api ruff format app/ tests/

shell:
	docker compose run --rm api bash

logs:
	docker compose logs -f

api-logs:
	docker compose logs -f api

worker-logs:
	docker compose logs -f worker beat
