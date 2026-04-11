"""Use case for transitioning a task status and recording an audit trail."""

from dataclasses import dataclass
from datetime import date, datetime

from application.ports import Clock, UnitOfWork
from application.use_cases._resource_access import get_accessible_task
from domain import ProjectId, Task, TaskEvent, TaskId, TaskStatus, UserId


@dataclass(frozen=True, slots=True)
class TransitionTaskCommand:
    """Input data required to transition a task status."""

    actor_id: UserId
    task_id: TaskId
    target_status: TaskStatus


@dataclass(frozen=True, slots=True)
class TransitionTaskResult:
    """Serialized task data returned by the transition task use case."""

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
    def from_task(cls, task: Task) -> "TransitionTaskResult":
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


class TransitionTaskUseCase:
    """Transition a task status following domain rules."""

    def __init__(self, *, unit_of_work: UnitOfWork, clock: Clock) -> None:
        """Store the dependencies required to execute the use case."""
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, command: TransitionTaskCommand) -> TransitionTaskResult:
        """Apply a valid task transition and persist its audit event."""
        transitioned_at = self._clock.now()

        with self._unit_of_work as unit_of_work:
            task = get_accessible_task(
                unit_of_work,
                task_id=command.task_id,
                actor_id=command.actor_id,
            )

            previous_status = task.status
            task.transition_to(command.target_status, occurred_at=transitioned_at)
            unit_of_work.tasks.add(task)
            unit_of_work.task_events.add(
                TaskEvent.status_transitioned(
                    task_id=task.id,
                    from_status=previous_status,
                    to_status=task.status,
                    created_at=transitioned_at,
                )
            )
            unit_of_work.commit()

        return TransitionTaskResult.from_task(task)
