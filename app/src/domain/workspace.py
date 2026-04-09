"""Workspace domain entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from domain.identifiers import UserId, WorkspaceId


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_non_empty_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized_value


@dataclass(slots=True)
class Workspace:
    """Collaboration boundary that owns projects and members."""

    id: WorkspaceId
    name: str
    owner_id: UserId
    description: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        """Validate required workspace fields after initialization."""
        self.name = _require_non_empty_text(self.name, "workspace name")
