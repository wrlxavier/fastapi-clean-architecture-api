from datetime import UTC, datetime

from application import (
    Clock,
    JWTProvider,
    PasswordHasher,
    ProjectRepository,
    TaskRepository,
    TokenPair,
    UnitOfWork,
    WorkspaceRepository,
)
from domain import (
    Project,
    ProjectId,
    Task,
    TaskId,
    UserId,
    Workspace,
    WorkspaceId,
)


def build_workspace(*, owner_id: UserId | None = None) -> Workspace:
    return Workspace(
        id=WorkspaceId.new(),
        name="Engineering",
        owner_id=owner_id or UserId.new(),
    )


def build_project(*, workspace_id: WorkspaceId) -> Project:
    return Project(
        id=ProjectId.new(),
        workspace_id=workspace_id,
        name="Backend API",
    )


def build_task(*, project_id: ProjectId, created_by: UserId) -> Task:
    return Task(
        id=TaskId.new(),
        project_id=project_id,
        title="Define application ports",
        created_by=created_by,
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


class StubPasswordHasher:
    def hash(self, plain_password: str) -> str:
        return f"hashed::{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == self.hash(plain_password)


class StubJWTProvider:
    def __init__(self, subject: UserId) -> None:
        self._subject = subject

    def issue_tokens(self, *, subject: UserId) -> TokenPair:
        return TokenPair(
            access_token=f"access::{subject.value}",
            refresh_token=f"refresh::{subject.value}",
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        return refresh_token.replace("refresh::", "access::", 1)

    def decode_subject(self, token: str) -> UserId:
        return self._subject


class FakeUnitOfWork:
    def __init__(
        self,
        *,
        tasks: TaskRepository,
        projects: ProjectRepository,
        workspaces: WorkspaceRepository,
    ) -> None:
        self.tasks = tasks
        self.projects = projects
        self.workspaces = workspaces
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None:
        if exc is not None:
            self.rollback()
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_application_ports_define_use_case_boundaries() -> None:
    owner_id = UserId.new()
    workspace = build_workspace(owner_id=owner_id)
    project = build_project(workspace_id=workspace.id)
    task = build_task(project_id=project.id, created_by=owner_id)

    task_repository = InMemoryTaskRepository()
    project_repository = InMemoryProjectRepository()
    workspace_repository = InMemoryWorkspaceRepository()
    fixed_clock = FixedClock(datetime(2026, 4, 9, 12, 0, tzinfo=UTC))
    password_hasher = StubPasswordHasher()
    jwt_provider = StubJWTProvider(owner_id)
    unit_of_work = FakeUnitOfWork(
        tasks=task_repository,
        projects=project_repository,
        workspaces=workspace_repository,
    )

    assert isinstance(task_repository, TaskRepository)
    assert isinstance(project_repository, ProjectRepository)
    assert isinstance(workspace_repository, WorkspaceRepository)
    assert isinstance(fixed_clock, Clock)
    assert isinstance(password_hasher, PasswordHasher)
    assert isinstance(jwt_provider, JWTProvider)
    assert isinstance(unit_of_work, UnitOfWork)

    with unit_of_work as active_unit_of_work:
        active_unit_of_work.workspaces.add(workspace)
        active_unit_of_work.projects.add(project)
        active_unit_of_work.tasks.add(task)
        active_unit_of_work.commit()

    issued_tokens = jwt_provider.issue_tokens(subject=owner_id)

    assert unit_of_work.committed is True
    assert fixed_clock.now() == datetime(2026, 4, 9, 12, 0, tzinfo=UTC)
    assert password_hasher.verify("secret", password_hasher.hash("secret")) is True
    assert issued_tokens.token_type == "bearer"
    assert jwt_provider.refresh_access_token(issued_tokens.refresh_token).startswith(
        "access::"
    )
    assert jwt_provider.decode_subject(issued_tokens.access_token) == owner_id
    assert task_repository.get_by_id(task.id) == task
    assert project_repository.list_by_workspace(workspace.id) == [project]
    assert workspace_repository.list_by_user(owner_id) == [workspace]
