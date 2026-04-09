"""Domain-level error types."""


class DomainError(Exception):
    """Base type for domain-level exceptions."""


class InvalidTaskTransitionError(DomainError):
    """Raised when a task status transition violates the state machine."""

    def __init__(self, current_status: str, target_status: str) -> None:
        """Initialize the error with the current and target task statuses."""
        self.current_status = current_status
        self.target_status = target_status
        message = (
            f"Cannot transition task from '{current_status}' to '{target_status}'."
        )
        super().__init__(message)
