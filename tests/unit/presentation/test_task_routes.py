from datetime import UTC, datetime

from fastapi.testclient import TestClient

from application import (
    ListTasksItem,
    ListTasksQuery,
    ListTasksResult,
    TransitionTaskCommand,
    TransitionTaskResult,
)
from domain import InvalidTaskTransitionError, ProjectId, TaskId, TaskStatus, UserId
from presentation.dependencies import (
    get_list_tasks_use_case,
    get_transition_task_use_case,
)
from presentation.main import create_app


class StubListTasksUseCase:
    def __init__(self) -> None:
        self.query: ListTasksQuery | None = None

    def execute(self, query: ListTasksQuery) -> ListTasksResult:
        self.query = query
        created_at = datetime(2026, 4, 11, 15, 0, tzinfo=UTC)
        return ListTasksResult(
            items=(
                ListTasksItem(
                    id=TaskId.new(),
                    project_id=query.project_id,
                    title="Expose paginated tasks",
                    created_by=UserId.new(),
                    description=None,
                    status=TaskStatus.TODO,
                    priority=None,
                    due_date=None,
                    assigned_to=None,
                    created_at=created_at,
                    updated_at=created_at,
                ),
            ),
            total=1,
            page=query.page,
            page_size=query.page_size,
        )


class StubTransitionTaskUseCase:
    def __init__(
        self,
        *,
        result: TransitionTaskResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.command: TransitionTaskCommand | None = None
        self._result = result
        self._error = error

    def execute(self, command: TransitionTaskCommand) -> TransitionTaskResult:
        self.command = command
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise AssertionError("Transition task route test is missing a stub result.")
        return self._result


def test_list_tasks_route_returns_paginated_payload() -> None:
    stub_use_case = StubListTasksUseCase()
    project_id = ProjectId.new()
    app = create_app()
    app.dependency_overrides[get_list_tasks_use_case] = lambda: stub_use_case

    try:
        client = TestClient(app)
        response = client.get(
            "/v1/tasks",
            params={
                "project_id": str(project_id.value),
                "page": 2,
                "page_size": 10,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert stub_use_case.query is not None
    assert stub_use_case.query.project_id == project_id
    assert stub_use_case.query.page == 2
    assert stub_use_case.query.page_size == 10
    assert response.json()["total"] == 1


def test_list_tasks_route_rejects_page_size_above_limit() -> None:
    app = create_app()
    app.dependency_overrides[get_list_tasks_use_case] = lambda: StubListTasksUseCase()

    try:
        client = TestClient(app)
        response = client.get(
            "/v1/tasks",
            params={
                "project_id": str(ProjectId.new().value),
                "page_size": 101,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_transition_task_route_returns_updated_task() -> None:
    task_id = TaskId.new()
    project_id = ProjectId.new()
    updated_at = datetime(2026, 4, 11, 16, 30, tzinfo=UTC)
    stub_use_case = StubTransitionTaskUseCase(
        result=TransitionTaskResult(
            id=task_id,
            project_id=project_id,
            title="Move workflow forward",
            created_by=UserId.new(),
            description=None,
            status=TaskStatus.DOING,
            priority=None,
            due_date=None,
            assigned_to=None,
            created_at=updated_at,
            updated_at=updated_at,
        )
    )
    app = create_app()
    app.dependency_overrides[get_transition_task_use_case] = lambda: stub_use_case

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task_id.value}/transition",
            json={"status": "doing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert stub_use_case.command is not None
    assert stub_use_case.command.task_id == task_id
    assert stub_use_case.command.target_status is TaskStatus.DOING
    assert response.json()["status"] == "doing"


def test_transition_task_route_returns_conflict_for_invalid_transition() -> None:
    task_id = TaskId.new()
    stub_use_case = StubTransitionTaskUseCase(
        error=InvalidTaskTransitionError(
            current_status="done",
            target_status="doing",
        )
    )
    app = create_app()
    app.dependency_overrides[get_transition_task_use_case] = lambda: stub_use_case

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task_id.value}/transition",
            json={"status": "doing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "code": "INVALID_TRANSITION",
        "message": "Cannot transition task from 'done' to 'doing'.",
        "details": {
            "current_status": "done",
            "target_status": "doing",
        },
    }
