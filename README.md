# fastapi-clean-architecture-api

Source code lives in app/src.

Clean Architecture layers:
- domain: entities/value objects, invariants, domain errors (no framework/DB deps).
- application: use cases and ports (interfaces) that the outer layers implement.
- infrastructure: DB/ORM, external clients, implementations of ports.
- presentation: FastAPI routers/controllers and request/response schemas.


## Product & Quality Standards

- [Product Contract](docs/CONTRACT.md) - API surface, entities, rules, scope
- [Non-Functional Requirements](docs/NFRS.md) - Quality standards, testing, security, deployment


## Setting environment variables
Create a `.env` file in the project root based on the `.env.example` file and set the required environment variables. You can easily copy the example file using the following command:

- Linux/MacOS:

```bash
cp .env.example .env
```

- Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```
