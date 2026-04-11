# Architecture

This document explains how the repository applies Clean Architecture today and how to extend it without breaking layer boundaries.

Source code lives under `app/src`:

```text
app/src/
|-- application/
|   |-- ports/
|   `-- use_cases/
|-- domain/
|-- infrastructure/
|   |-- config/
|   `-- database/
`-- presentation/
    |-- routers/
    `-- schemas/
```

## Architecture Goals

- Keep business rules independent from FastAPI, SQLAlchemy, and Pydantic.
- Make use cases testable with in-memory doubles instead of a real database.
- Isolate framework and persistence details in outer adapters.
- Make new features follow a repeatable flow: domain -> application -> infrastructure -> presentation -> tests.

## Layer Responsibilities

### Domain

Location: `app/src/domain`

The domain layer contains the business model and its invariants.

Typical contents:

- Entities and value objects such as `Task`, `Project`, `Workspace`, and identifier types.
- Domain errors such as invalid task transition failures.
- Pure business behavior such as the task status state machine.

Current examples:

- `domain/task.py` enforces non-empty task titles and allowed status transitions.
- `domain/task_event.py` models immutable audit events.
- `domain/identifiers.py` keeps UUID-based identifiers explicit at the type level.

Rules for this layer:

- No FastAPI imports.
- No SQLAlchemy imports.
- No Pydantic imports.
- No environment, logging, HTTP, or database concerns.
- Prefer Python standard library types, dataclasses, enums, and small domain-specific exceptions.

If a rule is part of the business language, it belongs here.

### Application

Location: `app/src/application`

The application layer orchestrates business workflows. It does not know how data is stored or how requests arrive.

Typical contents:

- Use cases under `application/use_cases/`.
- Input and output DTOs such as commands, queries, and result objects.
- Ports under `application/ports/` for repositories, clocks, security services, and the unit of work.
- Application errors that represent use-case level failures.

Current examples:

- `application/use_cases/create_task.py` builds a `Task`, checks project visibility, and commits through the `UnitOfWork` port.
- `application/use_cases/list_tasks.py` reads paginated data through repository ports.
- `application/use_cases/_resource_access.py` centralizes access checks used across task workflows.

Rules for this layer:

- It may import `domain`.
- It may import its own ports and helper modules.
- It must not import `infrastructure`.
- It must not import `presentation`.
- It must not import FastAPI, SQLAlchemy, or Pydantic.

If a piece of code describes an action like "create task", "list tasks", or "transition task", it belongs here.

### Infrastructure

Location: `app/src/infrastructure`

The infrastructure layer provides concrete implementations for application ports and integrates external technology.

Typical contents:

- SQLAlchemy models and repositories.
- Session factory and unit-of-work implementation.
- Environment-backed settings.
- Logging and database health helpers.

Current examples:

- `infrastructure/database/repositories.py` maps SQLAlchemy rows to domain entities.
- `infrastructure/database/unit_of_work.py` implements the `UnitOfWork` protocol.
- `infrastructure/config/settings.py` loads runtime configuration.
- `infrastructure/logging.py` configures structured logging and correlation IDs.

Rules for this layer:

- It may import `application` ports and `domain` models.
- It owns persistence and framework-specific implementation details.
- It should not contain business decisions that belong in domain entities or use cases.

If code answers "how do we talk to Postgres or configure runtime behavior?", it belongs here.

### Presentation

Location: `app/src/presentation`

The presentation layer exposes the HTTP API through FastAPI and translates between HTTP payloads and application DTOs.

Typical contents:

- FastAPI app creation and middleware.
- Dependency wiring for runtime objects.
- Routers and endpoint handlers.
- Pydantic request and response schemas.

Current examples:

- `presentation/main.py` creates the FastAPI app and configures middleware.
- `presentation/dependencies.py` wires use cases to concrete infrastructure adapters.
- `presentation/routers/v1/tasks.py` maps HTTP requests to task use cases.
- `presentation/schemas/tasks.py` defines request and response models.

Rules for this layer:

- Routers stay thin: validate input, call a use case, map output, translate exceptions to HTTP.
- Pydantic models stay here instead of leaking into `application` or `domain`.
- FastAPI-specific concerns stay here instead of leaking into use cases.

If code answers "how does this capability become an HTTP endpoint?", it belongs here.

## Dependency Rule

The business core points inward.

```text
presentation ---> application ---> domain
infrastructure -> application ---> domain
```

