from datetime import UTC, datetime

import pytest

from domain import (
    InvalidTaskTransitionError,
    ProjectId,
    Task,
    TaskId,
    TaskStatus,
    UserId,
)


def build_task(
    *,
    status: TaskStatus = TaskStatus.TODO,
    title: str = "Implement domain invariants",
) -> Task:
    return Task(
        id=TaskId.new(),
        project_id=ProjectId.new(),
        title=title,
        created_by=UserId.new(),
        status=status,
    )


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (TaskStatus.TODO, TaskStatus.DOING),
        (TaskStatus.TODO, TaskStatus.DONE),
        (TaskStatus.DOING, TaskStatus.DONE),
    ],
)
def test_task_allows_valid_status_transitions(
    current_status: TaskStatus,
    target_status: TaskStatus,
) -> None:
    task = build_task(status=current_status)
    transitioned_at = datetime(2026, 4, 9, 12, 0, tzinfo=UTC)

    task.transition_to(target_status, occurred_at=transitioned_at)

    assert task.status is target_status
    assert task.updated_at == transitioned_at


@pytest.mark.parametrize(
    ("current_status", "target_status"),
    [
        (TaskStatus.DOING, TaskStatus.TODO),
        (TaskStatus.TODO, TaskStatus.TODO),
        (TaskStatus.DONE, TaskStatus.DOING),
    ],
)
def test_task_rejects_invalid_status_transitions(
    current_status: TaskStatus,
    target_status: TaskStatus,
) -> None:
    task = build_task(status=current_status)
    previous_updated_at = task.updated_at

    with pytest.raises(InvalidTaskTransitionError) as caught_error:
        task.transition_to(target_status)

    assert caught_error.value.current_status == current_status.value
    assert caught_error.value.target_status == target_status.value
    assert task.status is current_status
    assert task.updated_at == previous_updated_at


def test_task_requires_non_empty_title() -> None:
    with pytest.raises(ValueError, match="task title must not be empty"):
        build_task(title="   ")


def test_task_assignment_updates_assignee_and_timestamp() -> None:
    task = build_task()
    assigned_at = datetime(2026, 4, 11, 17, 0, tzinfo=UTC)
    assignee_id = UserId.new()

    task.assign_to_user(assignee_id, occurred_at=assigned_at)

    assert task.assigned_to == assignee_id
    assert task.updated_at == assigned_at
