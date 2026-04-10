"""Concrete SQLAlchemy unit of work implementation."""

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from infrastructure.database.repositories import (
    SqlAlchemyProjectRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyWorkspaceRepository,
)


class SqlAlchemyUnitOfWork:
    """Coordinate repository adapters within a transactional session."""

    tasks: SqlAlchemyTaskRepository
    projects: SqlAlchemyProjectRepository
    workspaces: SqlAlchemyWorkspaceRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Store the factory used to open transactional SQLAlchemy sessions."""
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        """Open a SQLAlchemy session and bind repositories to it."""
        if self._session is not None:
            raise RuntimeError("Unit of work is already active.")

        self._session = self._session_factory()
        self.tasks = SqlAlchemyTaskRepository(self._session)
        self.projects = SqlAlchemyProjectRepository(self._session)
        self.workspaces = SqlAlchemyWorkspaceRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Rollback any open transaction and close the session."""
        del exc_type, exc, traceback

        if self._session is None:
            return None

        if self._session.in_transaction():
            self._session.rollback()

        self._session.close()
        self._session = None
        return None

    def commit(self) -> None:
        """Persist pending changes in the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Discard pending changes in the current transaction."""
        self.session.rollback()

    @property
    def session(self) -> Session:
        """Return the active SQLAlchemy session."""
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._session
