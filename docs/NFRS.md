# Non-Functional Requirements (NFRs)

## Overview

Non-Functional Requirements (NFRs) define the quality attributes and operational characteristics that make the API production-ready. Unlike functional requirements (which define *what* the API does), NFRs define *how well* it does it.

Each NFR below is **measurable and verifiable**, with clear acceptance criteria that can be checked by automated tools, tests, or manual inspection.

## v0.1.0 Verification Status

Verification date: `2026-04-11`

The sections below describe the target NFR standard for the broader product contract. The table here records what is already implemented in the current release, what is only partial for the shipped task slice, and what remains deferred or external.

| Area | Status | Verification notes |
| --- | --- | --- |
| Security: BOLA for current task slice | Implemented | Cross-user integration tests cover create, list, transition, and assign task flows and return `404 Not Found` concealment responses for foreign resources. Deferred: broader workspace/project/user CRUD surfaces are not public yet. |
| Security: Resource consumption | Partial | Task list pagination is bounded to `1..100` and covered by unit and integration tests. Deferred: request/DB timeout settings and rate limiting are documented goals, not implemented controls. |
| Security: Reverse proxy behavior | Implemented | Nginx forwards `X-Forwarded-*` headers, the app trusts configured proxy hops, and `/docs` was verified through Nginx on `2026-04-11`. Deferred: HTTPS/TLS termination and HSTS are not configured in the local HTTP stack. |
| Security: Input validation | Partial | FastAPI and Pydantic validate the shipped task endpoints, and SQLAlchemy ORM is used for persistence. Deferred: explicit malicious-payload security tests are not yet part of the suite. |
| Reliability: Liveness and readiness | Implemented | `/health` and `/ready` are covered by smoke tests, and both endpoints returned successful responses through Nginx during local verification. |
| Reliability: Graceful shutdown | Partial | Docker uses exec-form startup and `docker compose down` completed cleanly during verification. Deferred: no explicit FastAPI lifespan shutdown hooks or dedicated shutdown tests exist yet. |
| Observability | Implemented | Structured JSON logs, error codes, request duration, correlation IDs, and stdout logging are implemented and covered by unit tests. |
| Testing and code quality | Partial | Ruff, format check, mypy, and pytest passed locally on `2026-04-11`; integration tests are present but require `TEST_DATABASE_URL`. Deferred: coverage reports and threshold enforcement are not configured. |
| Database and migrations | Partial | Alembic migrations, upgrade/downgrade commands, and the current task schema are implemented. Deferred: user/workspace-member schema and some target indexes/constraints belong to deferred endpoints. |
| DevOps and containerization | Implemented | The Dockerfile is multi-stage, runs as a non-root user, and uses exec-form `CMD`; `docker compose config --quiet` and `docker compose up -d --build` succeeded locally. |
| CI | Partial | `.github/workflows/ci.yml` runs quality, integration, and Docker build jobs on pull requests. External/manual: branch protection and run-history verification live in GitHub settings, not the repository. |
| API documentation | Partial | `/docs` and `/openapi.json` are available and tested. Deferred: example payload metadata is still sparse, and only the shipped task slice appears in the public schema. |
| Performance | Partial | A k6 workload, a seed script, and a documented local baseline exist in `docs/PERFORMANCE.md`. Deferred: automated SLO enforcement in CI is not implemented. |
| Release | Partial | Version `0.1.0` and release checklist/notes exist. External/manual: the `v0.1.0` git tag and published GitHub Release are manual release steps and are not present in the local workspace yet. |

Unless a row above is marked as implemented, the detailed sections below describe the target state rather than a guarantee that the current release already fulfills every item.

---

## 1. Security

### 1.1 Broken Object Level Authorization (BOLA) Prevention

**Requirement:** Users cannot access, modify, or delete tasks/projects/workspaces that they do not own or have permission to view.

**Verification:**
- Unit/integration tests for every ID-based endpoint (`GET /v1/tasks/{id}`, `PATCH /v1/tasks/{id}`, etc.):
  - Create task as User A.
  - Attempt access as User B (different workspace member or outsider) → expect `403 Forbidden` or `404 Not Found`.
  - Attempt modification as User B → expect `403 Forbidden`.
- Coverage: All CRUD operations on `tasks`, `projects`, `workspaces`, and commands (`/transition`, `/assign`).
- **Acceptance:** 100% of identity-based endpoints have explicit authorization checks in the use case layer; test suite covers >90% of cross-user scenarios.

