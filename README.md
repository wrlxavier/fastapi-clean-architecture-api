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
- Docker Engine with the Compose plugin (for the local production-like stack)

## Docker Compose stack

The repository includes a local production-like stack with:

- `postgres`: PostgreSQL database with a container healthcheck.
- `api`: FastAPI application container that applies Alembic migrations on startup and exposes `/health` and `/ready` internally.
- `nginx`: reverse proxy that forwards traffic to the API and exposes the stack on `http://localhost:${NGINX_PORT:-8080}`.

Start the full stack:

```bash
docker compose up -d --build
```

Or use the Makefile helper:

```bash
make compose-up
```

The API is available through Nginx by default at:

- `http://localhost:8080/health`
- `http://localhost:8080/ready`
- `http://localhost:8080/docs`
- `http://localhost:8080/openapi.json`

You can override the published Nginx port with `NGINX_PORT` in `.env`.

## Reverse proxy behavior

The stack is configured so the application behaves correctly behind Nginx:

- Nginx preserves the original external host header with `$http_host`, which keeps non-default ports such as `:8080` available to FastAPI.
- Nginx forwards `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` so the app can reconstruct the original client IP, scheme, and host.
- The application trusts proxy headers only when `PROXY_HEADERS_ENABLED=true` and the immediate client matches `FORWARDED_ALLOW_IPS`.

Docker Compose sets `FORWARDED_ALLOW_IPS=*` because the API container is only reachable from the internal Docker network and the Nginx container receives a dynamic IP there. If you deploy this stack in another environment, replace `*` with the IP or CIDR range of your trusted reverse proxy.

Inspect stack status and logs:

```bash
docker compose ps
docker compose logs -f api
```

Stop the stack:

```bash
docker compose down
```

Nginx forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` headers to the API. The FastAPI application normalizes request metadata from those forwarded headers so `/docs`, generated URLs, and request logging work correctly through the reverse proxy.

## Developer workflow

This project uses Ruff for linting/formatting, mypy (strict) for type checking, and pre-commit for automated checks.

## GitHub Actions CI

The repository includes a GitHub Actions workflow at `.github/workflows/ci.yml` with three required jobs:

- `Quality`: runs `ruff check`, `ruff format --check`, `mypy --strict`, and `pytest`.
- `Integration`: starts PostgreSQL 17, applies Alembic migrations, and runs `tests/integration`.
- `Docker Build`: builds the production Docker image from `Dockerfile`.

The workflow runs on every pull request, on pushes to `main` and `staging`, and can also be triggered manually from the Actions tab.

## Branch protection

Branch protection must be configured manually in GitHub after the workflow has run at least once:

1. Open the repository on GitHub and go to `Settings` -> `Branches`.
2. Add or edit a branch protection rule for `main`.
3. Enable `Require a pull request before merging`.
4. Enable `Require status checks to pass before merging`.
5. Mark these checks as required: `Quality`, `Integration`, and `Docker Build`.
6. Repeat the same rule for `staging` if that branch is part of your review flow.

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

### Integration tests against PostgreSQL

Set `TEST_DATABASE_URL` to a dedicated test database, then run:

```bash
make test-integration
```

The integration test script applies `alembic upgrade head` to the test database before running `tests/integration`.

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

Set `APP_ENV=development` to include stack traces in server error logs during local work. Logs are emitted as JSON to stdout, which keeps containers and CI output easy to parse.

Example:

```bash
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_clean_architecture_api
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_clean_architecture_api_test
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

## Database migrations

Alembic migrations are versioned under `alembic/versions` and read database settings from environment variables or the local `.env` file.

Apply the latest schema version:

```bash
make migrate
```

Roll back the latest migration:

```bash
make migrate-down
```

Create a new migration after changing SQLAlchemy models:

```bash
./.venv/bin/alembic revision --autogenerate -m "describe schema change"
```

## pre-commit hooks

> Note: the configuration file must be named `.pre-commit-config.yaml` at the repository root.

Install hooks (run once after cloning):

```bash
uv run pre-commit install
```