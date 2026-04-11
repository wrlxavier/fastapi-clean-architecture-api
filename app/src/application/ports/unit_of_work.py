"""Unit of work port for transaction boundaries."""

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from application.ports.repositories import (
    ProjectRepository,
    TaskEventRepository,
    TaskRepository,
    WorkspaceRepository,
)


@runtime_checkable
class UnitOfWork(Protocol):
    """Coordinates repositories and persistence boundaries for a use case."""

    tasks: TaskRepository
    task_events: TaskEventRepository
    projects: ProjectRepository
    workspaces: WorkspaceRepository

    def __enter__(self) -> Self:
        """Open the transactional boundary."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Close the transactional boundary."""

    def commit(self) -> None:
        """Persist pending changes."""

    def rollback(self) -> None:
        """Discard pending changes."""
