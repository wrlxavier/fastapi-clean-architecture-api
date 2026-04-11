"""Use case for creating tasks."""

from dataclasses import dataclass
from datetime import date, datetime

from application.errors import ProjectNotFoundError
from application.ports import Clock, UnitOfWork
from domain import ProjectId, Task, TaskId, TaskStatus, UserId


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    """Input data required to create a new task."""

    project_id: ProjectId
    title: str
    created_by: UserId
    description: str | None = None
    priority: str | None = None
    due_date: date | None = None
    assigned_to: UserId | None = None


@dataclass(frozen=True, slots=True)
class CreateTaskResult:
    """Serialized task data returned by the create task use case."""

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
    def from_task(cls, task: Task) -> "CreateTaskResult":
        """Build the use case result from a persisted task entity."""
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


class CreateTaskUseCase:
    """Create a task inside an existing project."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock: Clock) -> None:
        """Store the dependencies required to execute the use case."""
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, command: CreateTaskCommand) -> CreateTaskResult:
        """Create and persist a task for the requested project."""
        created_at = self._clock.now()

        with self._unit_of_work as unit_of_work:
            if unit_of_work.projects.get_by_id(command.project_id) is None:
                raise ProjectNotFoundError(command.project_id)

            task = Task(
                id=TaskId.new(),
                project_id=command.project_id,
                title=command.title,
                created_by=command.created_by,
                description=_normalize_optional_text(command.description),
                priority=_normalize_optional_text(command.priority),
                due_date=command.due_date,
                assigned_to=command.assigned_to,
                created_at=created_at,
                updated_at=created_at,
            )
            unit_of_work.tasks.add(task)
            unit_of_work.commit()

        return CreateTaskResult.from_task(task)
