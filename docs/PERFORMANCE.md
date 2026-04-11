# Performance Baseline

This document records the local load-test workflow and the current baseline for the task-management slice.

## Scope

The scenario covers the most relevant endpoints that exist today in the public API surface:

- `GET /health`
- `GET /ready`
- `GET /v1/tasks`
- `POST /v1/tasks`
- `POST /v1/tasks/{task_id}/transition`
- `POST /v1/tasks/{task_id}/assign`

Each virtual user executes the same workflow in a loop:

1. Check liveness (`/health`).
2. List tasks for a deterministic project fixture.
3. Create a new task.
4. Transition the new task from `todo` to `doing`.
5. Assign the task to a synthetic user id.
6. Check readiness (`/ready`).

The fixture data is seeded from an ephemeral `api` container on the Compose network because the current public slice does not yet expose workspace or project creation routes.

## Files

- `loadtests/task_workflow.js`: k6 workload definition.
- `scripts/seed_load_test_data.py`: idempotent fixture seed for the load-test workspace/project.
- `scripts/run_load_tests.sh`: local wrapper that seeds the data, checks readiness, and runs k6.

## How To Run Locally

### Prerequisites

- Docker Engine with Compose
- Linux host if you want to use the Docker-based k6 fallback (`--network host`)

### 1. Start the stack

```bash
docker compose up -d --build
```

### 2. Seed the deterministic project fixture

```bash
make load-test-seed
```

The seed script creates or reuses these defaults:

- `LOAD_TEST_USER_ID=00000000-0000-0000-0000-000000000101`
- `LOAD_TEST_ASSIGNEE_ID=00000000-0000-0000-0000-000000000102`
- `LOAD_TEST_PROJECT_ID=00000000-0000-0000-0000-000000000301`

### 3. Run the baseline workload

```bash
make load-test
```

Defaults:

- `BASE_URL=http://127.0.0.1:8080`
- `LOAD_TEST_VUS=10`
- `LOAD_TEST_DURATION=30s`
- `LOAD_TEST_PAGE_SIZE=20`

### 4. Customize the run when needed

```bash
BASE_URL=http://127.0.0.1:8080 LOAD_TEST_VUS=20 LOAD_TEST_DURATION=1m make load-test
```

Export the machine-readable summary when you want to archive a run:

```bash
LOAD_TEST_SUMMARY_EXPORT=artifacts/load-test-summary.json make load-test
```

If you already have a local `k6` binary, the wrapper will use it automatically. Otherwise it falls back to the official `grafana/k6` Docker image.

## Baseline Environment

The baseline below was captured on 2026-04-11 on a local Linux workstation with the repository's default Docker Compose stack:

- Nginx reverse proxy on port `8080`
- FastAPI application container behind Nginx
- PostgreSQL 17 container
- k6 scenario: `10` virtual users for `30s`
- Result: `1001` iterations, `6007` HTTP requests, `0.00%` failed requests, `198.66 req/s`

## Baseline Results

| Endpoint | p95 latency | Notes |
| --- | ---: | --- |
| `GET /health` | `10.29 ms` | Liveness stayed comfortably below the `100 ms` local guardrail. |
| `GET /ready` | `21.22 ms` | Includes the lightweight database readiness check. |
| `GET /v1/tasks` | `39.22 ms` | Uses page `1` with page size `20`. |
| `POST /v1/tasks` | `38.66 ms` | Creates a new task on each iteration. |
| `POST /v1/tasks/{task_id}/transition` | `43.77 ms` | Transitions each fresh task to `doing`. |
| `POST /v1/tasks/{task_id}/assign` | `42.34 ms` | Assigns each fresh task to the synthetic assignee. |

End-to-end workflow iteration p95: `362.36 ms`.

## Suggested Local SLO Guardrails

The k6 script encodes pragmatic thresholds for this repository's local baseline:

- `http_req_failed < 1%`
- `checks > 99%`
- `GET /health` p95 `< 100 ms`
- `GET /ready` p95 `< 150 ms`
- `GET /v1/tasks` p95 `< 250 ms`
- `POST /v1/tasks` p95 `< 350 ms`
- `POST /v1/tasks/{task_id}/transition` p95 `< 350 ms`
- `POST /v1/tasks/{task_id}/assign` p95 `< 350 ms`
- End-to-end iteration p95 `< 1250 ms`

These are local-development SLOs, not production commitments. They exist to provide a repeatable regression signal when the current vertical slice changes.
