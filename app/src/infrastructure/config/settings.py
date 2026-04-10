"""This module contains the application settings loaded from environment variables."""

from functools import lru_cache
from typing import Self
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database settings
    database_url: str | None = Field(alias="DATABASE_URL", default=None)
    database_host: str | None = Field(alias="DATABASE_HOST", default=None)
    database_port: int | None = Field(alias="DATABASE_PORT", default=None)
    database_user: str | None = Field(alias="DATABASE_USER", default=None)
    database_password: str | None = Field(alias="DATABASE_PASSWORD", default=None)
    database_name: str | None = Field(alias="DATABASE_NAME", default=None)

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

    @model_validator(mode="after")
    def validate_database_configuration(self) -> Self:
        """Require either a full database URL or all discrete database fields."""
        if self.database_url:
            return self

        missing_fields: list[str] = []

        if not self.database_host:
            missing_fields.append("DATABASE_HOST")
        if self.database_port is None:
            missing_fields.append("DATABASE_PORT")
        if not self.database_user:
            missing_fields.append("DATABASE_USER")
        if self.database_password is None:
            missing_fields.append("DATABASE_PASSWORD")
        if not self.database_name:
            missing_fields.append("DATABASE_NAME")

        if missing_fields:
            joined_missing_fields = ", ".join(missing_fields)
            raise ValueError(
                "Provide DATABASE_URL or all discrete database settings. "
                f"Missing: {joined_missing_fields}."
            )

        return self

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return the SQLAlchemy-compatible database URL."""
        if self.database_url:
            return self.database_url

        if (
            self.database_host is None
            or self.database_port is None
            or self.database_user is None
            or self.database_password is None
            or self.database_name is None
        ):
            raise ValueError("Database settings are not fully configured.")

        encoded_user = quote_plus(self.database_user)
        encoded_password = quote_plus(self.database_password)
        return (
            "postgresql+psycopg://"
            f"{encoded_user}:{encoded_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
