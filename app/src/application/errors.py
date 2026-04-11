"""Application-level error types."""

from domain import ProjectId


class ApplicationError(Exception):
    """Base type for application-layer exceptions."""


class ProjectNotFoundError(ApplicationError):
    """Raised when a use case references a project that does not exist."""

    def __init__(self, project_id: ProjectId) -> None:
        """Store the missing project identifier for outer layers."""
        self.project_id = project_id
        super().__init__(f"Project '{project_id.value}' was not found.")