"""Shared dependency wiring for FastAPI routes."""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from application import (
    AssignTaskUseCase,
    CreateTaskUseCase,
    ListTasksUseCase,
    TransitionTaskUseCase,
)
from domain import UserId
from infrastructure import (
    SqlAlchemyUnitOfWork,
    create_session_factory,
    is_database_reachable,
)

USER_ID_HEADER = "X-User-ID"


class SystemClock:
    """Clock implementation backed by the system UTC time."""

    def now(self) -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(UTC)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Build and cache the session factory used by request handlers."""
    return create_session_factory()


SessionFactoryDependency = Annotated[
    sessionmaker[Session],
    Depends(get_session_factory),
]


def get_database_readiness(session_factory: SessionFactoryDependency) -> bool:
    """Check whether the configured database dependency is reachable."""
    return is_database_reachable(session_factory)


DatabaseReadinessDependency = Annotated[
    bool,
    Depends(get_database_readiness),
]


def get_current_user_id(
    x_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
) -> UserId:
    """Resolve the authenticated principal for task routes.

    The project will eventually source this identity from bearer tokens, but the
    current task slice accepts a user UUID header so authorization can be enforced
    consistently before the JWT workflow is implemented.
    """
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {USER_ID_HEADER} header.",
        )

    try:
        return UserId(UUID(x_user_id))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid {USER_ID_HEADER} header.",
        ) from error


def get_create_task_use_case(
    session_factory: SessionFactoryDependency,
) -> CreateTaskUseCase:
    """Provide the create task use case with runtime infrastructure wiring."""
    return CreateTaskUseCase(
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        clock=SystemClock(),
    )


def get_list_tasks_use_case(
    session_factory: SessionFactoryDependency,
) -> ListTasksUseCase:
    """Provide the list tasks use case with runtime infrastructure wiring."""
    return ListTasksUseCase(unit_of_work=SqlAlchemyUnitOfWork(session_factory))


def get_transition_task_use_case(
    session_factory: SessionFactoryDependency,
) -> TransitionTaskUseCase:
    """Provide the transition task use case with runtime infrastructure wiring."""
    return TransitionTaskUseCase(
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        clock=SystemClock(),
    )


def get_assign_task_use_case(
    session_factory: SessionFactoryDependency,
) -> AssignTaskUseCase:
    """Provide the assign task use case with runtime infrastructure wiring."""
    return AssignTaskUseCase(
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        clock=SystemClock(),
    )