In this repository, the dependency rule is applied as follows:

- `domain` depends on nothing outside itself.
- `application` depends on `domain` and on application-local ports/helpers.
- `infrastructure` depends on `application` and `domain` to implement ports.
- `presentation` depends on `application` and presentation-local schemas/helpers.

There is one deliberate edge-only exception to call out clearly: the composition root lives in `presentation/main.py` and `presentation/dependencies.py`, so those modules also import `infrastructure` to wire real adapters at runtime. That wiring is allowed because it stays at the outermost boundary. Domain entities and use cases still remain independent from framework and persistence code.

### What Must Never Happen

- `domain` importing FastAPI, SQLAlchemy, or Pydantic.
- `application` importing repository implementations from `infrastructure`.
- `application` returning ORM models or Pydantic models.
- `presentation` putting business rules directly in route handlers.
- `infrastructure` deciding business rules that should be enforced in domain or application.

### What This Looks Like in Practice

Current task creation flow:

1. `presentation/routers/v1/tasks.py` receives `POST /v1/tasks`.
2. `presentation/schemas/tasks.py` validates the HTTP payload.
3. The route builds a `CreateTaskCommand` from HTTP data and the current user.
4. `presentation/dependencies.py` provides `CreateTaskUseCase` with a `SqlAlchemyUnitOfWork` and a clock.
5. `application/use_cases/create_task.py` checks access, creates the `Task`, and commits through the unit of work port.
6. `infrastructure/database/repositories.py` and `infrastructure/database/unit_of_work.py` persist the change in PostgreSQL.
7. The route maps `CreateTaskResult` into `TaskResponseSchema` and returns HTTP 201.

The route knows about HTTP. The use case knows about the business workflow. The infrastructure adapter knows about SQLAlchemy. Each concern stays in its own layer.

## Request Lifecycle

For most endpoints, the execution flow is:

1. FastAPI router receives the request.
2. Pydantic schema validates and normalizes payload/query data.
3. Dependency functions resolve the authenticated actor and construct the use case.
4. The router converts HTTP data into a command or query object.
5. The use case runs inside a `UnitOfWork`, loading domain entities through repository ports.
6. Domain entities enforce invariants.
7. Infrastructure adapters persist or load data.
8. The use case returns a result DTO.
9. The router converts that DTO into the response schema and HTTP status code.

This keeps the same business workflow reusable even if the delivery mechanism changes later.

## How To Add a New Use Case + Endpoint + Tests

The safest way to extend this project is to work from the inside out, then add tests at the appropriate layer.

### Step 1. Define the feature at the application boundary

Start by writing down the behavior in terms of a command or query.

Questions to answer first:

- Is this a command that changes state or a query that only reads data?
- Which actor performs it?
- Which aggregate or resource does it touch?
- What should the use case return?
- Which errors are part of the expected business flow?

Use current files as templates:

- Command example: `application/use_cases/create_task.py`
- Query example: `application/use_cases/list_tasks.py`

### Step 2. Change the domain only when the business model changes

If the new feature introduces a new rule or invariant, update the domain first.

Examples:

- Add a new method to an entity when behavior belongs to the entity.
- Add a new domain error when a rule violation is business-specific.
- Add or extend value objects when a concept needs stronger typing.

Do not add HTTP or database logic here.

### Step 3. Add or extend application ports

If the use case needs new persistence operations, define them in `application/ports/` before writing any adapter code.

Typical changes:

- Add a repository method to `application/ports/repositories.py`.
- Add a new service port if the use case needs time, tokens, hashing, or another external capability.
- Extend `application/ports/unit_of_work.py` only when the use case needs access to a new repository.

Keep ports expressed in domain terms, not SQLAlchemy terms.

### Step 4. Implement the use case

Create a new module under `application/use_cases/`.

Follow the existing pattern:

- Define a `Command` or `Query` dataclass.
- Define a `Result` dataclass when the use case returns structured data.
- Inject dependencies through the constructor using ports such as `UnitOfWork` and `Clock`.
- Open the transactional boundary inside the use case with `with self._unit_of_work as unit_of_work:`.
- Load entities through ports, invoke domain behavior, then call `unit_of_work.commit()` when state changes.

Keep the use case free from FastAPI, SQLAlchemy, and Pydantic.

### Step 5. Export the new use case for outer layers

After creating the use case module, export it so the presentation layer can import it cleanly.

Update:

- `application/use_cases/__init__.py`
- `application/__init__.py`

