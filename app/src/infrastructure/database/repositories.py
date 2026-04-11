"""SQLAlchemy repository adapters implementing application persistence ports."""

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from application import (
    ProjectRepository,
    TaskEventRepository,
    TaskRepository,
    WorkspaceRepository,
)
from domain import (
    Project,
    ProjectId,
    Task,
    TaskEvent,
    TaskEventId,
    TaskEventType,
    TaskId,
    TaskStatus,
    UserId,
    Workspace,
    WorkspaceId,
)
from infrastructure.database.models import (
    ProjectModel,
    TaskEventModel,
    TaskModel,
    WorkspaceModel,
)


def _to_workspace_model(workspace: Workspace) -> WorkspaceModel:
    return WorkspaceModel(
        id=workspace.id.value,
        name=workspace.name,
        owner_id=workspace.owner_id.value,
        description=workspace.description,
        created_at=workspace.created_at,
    )


def _to_workspace_domain(model: WorkspaceModel) -> Workspace:
    return Workspace(
        id=WorkspaceId(model.id),
        name=model.name,
        owner_id=UserId(model.owner_id),
        description=model.description,
        created_at=model.created_at,
    )


def _to_project_model(project: Project) -> ProjectModel:
    return ProjectModel(
        id=project.id.value,
        workspace_id=project.workspace_id.value,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


def _to_project_domain(model: ProjectModel) -> Project:
    return Project(
        id=ProjectId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        name=model.name,
        description=model.description,
        created_at=model.created_at,
    )


def _to_task_model(task: Task) -> TaskModel:
    return TaskModel(
        id=task.id.value,
        project_id=task.project_id.value,
        title=task.title,
        created_by=task.created_by.value,
        description=task.description,
        status=task.status.value,
        priority=task.priority,
        due_date=task.due_date,
        assigned_to=None if task.assigned_to is None else task.assigned_to.value,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_task_domain(model: TaskModel) -> Task:
    return Task(
        id=TaskId(model.id),
        project_id=ProjectId(model.project_id),
        title=model.title,
        created_by=UserId(model.created_by),
        description=model.description,
        status=TaskStatus(model.status),
        priority=model.priority,
        due_date=model.due_date,
        assigned_to=None if model.assigned_to is None else UserId(model.assigned_to),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_task_event_model(task_event: TaskEvent) -> TaskEventModel:
    return TaskEventModel(
        id=task_event.id.value,
        task_id=task_event.task_id.value,
        event_type=task_event.event_type.value,
        payload=task_event.payload,
        created_at=task_event.created_at,
    )


def _to_task_event_domain(model: TaskEventModel) -> TaskEvent:
    return TaskEvent(
        id=TaskEventId(model.id),
        task_id=TaskId(model.task_id),
        event_type=TaskEventType(model.event_type),
        payload=model.payload,
        created_at=model.created_at,
    )


class SqlAlchemyTaskRepository(TaskRepository):
    """SQLAlchemy-backed task repository."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to an active SQLAlchemy session."""
        self._session = session

    def add(self, task: Task) -> None:
        """Insert or update a task aggregate in the current session."""
        self._session.merge(_to_task_model(task))

    def get_by_id(self, task_id: TaskId) -> Task | None:
        """Load a task aggregate by identifier."""
        model = self._session.get(TaskModel, task_id.value)
        if model is None:
            return None
        return _to_task_domain(model)

    def list_by_project(
        self,
        project_id: ProjectId,
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> Sequence[Task]:
        """List task aggregates that belong to a project."""
        statement = (
            select(TaskModel)
            .where(TaskModel.project_id == project_id.value)
            .order_by(TaskModel.created_at, TaskModel.id)
        )

        if offset > 0:
            statement = statement.offset(offset)

        if limit is not None:
            statement = statement.limit(limit)

        models = self._session.scalars(statement).all()
        return [_to_task_domain(model) for model in models]

    def count_by_project(self, project_id: ProjectId) -> int:
        """Count task aggregates that belong to a project."""
        statement = (
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.project_id == project_id.value)
        )
        return self._session.execute(statement).scalar_one()

    def remove(self, task: Task) -> None:
        """Delete a task aggregate by identifier."""
        self._session.execute(delete(TaskModel).where(TaskModel.id == task.id.value))


class SqlAlchemyTaskEventRepository(TaskEventRepository):
    """SQLAlchemy-backed task event repository."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to an active SQLAlchemy session."""
        self._session = session

    def add(self, task_event: TaskEvent) -> None:
        """Insert a task event in the current session."""
        self._session.add(_to_task_event_model(task_event))

    def list_by_task(self, task_id: TaskId) -> Sequence[TaskEvent]:
        """List task audit events ordered by creation time."""
        statement = (
            select(TaskEventModel)
            .where(TaskEventModel.task_id == task_id.value)
            .order_by(TaskEventModel.created_at, TaskEventModel.id)
        )
        models = self._session.scalars(statement).all()
        return [_to_task_event_domain(model) for model in models]


class SqlAlchemyProjectRepository(ProjectRepository):
    """SQLAlchemy-backed project repository."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to an active SQLAlchemy session."""
        self._session = session

    def add(self, project: Project) -> None:
        """Insert or update a project aggregate in the current session."""
        self._session.merge(_to_project_model(project))

    def get_by_id(self, project_id: ProjectId) -> Project | None:
        """Load a project aggregate by identifier."""
        model = self._session.get(ProjectModel, project_id.value)
        if model is None:
            return None
        return _to_project_domain(model)

    def list_by_workspace(self, workspace_id: WorkspaceId) -> Sequence[Project]:
        """List project aggregates that belong to a workspace."""
        statement = (
            select(ProjectModel)
            .where(ProjectModel.workspace_id == workspace_id.value)
            .order_by(ProjectModel.created_at, ProjectModel.id)
        )
        models = self._session.scalars(statement).all()
        return [_to_project_domain(model) for model in models]

    def remove(self, project: Project) -> None:
        """Delete a project aggregate by identifier."""
        self._session.execute(
            delete(ProjectModel).where(ProjectModel.id == project.id.value)
        )


class SqlAlchemyWorkspaceRepository(WorkspaceRepository):
    """SQLAlchemy-backed workspace repository."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to an active SQLAlchemy session."""
        self._session = session

    def add(self, workspace: Workspace) -> None:
        """Insert or update a workspace aggregate in the current session."""
        self._session.merge(_to_workspace_model(workspace))

    def get_by_id(self, workspace_id: WorkspaceId) -> Workspace | None:
        """Load a workspace aggregate by identifier."""
        model = self._session.get(WorkspaceModel, workspace_id.value)
        if model is None:
            return None
        return _to_workspace_domain(model)

    def list_by_user(self, user_id: UserId) -> Sequence[Workspace]:
        """List workspaces visible to the provided owner identifier."""
        statement = (
            select(WorkspaceModel)
            .where(WorkspaceModel.owner_id == user_id.value)
            .order_by(WorkspaceModel.created_at, WorkspaceModel.id)
        )
        models = self._session.scalars(statement).all()
        return [_to_workspace_domain(model) for model in models]

    def remove(self, workspace: Workspace) -> None:
        """Delete a workspace aggregate by identifier."""
        self._session.execute(
            delete(WorkspaceModel).where(WorkspaceModel.id == workspace.id.value)
        )
