# fastapi-clean-architecture-api

Source code lives in `app/src`.

Clean Architecture layers:
- domain: entities/value objects, invariants, domain errors (no framework/DB deps).
- application: use cases and ports (interfaces) that the outer layers implement.
- infrastructure: DB/ORM, external clients, implementations of ports.
- presentation: FastAPI routers/controllers and request/response schemas.

## Product & Quality Standards

- [Product Contract](docs/CONTRACT.md) - API surface, entities, rules, scope
- [Non-Functional Requirements](docs/NFRS.md) - Quality standards, testing, security, deployment

## Requirements

- Python >= 3.12
- uv installed

## Developer workflow

This project uses Ruff for linting/formatting, mypy (strict) for type checking, and pre-commit for automated checks.

### One-shot checks

```bash
make check
```

### Lint & format

```bash
make lint
make format
make format-check
```

### Type checking

```bash
make typecheck  # runs mypy --strict using pyproject.toml config
```

### Tests

```bash
make test
```

## pre-commit hooks

Install hooks (run once after cloning):

```bash
uv run pre-commit install
```

Run hooks on the whole repository:

```bash
make pre-commit
```

## Setting environment variables

Create a `.env` file in the project root based on the `.env.example` file and set the required environment variables. You can easily copy the example file using the following command:

For the database connection, you can either provide `DATABASE_URL` directly, or use the discrete `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, and `DATABASE_NAME` variables.

Example:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_clean_architecture_api
```

- Linux/MacOS:

```bash
cp .env.example .env
```

- Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

## Installing dependencies (uv)

This will run `uv sync` and create/use the project virtualenv at `.venv`.

```bash
make install
```

## pre-commit hooks

> Note: the configuration file must be named `.pre-commit-config.yaml` at the repository root.

Install hooks (run once after cloning):

```bash
uv run pre-commit install
```