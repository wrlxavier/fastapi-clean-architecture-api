"""Health response schema module."""

from typing import Literal

from pydantic import BaseModel


class HealthResponseSchema(BaseModel):
    """Schema for health check response."""

    status: Literal["ok", "error"]
