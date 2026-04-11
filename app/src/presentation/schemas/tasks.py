"""Schemas for task endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from domain import TaskStatus


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


class CreateTaskRequestSchema(BaseModel):
    """Request payload for creating a task."""

    project_id: UUID
    title: str = Field(min_length=1, max_length=255)
    created_by: UUID
    description: str | None = None
    priority: str | None = Field(default=None, max_length=32)
    due_date: date | None = None
    assigned_to: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Reject empty or whitespace-only task titles."""
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Task title must not be empty.")
        return normalized_value

    @field_validator("description", "priority")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Trim optional textual fields and collapse blanks to null."""
        return _normalize_optional_text(value)


class TaskResponseSchema(BaseModel):
    """Response payload for task resources."""

    id: UUID
    project_id: UUID
    title: str
    created_by: UUID
    description: str | None = None
    status: TaskStatus
    priority: str | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime