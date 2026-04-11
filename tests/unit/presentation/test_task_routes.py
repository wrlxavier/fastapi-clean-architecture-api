from datetime import UTC, datetime

from fastapi.testclient import TestClient

from application import ListTasksItem, ListTasksQuery, ListTasksResult
from domain import ProjectId, TaskId, TaskStatus, UserId
from presentation.dependencies import get_list_tasks_use_case
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