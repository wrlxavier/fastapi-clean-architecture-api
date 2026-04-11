"""Repository ports for application use cases."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from domain import (
    Project,
    ProjectId,
    Task,
    TaskId,
    UserId,
    Workspace,
    WorkspaceId,
)


@runtime_checkable
class TaskRepository(Protocol):
    """Persistence contract for task aggregates."""

    def add(self, task: Task) -> None:
        """Persist a new task."""

    def get_by_id(self, task_id: TaskId) -> Task | None:
        """Load a task by its identifier."""

    def list_by_project(
        self,
        project_id: ProjectId,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[Task]:
        """List tasks that belong to a project."""

    def count_by_project(self, project_id: ProjectId) -> int:
        """Count tasks that belong to a project."""

    def remove(self, task: Task) -> None:
        """Delete a task from persistence."""


@runtime_checkable
class ProjectRepository(Protocol):
    """Persistence contract for project aggregates."""

    def add(self, project: Project) -> None:
        """Persist a new project."""

    def get_by_id(self, project_id: ProjectId) -> Project | None:
        """Load a project by its identifier."""

    def list_by_workspace(self, workspace_id: WorkspaceId) -> Sequence[Project]:
        """List projects that belong to a workspace."""

    def remove(self, project: Project) -> None:
        """Delete a project from persistence."""


@runtime_checkable
class WorkspaceRepository(Protocol):
    """Persistence contract for workspace aggregates."""

    def add(self, workspace: Workspace) -> None:
        """Persist a new workspace."""

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        """Load a workspace by its identifier."""

    def list_by_user(self, user_id: UserId) -> Sequence[Workspace]:
        """List workspaces visible to a user."""

    def remove(self, workspace: Workspace) -> None:
        """Delete a workspace from persistence."""
