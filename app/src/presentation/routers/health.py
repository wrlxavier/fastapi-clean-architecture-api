"""This module contains the health check router."""

from fastapi import APIRouter

from presentation.schemas.heath import HealthResponseSchema

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseSchema)
def health() -> HealthResponseSchema:
    """Health check endpoint."""
    return HealthResponseSchema(status="ok")
