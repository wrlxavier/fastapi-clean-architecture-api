from datetime import UTC, datetime

import pytest

from application.errors import TaskNotFoundError
from application.use_cases import TransitionTaskCommand, TransitionTaskUseCase
from domain import (
    InvalidTaskTransitionError,
    Project,
    ProjectId,
    Task,
    TaskEvent,
    TaskEventType,
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


class InMemoryTaskEventRepository:
    def __init__(self) -> None:
        self._events: dict[TaskId, list[TaskEvent]] = {}

    def add(self, task_event: TaskEvent) -> None:
        self._events.setdefault(task_event.task_id, []).append(task_event)

    def list_by_task(self, task_id: TaskId) -> list[TaskEvent]:
        return list(self._events.get(task_id, []))


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
    def __init__(
        self,
        task: Task | None = None,
        *,
        workspace_owner_id: UserId | None = None,
    ) -> None:
        self.tasks = InMemoryTaskRepository()
        self.task_events = InMemoryTaskEventRepository()
        self.projects = InMemoryProjectRepository()
        self.workspaces = InMemoryWorkspaceRepository()
        self.committed = False
        self.rolled_back = False
        if task is not None:
            self.tasks.add(task)
            workspace = Workspace(
                id=WorkspaceId.new(),
                name="Task workspace",
                owner_id=(
                    task.created_by
                    if workspace_owner_id is None
                    else workspace_owner_id
                ),
            )
            project = Project(
                id=task.project_id,
                workspace_id=workspace.id,
                name="Task project",
            )
            self.workspaces.add(workspace)
            self.projects.add(project)

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


def build_task(
    *,
    status: TaskStatus = TaskStatus.TODO,
    created_by: UserId | None = None,
) -> Task:
    return Task(
        id=TaskId.new(),
        project_id=ProjectId.new(),
        title="Transition the workflow state",
        created_by=UserId.new() if created_by is None else created_by,
        status=status,
    )


def test_transition_task_use_case_updates_status_and_records_event() -> None:
    transitioned_at = datetime(2026, 4, 11, 16, 0, tzinfo=UTC)
    owner_id = UserId.new()
    task = build_task(status=TaskStatus.TODO, created_by=owner_id)
    unit_of_work = FakeUnitOfWork(task)
    use_case = TransitionTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(transitioned_at),
    )

    result = use_case.execute(
        TransitionTaskCommand(
            actor_id=owner_id,
            task_id=task.id,
            target_status=TaskStatus.DOING,
        )
    )

    saved_task = unit_of_work.tasks.get_by_id(task.id)
    task_events = unit_of_work.task_events.list_by_task(task.id)

    assert unit_of_work.committed is True
    assert saved_task is not None
    assert saved_task.status is TaskStatus.DOING
    assert saved_task.updated_at == transitioned_at
    assert result.status is TaskStatus.DOING
    assert len(task_events) == 1
    assert task_events[0].event_type is TaskEventType.STATUS_TRANSITIONED
    assert task_events[0].payload == {
        "from_status": "todo",
        "to_status": "doing",
    }
    assert task_events[0].created_at == transitioned_at


def test_transition_task_use_case_rejects_invalid_transition_without_event() -> None:
    owner_id = UserId.new()
    finished_task = build_task(status=TaskStatus.DONE, created_by=owner_id)
    unit_of_work = FakeUnitOfWork(finished_task)
    use_case = TransitionTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(datetime(2026, 4, 11, 16, 0, tzinfo=UTC)),
    )

    with pytest.raises(InvalidTaskTransitionError) as caught_error:
        use_case.execute(
            TransitionTaskCommand(
                actor_id=owner_id,
                task_id=finished_task.id,
                target_status=TaskStatus.DOING,
            )
        )

    assert caught_error.value.current_status == "done"
    assert caught_error.value.target_status == "doing"
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
    assert finished_task.status is TaskStatus.DONE
    assert unit_of_work.task_events.list_by_task(finished_task.id) == []


def test_transition_task_use_case_rejects_missing_task() -> None:
    missing_task_id = TaskId.new()
    unit_of_work = FakeUnitOfWork()
    use_case = TransitionTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(datetime(2026, 4, 11, 16, 0, tzinfo=UTC)),
    )

    with pytest.raises(TaskNotFoundError) as caught_error:
        use_case.execute(
            TransitionTaskCommand(
                actor_id=UserId.new(),
                task_id=missing_task_id,
                target_status=TaskStatus.DOING,
            )
        )

    assert caught_error.value.task_id == missing_task_id
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True


def test_transition_task_use_case_conceals_inaccessible_task_as_not_found() -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    task = build_task(status=TaskStatus.TODO, created_by=owner_id)
    unit_of_work = FakeUnitOfWork(task, workspace_owner_id=owner_id)
    use_case = TransitionTaskUseCase(
        unit_of_work=unit_of_work,
        clock=FixedClock(datetime(2026, 4, 11, 16, 0, tzinfo=UTC)),
    )

    with pytest.raises(TaskNotFoundError) as caught_error:
        use_case.execute(
            TransitionTaskCommand(
                actor_id=outsider_id,
                task_id=task.id,
                target_status=TaskStatus.DOING,
            )
        )

    assert caught_error.value.task_id == task.id
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
    assert unit_of_work.task_events.list_by_task(task.id) == []
