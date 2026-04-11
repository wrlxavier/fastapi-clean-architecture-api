"""Task event entities used for audit trails."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from domain.identifiers import TaskEventId, TaskId
from domain.task import TaskStatus


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TaskEventType(StrEnum):
    """Supported task event categories."""

    STATUS_TRANSITIONED = "status_transitioned"


@dataclass(frozen=True, slots=True)
class TaskEvent:
    """Immutable audit record for significant task changes."""

    id: TaskEventId
    task_id: TaskId
    event_type: TaskEventType
    payload: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)

    @classmethod
    def status_transitioned(
        cls,
        *,
        task_id: TaskId,
        from_status: TaskStatus,
        to_status: TaskStatus,
        created_at: datetime,
    ) -> "TaskEvent":
        """Build an audit event for a task status transition."""
        return cls(
            id=TaskEventId.new(),
            task_id=task_id,
            event_type=TaskEventType.STATUS_TRANSITIONED,
            payload={
                "from_status": from_status.value,
                "to_status": to_status.value,
            },
            created_at=created_at,
        )
