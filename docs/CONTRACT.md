# Product Contract

## Vision & Objective

This FastAPI backend project demonstrates **production-ready API architecture** through a Workspace → Project → Task management domain. The primary value is showcasing **Clean Architecture principles**, quality assurance practices, and operational maturity (CI/CD, testing, containerization, observability) for a distributed system—not the domain utility itself.

**Target Audience:** Engineering teams and technical recruiters evaluating backend competency in architecture, testing, quality, and deployment.

---

## Scope (Target v1)

This section defines the target product contract for the full v1 API surface. The current `v0.1.0` release intentionally implements a smaller, verified subset centered on task workflows and operational readiness; the shipped status is tracked in [Success Criteria & Acceptance](#success-criteria--acceptance).

### Core Entities & Data Model

The API manages the following entities within a Postgres database:

- **User**: Authentication identity with email and password (hashed).
- **Workspace**: A boundary/organization for collaboration; users become members with roles.
- **WorkspaceMember**: Relationship between User and Workspace, including role-based access (e.g., owner, collaborator, viewer).
- **Project**: Belongs to a Workspace; represents a grouping of tasks.
- **Task**: Belongs to a Project; has title, description, status, priority, due date, assigned_to, created_by.
- **TaskEvent**: Immutable log of changes to tasks (auditoria/event sourcing pattern for traceability).

### Core Business Rules (v1)

1. **Task Status Transitions**: Tasks follow a validated state machine:
   - Valid transitions: `todo` → `doing` → `done` (or `todo` → `done` directly).
   - Invalid transitions are rejected with a 409 Conflict error and a descriptive message.
   - Transitions are exposed as a dedicated command endpoint (`POST /v1/tasks/{id}/transition`) in addition to raw CRUD.

2. **Role-Based Access Control (RBAC)**:
   - Workspace members have roles: `owner`, `collaborator`, `viewer`.
   - Only owners can add/remove members or delete a workspace.
   - Collaborators and owners can create/edit projects and tasks; viewers can only read.
   - Fine-grained checks prevent direct access to objects outside the authorized workspace.

3. **Audit Trail**:
   - Every significant action (create, update, status change, assignment) is logged in `TaskEvent` for compliance and debugging.

### Target API Surface (v1)

All business endpoints are prefixed with `/v1/`.

#### Authentication & Users

```
POST /v1/auth/login
  Request:  { email, password }
  Response: { access_token, refresh_token, token_type }
  
POST /v1/auth/refresh
  Request:  { refresh_token }
  Response: { access_token, token_type }
  
POST /v1/users
  Request:  { email, password, full_name? }
  Response: { id, email, created_at }
```

#### Workspaces

```
GET /v1/workspaces
  Query params: page=1, page_size=20
  Response: { items: [...], total, page, page_size }
  
POST /v1/workspaces
  Request:  { name, description? }
  Response: { id, name, description, created_at }
  
GET /v1/workspaces/{workspace_id}
  Response: { id, name, description, owner, members: [...], created_at }
  
PATCH /v1/workspaces/{workspace_id}
  Request:  { name?, description? }
  Response: { id, name, ... }
  
DELETE /v1/workspaces/{workspace_id}
  Response: 204 No Content
  
POST /v1/workspaces/{workspace_id}/members
  Request:  { user_id, role }
  Response: { workspace_id, user_id, role, joined_at }
  
GET /v1/workspaces/{workspace_id}/members
  Query params: page=1, page_size=20
  Response: { items: [...], total, page, page_size }
```

#### Projects

```
GET /v1/projects
  Query params: workspace_id (required), q?, page=1, page_size=20
  Response: { items: [...], total, page, page_size }
  
POST /v1/projects
  Request:  { workspace_id, name, description? }
  Response: { id, workspace_id, name, description, created_at }
  
GET /v1/projects/{project_id}
  Response: { id, workspace_id, name, description, task_count, created_at }
  
PATCH /v1/projects/{project_id}
  Request:  { name?, description? }
  Response: { id, workspace_id, name, ... }
  
DELETE /v1/projects/{project_id}
  Response: 204 No Content
```

#### Tasks

```
GET /v1/tasks
  Query params: project_id (required), status?, priority?, assigned_to?, page=1, page_size=50
  Response: { items: [...], total, page, page_size }
  
POST /v1/tasks
  Request:  { project_id, title, description?, priority?, due_date?, assigned_to? }
  Response: { id, project_id, title, ..., status, created_at }
  
GET /v1/tasks/{task_id}
  Response: { id, project_id, title, ..., events: [...] }
  
PATCH /v1/tasks/{task_id}
  Request:  { title?, description?, priority?, due_date? }
  Response: { id, project_id, ... }
  
DELETE /v1/tasks/{task_id}
  Response: 204 No Content
  
POST /v1/tasks/{task_id}/transition
  Request:  { status }
  Response: { id, ..., status, updated_at }
  Error 409: { code: "INVALID_TRANSITION", message: "...", details: {...} }
  
POST /v1/tasks/{task_id}/assign
  Request:  { user_id }
  Response: { id, ..., assigned_to, updated_at }
```

#### Observability & Health

```
GET /health
  Response: { status: "ok" }
  Description: Liveness probe; returns 200 if process is alive (does NOT check DB).
  
GET /ready
  Response: { status: "ok", checks: { database: "ok", ... } }
  Response: 503 Service Unavailable if critical dependency fails.
  Description: Readiness probe; checks if all dependencies (DB, etc.) are reachable.
  
GET /metrics
  Response: Prometheus-format metrics (optional for v1).
  
GET /docs
  Response: OpenAPI/Swagger UI (auto-generated by FastAPI).
  
GET /openapi.json
  Response: OpenAPI schema in JSON (machine-readable contract).
```

### Error Handling & Response Format

All endpoints return consistent error responses:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable message",
  "details": {
    "field": "error detail",
    "...": "..."
  }
}
```

**Common HTTP Status Codes:**
- `200 OK`: Success.
- `201 Created`: Resource created.
- `204 No Content`: Success with no response body.
- `400 Bad Request`: Invalid input (e.g., invalid date format).
- `401 Unauthorized`: Missing or invalid authentication.
- `403 Forbidden`: Authenticated but not authorized for this resource.
- `404 Not Found`: Resource does not exist.
- `409 Conflict`: Business rule violation (e.g., invalid status transition).
- `422 Unprocessable Entity`: Validation error (e.g., missing required field, page_size too large).
- `500 Internal Server Error`: Unhandled exception (logs should provide details).

### Pagination & Filtering

- All list endpoints must support **pagination** with `page` (1-indexed) and `page_size` (max 100 for `/tasks`, max 50 for others).
- Requests exceeding `page_size` limits return `422 Unprocessable Entity`.
- Filter parameters (e.g., `status`, `priority`, `assigned_to`) are optional; absent filters are treated as "any value".
- Response includes `total` count and pagination metadata.

### Authentication & Authorization

- **Authentication**: JWT (JSON Web Token) via `Authorization: Bearer <token>` header.
- **Token Lifecycle**:
  - `access_token`: short-lived (e.g., 15 minutes).
  - `refresh_token`: longer-lived (e.g., 7 days), used to obtain new access tokens.
- **Authorization**: Checked at the presentation layer (controller) and enforced in the application layer (use case). Domain entities are oblivious to auth.

---

## Out of Scope (v1)

The following features are **explicitly excluded** from v1 and reserved for future iterations:

- **User Interface (UI/Web)**: No web, mobile, or desktop client.
- **Notifications**: No email, SMS, push notifications, or webhooks.
- **External Integrations**: No Slack, GitHub, Jira, or third-party APIs.
- **Advanced Search**: No full-text search, Elasticsearch, or complex faceted search.
- **Machine Learning**: No classification, recommendation, or anomaly detection (reserved for v2+).
- **Real-time Features**: No WebSockets, Server-Sent Events, or live updates.
- **Media Storage**: No file uploads, S3 integration, or media serving.
- **Internationalization (i18n)**: All content is in English; no translation support.
- **API Versioning Beyond v1**: Only v1 is implemented; no v2/v3 routing.

---

## Architecture Principles

To evaluate the quality of this codebase, the following architectural principles are non-negotiable:

### Clean Architecture & Dependency Rule

The codebase is organized into **four distinct layers** (from innermost to outermost):

1. **Domain** (Entities & Business Rules)
   - Pure domain models (e.g., `Task`, `User`, `Workspace`).
   - Validation rules and invariants (e.g., status transition rules).
   - **No dependencies** on frameworks, ORMs, HTTP libraries, or external services.
   - Uses: Python standard library, typing, dataclasses.

2. **Application** (Use Cases)
   - High-level orchestration of domain logic.
   - Defines **Ports** (abstract interfaces): `TaskRepository`, `UserRepository`, `UnitOfWork`, `PasswordHasher`, `Clock`, `JWTProvider`, etc.
   - **Never depends** on infrastructure (Postgres, FastAPI, SQLAlchemy) or presentation details.
   - Command/query handlers: `CreateTaskUseCase`, `TransitionTaskUseCase`, `ListTasksUseCase`, etc.

3. **Infrastructure** (Adapters & Implementations)
   - Implements Ports defined by Application.
   - Database adapters (SQLAlchemy ORM, Alembic migrations), external service clients, etc.
   - **Depends on** domain and application layers (inversion of control).

4. **Presentation** (Controllers & Routers)
   - FastAPI routers and endpoint handlers.
   - Pydantic schemas for request/response validation and serialization.
   - Thin orchestration layer: parse input → call use case → format response.
   - **No business logic** in controllers; all logic delegated to use cases.

**The Dependency Rule:** Inner layers do not depend on outer layers. Only outer layers depend on inner ones (via Dependency Injection or service locators).

### Key Practices

- **Testability**: Each layer can be tested independently; infrastructure and application are decoupled via interfaces.
- **Maintainability**: Changes to frameworks (e.g., swapping FastAPI for Flask, Postgres for MongoDB) require only outer-layer changes.
- **Clarity**: Code organization mirrors business domain, not technical concerns.

---

## Success Criteria & Acceptance

Verification date: `2026-04-11`

Status legend:

- **Implemented**: shipped and verified in the current repository.
- **Partial**: shipped for the current task slice, but not for the full target contract.
- **Deferred**: intentionally left for a later milestone or release.
- **External/manual**: depends on GitHub or release operations outside the repository contents.

| Criterion | Status | Verification notes |
| --- | --- | --- |
| Repository Structure | Implemented | `app/src` is split into `domain`, `application`, `infrastructure`, and `presentation`, and the dependency rule is documented in `docs/ARCHITECTURE.md`. |
| API Surface | Partial | Verified public routes: `GET /health`, `GET /ready`, `GET /docs`, `GET /openapi.json`, `POST /v1/tasks`, `GET /v1/tasks`, `POST /v1/tasks/{task_id}/transition`, and `POST /v1/tasks/{task_id}/assign`. Deferred: JWT auth, users, workspaces, projects, task detail/update/delete, and `/metrics`. |
| Business Rules | Partial | Task status transitions, audit events, and owner-scoped concealment checks are implemented for the task slice. Deferred: role-based workspace membership and the broader owner/collaborator/viewer RBAC model. |
| Database | Partial | PostgreSQL schema and Alembic migrations are reproducible for `workspaces`, `projects`, `tasks`, and `task_events`. Deferred: `users` and `workspace_members` tables from the broader contract. |
| Testing | Partial | Domain, application, presentation, smoke, and PostgreSQL integration tests exist. Local verification on `2026-04-11`: `39 passed`, `11 skipped` without `TEST_DATABASE_URL`. Deferred: automated coverage reporting and threshold enforcement. |
| Code Quality | Implemented | Ruff, format check, mypy, and pre-commit are configured. Local verification on `2026-04-11`: lint, format, and typing checks passed. |
| CI/CD | Implemented | `.github/workflows/ci.yml` runs quality, integration, and Docker build jobs on pull requests and pushes to `main`/`staging`. |
| Containerization | Implemented | `docker compose config --quiet` succeeded, `docker compose up -d --build` started API, Postgres, and Nginx successfully, and the public endpoints responded through Nginx on `2026-04-11`. |
| Observability | Implemented | `/health` and `/ready` are implemented and tested, and the app emits structured logs with correlation IDs and request metadata. |
| Documentation | Implemented | `README.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACT.md`, `docs/NFRS.md`, `docs/PERFORMANCE.md`, and `docs/RELEASE.md` document setup, architecture, quality expectations, performance, and release flow. |
| OpenAPI | Implemented | `/docs` and `/openapi.json` are available, covered by smoke tests, and `/docs` was verified through Nginx on `2026-04-11`. |
| Release | Partial | `pyproject.toml` declares version `0.1.0` and the release checklist/notes exist in `docs/RELEASE.md`. External/manual: the local workspace does not yet contain the `v0.1.0` git tag, and a published GitHub Release cannot be verified from the repository contents alone. |

Result: `v0.1.0` satisfies the acceptance gate for the current task-management slice and operational baseline. The broader target contract remains intentionally incomplete until the deferred authentication, user, workspace, and project capabilities are shipped.

---

## Versioning & Release Policy

- **Semantic Versioning**: MAJOR.MINOR.PATCH (e.g., `v0.1.0`).
  - MAJOR: Breaking changes to the API contract.
  - MINOR: New features (backward compatible).
  - PATCH: Bug fixes.
- **Branching**: `main` (releases), `staging` (integration), `feature/*` (development); PRs required for all changes.
- **Release Checklist**: Before tagging:
  - [ ] All CI checks pass.
  - [ ] Release notes in `docs/RELEASE.md` and/or the GitHub Release draft are current.
  - [ ] README and docs are current.
  - [ ] No open issues blocking the release.
  - [ ] Manual smoke test on Compose environment.

---

## Non-Functional Requirements

See **NFRS.md** for detailed non-functional requirements, quality standards, and verification criteria.