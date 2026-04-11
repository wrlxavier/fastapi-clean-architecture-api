from application.use_cases import ListTasksQuery, ListTasksUseCase
from domain import ProjectId, Task, TaskId, UserId


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
        self._tasks = [saved_task for saved_task in self._tasks if saved_task.id != task.id]


class FakeUnitOfWork:
    def __init__(self, tasks: InMemoryTaskRepository) -> None:
        self.tasks = tasks
        self.projects = object()
        self.workspaces = object()

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
    project_id = ProjectId.new()
    other_project_id = ProjectId.new()
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
        unit_of_work=FakeUnitOfWork(InMemoryTaskRepository(tasks)),
    )

    result = use_case.execute(
        ListTasksQuery(
            project_id=project_id,
            page=2,
            page_size=2,
        )
    )

    assert result.total == 3
    assert result.page == 2
    assert result.page_size == 2
    assert [item.title for item in result.items] == ["Third task"]