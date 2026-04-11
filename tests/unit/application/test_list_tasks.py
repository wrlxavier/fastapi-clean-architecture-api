import pytest

from application.errors import ProjectNotFoundError
from application.use_cases import ListTasksQuery, ListTasksUseCase
from domain import Project, ProjectId, Task, TaskId, UserId, Workspace, WorkspaceId


class InMemoryTaskRepository:
    def __init__(self, tasks: list[Task]) -> None:
        self._tasks = tasks

    def add(self, task: Task) -> None:
        self._tasks.append(task)

    def get_by_id(self, task_id: TaskId) -> Task | None:
        return next((task for task in self._tasks if task.id == task_id), None)

    def list_by_project(
        self,
        project_id: ProjectId,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Task]:
        tasks = [task for task in self._tasks if task.project_id == project_id]
        if limit is None:
            return tasks[offset:]
        return tasks[offset : offset + limit]

    def count_by_project(self, project_id: ProjectId) -> int:
        return sum(1 for task in self._tasks if task.project_id == project_id)

    def remove(self, task: Task) -> None:
        self._tasks = [
            saved_task for saved_task in self._tasks if saved_task.id != task.id
        ]


class InMemoryProjectRepository:
    def __init__(self, projects: list[Project]) -> None:
        self._projects = {project.id: project for project in projects}

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
    def __init__(self, workspaces: list[Workspace]) -> None:
        self._workspaces = {workspace.id: workspace for workspace in workspaces}

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


class FakeUnitOfWork:
    def __init__(
        self,
        tasks: InMemoryTaskRepository,
        projects: InMemoryProjectRepository,
        workspaces: InMemoryWorkspaceRepository,
    ) -> None:
        self.tasks = tasks
        self.task_events = object()
        self.projects = projects
        self.workspaces = workspaces

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None:
        del exc_type, exc, traceback
        return None

    def commit(self) -> None:
        raise AssertionError("List tasks should not commit changes.")

    def rollback(self) -> None:
        raise AssertionError("List tasks should not rollback changes.")


def test_list_tasks_use_case_returns_requested_page_and_total() -> None:
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project_id = ProjectId.new()
    other_project_id = ProjectId.new()
    project = Project(id=project_id, workspace_id=workspace.id, name="Task API")
    other_project = Project(
        id=other_project_id,
        workspace_id=workspace.id,
        name="Other project",
    )
    tasks = [
        Task(
            id=TaskId.new(),
            project_id=project_id,
            title="First task",
            created_by=owner_id,
        ),
        Task(
            id=TaskId.new(),
            project_id=project_id,
            title="Second task",
            created_by=owner_id,
        ),
        Task(
            id=TaskId.new(),
            project_id=project_id,
            title="Third task",
            created_by=owner_id,
        ),
        Task(
            id=TaskId.new(),
            project_id=other_project_id,
            title="Filtered task",
            created_by=owner_id,
        ),
    ]
    use_case = ListTasksUseCase(
        unit_of_work=FakeUnitOfWork(
            InMemoryTaskRepository(tasks),
            InMemoryProjectRepository([project, other_project]),
            InMemoryWorkspaceRepository([workspace]),
        ),
    )

    result = use_case.execute(
        ListTasksQuery(
            actor_id=owner_id,
            project_id=project_id,
            page=2,
            page_size=2,
        )
    )

    assert result.total == 3
    assert result.page == 2
    assert result.page_size == 2
    assert [item.title for item in result.items] == ["Third task"]


def test_list_tasks_use_case_conceals_inaccessible_project_as_not_found() -> None:
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
    use_case = ListTasksUseCase(
        unit_of_work=FakeUnitOfWork(
            InMemoryTaskRepository([]),
            InMemoryProjectRepository([project]),
            InMemoryWorkspaceRepository([workspace]),
        ),
    )

    with pytest.raises(ProjectNotFoundError) as caught_error:
        use_case.execute(
            ListTasksQuery(
                actor_id=outsider_id,
                project_id=project.id,
            )
        )

    assert caught_error.value.project_id == project.id
