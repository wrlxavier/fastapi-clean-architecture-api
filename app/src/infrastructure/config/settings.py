"""This module contains the application settings loaded from environment variables."""

from functools import lru_cache
from pydantic import Field
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
    database_host: str = Field(alias="DATABASE_HOST")
    database_port: int = Field(alias="DATABASE_PORT")
    database_user: str = Field(alias="DATABASE_USER")
    database_password: str = Field(alias="DATABASE_PASSWORD")
    database_name: str = Field(alias="DATABASE_NAME")

    # Authentication settings
    jwt_secret: str = Field(alias="JWT_SECRET", min_length=16)
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM", default="HS256")
    access_token_ttl_in_seconds: int = Field(alias="ACCESS_TOKEN_TTL_IN_SECONDS", gt=0)
    refresh_token_ttl_in_seconds: int = Field(alias="REFRESH_TOKEN_TTL_IN_SECONDS", gt=0)

    # Logging and pagination
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    pagination_limits: str = Field(alias="PAGINATION_LIMITS", default="1, 100")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
