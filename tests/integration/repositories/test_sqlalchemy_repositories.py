from collections.abc import Iterator
from os import getenv

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from domain import Project, ProjectId, Task, TaskId, UserId, Workspace, WorkspaceId
from infrastructure import Base, SqlAlchemyUnitOfWork, create_engine_from_database_url
from infrastructure.database.session import create_session_factory


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    database_url = getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")
    return database_url


@pytest.fixture(scope="session")
def postgres_engine(postgres_database_url: str) -> Iterator[Engine]:
    engine = create_engine_from_database_url(postgres_database_url)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def reset_database_schema(postgres_engine: Engine) -> Iterator[None]:
    Base.metadata.drop_all(postgres_engine, checkfirst=True)
    Base.metadata.create_all(postgres_engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(postgres_engine, checkfirst=True)


@pytest.fixture
def session_factory(postgres_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine=postgres_engine)


def test_sqlalchemy_repositories_persist_and_load_aggregates(
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
        description="Vertical slice for repository integration",
    )
    task = Task(
        id=TaskId.new(),
        project_id=project.id,
        title="Persist aggregates with SQLAlchemy",
        created_by=owner_id,
        assigned_to=owner_id,
        priority="high",
    )

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.workspaces.add(workspace)
        unit_of_work.projects.add(project)
        unit_of_work.tasks.add(task)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        loaded_workspace = unit_of_work.workspaces.get_by_id(workspace.id)
        loaded_project = unit_of_work.projects.get_by_id(project.id)
        loaded_task = unit_of_work.tasks.get_by_id(task.id)

        assert loaded_workspace == workspace
        assert loaded_project == project
        assert loaded_task == task
        assert unit_of_work.workspaces.list_by_user(owner_id) == [workspace]
        assert unit_of_work.projects.list_by_workspace(workspace.id) == [project]
        assert unit_of_work.tasks.list_by_project(project.id) == [task]

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.tasks.remove(task)
        unit_of_work.projects.remove(project)
        unit_of_work.workspaces.remove(workspace)
        unit_of_work.commit()

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.tasks.get_by_id(task.id) is None
        assert unit_of_work.projects.get_by_id(project.id) is None
        assert unit_of_work.workspaces.get_by_id(workspace.id) is None
