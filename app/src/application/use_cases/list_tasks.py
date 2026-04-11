"""Use case for listing tasks with safe pagination."""

from dataclasses import dataclass
from datetime import date, datetime

from application.ports import UnitOfWork
from domain import ProjectId, Task, TaskId, TaskStatus, UserId


@dataclass(frozen=True, slots=True)
class ListTasksQuery:
    """Input data required to list tasks for a project."""

    project_id: ProjectId
    page: int = 1
    page_size: int = 50

    @property
    def offset(self) -> int:
        """Return the row offset derived from the requested page."""
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class ListTasksItem:
    """Serialized task data returned inside a paginated list."""

    id: TaskId
    project_id: ProjectId
    title: str
    created_by: UserId
    description: str | None
    status: TaskStatus
    priority: str | None
    due_date: date | None
    assigned_to: UserId | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: Task) -> "ListTasksItem":
        """Build a paginated item from a domain task entity."""
        return cls(
            id=task.id,
            project_id=task.project_id,
            title=task.title,
            created_by=task.created_by,
            description=task.description,
            status=task.status,
            priority=task.priority,
            due_date=task.due_date,
            assigned_to=task.assigned_to,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


@dataclass(frozen=True, slots=True)
class ListTasksResult:
    """Paginated task collection returned by the use case."""

    items: tuple[ListTasksItem, ...]
    total: int
    page: int
    page_size: int


class ListTasksUseCase:
    """List tasks for a project using bounded pagination."""

    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        """Store the dependencies required to execute the use case."""
        self._unit_of_work = unit_of_work

    def execute(self, query: ListTasksQuery) -> ListTasksResult:
        """Load a page of tasks and the total number of matching records."""
        with self._unit_of_work as unit_of_work:
            total = unit_of_work.tasks.count_by_project(query.project_id)
            tasks = unit_of_work.tasks.list_by_project(
                query.project_id,
                offset=query.offset,
                limit=query.page_size,
            )

        return ListTasksResult(
            items=tuple(ListTasksItem.from_task(task) for task in tasks),
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
