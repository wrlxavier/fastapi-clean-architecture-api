# Architecture

## Layers
- domain: pure business rules (no FastAPI/SQLAlchemy/Pydantic).
- application: use cases + ports (interfaces). Depends only on domain.
- infrastructure: implements ports (repositories/UoW), DB details.
- presentation: FastAPI entrypoints (routers), IO schemas, auth wiring.

## Dependency rule
Code dependencies point inwards:
presentation -> application -> domain
infrastructure -> application -> domain

## Forbidden imports (enforced by convention for now)
- domain/application MUST NOT import: fastapi, sqlalchemy, pydantic, and anything from infrastructure/presentation.
