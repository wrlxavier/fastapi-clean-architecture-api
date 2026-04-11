"""Authorization helpers for resource-scoped task operations."""

from application.errors import ProjectNotFoundError, TaskNotFoundError
from application.ports import UnitOfWork
from domain import Project, ProjectId, Task, TaskId, UserId


def get_accessible_project(
    unit_of_work: UnitOfWork,
    *,
    project_id: ProjectId,
    actor_id: UserId,
) -> Project:
    """Load a project only when the actor owns its workspace.

    The API uses a concealment policy for cross-user access attempts, so callers
    receive the same not-found error whether the project is missing or simply not
    visible to the authenticated actor.
    """
    project = unit_of_work.projects.get_by_id(project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)

    workspace = unit_of_work.workspaces.get_by_id(project.workspace_id)
    if workspace is None or workspace.owner_id != actor_id:
        raise ProjectNotFoundError(project_id)

    return project


def get_accessible_task(
    unit_of_work: UnitOfWork,
    *,
    task_id: TaskId,
    actor_id: UserId,
) -> Task:
    """Load a task only when the actor owns its parent workspace.

    Cross-user task lookups intentionally reuse the same not-found error used for
    genuinely missing tasks to avoid leaking object existence across tenants.
    """
    task = unit_of_work.tasks.get_by_id(task_id)
    if task is None:
        raise TaskNotFoundError(task_id)

    project = unit_of_work.projects.get_by_id(task.project_id)
    if project is None:
        raise TaskNotFoundError(task_id)

    workspace = unit_of_work.workspaces.get_by_id(project.workspace_id)
    if workspace is None or workspace.owner_id != actor_id:
        raise TaskNotFoundError(task_id)

    return task
