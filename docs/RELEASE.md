# Release Process

This document defines the release checklist for tagged versions of this repository and includes the ready-to-paste GitHub Release notes for `v0.1.0`.

## Target Release

- Git tag: `v0.1.0`
- Package version: `0.1.0`
- Release scope: the current task-management vertical slice implemented in this repository

## Release Checklist

- [ ] Merge the release candidate into `main` and confirm the working tree is clean.
- [ ] Confirm `pyproject.toml` still declares version `0.1.0`.
- [ ] Run `make check`.
- [ ] Run `make test-integration`.
- [ ] Run `docker build --tag fastapi-clean-architecture-api:v0.1.0 .`.
- [ ] Run `docker compose up -d --build` and verify the service through Nginx.
- [ ] Verify `http://localhost:8080/health`, `http://localhost:8080/ready`, and `http://localhost:8080/docs`.
- [ ] Confirm `.github/workflows/ci.yml` is green on `main` for `Quality`, `Integration`, and `Docker Build`.
- [ ] Review release-facing documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACT.md`, `docs/NFRS.md`, and `docs/PERFORMANCE.md`.
- [ ] Create the annotated Git tag `v0.1.0`.
- [ ] Push `main` and the tag to `origin`.
- [ ] Publish the GitHub Release using the notes in this document.

## Release Commands

Run the release from a local checkout that already contains the final release commit:

```bash
git checkout main
git pull --ff-only
make check
make test-integration
docker build --tag fastapi-clean-architecture-api:v0.1.0 .
docker compose up -d --build
curl -fsS http://localhost:8080/health
curl -fsS http://localhost:8080/ready
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin main
git push origin v0.1.0
```

If the Compose stack was only started for release verification, stop it after the checks finish:

```bash
docker compose down
```

## GitHub Release Fields

- Release title: `v0.1.0`
- Tag: `v0.1.0`
- Target branch: `main`

## GitHub Release Notes For `v0.1.0`

Copy the block below into the GitHub Release description.

```md
## What's included

- A FastAPI backend organized with Clean Architecture across `domain`, `application`, `infrastructure`, and `presentation` layers.
- A task-management vertical slice with create, list, status transition, and assignment endpoints.
- PostgreSQL persistence through SQLAlchemy repositories and a Unit of Work, plus Alembic migrations for reproducible schema setup.
- A local production-like stack with Docker Compose, PostgreSQL, and Nginx reverse proxying the API.
- Structured logging, correlation IDs, `/health`, and `/ready` endpoints for operational visibility.
- Automated quality gates with Ruff, mypy, pytest, integration tests against Postgres, Docker image builds, and a documented k6 baseline.

## How to run

1. Copy the environment template: `cp .env.example .env`
2. Install dependencies: `make install`
3. Start the local stack: `docker compose up -d --build`
4. Open the service through Nginx:
   - `http://localhost:8080/health`
   - `http://localhost:8080/ready`
   - `http://localhost:8080/docs`
5. Run the local quality gate when needed: `make check`
6. Run PostgreSQL integration tests when needed: `make test-integration`

## Current slice and constraints

- The public HTTP slice currently focuses on task workflows.
- Task endpoints require the `X-User-ID` header for the authenticated principal in the current version.
- The broader target contract for workspaces, projects, and JWT auth is documented and scaffolded, but not fully exposed yet in the public API.

## Documentation

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CONTRACT.md`
- `docs/NFRS.md`
- `docs/PERFORMANCE.md`
```