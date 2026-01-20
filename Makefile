.PHONY: help install lint format format-check typecheck test pre-commit check

help:
	@echo "Targets:"
	@echo "  make install      - Sync dependencies (uv sync)"
	@echo "  make lint         - Ruff lint (uv run ruff check .)"
	@echo "  make format       - Ruff format (uv run ruff format .)"
	@echo "  make format-check - Check formatting (uv run ruff format --check .)"
	@echo "  make typecheck    - Mypy (uv run mypy --strict app/src)"
	@echo "  make test         - Pytest (uv run pytest)"
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

pre-commit:
	uv run pre-commit run --all-files

check: lint format-check typecheck test
