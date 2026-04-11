.PHONY: help install lint format format-check typecheck test test-integration pre-commit check migrate migrate-down compose-up compose-down compose-logs load-test-seed load-test

help:
	@echo "Targets:"
	@echo "  make install      - Sync dependencies (uv sync)"
	@echo "  make lint         - Ruff lint (uv run ruff check .)"
	@echo "  make format       - Ruff format (uv run ruff format .)"
	@echo "  make format-check - Check formatting (uv run ruff format --check .)"
	@echo "  make typecheck    - Mypy (uv run mypy --strict app/src)"
	@echo "  make test         - Pytest (uv run pytest)"
	@echo "  make test-integration - Apply migrations and run PostgreSQL integration tests"
	@echo "  make migrate      - Apply Alembic migrations to the configured database"
	@echo "  make migrate-down - Roll back the latest Alembic migration"
	@echo "  make compose-up   - Build and start the Docker Compose stack"
	@echo "  make compose-down - Stop the Docker Compose stack"
	@echo "  make compose-logs - Tail Docker Compose logs"
	@echo "  make load-test-seed - Seed deterministic workspace/project data for local load tests"
	@echo "  make load-test    - Run the k6 task workflow load test"
	@echo "  make pre-commit   - Run pre-commit on all files (uv run pre-commit ...)"
	@echo "  make check        - lint + format-check + typecheck + test"

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy --strict app/src

test:
	PYTHONPATH=app/src uv run pytest

test-integration:
	bash scripts/run_integration_tests.sh

migrate:
	./.venv/bin/alembic upgrade head

migrate-down:
	./.venv/bin/alembic downgrade -1

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f

load-test-seed:
	docker compose run --rm --no-deps api python scripts/seed_load_test_data.py

load-test:
	bash scripts/run_load_tests.sh

pre-commit:
	uv run pre-commit run --all-files

check: lint format-check typecheck test
