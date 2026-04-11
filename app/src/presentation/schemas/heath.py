"""Health response schema module."""

from typing import Literal

from pydantic import BaseModel


class HealthResponseSchema(BaseModel):
    """Schema for health check response."""

    status: Literal["ok"]


class ReadinessChecksSchema(BaseModel):
    """Schema for readiness dependency checks."""

    database: Literal["ok", "down"]


class ReadinessResponseSchema(BaseModel):
    """Schema for readiness check responses."""

    status: Literal["ok", "unavailable"]
    checks: ReadinessChecksSchema
