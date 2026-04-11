from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from domain import (
    Project,
    Task,
    TaskEventType,
    TaskId,
    TaskStatus,
    UserId,
    Workspace,
    WorkspaceId,
)
from domain.identifiers import ProjectId
from infrastructure import SqlAlchemyUnitOfWork
from presentation.dependencies import USER_ID_HEADER, get_session_factory
from presentation.main import create_app


def auth_headers(user_id: UserId) -> dict[str, str]:
    return {USER_ID_HEADER: str(user_id.value)}


def test_create_task_endpoint_persists_task_in_postgres(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
        description="Primary workspace for API delivery",
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
        description="Vertical slice for create task integration",
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/tasks",
            headers=auth_headers(owner_id),
            json={
                "project_id": str(project.id.value),
                "title": "  Ship create-task vertical slice  ",
                "description": "  Persist tasks through the API  ",
                "priority": "  high  ",
                "assigned_to": str(owner_id.value),
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201

    payload = response.json()
    assert payload["project_id"] == str(project.id.value)
    assert payload["title"] == "Ship create-task vertical slice"
    assert payload["description"] == "Persist tasks through the API"
    assert payload["priority"] == "high"
    assert payload["status"] == "todo"
    assert payload["created_by"] == str(owner_id.value)
    assert payload["assigned_to"] == str(owner_id.value)

    task_id = TaskId(UUID(payload["id"]))

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task_id)

    assert saved_task is not None
    assert saved_task.project_id == project.id
    assert saved_task.title == "Ship create-task vertical slice"
    assert saved_task.description == "Persist tasks through the API"
    assert saved_task.priority == "high"
    assert saved_task.created_by == owner_id
    assert saved_task.assigned_to == owner_id


def test_list_tasks_endpoint_returns_paginated_tasks(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
    )
    other_project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Ignored Project",
    )
    created_at = datetime(2026, 4, 11, 14, 0, tzinfo=UTC)
    tasks = [
        Task(
            id=TaskId.new(),
            project_id=project.id,
            title="Define pagination contract",
            created_by=owner_id,
            created_at=created_at,
            updated_at=created_at,
        ),
        Task(
            id=TaskId.new(),
            project_id=project.id,
            title="Implement repository paging",
            created_by=owner_id,
            created_at=created_at.replace(minute=1),
            updated_at=created_at.replace(minute=1),
        ),
        Task(
            id=TaskId.new(),
            project_id=project.id,
            title="Expose GET /v1/tasks",
            created_by=owner_id,
            created_at=created_at.replace(minute=2),
            updated_at=created_at.replace(minute=2),
        ),
        Task(
            id=TaskId.new(),
            project_id=other_project.id,
            title="Ignore other project tasks",
            created_by=owner_id,
            created_at=created_at.replace(minute=3),
            updated_at=created_at.replace(minute=3),
        ),
    ]

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.projects.add(other_project)
        for task in tasks:
            unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.get(
            "/v1/tasks",
            headers=auth_headers(owner_id),
            params={
                "project_id": str(project.id.value),
                "page": 2,
                "page_size": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 2
    assert payload["page_size"] == 2
    assert [item["title"] for item in payload["items"]] == ["Expose GET /v1/tasks"]


def test_list_tasks_endpoint_rejects_page_size_above_limit(
    session_factory: sessionmaker[Session],
) -> None:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.get(
            "/v1/tasks",
            headers=auth_headers(UserId.new()),
            params={
                "project_id": str(ProjectId.new().value),
                "page_size": 101,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_transition_task_endpoint_updates_status_and_records_event(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Implement transition endpoint",
        created_by=owner_id,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task.id.value}/transition",
            headers=auth_headers(owner_id),
            json={"status": "doing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "doing"

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task.id)
        task_events = unit_of_work.task_events.list_by_task(task.id)

    assert saved_task is not None
    assert saved_task.status is TaskStatus.DOING
    assert len(task_events) == 1
    assert task_events[0].event_type is TaskEventType.STATUS_TRANSITIONED
    assert task_events[0].payload == {
        "from_status": "todo",
        "to_status": "doing",
    }


def test_assign_task_endpoint_updates_assignee_and_records_event(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    assignee_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Implement assign endpoint",
        created_by=owner_id,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task.id.value}/assign",
            headers=auth_headers(owner_id),
            json={"user_id": str(assignee_id.value)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["assigned_to"] == str(assignee_id.value)

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task.id)
        task_events = unit_of_work.task_events.list_by_task(task.id)

    assert saved_task is not None
    assert saved_task.assigned_to == assignee_id
    assert len(task_events) == 1
    assert task_events[0].event_type is TaskEventType.ASSIGNED
    assert task_events[0].payload == {
        "assigned_to": str(assignee_id.value),
    }


def test_transition_task_endpoint_returns_conflict_for_invalid_transition(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Task API",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Already finished task",
        created_by=owner_id,
        status=TaskStatus.DONE,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task.id.value}/transition",
            headers=auth_headers(owner_id),
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

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task.id)
        task_events = unit_of_work.task_events.list_by_task(task.id)

    assert saved_task is not None
    assert saved_task.status is TaskStatus.DONE
    assert task_events == []


def test_create_task_endpoint_returns_not_found_for_foreign_project(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Protected Project",
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/tasks",
            headers=auth_headers(outsider_id),
            json={
                "project_id": str(project.id.value),
                "title": "Unauthorized task creation",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Project '{project.id.value}' was not found.",
    }

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.tasks.list_by_project(project.id) == []


def test_list_tasks_endpoint_returns_not_found_for_foreign_project(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Protected Project",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Owner-only task",
        created_by=owner_id,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.get(
            "/v1/tasks",
            headers=auth_headers(outsider_id),
            params={"project_id": str(project.id.value)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Project '{project.id.value}' was not found.",
    }


def test_transition_task_endpoint_returns_not_found_for_foreign_task(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Protected Project",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Transition-protected task",
        created_by=owner_id,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task.id.value}/transition",
            headers=auth_headers(outsider_id),
            json={"status": "doing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Task '{task.id.value}' was not found.",
    }

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task.id)
        task_events = unit_of_work.task_events.list_by_task(task.id)

    assert saved_task is not None
    assert saved_task.status is TaskStatus.TODO
    assert task_events == []


def test_assign_task_endpoint_returns_not_found_for_foreign_task(
    session_factory: sessionmaker[Session],
) -> None:
    owner_id = UserId.new()
    outsider_id = UserId.new()
    assignee_id = UserId.new()
    workspace = Workspace(
        id=WorkspaceId.new(),
        name="Platform Engineering",
        owner_id=owner_id,
    )
    project = Project(
        id=ProjectId.new(),
        workspace_id=workspace.id,
        name="Protected Project",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Assign-protected task",
        created_by=owner_id,
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: session_factory

    try:
        client = TestClient(app)
        response = client.post(
            f"/v1/tasks/{task.id.value}/assign",
            headers=auth_headers(outsider_id),
            json={"user_id": str(assignee_id.value)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Task '{task.id.value}' was not found.",
    }

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        saved_task = unit_of_work.tasks.get_by_id(task.id)
        task_events = unit_of_work.task_events.list_by_task(task.id)

    assert saved_task is not None
    assert saved_task.assigned_to is None
    assert task_events == []
