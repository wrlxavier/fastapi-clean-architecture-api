from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from domain import Project, TaskId, UserId, Workspace, WorkspaceId
from domain.identifiers import ProjectId
from infrastructure import SqlAlchemyUnitOfWork
from presentation.dependencies import get_session_factory
from presentation.main import create_app


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
            json={
                "project_id": str(project.id.value),
                "title": "  Ship create-task vertical slice  ",
                "created_by": str(owner_id.value),
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