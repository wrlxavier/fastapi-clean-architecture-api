"""Time-related ports for the application layer."""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Provides the current time to use cases."""

    def now(self) -> datetime:
        """Return the current datetime."""
