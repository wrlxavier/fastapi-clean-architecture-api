from datetime import UTC, date, datetime

import pytest

from application.errors import ProjectNotFoundError
from application.use_cases import CreateTaskCommand, CreateTaskUseCase
from domain import (
    Project,
    ProjectId,
    Task,
    TaskId,
    TaskStatus,
    UserId,
    Workspace,
    WorkspaceId,
)


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[TaskId, Task] = {}

    def add(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get_by_id(self, task_id: TaskId) -> Task | None:
        return self._tasks.get(task_id)

    def list_by_project(
        self,
        project_id: ProjectId,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Task]:
        tasks = [task for task in self._tasks.values() if task.project_id == project_id]
        if limit is None:
            return tasks[offset:]
        return tasks[offset : offset + limit]

    def count_by_project(self, project_id: ProjectId) -> int:
        return sum(1 for task in self._tasks.values() if task.project_id == project_id)

    def remove(self, task: Task) -> None:
        self._tasks.pop(task.id, None)


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[ProjectId, Project] = {}

    def add(self, project: Project) -> None:
        self._projects[project.id] = project

    def get_by_id(self, project_id: ProjectId) -> Project | None:
        return self._projects.get(project_id)

    def list_by_workspace(self, workspace_id: WorkspaceId) -> list[Project]:
        return [
            project
            for project in self._projects.values()
            if project.workspace_id == workspace_id
        ]

    def remove(self, project: Project) -> None:
        self._projects.pop(project.id, None)


class InMemoryWorkspaceRepository:
    def __init__(self) -> None:
        self._workspaces: dict[WorkspaceId, Workspace] = {}

    def add(self, workspace: Workspace) -> None:
        self._workspaces[workspace.id] = workspace

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    def list_by_user(self, user_id: UserId) -> list[Workspace]:
        return [
            workspace
            for workspace in self._workspaces.values()
            if workspace.owner_id == user_id
        ]

    def remove(self, workspace: Workspace) -> None:
        self._workspaces.pop(workspace.id, None)


class FixedClock:
    def __init__(self, current_time: datetime) -> None:
        self._current_time = current_time

    def now(self) -> datetime:
        return self._current_time


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.tasks = InMemoryTaskRepository()
        self.task_events = object()
        self.projects = InMemoryProjectRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None:
        del exc_type, traceback
        if exc is not None:
            self.rollback()
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_create_task_use_case_persists_task_and_returns_result() -> None:
    created_at = datetime(2026, 4, 11, 13, 0, tzinfo=UTC)
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
    )
    unit_of_work = FakeUnitOfWork()
    unit_of_work.workspaces.add(workspace)
    unit_of_work.projects.add(project)
    use_case = CreateTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(created_at),
    )

    result = use_case.execute(
        CreateTaskCommand(
            actor_id=owner_id,
            project_id=project.id,
            title="  Ship create task vertical slice  ",
            description="  Add POST /v1/tasks  ",
            priority="  high  ",
            due_date=date(2026, 4, 30),
            assigned_to=owner_id,
        )
    )

    saved_task = unit_of_work.tasks.get_by_id(result.id)

    assert unit_of_work.committed is True
    assert saved_task is not None
    assert saved_task.project_id == project.id
    assert saved_task.title == "Ship create task vertical slice"
    assert saved_task.description == "Add POST /v1/tasks"
    assert saved_task.status is TaskStatus.TODO
    assert saved_task.priority == "high"
    assert saved_task.due_date == date(2026, 4, 30)
    assert saved_task.created_by == owner_id
    assert saved_task.assigned_to == owner_id
    assert saved_task.created_at == created_at
    assert saved_task.updated_at == created_at
    assert result.id == saved_task.id
    assert result.status is TaskStatus.TODO


def test_create_task_use_case_rejects_unknown_project() -> None:
    missing_project_id = ProjectId.new()
    unit_of_work = FakeUnitOfWork()
    use_case = CreateTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(datetime(2026, 4, 11, 13, 0, tzinfo=UTC)),
    )

    with pytest.raises(ProjectNotFoundError) as caught_error:
        use_case.execute(
            CreateTaskCommand(
                actor_id=UserId.new(),
                project_id=missing_project_id,
                title="Task without a project",
            )
        )

    assert caught_error.value.project_id == missing_project_id
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
    assert unit_of_work.tasks.list_by_project(missing_project_id) == []


def test_create_task_use_case_conceals_inaccessible_project_as_not_found() -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Owner Workspace",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Hidden Project",
    )
    unit_of_work = FakeUnitOfWork()
    unit_of_work.workspaces.add(workspace)
    unit_of_work.projects.add(project)
    use_case = CreateTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(datetime(2026, 4, 11, 13, 0, tzinfo=UTC)),
    )

    with pytest.raises(ProjectNotFoundError) as caught_error:
        use_case.execute(
            CreateTaskCommand(
                actor_id=outsider_id,
                project_id=project.id,
                title="Attempt cross-user task creation",
            )
        )

    assert caught_error.value.project_id == project.id
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
    assert unit_of_work.tasks.list_by_project(project.id) == []
