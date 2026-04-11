"""This module contains the health and readiness routers."""

from fastapi import APIRouter, Response, status

from presentation.dependencies import DatabaseReadinessDependency
from presentation.schemas.heath import (
    HealthResponseSchema,
    ReadinessChecksSchema,
    ReadinessResponseSchema,
)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseSchema)
def health() -> HealthResponseSchema:
    """Health check endpoint."""
    return HealthResponseSchema(status="ok")


@router.get("/ready", response_model=ReadinessResponseSchema)
def ready(
    response: Response,
    database_ready: DatabaseReadinessDependency,
) -> ReadinessResponseSchema:
    """Readiness check endpoint."""
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponseSchema(
            status="unavailable",
            checks=ReadinessChecksSchema(database="down"),
        )

    return ReadinessResponseSchema(
        status="ok",
        checks=ReadinessChecksSchema(database="ok"),
    )
