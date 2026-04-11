"""Typed identifier value objects for the domain layer."""

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4


def _new_uuid() -> UUID:
    return uuid4()


@dataclass(frozen=True, slots=True)
class UserId:
    """Unique identifier for a user."""

    value: UUID

    @classmethod
    def new(cls) -> Self:
        """Create a new user identifier."""
        return cls(_new_uuid())


@dataclass(frozen=True, slots=True)
class WorkspaceId:
    """Unique identifier for a workspace."""

    value: UUID

    @classmethod
    def new(cls) -> Self:
        """Create a new workspace identifier."""
        return cls(_new_uuid())


@dataclass(frozen=True, slots=True)
class ProjectId:
    """Unique identifier for a project."""

    value: UUID

    @classmethod
    def new(cls) -> Self:
        """Create a new project identifier."""
        return cls(_new_uuid())


@dataclass(frozen=True, slots=True)
class TaskId:
    """Unique identifier for a task."""

    value: UUID

    @classmethod
    def new(cls) -> Self:
        """Create a new task identifier."""
        return cls(_new_uuid())


@dataclass(frozen=True, slots=True)
class TaskEventId:
    """Unique identifier for a task event."""

    value: UUID

    @classmethod
    def new(cls) -> Self:
        """Create a new task event identifier."""
        return cls(_new_uuid())