**Implementation Note:** The current task slice uses an ownership-based concealment policy. When an authenticated actor references a `project_id` or `task_id` that belongs to another workspace owner, the API returns `404 Not Found` instead of `403 Forbidden` so resource existence is not leaked across tenants. The principal is currently supplied through the `X-User-ID` header, and the same application-layer checks can later be reused behind JWT authentication.

---

### 1.2 Unrestricted Resource Consumption Prevention

**Requirement:** API prevents denial-of-service via unbounded pagination, large payloads, or uncontrolled loops.

**Sub-Requirements:**

#### 1.2.1 Pagination Limits
- `page_size` parameter:
  - **Max page_size for `/v1/tasks`:** 100 items per page.
  - **Max page_size for other list endpoints:** 50 items per page.
  - Requests with `page_size > limit` return `422 Unprocessable Entity` with descriptive error.
  - Requests with `page_size < 1` or `page <= 0` return `422 Unprocessable Entity`.

**Verification:**
- Test: `GET /v1/tasks?page_size=200` → expect 422 and error code `INVALID_PAGE_SIZE`.
- Test: `GET /v1/workspaces?page_size=60` → expect 422.
- Test: `GET /v1/tasks?page=0` → expect 422 or 400.
- **Acceptance:** All list endpoints enforce limits; no pagination parameter bypasses the check.

#### 1.2.2 Timeouts & Performance Guardrails
- **Request timeout:** 30 seconds maximum per request (configurable via app settings).
- **DB query timeout:** 10 seconds per database operation (configurable).
- Timeouts result in `504 Gateway Timeout` or `500 Internal Server Error` with safe error message (no stack trace exposed to client).

**Verification:**
- Configuration documented in README or `.env.example`.
- Manual test: Simulate slow DB query; confirm timeout is triggered.
- **Acceptance:** Timeout values documented; no request hangs indefinitely.

#### 1.2.3 Rate Limiting (Optional but Recommended)
- Implement per-IP or per-user rate limiting (e.g., 100 requests/minute).
- Exceeding limit returns `429 Too Many Requests`.
- Can be implemented via FastAPI middleware or reverse proxy (Nginx).

**Verification:**
- If implemented: Test via load script (e.g., k6, locust) confirming 429 responses.
- **Acceptance:** Rate limit configuration documented and functional.

---

### 1.3 Correct Behavior Behind Reverse Proxy

**Requirement:** When the API runs behind a reverse proxy (Nginx in this case), HTTPS scheme, client IP, and other forwarded information are correctly interpreted.

**Verification:**

- **Setup:** Run via `docker compose up -d` with Nginx reverse proxy.
- **Test Cases:**
  1. Access `/docs` via Nginx (e.g., `http://localhost/docs`) → check that Swagger UI loads and API schema shows correct servers/URLs.
  2. Verify that `request.url.scheme` in logs shows `https` (if client accessed via HTTPS) or correctly reflects the original request.
  3. Check that `request.client.host` correctly identifies the original client IP (not Nginx's localhost).
- **Configuration:**
  - FastAPI app must be run with `--proxy-headers` flag (or `TrustedHost` middleware configured) to trust `X-Forwarded-*` headers from Nginx.
  - Nginx must forward headers: `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`.
  
**Acceptance Criteria:**
- [ ] Nginx reverse proxy is functional (`docker compose up` starts Nginx, routes requests to API).
- [ ] FastAPI respects forwarded headers (configurable, documented in README).
- [ ] Logs and generated URLs (e.g., in OpenAPI docs) reflect the correct origin.
- [ ] Security headers (e.g., `Strict-Transport-Security` if applicable) are set by Nginx or app.

---

### 1.4 Input Validation & Injection Prevention

**Requirement:** All user inputs are validated; SQL injection, command injection, and other injection attacks are prevented.

**Verification:**
- Pydantic schemas validate:
  - Data types (e.g., email format, date format).
  - Field lengths (e.g., task title max 255 characters).
  - Enum constraints (e.g., status ∈ {todo, doing, done}).
- SQLAlchemy ORM with parameterized queries prevents SQL injection (no raw SQL string concatenation).
- Test: Attempt injection payloads (e.g., `title: "'; DROP TABLE tasks; --"`) → expect validation error or safe insertion.

**Acceptance Criteria:**
- [ ] Pydantic schemas are used for all request bodies.
- [ ] SQLAlchemy or equivalent ORM is used for database queries (no raw SQL).
- [ ] Tests cover validation edge cases (empty strings, max length, special characters).

---

## 2. Reliability & Availability

### 2.1 Liveness Probe (`/health`)

**Requirement:** A dedicated endpoint signals whether the API process is alive.

**Specification:**
- **Endpoint:** `GET /health`
- **Response (Success):** `200 OK` with `{ "status": "ok" }`
- **Response (Failure):** Should rarely fail; indicates process is crashed or in a bad state.
- **Behavior:** Does **NOT** check external dependencies (DB, cache, etc.); only confirms the process is running.
- **Use Case:** Kubernetes/Docker Compose uses this to restart unhealthy containers.

**Verification:**
```bash
curl http://localhost:8000/health
# Expected: 200 { "status": "ok" }
```

**Acceptance Criteria:**
- [ ] Endpoint implemented and returns 200 with correct payload.
- [ ] No database or external service calls in the health check.
- [ ] Responds in < 100ms.

---

### 2.2 Readiness Probe (`/ready`)

**Requirement:** A dedicated endpoint signals whether the API is ready to accept traffic (all critical dependencies are healthy).

**Specification:**
- **Endpoint:** `GET /ready`
- **Response (Ready):** `200 OK` with `{ "status": "ok", "checks": { "database": "ok", ... } }`
- **Response (Not Ready):** `503 Service Unavailable` with detailed checks.
- **Checks Include:**
  - Database connectivity (attempt a test query or connection pool check).
  - Optional: Cache (Redis), message queue, external APIs if integrated.
- **Use Case:** Load balancers use this to drain traffic before shutdown; Kubernetes uses this to decide pod readiness.

**Verification:**
```bash
# Before DB is up:
curl http://localhost:8000/ready
# Expected: 503 { "status": "unavailable", "checks": { "database": "down" } }

# After DB is healthy:
curl http://localhost:8000/ready
# Expected: 200 { "status": "ok", "checks": { "database": "ok" } }
```

**Acceptance Criteria:**
- [ ] Endpoint implemented and returns 200 (when ready) or 503 (when not ready).
- [ ] Checks at least database connectivity.
- [ ] Responds in < 500ms.
- [ ] Returns JSON with `status` and `checks` fields.

---

### 2.3 Graceful Shutdown

**Requirement:** The API cleanly shuts down on SIGTERM (e.g., via `docker stop` or K8s termination), closing database connections and completing in-flight requests.

**Verification:**
- Use FastAPI's lifespan context manager (or similar) to register shutdown handlers.
- Test: Run `docker compose up`, then `docker compose down` (sends SIGTERM) → check logs for clean shutdown messages, no connection errors in other services.
- Confirm that database connections are closed (check Postgres logs for disconnections).

**Acceptance Criteria:**
- [ ] Lifespan handlers are configured (shutdown context manager or `@app.on_event("shutdown")`).
- [ ] In-flight requests are completed gracefully (or timed out after a short grace period).
- [ ] Database connections are explicitly closed on shutdown.
- [ ] Logs show "Shutting down" or similar message.

---

## 3. Observability & Logging

### 3.1 Structured Logging

**Requirement:** All significant events are logged in a consistent, machine-parseable format (JSON or key=value).

**Specification:**
- **Log Format:** JSON with fields:
  ```json
  {
    "timestamp": "2026-01-17T22:00:00.000Z",
    "level": "INFO|WARNING|ERROR|DEBUG",
    "message": "Task created successfully",
    "request_id": "req_abc123",
    "user_id": "user_123",
    "path": "/v1/tasks",
    "method": "POST",
    "status_code": 201,
    "duration_ms": 45
  }
  ```
- **Minimum Fields:** timestamp, level, message, request_id (or correlation_id).
- **Log Levels:**
  - `INFO`: Normal operation (create, update, delete, login, etc.).
  - `WARNING`: Recoverable issues (retries, validation failures, deprecated endpoints).
  - `ERROR`: Failures requiring attention (DB errors, auth failures, unhandled exceptions).
  - `DEBUG`: Detailed tracing (use case transitions, query parameters, etc.), off by default in production.

**Verification:**
- Log a few requests and examine output:
  ```bash
  curl -X POST http://localhost:8000/v1/tasks -d '{"project_id": "...", "title": "Test"}' -H "Content-Type: application/json"
  # Check application logs for structured JSON output.
  ```
- Confirm that `request_id` appears in all logs for a single request (aids debugging).

**Acceptance Criteria:**
- [ ] Logs are JSON-formatted (or another structured format).
- [ ] All requests log: timestamp, level, message, status_code, duration.
- [ ] All errors log: error code, error message, traceback (in dev mode).
- [ ] `request_id` is generated per request and included in all logs.
- [ ] Logs are written to stdout (Docker/K8s standard).

---

### 3.2 Correlation ID / Request Tracing

**Requirement:** Related operations (e.g., a request and internal domain events) share a correlation ID for end-to-end tracing.

**Specification:**
- **Generation:** If client provides `X-Correlation-ID` header, use it; otherwise, generate a UUID.
- **Propagation:** Include correlation ID in all logs and outgoing requests (if calling external APIs).
- **Format:** UUID v4 or similar (e.g., `550e8400-e29b-41d4-a716-446655440000`).

**Verification:**
- Test: Send request with `curl -H "X-Correlation-ID: my-test-123"`.
- Check logs: Confirm `correlation_id: "my-test-123"` appears in all related log entries.
- Test: Send request without header; check that a new ID is generated and consistent in logs.

**Acceptance Criteria:**
- [ ] Correlation ID is extracted from header or generated.
- [ ] Correlation ID is included in all logs for a request.
- [ ] Correlation ID is accessible in domain/application layer (for debugging).

---

## 4. Testing & Code Quality

### 4.1 Automated Testing

**Requirement:** Code is tested at multiple levels; target >= 80% coverage for core layers (domain, application).

**Specification:**

#### 4.1.1 Unit Tests
- **Scope:** Domain entities, value objects, and use cases.
- **Approach:** Use fakes/mocks for repositories and external services (no DB, no network).
- **Framework:** `pytest` with fixtures.
- **Example:**
  ```python
  def test_task_cannot_transition_from_doing_to_todo():
      task = Task(id="1", status="doing", ...)
      with pytest.raises(InvalidTransitionError):
          task.transition_to("todo")
  ```

#### 4.1.2 Integration Tests
- **Scope:** Use cases with real repository implementations (in-memory DB or test Postgres instance).
- **Approach:** Set up a test database (via Docker Compose or test fixtures), run migrations, and verify end-to-end flows.
- **Example:**
  ```python
  @pytest.mark.asyncio
  async def test_create_task_use_case(postgres_session):
      repo = SQLAlchemyTaskRepository(postgres_session)
      use_case = CreateTaskUseCase(repo)
      result = await use_case.execute(CreateTaskCommand(...))
      assert result.id is not None
  ```

#### 4.1.3 End-to-End Tests (Optional)
- **Scope:** Full HTTP flow via test client (FastAPI's `TestClient`).
- **Approach:** Test a few critical paths (login, create task, list, transition).
- **Example:**
  ```python
  def test_create_task_via_api(client):
      response = client.post("/v1/tasks", json={"project_id": "...", "title": "..."})
      assert response.status_code == 201
  ```

**Verification:**
- Run `pytest --cov` and generate coverage report.
- Coverage report shows >= 80% for `domain/` and `application/` layers.
- CI pipeline fails if coverage drops below threshold.

**Acceptance Criteria:**
- [ ] Unit tests exist for domain entities and use cases.
- [ ] Integration tests exist for repositories and use cases.
- [ ] Test suite runs via `pytest` and passes.
- [ ] Coverage report is generated (via `pytest-cov`).
- [ ] Target coverage >= 80% for core layers (domain, application).
- [ ] Tests are run in CI (GitHub Actions).

---

### 4.2 Linting & Code Formatting

**Requirement:** Code follows consistent style and passes static analysis checks.

**Specification:**
- **Tool:** `ruff` (linting and formatting).
  - `ruff check .` → Lint checks (import order, unused variables, etc.).
  - `ruff format .` → Auto-format code (indentation, line length, etc.).
- **Configuration:** `pyproject.toml` with `[tool.ruff]` section.
- **Line Length:** 100 characters (configurable).
- **Pre-commit Hook:** Automated via `pre-commit` framework; lint/format runs before every commit.

**Verification:**
```bash
ruff check .
ruff format --check .
```

**Acceptance Criteria:**
- [ ] `ruff check .` passes (no linting errors).
- [ ] `ruff format --check .` passes (code is formatted correctly).
- [ ] Pre-commit hook is configured (`.pre-commit-config.yaml`) and installed locally.
- [ ] CI pipeline runs `ruff check` and `ruff format --check` on every PR.

---

### 4.3 Type Checking

**Requirement:** All Python code is annotated with type hints; `mypy` (strict mode) passes without errors.

**Specification:**
- **Tool:** `mypy`.
- **Mode:** Strict (`--strict` flag or `strict = true` in `mypy.ini`).
- **Coverage:** All production code (domain, application, infrastructure, presentation).
- **Configuration:** `pyproject.toml` or `mypy.ini` with:
  ```ini
  [mypy]
  strict = true
  python_version = 3.11  # or your target version
  ```

**Verification:**
```bash
mypy src/
# Expected: No errors
```

**Acceptance Criteria:**
- [ ] All functions have return type annotations.
- [ ] All parameters have type annotations.
- [ ] No `Any` types used (or explicitly justified with comments).
- [ ] `mypy --strict` passes.
- [ ] CI pipeline runs `mypy --strict` and fails if errors are found.

---

## 5. Database & Migrations

### 5.1 Version-Controlled Migrations

**Requirement:** Database schema changes are tracked, reviewable, and safely applied/rolled back via Alembic.

**Specification:**
- **Tool:** Alembic (SQLAlchemy migration tool).
- **Migrations Directory:** `alembic/versions/`.
- **Naming:** Auto-generated or manual (e.g., `001_initial_schema.py`, `002_add_task_priority.py`).
- **Tracking:** Migrations are checked into version control (Git).
- **Idempotency:** Each migration is idempotent (can be safely re-applied if interrupted).

**Verification:**
- Start with a clean Postgres database.
- Run `alembic upgrade head` → all tables are created correctly.
- Connect to Postgres and inspect schema:
  ```sql
  \dt  -- list tables
  \d tasks  -- describe tasks table
  ```
- Verify that all expected tables and columns exist.
- Test rollback: `alembic downgrade -1` → schema reverts to previous version.
- Test re-apply: `alembic upgrade head` → schema returns to current version.

**Acceptance Criteria:**
- [ ] Alembic is initialized (alembic/ directory exists).
- [ ] At least one initial migration exists (`001_initial_schema.py` or similar).
- [ ] `alembic upgrade head` successfully creates all tables on a clean database.
- [ ] `alembic downgrade -1` and `alembic upgrade head` work correctly.
- [ ] Migration commands are documented in README.
- [ ] CI runs migrations as part of the test suite (to catch schema errors early).

---

### 5.2 Database Constraints & Indexes

**Requirement:** Database enforces data integrity via constraints; performance-critical columns are indexed.

**Specification:**
- **Primary Keys:** All tables have a primary key (e.g., `id UUID PRIMARY KEY`).
- **Foreign Keys:** Relationships are enforced via FK constraints (e.g., `tasks.project_id REFERENCES projects(id) ON DELETE CASCADE`).
- **Unique Constraints:** Email uniqueness (`users.email UNIQUE`), workspace name within organization, etc.
- **Check Constraints:** Optional (e.g., `tasks.status IN ('todo', 'doing', 'done')`).
- **Indexes:**
  - `tasks.status` (for filtering by status).
  - `tasks.due_date` (for sorting/filtering).
  - `tasks.assigned_to` (for filtering by assignee).
  - `tasks.project_id` (for list queries by project).
  - `workspaces.name` (for search/filtering).

**Verification:**
- Query Postgres metadata:
  ```sql
  \d tasks  -- show columns and indexes
  SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name = 'tasks';
  ```
- Confirm primary keys, foreign keys, and indexes exist.

**Acceptance Criteria:**
- [ ] All tables have primary keys.
- [ ] Foreign key relationships are defined and enforced.
- [ ] Email/unique fields have unique constraints.
- [ ] Performance-critical columns are indexed.
- [ ] Constraints are defined in migration files (not in ORM model alone).

---

## 6. DevOps & Containerization

### 6.1 Docker Image & Compose Setup

**Requirement:** The entire stack (API, Postgres, Nginx) can be started locally via `docker compose up` with no manual setup.

**Specification:**
- **Dockerfile:** Multi-stage build for efficiency; runs app with `fastapi run` or equivalent.
- **Docker Compose File:** `docker-compose.yml` with services:
  - `api`: FastAPI application.
  - `postgres`: PostgreSQL 15+ database.
  - `nginx`: Reverse proxy (routes HTTP to FastAPI, handles TLS termination if needed).
- **Health Checks:** All services have `healthcheck` definitions (Compose uses these to determine readiness).
- **Ports Exposed:**
  - Nginx: `80` or `443` (HTTP/HTTPS).
  - FastAPI: (internal, not exposed directly; accessed via Nginx).
  - Postgres: (internal, exposed only for development/debugging).
- **Environment Variables:** Configured via `.env` file or `docker-compose.override.yml` for development overrides.

**Verification:**
```bash
cd /path/to/repo
docker compose up -d
# Wait for services to be healthy
sleep 5
curl http://localhost/health
# Expected: 200 { "status": "ok" }

curl http://localhost/docs
# Expected: Swagger UI loads (served via Nginx)
```

**Acceptance Criteria:**
- [ ] `docker-compose.yml` exists and is valid.
- [ ] `docker compose up -d` successfully starts all services.
- [ ] All services reach "healthy" state (check `docker compose ps`).
- [ ] `/health` and `/ready` endpoints respond correctly.
- [ ] `/docs` is accessible via Nginx.
- [ ] README includes Docker Compose setup instructions.

---

### 6.2 Dockerfile Best Practices

**Requirement:** Docker image is lean, secure, and follows best practices.

**Specification:**
- **Base Image:** Python 3.11+ slim or alpine (e.g., `python:3.11-slim`).
- **Multi-Stage Build:** Separate build stage (dependencies compiled) from runtime stage (lean image).
- **Non-Root User:** App runs as non-root user (e.g., `appuser`), not `root`.
- **Minimal Layers:** Combine `RUN` commands where possible to reduce image size.
- **Health Check:** Define `HEALTHCHECK` instruction (e.g., `curl /health`).
- **Command Form:** Use exec form (array) for `CMD` and `ENTRYPOINT` to ensure proper signal handling.
  ```dockerfile
  CMD ["fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]
  ```

**Verification:**
```bash
docker build -t my-api:latest .
docker inspect my-api:latest | grep -A 10 '"Cmd"'
# Expected: array form, not shell form
docker image ls
# Expected: image size < 500 MB (typical for Python app)
```

**Acceptance Criteria:**
- [ ] Dockerfile exists and builds successfully.
- [ ] Image is based on Python 3.11+ slim/alpine.
- [ ] Non-root user is configured.
- [ ] CMD is in exec form (array).
- [ ] Image size is reasonable (< 500 MB).

---

## 7. Continuous Integration (CI)

### 7.1 GitHub Actions Workflow

**Requirement:** Automated pipeline runs on every PR; must pass before merging.

**Specification:**
- **Trigger:** On push to `feature/*` branches and `main`.
- **Jobs:**
  1. **Lint:** `ruff check .`
  2. **Format:** `ruff format --check .`
  3. **Type Check:** `mypy --strict src/`
  4. **Test:**
     - Start Postgres via Docker.
     - Run `alembic upgrade head`.
     - Run `pytest --cov`.
     - Fail if coverage < 80%.
  5. **Build Image:** Build Docker image (validate Dockerfile syntax).
  6. **Optional:** Push image to registry (Docker Hub, GHCR, etc.).

**File:** `.github/workflows/ci.yml`

**Verification:**
- Create a test PR with a linting error; confirm workflow fails.
- Create a test PR with a passing change; confirm workflow passes.
- Confirm branch protection rule requires CI to pass before merge.

**Acceptance Criteria:**
- [ ] `.github/workflows/ci.yml` exists and is valid.
- [ ] Workflow runs on every PR.
- [ ] All jobs (lint, type check, test, build) pass.
- [ ] Branch protection rule blocks merges if CI fails.
- [ ] Workflow completes in < 10 minutes.

---

## 8. API Contract & Documentation

### 8.1 OpenAPI Specification

**Requirement:** API contract is auto-generated and always up-to-date (via FastAPI).

**Specification:**
- **Endpoint:** `GET /openapi.json` returns OpenAPI 3.0.2 schema.
- **Swagger UI:** `GET /docs` renders interactive Swagger UI.
- **ReDoc:** `GET /redoc` renders alternative API documentation.
- **Schema Accuracy:** All endpoints, parameters, request/response models are documented in Pydantic schemas and auto-reflected in OpenAPI.

**Verification:**
```bash
curl http://localhost/openapi.json | jq . | head -50
# Expected: Valid OpenAPI JSON with paths, definitions, info, etc.

curl http://localhost/docs
# Expected: HTML Swagger UI loads
```

**Acceptance Criteria:**
- [ ] `/openapi.json` returns valid OpenAPI 3.0.2 schema.
- [ ] `/docs` is accessible and interactive.
- [ ] All endpoints are documented in OpenAPI schema.
- [ ] Request/response models are reflected accurately.
- [ ] Example values are provided (via Pydantic `Field(example="...")`).

---

### 8.2 README & Architecture Documentation

**Requirement:** Repository includes clear documentation for setup, architecture, and contribution.

**Specification:**
- **README.md:**
  - Project overview and vision.
  - Quick start (how to clone, install, run).
  - `docker compose up` instructions.
  - How to run tests, lint, type-check.
  - How to create migrations.
  - Architecture overview (high-level diagram or description).
  - Links to CONTRACT.md and NFRS.md.
  
- **docs/ARCHITECTURE.md:**
  - Detailed layer descriptions (domain, application, infrastructure, presentation).
  - Dependency diagram (ASCII or image).
  - Example: "How to add a new use case."
  - Key design decisions (why Clean Architecture, why SQLAlchemy, etc.).

- **CONTRIBUTING.md:**
  - Code style guide.
  - Branch naming convention.
  - PR checklist.
  - How to report issues.

**Verification:**
- Open README.md in browser or editor; confirm it reads clearly.
- Follow README instructions to run the app from scratch (or CI simulates this).

**Acceptance Criteria:**
- [ ] README.md exists and is comprehensive.
- [ ] docs/ARCHITECTURE.md exists with layer descriptions.
- [ ] CONTRIBUTING.md exists (optional but recommended).
- [ ] CONTRACT.md and NFRS.md are linked in README.

---

## 9. Performance & Efficiency

### 9.1 Response Time SLOs

**Requirement:** API responds within acceptable latency for typical operations.

**Specification:**
- **Read Operations** (GET):
  - Single resource (e.g., `GET /v1/tasks/{id}`): p95 < 200ms.
  - List with pagination (e.g., `GET /v1/tasks?page_size=50`): p95 < 300ms.
- **Write Operations** (POST/PATCH):
  - Create resource (e.g., `POST /v1/tasks`): p95 < 500ms.
  - Update resource (e.g., `PATCH /v1/tasks/{id}`): p95 < 500ms.
- **Measurement:** Load test (via k6 or similar) with 10 concurrent users, typical payloads.

**Verification:**
- Create `tests/load/simple_load_test.js` (k6 script) that:
  - Authenticates.
  - Creates a workspace and project.
  - Lists and creates tasks in a loop.
  - Reports latency percentiles.
- Run: `k6 run tests/load/simple_load_test.js`.
- Compare results against SLOs.

**Acceptance Criteria:**
- [ ] Load test script exists.
- [ ] Measured latencies meet SLOs (or are documented as exceptions).
- [ ] Load test can be run locally and in CI.
- [ ] Results are reported in README or CI artifacts.

---

### 9.2 Database Query Efficiency

**Requirement:** Queries are optimized; N+1 problems and unnecessary full-table scans are avoided.

**Specification:**
- **Eager Loading:** Use SQLAlchemy `selectinload` or `joinedload` to avoid N+1 queries.
- **Indexes:** Critical columns (status, due_date, assigned_to, project_id) are indexed (see NFR 5.2).
- **Pagination:** All list queries use pagination (no unbounded result sets).

**Verification:**
- Enable SQLAlchemy query logging (`echo=True` in development).
- Test: `GET /v1/tasks?project_id=...` → inspect logs; should see 1–2 queries, not 1 + N.
- Test: `GET /v1/projects?workspace_id=...` → confirm projects are loaded via single query with proper indexes.

**Acceptance Criteria:**
- [ ] No N+1 queries in critical paths (verified via logging or profiling).
- [ ] All list endpoints use pagination.
- [ ] Indexes are created for frequently filtered/sorted columns.

---

## 10. Deployment & Release

### 10.1 Semantic Versioning

**Requirement:** Releases follow semantic versioning (MAJOR.MINOR.PATCH).

**Specification:**
- **Version Format:** `vMAJOR.MINOR.PATCH` (e.g., `v0.1.0`, `v1.2.3`).
- **MAJOR:** Breaking changes to API contract.
- **MINOR:** New features (backward compatible).
- **PATCH:** Bug fixes.
- **Tagging:** Tag in Git (e.g., `git tag v0.1.0`) and create a GitHub Release with notes.

**Verification:**
- Check Git tags: `git tag --list`.
- Check GitHub Releases page.

**Acceptance Criteria:**
- [ ] First release is tagged (e.g., `v0.1.0`).
- [ ] Release notes/CHANGELOG are included.
- [ ] Version is bumped in `__version__` or `pyproject.toml` for each release.

---

### 10.2 Release Checklist

**Requirement:** Before tagging a release, a checklist ensures quality and readiness.

**Specification:**

```markdown
## Release Checklist for v{VERSION}

- [ ] All CI jobs pass (lint, type check, tests, build).
- [ ] Release notes in `docs/RELEASE.md` and/or the GitHub Release draft are updated with new features, fixes, and deferred items.
- [ ] README and docs (CONTRACT.md, NFRS.md, ARCHITECTURE.md) are current.
- [ ] No open issues blocking the release (or marked as post-release).
- [ ] Manual smoke test on Compose environment:
  - [ ] `docker compose up -d` starts all services.
  - [ ] `/health` and `/ready` respond correctly.
  - [ ] Current public task workflow can be exercised via Swagger UI or curl (`POST /v1/tasks`, `GET /v1/tasks`, transition, assign).
  - [ ] `docker compose down` shuts down gracefully.
- [ ] Database migrations are tested (clean DB → upgrade head → queries work).
- [ ] Performance baselines are met (load test passes SLOs).
- [ ] Security checks passed (no known vulnerabilities in dependencies).
- [ ] Git tag is created: `git tag v{VERSION}`.
- [ ] GitHub Release is published with notes and link to docs.
```

**Verification:**
- Before release, print checklist and manually verify each item (or automate via CI where possible).

**Acceptance Criteria:**
- [ ] Release checklist exists (e.g., in `docs/RELEASE.md` or GitHub Releases template).
- [ ] Each release has a GitHub Release with notes.
- [ ] CHANGELOG.md is kept up-to-date.

---

## Summary Table

| Category | NFR | Acceptance Metric |
|---|---|---|
| **Security** | BOLA Prevention | 100% of ID-based endpoints have auth tests; all cross-user scenarios covered. |
| | Resource Consumption | Pagination limits enforced; 422 for violations; timeouts configured. |
| | Proxy Config | FastAPI runs with `--proxy-headers`; Nginx forwards headers correctly. |
| **Reliability** | Liveness (`/health`) | Endpoint returns 200; no DB check; responds < 100ms. |
| | Readiness (`/ready`) | Endpoint returns 200 (ready) or 503 (not ready); checks DB. |
| **Observability** | Structured Logging | JSON logs with timestamp, level, message, request_id, status_code. |
| **Testing** | Unit + Integration | >= 80% coverage for domain/application; `pytest` passes. |
| | Linting | `ruff check .` and `ruff format --check .` pass. |
| | Typing | `mypy --strict` passes; no `Any` types. |
| **Database** | Migrations | `alembic upgrade head` works; rollback/reapply tested. |
| | Constraints & Indexes | Primary keys, FKs, unique constraints, and indexes defined. |
| **DevOps** | Docker Compose | `docker compose up -d`; all services healthy; endpoints respond. |
| | Dockerfile | Multi-stage; non-root user; exec form CMD; image < 500 MB. |
| **CI/CD** | GitHub Actions | Workflow runs on PR; all jobs pass before merge. |
| **API** | OpenAPI | `/openapi.json` and `/docs` accurate and up-to-date. |
| **Performance** | Response Time | p95 < 200ms (reads), < 500ms (writes). |
| | Query Efficiency | No N+1 queries; indexes on critical columns; pagination enforced. |
| **Release** | Versioning | Releases follow MAJOR.MINOR.PATCH; tagged in Git. |
| | Release Process | Checklist completed before each release. |

---

## How to Use This Document

1. **During Development:** Refer to this document to understand what "done" means for each NFR.
2. **Before PR:** Self-check against relevant NFRs; ensure acceptance criteria are met.
3. **During Review:** Reviewers use this as a checklist to validate PRs.
4. **Before Release:** Run through the Summary Table to confirm all NFRs are met.
5. **For Onboarding:** New team members use this to understand code quality expectations.