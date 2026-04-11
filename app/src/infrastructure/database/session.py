"""SQLAlchemy engine and session factory helpers."""

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.config.settings import Settings, get_settings


def create_engine_from_database_url(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the provided database URL."""
    return create_engine(database_url, pool_pre_ping=True)


def create_engine_from_settings(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine from application settings."""
    resolved_settings = settings if settings is not None else get_settings()
    return create_engine_from_database_url(resolved_settings.sqlalchemy_database_url)


def create_session_factory(
    *,
    engine: Engine | None = None,
    settings: Settings | None = None,
) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory."""
    bound_engine = (
        engine if engine is not None else create_engine_from_settings(settings)
    )
    return sessionmaker(bind=bound_engine, autoflush=False, expire_on_commit=False)


def is_database_reachable(session_factory: sessionmaker[Session]) -> bool:
    """Return whether the database can be reached with a lightweight query."""
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
