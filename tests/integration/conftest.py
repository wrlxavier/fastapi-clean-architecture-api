from collections.abc import Iterator
from os import getenv

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure import Base, create_engine_from_database_url
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