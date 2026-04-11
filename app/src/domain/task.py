"""Task domain entity and workflow invariants."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Final

from domain.errors import InvalidTaskTransitionError
from domain.identifiers import ProjectId, TaskId, UserId


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_non_empty_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized_value


class TaskStatus(StrEnum):
    """Supported statuses in the task lifecycle."""

    TODO = "todo"
    DOING = "doing"
    DONE = "done"


_ALLOWED_TASK_STATUS_TRANSITIONS: Final[dict[TaskStatus, frozenset[TaskStatus]]] = {
    TaskStatus.TODO: frozenset({TaskStatus.DOING, TaskStatus.DONE}),
    TaskStatus.DOING: frozenset({TaskStatus.DONE}),
    TaskStatus.DONE: frozenset(),
}


@dataclass(slots=True)
class Task:
    """Task entity with workflow state enforced in the domain layer."""

    id: TaskId
    project_id: ProjectId
    title: str
    created_by: UserId
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: str | None = None
    due_date: date | None = None
    assigned_to: UserId | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Validate required task fields after initialization."""
        self.title = _require_non_empty_text(self.title, "task title")

    def can_transition_to(self, target_status: TaskStatus) -> bool:
        """Return whether the task can move to the target status."""
        return target_status in _ALLOWED_TASK_STATUS_TRANSITIONS[self.status]

    def transition_to(
        self,
        target_status: TaskStatus,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        """Transition the task to a new status when the state machine allows it."""
        if not self.can_transition_to(target_status):
            raise InvalidTaskTransitionError(
                current_status=self.status.value,
                target_status=target_status.value,
            )

        self.status = target_status
        self.updated_at = occurred_at if occurred_at is not None else _utc_now()

    def assign_to_user(
        self,
        assignee_id: UserId,
        *,
        occurred_at: datetime | None = None,
    ) -> None:
        """Assign the task to a user and refresh its update timestamp."""
        self.assigned_to = assignee_id
        self.updated_at = occurred_at if occurred_at is not None else _utc_now()
