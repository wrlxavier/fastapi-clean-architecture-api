"""This module contains the application settings loaded from environment variables."""

from functools import lru_cache
from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class ObservabilitySettings(BaseSettings):
    """Settings used by runtime observability and logging concerns."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = Field(alias="APP_ENV", default="development")
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")

    @property
    def is_development(self) -> bool:
        """Return whether the current runtime should emit dev diagnostics."""
        return self.app_env.lower() in {"dev", "development", "local"}


def build_sqlalchemy_database_url(
    *,
    database_url: str | None,
    database_host: str | None,
    database_port: int | None,
    database_user: str | None,
    database_password: str | None,
    database_name: str | None,
) -> str:
    """Build a SQLAlchemy database URL from full or discrete database settings."""
    if database_url:
        return database_url

    missing_fields: list[str] = []

    if not database_host:
        missing_fields.append("DATABASE_HOST")
    if database_port is None:
        missing_fields.append("DATABASE_PORT")
    if not database_user:
        missing_fields.append("DATABASE_USER")
    if database_password is None:
        missing_fields.append("DATABASE_PASSWORD")
    if not database_name:
        missing_fields.append("DATABASE_NAME")

    if missing_fields:
        joined_missing_fields = ", ".join(missing_fields)
        raise ValueError(
            "Provide DATABASE_URL or all discrete database settings. "
            f"Missing: {joined_missing_fields}."
        )

    assert database_host is not None
    assert database_port is not None
    assert database_user is not None
    assert database_password is not None
    assert database_name is not None

    encoded_user = quote_plus(database_user)
    encoded_password = quote_plus(database_password)
    return (
        "postgresql+psycopg://"
        f"{encoded_user}:{encoded_password}@"
        f"{database_host}:{database_port}/{database_name}"
    )


class DatabaseSettings(BaseSettings):
    """Database-only settings for tooling that should not require app secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Database settings
    database_url: str | None = Field(alias="DATABASE_URL", default=None)
    database_host: str | None = Field(alias="DATABASE_HOST", default=None)
    database_port: int | None = Field(alias="DATABASE_PORT", default=None)
    database_user: str | None = Field(alias="DATABASE_USER", default=None)
    database_password: str | None = Field(alias="DATABASE_PASSWORD", default=None)
    database_name: str | None = Field(alias="DATABASE_NAME", default=None)

    @model_validator(mode="after")
    def validate_database_configuration(self) -> Self:
        """Require either a full database URL or all discrete database fields."""
        build_sqlalchemy_database_url(
            database_url=self.database_url,
            database_host=self.database_host,
            database_port=self.database_port,
            database_user=self.database_user,
            database_password=self.database_password,
            database_name=self.database_name,
        )
        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return the SQLAlchemy-compatible database URL."""
        return build_sqlalchemy_database_url(
            database_url=self.database_url,
            database_host=self.database_host,
            database_port=self.database_port,
            database_user=self.database_user,
            database_password=self.database_password,
            database_name=self.database_name,
        )


class Settings(DatabaseSettings):
    """Application settings loaded from environment variables."""

    # Authentication settings
    jwt_secret: str = Field(alias="JWT_SECRET", min_length=16)
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM", default="HS256")
    access_token_ttl_in_seconds: int = Field(alias="ACCESS_TOKEN_TTL_IN_SECONDS", gt=0)
    refresh_token_ttl_in_seconds: int = Field(
        alias="REFRESH_TOKEN_TTL_IN_SECONDS", gt=0
    )

    # Logging and pagination
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    pagination_limits: str = Field(alias="PAGINATION_LIMITS", default="1, 100")


@lru_cache
def get_observability_settings() -> ObservabilitySettings:
    """Get cached runtime settings used by logging and diagnostics."""
    return ObservabilitySettings()


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
