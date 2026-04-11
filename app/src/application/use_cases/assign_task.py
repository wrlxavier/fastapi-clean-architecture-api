"""Use case for assigning a task and recording an audit trail."""

from dataclasses import dataclass
from datetime import date, datetime

from application.ports import Clock, UnitOfWork
from application.use_cases._resource_access import get_accessible_task
from domain import ProjectId, Task, TaskEvent, TaskId, TaskStatus, UserId


@dataclass(frozen=True, slots=True)
class AssignTaskCommand:
    """Input data required to assign a task to a user."""

    actor_id: UserId
    task_id: TaskId
    user_id: UserId


@dataclass(frozen=True, slots=True)
class AssignTaskResult:
    """Serialized task data returned by the assign task use case."""

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
    def from_task(cls, task: Task) -> "AssignTaskResult":
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


class AssignTaskUseCase:
    """Assign a task to a user and persist its audit event."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock: Clock) -> None:
        """Store the dependencies required to execute the use case."""
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, command: AssignTaskCommand) -> AssignTaskResult:
        """Apply the assignment change and persist its audit event."""
        assigned_at = self._clock.now()

        with self._unit_of_work as unit_of_work:
            task = get_accessible_task(
                unit_of_work,
                task_id=command.task_id,
                actor_id=command.actor_id,
            )

            previous_assignee = task.assigned_to
            task.assign_to_user(command.user_id, occurred_at=assigned_at)
            unit_of_work.tasks.add(task)
            unit_of_work.task_events.add(
                TaskEvent.assigned(
                    task_id=task.id,
                    assigned_to=command.user_id,
                    previous_assigned_to=previous_assignee,
                    created_at=assigned_at,
                )
            )
            unit_of_work.commit()

        return AssignTaskResult.from_task(task)