This repository uses those modules as the public application-layer surface.

### Step 6. Implement infrastructure adapters

Only after the port is defined should you change infrastructure.

Typical changes:

- Implement the new repository method in `infrastructure/database/repositories.py`.
- Update `infrastructure/database/models.py` if persistence shape changes.
- Add or update migrations under `alembic/versions/` if the database schema changes.
- Keep `infrastructure/database/unit_of_work.py` aligned if a new repository dependency is introduced.

Infrastructure should translate between storage concerns and domain/application contracts. It should not define business rules.

### Step 7. Wire the use case in presentation dependencies

Add a dependency factory to `presentation/dependencies.py`.

Typical pattern:

```python
def get_example_use_case(
		session_factory: SessionFactoryDependency,
) -> ExampleUseCase:
		return ExampleUseCase(
				unit_of_work=SqlAlchemyUnitOfWork(session_factory),
				clock=SystemClock(),
		)
```

If the use case is read-only and does not need a clock or another service, inject only what it needs.

### Step 8. Add schemas and the HTTP endpoint

Implement the HTTP contract in the presentation layer.

Typical changes:

- Add request or response schemas under `presentation/schemas/`.
- Add the route handler under the appropriate router in `presentation/routers/v1/`.
- Convert incoming UUIDs or primitive values into domain/application types.
- Catch expected application or domain errors and map them to HTTP status codes.
- Keep response mapping in the router or a small presentation-local helper.

If you add a new router module, include it from `presentation/routers/v1/router.py`.

### Step 9. Add tests at the correct layer

This repository expects tests to mirror the architecture.

#### Domain tests

Add or update tests under `tests/unit/domain/` when you change invariants or entity behavior.

Examples:

- Valid state transitions.
- Rejected invalid transitions.
- Normalization or validation rules owned by the entity.

#### Application tests

Add a focused unit test module under `tests/unit/application/` for the new use case.

Pattern used in this repository:

- Create fake repositories and a fake unit of work in the test file.
- Inject those fakes into the use case.
- Assert on returned results, persisted entities, commits, and rollback behavior.

Use `tests/unit/application/test_create_task.py` as the reference pattern.

#### Presentation route tests

Add unit tests under `tests/unit/presentation/` for HTTP behavior without a real database.

Pattern used in this repository:

- Build the app with `create_app()`.
- Override dependencies through `app.dependency_overrides`.
- Provide stub use cases and a stub current user.
- Assert on status codes, payload shape, validation, and exception-to-HTTP mapping.

Use `tests/unit/presentation/test_task_routes.py` as the reference pattern.

#### Integration tests

Add integration coverage under `tests/integration/` when the new feature touches persistence or real HTTP wiring.

Pattern used in this repository:

- Seed data with `SqlAlchemyUnitOfWork`.
- Override `get_session_factory` so the app uses the test database.
- Exercise the real FastAPI endpoint with `TestClient`.
- Assert both the HTTP response and the persisted database state.

Use `tests/integration/presentation/test_tasks.py` and `tests/integration/repositories/` as reference points.

### Step 10. Run the quality gate

Before opening a PR, run the relevant local checks.

Recommended commands:

```bash
make lint
make format-check
make typecheck
make test
make test-integration
```

When invoking tools directly, remember that this project expects `PYTHONPATH=app/src` for import resolution.

## Feature Review Checklist

Use this checklist before considering a new use case complete:

- The domain/application layers did not import FastAPI, SQLAlchemy, or Pydantic.
- New persistence behavior was introduced through application ports first.
- The use case owns orchestration and transaction boundaries.
- The router only handles HTTP concerns and response mapping.
- Database schema changes include an Alembic migration.
- Tests cover the changed rule at the domain, application, presentation, and integration levels when applicable.
- Public exports in `application/__init__.py` and `application/use_cases/__init__.py` are updated.

## Practical Reference Files

When adding new features, these files are the best templates to copy from:

- `app/src/domain/task.py`
- `app/src/application/use_cases/create_task.py`
- `app/src/application/use_cases/list_tasks.py`
- `app/src/application/ports/repositories.py`
- `app/src/presentation/dependencies.py`
- `app/src/presentation/routers/v1/tasks.py`
- `tests/unit/application/test_create_task.py`
- `tests/unit/presentation/test_task_routes.py`
- `tests/integration/presentation/test_tasks.py`

Following those patterns keeps the project consistent and preserves the boundary rules that this repository is meant to demonstrate.
