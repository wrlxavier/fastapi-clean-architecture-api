# fastapi-clean-architecture-api

A production-ready FastAPI backend portfolio project that demonstrates Clean Architecture with PostgreSQL, Alembic, Docker Compose, and Nginx. The current codebase delivers a task-management vertical slice together with the engineering practices expected in a deployable service: typed boundaries, automated tests, migrations, structured logging, readiness probes, and CI-friendly commands.

## Overview

This repository is intentionally architecture-first. The business domain is a Workspace -> Project -> Task system, but the main goal is to show how to structure a Python API so that core rules stay isolated from FastAPI, SQLAlchemy, and deployment concerns.

Scope note:

- [docs/CONTRACT.md](docs/CONTRACT.md) describes the broader product contract and target API surface for the project.
- The current implementation focuses on the task-oriented vertical slice of that contract.
- Authentication in the current slice is represented by the `X-User-ID` header while JWT-related settings and application ports are already modeled for later milestones.

## What's Implemented In v0.1.0

- FastAPI app with `/health`, `/ready`, `/docs`, and `/openapi.json`
- Task workflow endpoints: `POST /v1/tasks`, `GET /v1/tasks`, `POST /v1/tasks/{task_id}/transition`, and `POST /v1/tasks/{task_id}/assign`
- PostgreSQL persistence through SQLAlchemy repositories, a Unit of Work, and Alembic migrations for `workspaces`, `projects`, `tasks`, and `task_events`
- Docker Compose orchestration for PostgreSQL, the API, and Nginx, including reverse-proxy-aware request handling
- Structured JSON logging, correlation IDs, readiness checks, and task audit events
- Ruff, mypy, smoke tests, unit tests, integration tests, and a GitHub Actions workflow for quality, integration, and Docker image builds

The broader contract still defers JWT authentication, user registration, workspace and project CRUD routes, task detail/update/delete routes, and the optional `/metrics` endpoint.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/CONTRACT.md](docs/CONTRACT.md)
- [docs/NFRS.md](docs/NFRS.md)
- [docs/PERFORMANCE.md](docs/PERFORMANCE.md)
- [docs/RELEASE.md](docs/RELEASE.md)

## Clean Architecture Overview

Source code lives in `app/src` and is split into four layers:

| Layer | Responsibility | Depends on |
| --- | --- | --- |
| `domain` | Entities, value objects, invariants, domain errors | Python standard library only |
| `application` | Use cases, commands/queries, ports, unit-of-work contracts | `domain` |
| `infrastructure` | SQLAlchemy models, repositories, session management, logging/config adapters | `application`, `domain` |
| `presentation` | FastAPI app, routers, dependencies, request/response schemas | `application`, `infrastructure` |

Dependency flow always points inward:

```text
presentation -> application -> domain
infrastructure -> application -> domain
```

That separation keeps the domain and application layers free from FastAPI, SQLAlchemy, and Pydantic imports, which makes the use cases easier to test and swap across adapters.

## Quickstart

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker Engine with the Compose plugin

### 1. Configure environment variables

Copy the example file:

```bash
cp .env.example .env
```

The Docker Compose stack provides defaults for local development when these values are blank. If you want to run the API or migrations against a custom database, set `DATABASE_URL` or the discrete `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, and `DATABASE_NAME` variables in `.env`.

### 2. Install dependencies

```bash
make install
```

### 3. Start the local production-like stack

```bash
docker compose up -d --build
```

Equivalent Make target:

```bash
make compose-up
```

The stack exposes the API through Nginx on `http://localhost:8080` by default. You can change the public port with `NGINX_PORT` in `.env`.

### 4. Verify the service

Open the following endpoints through the reverse proxy:

- `http://localhost:8080/health`
- `http://localhost:8080/ready`
- `http://localhost:8080/docs`
- `http://localhost:8080/openapi.json`

Inspect running services and logs when needed:

```bash
docker compose ps
docker compose logs -f api
```

### 5. Stop the stack

```bash
docker compose down
```

Equivalent Make target:

```bash
make compose-down
```

## Development Commands

### Run the full local quality gate

```bash
make check
```

### Lint and format

```bash
make lint
make format
make format-check
```

### Type checking

```bash
make typecheck
```

### Tests

```bash
make test
```

Integration tests require PostgreSQL and a dedicated `TEST_DATABASE_URL`. The integration runner applies Alembic migrations before executing `tests/integration`:

```bash
make test-integration
```

### Load testing

Seed the deterministic workspace/project fixture and run the k6 workload:

```bash
make load-test-seed
make load-test
```

Override the workload shape when needed:

```bash
BASE_URL=http://127.0.0.1:8080 LOAD_TEST_VUS=20 LOAD_TEST_DURATION=1m make load-test
```

The full workflow, fixture IDs, thresholds, and baseline latency report live in [docs/PERFORMANCE.md](docs/PERFORMANCE.md).

### Migrations

```bash
make migrate
make migrate-down
```

### pre-commit hooks

```bash
uv run pre-commit install
make pre-commit
```

## Current HTTP Slice

The current public slice is centered on task workflows:

- `POST /v1/tasks`
- `GET /v1/tasks`
- `POST /v1/tasks/{task_id}/transition`
- `POST /v1/tasks/{task_id}/assign`

Task routes require an authenticated principal through the `X-User-ID` header. Because the repository has not exposed workspace and project creation routes yet, the easiest way to see the end-to-end task flow is through the integration suite in [tests/integration/presentation/test_tasks.py](tests/integration/presentation/test_tasks.py), which seeds the required workspace and project records directly in PostgreSQL before exercising the API.

## Project Layout

```text
.
├── alembic/                 # Migration environment and versioned schema changes
├── app/src/
│   ├── application/         # Use cases and ports
│   ├── domain/              # Pure business rules
│   ├── infrastructure/      # SQLAlchemy, settings, logging, UoW adapters
│   └── presentation/        # FastAPI app, routers, schemas, dependencies
├── docker/                  # Container entrypoint and Nginx config
├── docs/                    # Contract, architecture, and NFR documentation
├── scripts/                 # Test and automation helpers
└── tests/                   # Smoke, unit, and integration coverage
```

## Reverse Proxy Notes

Nginx forwards `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Forwarded-Host` to the API. The application only trusts forwarded headers when `PROXY_HEADERS_ENABLED=true` and the immediate client matches `FORWARDED_ALLOW_IPS`, which keeps generated URLs, request metadata, and logging correct behind the proxy.
