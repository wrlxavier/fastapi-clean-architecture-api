"""Shared dependency wiring for FastAPI routes."""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from application import CreateTaskUseCase
from infrastructure import SqlAlchemyUnitOfWork, create_session_factory


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


def get_create_task_use_case(
    session_factory: SessionFactoryDependency,
) -> CreateTaskUseCase:
    """Provide the create task use case with runtime infrastructure wiring."""
    return CreateTaskUseCase(
        unit_of_work=SqlAlchemyUnitOfWork(session_factory),
        clock=SystemClock(),
    )